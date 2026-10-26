# AGENTS.md - NomadPick 작업 규칙

## 환경
- Python 3.11.9, 가상환경 `.venv` (Windows: `.venv\Scripts\python.exe`)
- 외부 라이브러리는 `requirements.txt` 하나로 관리 (`pip install -r requirements.txt` + `playwright install chromium`)
- 환경 변수: 로컬·EC2 는 루트 `.env` 파일, Render 는 대시보드 Environment 에 `.env` 내용을 붙여넣기 (`.env` 커밋 금지)
  - Windows 에서는 `TZ` 환경 변수를 제거함(CRT 가 IANA TZ 미지원) - 시간은 `backend/app/utils.py` 의 KST 함수 사용
- DB 는 TiDB 만 사용 (SQLite 미사용). 로컬 테스트도 TiDB, pytest 는 `nomadpick_test` DB 를 자동 생성·초기화

## 명령
- 서버: `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload`
- 테스트: `.venv/Scripts/python.exe -m pytest` (루트 `conftest.py` 가 TiDB `nomadpick_test`·sample 모드 설정, DB 정보 없으면 API 테스트 생략)
- RPA: `.venv/Scripts/python.exe -m rpa.run all` (live 수집은 Playwright, 약 4분)
- 프런트 오프라인 데모 데이터 갱신(TiDB 스냅샷): `.venv/Scripts/python.exe -m rpa.export_sample`
- 산출물 문서 생성/PDF 변환: `.venv/Scripts/python.exe docs/tools/build_docs.py` (한컴오피스·PowerPoint 설치 필요, Windows)
  - 프로젝트 내용이 바뀌면 `docs/tools/content_spec.py`·`docs/md/*.md` 를 함께 수정하고 다시 생성

## 구조 메모
- API prefix `/api/v1`, 프런트엔드는 FastAPI StaticFiles 로 `/` 에 제공 (Netlify 는 `frontend/` 단독)
- RPA 수집: `rpa/collector/browser.py`(HumanBrowser) + `rpa/selectors.json`(홈 → 특가 페이지 탐색, 셀렉터/JSON 필드)
- RPA 적재: `RPA_SINK=direct`(DB 직접) / `api`(X-RPA-KEY 로 `/api/v1/rpa/*` 호출)
- 수집 데이터 `source` 컬럼: `live` / `sample`, 출발 기간 상품은 `depart_date`~`depart_end`
- 국토교통부 API: `https://apis.data.go.kr/1613000/DmstcFlightNvgInfo/GetFlightOpratInfoList` (2026-03 개편 경로)
- 배포: Netlify·Render 는 GitHub 연동 자동 배포(`netlify.toml` ignore / `render.yaml` buildFilter 로 경로 제한), EC2 는 `.github/workflows/deploy.yml`(테스트 → SSH)
