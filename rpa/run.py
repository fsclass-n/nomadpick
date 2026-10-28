"""RPA 실행 진입점.

    python -m rpa.run deals            # BOT-01 특가 수집 → 정제 → 적재
    python -m rpa.run public           # BOT-02 국토교통부 국내항공운항정보
    python -m rpa.run report           # BOT-03 일일 엑셀 리포트
    python -m rpa.run all              # 전체 (sample 모드 + 빈 DB 이면 시연용 가격 이력 14일 생성)
    옵션: --mode live|sample|auto  --sink direct|api
"""
import argparse
import asyncio
import gc
import logging
import threading
import time
from datetime import datetime, timedelta

from backend.app.config import settings
from backend.app.constants import CITY_AIRPORT, HOME_AIRPORT_ID
from backend.app.utils import now_kst

from .cleaner.normalize import clean
from .collector.agencies import COLLECTORS
from .collector.browser import HumanBrowser
from .public_data import molit_flight
from .report.daily_report import build_report
from .sink import domestic_departures, get_sink

log = logging.getLogger("rpa")
_lock = threading.Lock()
PARSE_FAIL_THRESHOLD = 20.0  # 파싱 실패율 20% 초과 시 경고


async def _collect_live_async() -> dict | None:
    """Playwright(Async) 브라우저 1개로 여행사 3곳을 차례로 수집. 여행사마다 컨텍스트를 열고 닫으며, 브라우저는 반드시 종료."""
    try:
        browser = await HumanBrowser().__aenter__()
    except Exception as e:  # 브라우저 미설치·메모리 부족 등 → auto 모드는 sample 로 대체
        log.error("Playwright 브라우저 시작 실패: %s", e)
        return None
    results = {}
    try:
        for cls in COLLECTORS:
            collector = cls()
            try:
                results[collector.agency] = await collector.collect_live(browser)
            except Exception as e:
                log.exception("[%s] live 수집 실패", collector.agency)
                from .collector.base import CollectResult
                results[collector.agency] = CollectResult(agency=collector.agency, messages=[f"live 수집 실패: {str(e)[:200]}"])
            gc.collect()
    finally:
        await browser.__aexit__(None, None, None)
    return results


def collect_live_all(mode: str) -> dict | None:
    """동기 코드(스케줄러 스레드·BackgroundTasks)에서 호출. 이미 이벤트 루프가 도는 스레드라면 별도 스레드에서 실행."""
    if mode not in ("live", "auto"):
        return None
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_collect_live_async())
    box = {}
    t = threading.Thread(target=lambda: box.update(r=asyncio.run(_collect_live_async())))
    t.start()
    t.join()
    return box.get("r")


def run_deals(sink, mode: str | None = None, at: datetime | None = None, write_log: bool = True) -> dict:
    """BOT-01: 여행사 3곳 특가 수집(Playwright Async) → pandas 정제 → upsert + 가격 스냅샷 → 로그."""
    at = at or now_kst()
    mode = mode or settings.rpa_source_mode
    return _run_deals(sink, mode, at, write_log, collect_live_all(mode))


def _run_deals(sink, mode: str, at: datetime, write_log: bool, live: dict | None) -> dict:
    totals = {}
    for cls in COLLECTORS:
        started = now_kst()
        collector = cls()
        try:
            result = collector.collect(at, mode, (live or {}).get(collector.agency))
            if mode == "auto" and result.source == "sample" and sink.has_live(collector.agency):
                # live 실패 시 이미 적재된 실데이터를 sample 로 덮어쓰지 않는다(기존 live 상품 유지)
                if write_log:
                    sink.log({"job_name": "BOT-01", "agency_code": collector.agency, "status": "WARN", "source": "live",
                              "collected": 0, "failed": 0, "retries": result.retries,
                              "message": " / ".join(result.messages[:3] + ["live 실패 - 기존 live 데이터 유지(sample 미적재)"]),
                              "started_at": started, "ended_at": now_kst()})
                totals[collector.agency] = {"collected": 0, "failed": 0, "source": "live-kept"}
                continue
            items, failed, _ = clean(result.raw, at.date())
            res = sink.products_bulk(collector.agency, at, result.source, items) if items else {"inserted": 0, "updated": 0}
            fail_rate = failed / (len(items) + failed) * 100 if (items or failed) else 0
            status = "FAIL" if not items else ("WARN" if fail_rate > PARSE_FAIL_THRESHOLD else "SUCCESS")
            msg = " / ".join(result.messages + [f"신규 {res['inserted']} · 갱신 {res['updated']} · 파싱실패율 {fail_rate:.1f}%"])
            totals[collector.agency] = {"collected": len(items), "failed": failed, "source": result.source, **res}
            if write_log:
                sink.log({"job_name": "BOT-01", "agency_code": collector.agency, "status": status, "source": result.source,
                          "collected": len(items), "failed": failed, "retries": result.retries, "message": msg,
                          "started_at": started, "ended_at": now_kst()})
        except Exception as e:  # 한 여행사 실패가 다른 여행사 수집을 막지 않도록
            log.exception("[%s] 수집 실패", collector.agency)
            if write_log:
                sink.log({"job_name": "BOT-01", "agency_code": collector.agency, "status": "FAIL", "collected": 0, "failed": 0,
                          "message": str(e)[:500], "started_at": started, "ended_at": now_kst()})
    return totals


def run_public(sink, mode: str | None = None) -> dict:
    """BOT-02: 국토교통부 국내항공운항정보 - 국내 상품 출발일(30일 이내) 김포 → 목적지 항공편."""
    started = now_kst()
    mode = mode or settings.rpa_source_mode
    use_live = bool(settings.data_go_kr_key) and mode != "sample"
    messages = [] if settings.data_go_kr_key else ["DATA_GO_KR_KEY 미설정"]

    if use_live:
        try:
            sink.airports(molit_flight.fetch_airports())
        except molit_flight.PublicApiError as e:
            messages.append(f"공항 목록 실패: {e}")

    targets = [(arr, day) for city, day in sorted(domestic_departures(sink.active_products()), key=lambda x: x[1])
               if (arr := CITY_AIRPORT.get(city)) and arr != HOME_AIRPORT_ID][:40]
    flights, failed, source = [], 0, "live"
    if use_live:
        for arr, day in targets:
            try:
                flights += molit_flight.fetch_flights(HOME_AIRPORT_ID, arr, day)
            except molit_flight.PublicApiError as e:
                failed += 1
                messages.append(f"{arr} {day}: {e}")
            time.sleep(min(settings.request_interval_sec, 1))
    if not flights and mode != "live":
        source = "sample"
        if use_live:
            messages.append("live 0건 → sample 대체")
        flights = [f for arr, day in targets for f in molit_flight.sample_flights(HOME_AIRPORT_ID, arr, day)]

    res = sink.flights(flights, source) if flights else {"inserted": 0, "updated": 0}
    status = "SUCCESS" if flights else ("SKIPPED" if not targets else "FAIL")
    sink.log({"job_name": "BOT-02", "status": status, "source": source, "collected": len(flights), "failed": failed,
              "message": " / ".join(messages[:5] + [f"노선·일자 {len(targets)}건, 항공편 신규 {res['inserted']} · 갱신 {res['updated']}"]),
              "started_at": started, "ended_at": now_kst()})
    return {"flights": len(flights), "source": source, **res}


def run_report(sink) -> dict:
    """BOT-03: 일일 엑셀 리포트(Seaborn 차트 포함) + Plotly HTML."""
    started = now_kst()
    day = started.date()
    blob, html, summary = build_report(sink.active_products(), day)
    name = f"nomadpick_daily_{day:%Y%m%d}.xlsx"
    sink.report(day, name, blob, html, summary)
    sink.log({"job_name": "BOT-03", "status": "SUCCESS", "collected": summary["total"], "failed": 0,
              "message": f"{name} 생성 (평균 할인율 {summary['avg_discount']}%)", "started_at": started, "ended_at": now_kst()})
    return summary


def backfill_sample_history(sink, days: int = 14) -> None:
    """최초 실행 시 sample 모드 가격 추이 차트를 위해 과거 14일 가격 스냅샷 생성 (source='sample')."""
    now = now_kst()
    for d in range(days, 0, -1):
        run_deals(sink, mode="sample", at=now - timedelta(days=d), write_log=False)


def run_job(job: str = "all", mode: str | None = None, sink_kind: str | None = None) -> dict:
    if not _lock.acquire(blocking=False):
        log.warning("이전 RPA 작업이 실행 중이어서 건너뜁니다: %s", job)
        return {"skipped": True}
    try:
        sink = get_sink(sink_kind)
        out = {}
        if job == "all" and (mode or settings.rpa_source_mode) == "sample" and sink.is_empty():
            backfill_sample_history(sink)  # 시연용 sample 모드에서만 과거 가격 이력 생성 (실데이터와 섞지 않음)
        if job in ("deals", "all"):
            out["deals"] = run_deals(sink, mode)
        if job in ("public", "all"):
            out["public"] = run_public(sink, mode)
        if job in ("report", "all"):
            out["report"] = run_report(sink)
        return out
    finally:
        _lock.release()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    p = argparse.ArgumentParser(description="NomadPick RPA")
    p.add_argument("job", choices=["deals", "public", "report", "all"], nargs="?", default="all")
    p.add_argument("--mode", choices=["live", "sample", "auto"])
    p.add_argument("--sink", choices=["direct", "api"])
    a = p.parse_args()
    print(run_job(a.job, a.mode, a.sink))


if __name__ == "__main__":
    main()
