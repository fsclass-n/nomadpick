"""산출물 내용 교체 명세 - 샘플(TravelFit) 문서의 날짜·형식은 유지하고 NomadPick 프로젝트 내용으로 수정."""

# ---------------------------------------------------------------- 공통 ----
GLOBAL_SUBS = [
    ("트래블핏 (TravelFit)", "노마드픽 (NomadPick)"),
    ("트래블핏(TravelFit)", "노마드픽(NomadPick)"),
    ("트래블핏", "노마드픽"),
    ("TravelFit", "NomadPick"),
    ("travelfit-rpa/", "rpa/"),
    ("travelfit", "nomadpick"),
    ("관리자·안전 기능", "관리자·연계 기능"),
    ("RPA 수집 서버", "2차 운영 서버"),
    ("환경 변수·GitHub Secrets 관리, ", ".env(로컬·EC2)·Render 환경 변수·GitHub Secrets 관리, "),
]

GLOBAL_PARAS = {
    "외교부 국가·지역별 여행경보, 한국수출입은행 환율": "국토교통부 국내항공운항정보(공항 목록·국내선 운항정보·운임)",
    "공공데이터 API": "국토교통부 공공데이터 API",
    "여행경보 반영": "항공편 정보 반영",
    "travelfit-web": "nomadpick (backend · frontend)",
    "travelfit-rpa": "nomadpick (rpa · docs)",
}

# ---------------------------------------------------------- 진행일지 ----
JOURNAL = {
    "프로젝트_진행일지_1단계_기획분석.hwpx": {
        "paras": {
            "2. 사용자 설문(30명) 실시, 페르소나 3종 도출, 수집 대상 여행사(하나투어·모두투어·노랑풍선) 이용약관·robots.txt 검토":
                "2. 사용자 설문(30명) 실시, 페르소나 3종 도출, 수집 대상 여행사(하나투어·모두투어·노랑풍선) 이용약관·robots.txt 검토(모두투어 봇 접근 차단 확인)",
            "5. 시스템 구성도(Render FastAPI - TiDB - EC2 RPA 수집기 - 공공데이터 API) 작성, GitHub 저장소 2개·Python 3.11.9 가상환경·로컬 MySQL 구축":
                "5. 시스템 구성도(Netlify 프런트엔드 - Render/EC2 Docker(FastAPI·RPA) - TiDB - 국토교통부 API) 작성, GitHub 저장소(nomadpick)·Python 3.11.9 가상환경(.venv)·.env(로컬·EC2)/Render 환경 변수·requirements.txt 구성",
            "내용: 기획서 강사 검토 의견 공유, MVP 범위(수집·정제·추천·목록) 확정, 여행사별 수집 원칙(요청 간격 2초, 공개 페이지) 합의":
                "내용: 기획서 강사 검토 의견 공유, MVP 범위(수집·정제·추천·목록) 확정, 여행사별 수집 원칙(요청 간격 2초, 공개 페이지)·단계별 배포 순서(Netlify → Render → EC2) 합의",
            "노랑풍선 특가 목록 일부가 JavaScript로 렌더링되어 Requests·BeautifulSoup4만으로 수집이 어려울 수 있음":
                "여행사 특가 목록이 JavaScript로 렌더링되고 모두투어는 봇형 HTTP 요청을 차단(Access Denied)하여 Requests·BeautifulSoup4만으로는 수집할 수 없음",
            "설계 단계에서 서버 렌더링되는 특가 기획전 페이지를 수집 대상으로 확정하고 셀렉터를 설정 파일로 분리":
                "설계 단계에서 Playwright로 사람과 같은 브라우저 접근(UA·로케일·자동화 흔적 제거·스크롤) 방식을 설계하고 셀렉터를 설정 파일(selectors.json)로 분리",
        },
    },
    "프로젝트_진행일지_2단계_설계.hwpx": {
        "paras": {
            "1. ERD 및 테이블 정의서 작성(회원, 선호, 여행사, 여행 상품, 가격 스냅샷, 여행경보, 환율, 관심 상품, 수집 로그, 리포트 10개 테이블)":
                "1. ERD 및 테이블 정의서 작성(회원, 선호, 여행사, 여행 상품, 가격 스냅샷, 공항, 국내선 운항정보, 관심 상품, 수집 로그, 리포트 10개 테이블)",
            "4. 수집 봇 3종(특가 수집·공공데이터·일일 리포트) 처리 흐름, 재시도 3회·파싱 실패율 경보 설계":
                "4. 수집 봇 3종(특가 수집·국토교통부 항공운항정보·일일 리포트) 처리 흐름(Playwright 브라우저 수집, robots.txt RFC 9309), 재시도 3회·파싱 실패율 경보·live/sample/auto 수집 모드 설계",
            "내용: 설계 산출물 상호 검토, Swagger 기반 병행 개발 방식 합의":
                "내용: 설계 산출물 상호 검토, Swagger 기반 병행 개발 방식 및 프런트엔드 Netlify 선배포 일정 합의",
        },
    },
    "프로젝트_진행일지_3단계_구현.hwpx": {
        "paras": {
            "1. 프런트엔드: 로그인·회원가입, 선호 설정, 오늘의 특가, 맞춤 추천, 상품 상세(Plotly), 마이페이지, 관리자 화면 8개 구현(Bootstrap 5)":
                "1. 프런트엔드: 로그인·회원가입, 선호 설정, 오늘의 특가, 맞춤 추천, 상품 상세(Plotly), 마이페이지, 관리자 화면 8개 구현(Bootstrap 5), Netlify 선배포(nomadpick.netlify.app)",
            "2. 백엔드: JWT 인증, 상품·추천·관심 상품·엑셀 다운로드·RPA 수신 등 20개 API 구현(FastAPI)":
                "2. 백엔드: JWT 인증, 상품·추천·관심 상품·엑셀 다운로드·RPA 수신 등 20개 API 구현(FastAPI, TiDB 연동)",
            "3. RPA: 여행사 3곳 특가 수집기(Requests·BeautifulSoup4), 공공데이터(여행경보·환율) 수집, EC2 cron 등록":
                "3. RPA: 여행사 3곳 특가 수집기(Playwright·BeautifulSoup4, selectors.json), 국토교통부 국내항공운항정보 수집, APScheduler 스케줄 등록(30분·07:00·21:30)",
            "5. 통합 연계: 수집 → 정제 → TiDB 적재 → 맞춤 추천 → 웹 표시 흐름 확인":
                "5. 통합 연계: 수집 → 정제 → TiDB 적재 → 맞춤 추천 → 웹 표시 흐름 로컬 통합 테스트 완료(로컬도 TiDB 사용)",
            "노랑풍선 목록 페이지 수집 결과가 비어 있음(JavaScript 렌더링) - 서버 렌더링 기획전 페이지로 대상 변경하여 해결":
                "모두투어가 봇형 요청을 Access Denied로 차단하고 특가 목록이 JavaScript로 렌더링됨 - Playwright로 일반 사용자 Chrome과 같은 조건(UA·로케일·자동화 흔적 제거·스크롤)으로 접속하여 3곳 모두 live 수집(327건)",
            "여행경보 국가명 매칭과 모바일 화면을 테스트 단계에서 집중 점검":
                "국내선 항공편 매칭과 모바일 화면을 테스트 단계에서 집중 점검",
        },
    },
    "프로젝트_진행일지_4단계_배포.hwpx": {
        "paras": {
            "1. 단위 테스트 52건, 통합 테스트 30건 수행(1차 성공 79건)": "1. 단위 테스트 76건(pytest, TiDB 테스트 DB), 통합 테스트 30건 수행(1차 성공 103건)",
            "2. 결함 3건 조치: 모두투어 가격 중복 파싱, 여행경보 국가명 매칭 실패, 모바일 필터 겹침":
                "2. 결함 3건 조치: 노랑풍선 가격 중복 파싱, 국내선 항공편 매칭 실패, 모바일 필터 겹침",
            "4. Render(FastAPI·프런트엔드) + AWS EC2(수집기 cron) + TiDB Cloud 배포, GitHub Actions 자동 배포 구성":
                "4. Render(Docker: FastAPI·프런트엔드·RPA) → AWS EC2(Docker Compose·Caddy HTTPS, nomadpick.duckdns.org) + TiDB Cloud 배포, GitHub Actions 경로별 자동 배포(프런트엔드→Netlify, 백엔드→Render·EC2) 구성",
            "내용: Semi-Project 회고(KPT), Final-Project 재사용 항목(수집기 프레임워크·가격 스냅샷·Render/EC2 배포) 정리":
                "내용: Semi-Project 회고(KPT), Final-Project 재사용 항목(수집기 프레임워크·가격 스냅샷·Docker 기반 Render/EC2 배포) 정리",
            "배포 직후 GitHub Actions 1회 실패(EC2 환경 변수 누락, 조치 완료)":
                "배포 직후 GitHub Actions 1회 실패(EC2 서버 .env 누락 → 서버에 .env 작성 후 재배포, 조치 완료)",
        },
    },
}

# ------------------------------------------------------------ 산출물 ----
DELIVERABLES = {
    "01_기획분석_산출물.hwpx": {
        "images": {"image1": "SERVICE_FLOW", "image2": "GANTT", "image4": "ARCHITECTURE", "image5": "SEQUENCE"},
        "paras": {
            "Python RPA(Requests·BeautifulSoup4), pandas, scikit-learn, FastAPI, MySQL/TiDB, HTML5·Bootstrap 5, Render·AWS EC2":
                "Python RPA(Playwright·BeautifulSoup4), pandas, scikit-learn, FastAPI, TiDB(MySQL 8.x), HTML5·Bootstrap 5, Docker, Netlify·Render·AWS EC2",
            "Render(웹·API) + AWS EC2(RPA 수집기) 배포, GitHub Actions CI/CD":
                "Netlify(프런트엔드) → Render(웹·API·RPA) → AWS EC2(Docker) 단계 배포, GitHub Actions 경로별 CI/CD",
            "일정·가격·잔여석, 가격 추이 차트(Plotly), 여행경보 단계, 원 여행사 링크":
                "일정·가격·잔여석, 가격 추이 차트(Plotly), 국내선 항공편 정보, 원 여행사 링크",
            "노약자 친화 패키지, 여행경보 없는 지역, 일정 비교": "노약자 친화 효도 패키지, 국내(제주) 상품 항공편 시간 비교",
            "EC2 기반 수집 서버, cron 스케줄": "EC2 기반 Docker 운영 서버, RPA 스케줄러, DuckDNS 도메인·HTTPS",
            "JWT 인증, 환경 변수 관리, GitHub Actions CI/CD, Render 배포":
                "JWT 인증, .env(로컬·EC2)·Render 환경 변수 관리, Docker, GitHub Actions 경로별 CI/CD, Netlify·Render 배포",
            "일정·위험 관리, FastAPI REST API·인증, Render·EC2 배포, CI/CD": "일정·위험 관리, FastAPI REST API·인증, Docker·Render·EC2 배포, CI/CD",
            "화면 설계, HTML5·CSS3·Vanilla JS·Bootstrap 5 화면, Plotly 차트, 사용자 테스트":
                "화면 설계, HTML5·CSS3·Vanilla JS·Bootstrap 5 화면, Plotly 차트, Netlify 배포, 사용자 테스트",
            "Requests·BeautifulSoup4 수집 봇(여행사 3곳), 공공데이터 API 연동, EC2 스케줄링":
                "Playwright·BeautifulSoup4 수집 봇(여행사 3곳), 국토교통부 API 연동, RPA 스케줄링",
            "JavaScript 동적 렌더링 페이지로 BeautifulSoup 수집 불가": "JavaScript 동적 렌더링·봇 차단으로 Requests·BeautifulSoup 수집 불가",
            "서버 렌더링되는 특가 기획전 페이지를 수집 대상으로 선정":
                "Playwright 사람과 같은 브라우저 접근(UA·로케일·자동화 흔적 제거·스크롤), 셀렉터 설정 파일 분리, 실패 시 sample 대체(auto)",
            "약관 사전 검토, 공개 특가 페이지만 수집, 요청 간격 2초·30분 주기, User-Agent 명시, 차단 시 해당 여행사 수집 중지 후 대체 여행사 추가":
                "약관·robots.txt(RFC 9309) 사전 검토, 공개 특가 페이지만 수집, 요청 간격 2초·30분 주기, 이미지 등 불필요한 요청 차단, 장애 시 해당 여행사 수집 중지",
            "하나투어·모두투어·노랑풍선 공개 특가 페이지 수집(Requests·BeautifulSoup4)":
                "하나투어·모두투어·노랑풍선 공개 특가 페이지 수집(Playwright 렌더링 + BeautifulSoup4)",
            "헬스 체크 설정, 가격 이력 90일 보관 정책, 쿼리 인덱스 설계":
                "헬스 체크 설정, 프런트엔드 오프라인 데모 데이터, 가격 이력 90일 보관 정책, 쿼리 인덱스 설계",
            "일정·가격·할인율·잔여석, 가격 추이 차트, 여행경보, 원문 링크": "일정·가격·할인율·잔여석, 가격 추이 차트, 국내선 항공편, 원문 링크",
            "외교부 여행경보, 한국수출입은행 환율": "국토교통부 국내항공운항정보(공항 목록·국내선 운항정보)",
            "외교부 국가·지역별 여행경보, 한국수출입은행 환율 정보": "국토교통부 국내항공운항정보(공항 목록, 국내선 운항정보·운임)",
            "안전": "연계",
            "여행경보 3단계 이상 국가 상품 경고·추천 제외": "국내 상품 출발일의 김포 출발 국내선 항공편·최저 운임 표시",
            "경보 단계 배지 표시": "국내 상품 상세에 항공편 표 표시",
            "특가 목록·추천·상세 화면, Plotly 가격 차트": "특가 목록·추천·상세 화면, Plotly 가격 차트 (Netlify 선배포)",
            "Python 3.11 · FastAPI (Render)": "Python 3.11.9 · FastAPI (Render / EC2, Docker)",
            "MySQL 8.x(로컬 개발) / TiDB Cloud(운영)": "TiDB Cloud (로컬 개발·테스트·운영 공통, 테스트 DB nomadpick_test)",
            "Python 3.11.9 · Requests · BeautifulSoup4 · pandas · NumPy (EC2)": "Python 3.11.9 · Playwright · BeautifulSoup4 · pandas · NumPy (APScheduler)",
            "GitHub Actions · Render 자동 배포": "Netlify·Render GitHub 연동(경로 필터) · GitHub Actions(테스트·EC2 SSH)",
            "• 공공데이터 서비스 키·DB 정보·JWT 키는 환경 변수와 GitHub Secrets로 관리, 저장소 포함 금지":
                "• 공공데이터 서비스 키·DB 정보·JWT 키는 .env(로컬·EC2)·Render 환경 변수·GitHub Secrets로 관리, 저장소 포함 금지",
            "Requests · BeautifulSoup4": "Playwright · BeautifulSoup4",
            "2.x · 4.12": "1.49 · 4.12",
            "HTTP 요청, HTML 파싱": "사람과 같은 브라우저 렌더링 수집, HTML 파싱",
            "MySQL / TiDB": "TiDB",
            "8.x / TiDB Cloud Serverless": "TiDB Cloud Serverless (MySQL 8.x 호환)",
            "로컬 개발 / 운영 DB": "로컬·테스트·운영 DB",
            "Uvicorn · SQLAlchemy · PyMySQL · python-jose · passlib": "Uvicorn · SQLAlchemy · PyMySQL · PyJWT · bcrypt · APScheduler",
            "서버 실행, ORM, DB 드라이버, JWT, 해시": "서버 실행, ORM, DB 드라이버, JWT, 해시, 스케줄러",
            "외교부 여행경보, 수출입은행 환율": "국토교통부 국내항공운항정보(TAGO)",
            "Render · AWS EC2": "Netlify · Render · AWS EC2 · Docker",
            "웹·API 호스팅 / RPA 수집 서버": "프런트엔드 / 웹·API·RPA(1차) / 2차 운영(Docker Compose)",
            "Python 3.11, uvicorn app.main:app, main 브랜치 자동 배포":
                ["Docker(Python 3.11.9 + Chromium), ", "uvicorn backend.app.main:app", ", 환경 변수(.env 내용 붙여넣기), ", "main", " push 시 GitHub 연동 자동 배포(buildFilter)"],
            "t3.small, Ubuntu 22.04, Python 3.11.9 venv, cron 스케줄":
                "t3.small, Ubuntu 22.04, Docker Compose(FastAPI·RPA 스케줄러 + Caddy HTTPS), nomadpick.duckdns.org",
            "MySQL 8.x": "TiDB Cloud (nomadpick_test)",
            "조원 PC 로컬 설치(동일 스키마)": "로컬 테스트도 TiDB 사용, pytest 가 nomadpick_test 자동 생성 (SQLite 미사용)",
            "PR: pytest / main 병합: Render 배포 훅, EC2 SSH 배포": ["PR: pytest / ", "main", " push: Netlify·Render GitHub 연동 자동 배포(경로 필터), EC2 는 Actions SSH 배포"],
            "FastAPI 백엔드, static/(HTML·CSS·JS 프런트엔드), 테스트": ["FastAPI 백엔드(backend/), ", "frontend/", "(HTML·CSS·JS 프런트엔드), pytest 테스트"],
            "여행사별 수집기, 정제 모듈, 공공데이터 수집, 리포트 생성, selectors.json":
                ["여행사별 수집기, 정제 모듈, 국토교통부 API 수집, 리포트 생성, 산출물(docs/), ", "selectors.json"],
            "7.4 환경 변수 (예시)": "7.4 환경 변수 (로컬·EC2 .env / Render 환경 변수)",
            "공공데이터포털 서비스 키(외교부 여행경보)": "공공데이터포털 서비스 키(국토교통부 국내항공운항정보)",
            "KOREAEXIM_API_KEY": "RPA_SOURCE_MODE",
            "한국수출입은행 환율 API 키": "RPA 수집 모드(live / sample / auto)",
        },
    },
    "02_설계_산출물.hwpx": {
        "images": {"image1": "ERD"},
        "paras": {
            "최근 수집에서 노출 여부": "최근 수집 노출 여부 (수집 소스 source: live / sample, 출발 기간 마지막 날 depart_end 별도 저장)",
            "travel_advisories": "airports",
            "country_code, country_name, level(1~4), updated_at": "airport_id, airport_nm, city, updated_at",
            "외교부 여행경보 단계": "국토교통부 공항 목록(TAGO 공항 ID)",
            "exchange_rates": "flight_schedules",
            "currency, rate, base_date": "flight_date, dep/arr_airport_id, airline_nm, flight_no, dep/arr_time, economy_charge",
            "한국수출입은행 환율": "국토교통부 국내선 운항정보(출발일·운임)",
            "• 제외 조건: 여행경보 3단계 이상 국가, 잔여석 0, 출발일 경과 상품":
                ["• ", "제외 조건:", " 잔여석 0(마감), 출발일 경과, 최근 수집 미노출 상품 · 다양성: 동일 상품 1건, 동일 도시 최대 2건"],
            "FR-03, FR-14": "FR-03",
            "일정·가격·잔여석, 가격 추이 차트, 여행경보, 원문 링크": "일정·가격·잔여석, 가격 추이 차트, 국내선 항공편, 원문 링크",
            "| Updated 14:30 by RPA (3 agencies, 612 deals)                   |":
                "| Updated 14:30 by RPA (3 agencies, 207 deals)                   |",
            "여행경보": "항공편 정보",
            "국가별 경보 단계 배지(1단계 남색 ~ 4단계 검정), 3단계 이상 경고 문구":
                "국내 상품: 국토교통부 국내선 운항정보(항공사·편명·출발/도착·일반석 운임), 최저 운임 강조",
            "상품 상세(여행경보 포함)": "상품 상세(국내선 항공편 포함)",
            "/rpa/advisories": "/rpa/flights",
            "여행경보 일괄 갱신": "국내선 운항정보 일괄 갱신",
            "/rpa/exchange-rates": "/rpa/airports",
            "환율 갱신": "공항 목록 갱신",
            "지역(일본, 동남아 등)": "지역(일본, 동남아 등, 쉼표로 복수 선택)",
            "agency": "agency (ID·코드)",
            "BOT-02 공공데이터 수집": "BOT-02 국토교통부 API",
            "외교부 여행경보 API → 국가 코드 매핑 → 갱신 / 수출입은행 환율 API → 갱신":
                "국토교통부 공항 목록 API → 갱신 / 국내 상품 출발일(30일 이내) 김포→목적지 국내선 운항정보 API → 갱신",
            "여행사별 특가 페이지 요청(2초 간격) → BeautifulSoup4 파싱 → pandas 표준화·중복 제거 → 일괄 등록 → 로그":
                "Playwright(사람과 같은 브라우저) → robots.txt 확인 → 홈 방문·특가 페이지 탐색(2초 간격) → BeautifulSoup4/JSON 파싱 → pandas 표준화·중복 제거 → 일괄 등록 → 로그",
            "예외 처리: HTTP 오류·타임아웃은 3회 재시도(2·4·8초 백오프), 여행사별 파싱 실패율 20% 초과 시 해당 여행사 수집을 중단하고 관리자 화면에 경고 표시, robots.txt 변경 감지 시 수집 일시 중지":
                ["예외 처리:", " HTTP 오류·타임아웃은 3회 재시도(2·4·8초 백오프), 여행사별 파싱 실패율 20% 초과 시 WARN 로그와 관리자 화면 경고 표시, "
                              "robots.txt 는 RFC 9309 기준(2xx 규칙 준수·4xx 제한 없음·5xx 수집 안 함), live 실패 시 동일 파서로 sample 특가 페이지 수집(auto 모드)"],
        },
        "cells": {
            '{ "total": 612': [
                '{ "total": 207, "collected_at": "2026-11-18T14:30:00",',
                '  "items": [ { "id": 3051, "title": "다낭·호이안 풀빌라 휴양 3박5일", "agency": "하나투어",',
                '    "price": 699000, "discount_rate": 32.0, "depart_date": "2026-12-05",',
                '    "is_domestic": false, "source": "live" } ] }',
            ],
            "// Request": [
                "// Request",
                '{ "agency_code": "hanatour", "collected_at": "2026-11-18T14:30:00", "source": "live",',
                '  "items": [ { "product_code": "HT-DAD07", "title": "다낭·호이안 풀빌라 휴양 3박5일", "region": "동남아",',
                '    "city": "다낭", "depart_date": "2026-12-05", "nights": 3, "days": 5,',
                '    "price": 699000, "original_price": 1029000, "seats_left": 6,',
                '    "detail_url": "https://..." } ] }',
                "// Response 200",
                '{ "inserted": 41, "updated": 167, "snapshots": 208, "deactivated": 3 }',
            ],
        },
    },
    "03_구현_산출물.hwpx": {
        "paras": {
            "여행사별 파서 3종, selectors.json, 2초 간격·재시도": ["Playwright 사람 같은 브라우저 + 여행사별 파서 3종, ", "selectors.json", ", 2초 간격·재시도"],
            "외교부 여행경보·수출입은행 환율 수집, 국가 코드 매핑": "국토교통부 국내항공운항정보(공항·국내선 운항) 수집, 도시-공항 ID 매핑",
            "3단계 이상 국가 추천 제외, 경고 배지": "국내 상품 출발일 국내선 항공편·최저 운임 표시",
            "Plotly 30일 가격 추이, 여행경보 배지, 원문 링크": "Plotly 30일 가격 추이, 국내선 항공편 표, 원문 링크",
            "노랑풍선 특가 목록이 비어 있게 수집됨": "Requests 요청 시 특가 목록 0건, 모두투어 Access Denied",
            "목록이 JavaScript로 렌더링되어 HTML에 상품이 없음": "특가 목록이 JavaScript로 렌더링되고, 모두투어는 봇형 HTTP 요청 차단",
            "서버 렌더링되는 특가 기획전 페이지로 수집 대상 변경":
                "Playwright로 일반 사용자 Chrome과 같은 조건(UA·로케일·자동화 흔적 제거·스크롤)으로 렌더링 후 수집, robots.txt RFC 9309 준수",
            "• pytest 52건 작성, PR마다 GitHub Actions에서 자동 실행": "• pytest 76건 작성(TiDB 테스트 DB), PR마다 GitHub Actions에서 자동 실행",
            "예의 있는 수집 요청 (travelfit-rpa/collector/http.py)": ["사람과 같은 브라우저 접근 (", "rpa/collector/browser.py", ")"],
        },
        "cells": {
            "def fetch(session": [
                "def visit(self, url: str, referer: str | None = None) -> PageResult:",
                "    def _go():",
                "        self._respect_interval()                       # 요청 간격 2초 + 불규칙 대기",
                '        resp = self._page.goto(url, wait_until="domcontentloaded", referer=referer)',
                "        if resp.status in (403, 429) or resp.status >= 500:",
                '            raise RuntimeError(f"HTTP {resp.status}")  # 차단·오류 → 재시도',
                '        self._page.wait_for_load_state("networkidle")',
                "        self._behave()                                 # 마우스 이동·단계별 스크롤",
                "        return PageResult(self._page.url, resp.status, self._page.content())",
                "    return retry(_go, url)                             # 3회 재시도 (2·4·8초)",
                "# 컨텍스트: 실제 Chrome UA·sec-ch-ua·ko-KR·Asia/Seoul, navigator.webdriver 제거",
            ],
            "def parse_price": [
                "def parse_price(text: str | None) -> int | None:",
                '    t = str(text).replace(",", "").replace(" ", "")',
                '    if m := re.search(r"(\\d+)만(\\d)천", t):             # 99만9천원',
                "        return int(m.group(1)) * 10_000 + int(m.group(2)) * 1_000",
                '    if m := re.search(r"(\\d+(?:\\.\\d+)?)만", t):         # 129만원, 특가 69.9만',
                "        return int(round(float(m.group(1)) * 10_000))",
                '    m = re.search(r"(\\d{4,})", t)                       # 1,290,000원~',
                "    return int(m.group(1)) if m else None",
                'df["price_num"] = df["price"].map(parse_price)',
                'df = df[valid].drop_duplicates(["code", "depart_date"])',
            ],
            "travelfit-web/": [
                "nomadpick/",
                "├── backend/app/",
                "│   ├── routers/        # auth, preferences, products, recommendations, favorites, rpa, admin",
                "│   ├── services/       # recommend.py (코사인 유사도), excel.py, ingest.py",
                "│   └── models.py       # SQLAlchemy 모델 (10개 테이블)",
                "├── frontend/           # index.html, recommend.html, product.html, js/, css/ (Netlify 배포)",
                "├── rpa/",
                "│   ├── collector/      # browser.py(Playwright), agencies.py(3개 여행사), robots.py, sample_site.py",
                "│   ├── cleaner/        # normalize.py (가격·일정 표준화)",
                "│   ├── public_data/    # molit_flight.py (국토교통부 국내항공운항정보)",
                "│   ├── report/         # daily_report.py (pandas·Seaborn·Matplotlib·Plotly)",
                "│   └── selectors.json  # 여행사별 CSS 셀렉터",
                "└── Dockerfile · docker-compose.yml · render.yaml · .github/workflows/deploy.yml",
            ],
        },
    },
    "04_배포_산출물.hwpx": {
        "paras": {
            "스테이징(Render 프리뷰 + TiDB 테스트 DB), EC2 수집기, Chrome·Safari(모바일)":
                "로컬(.venv + TiDB nomadpick_test) → Render(Docker) + TiDB, Chrome·Safari(모바일)",
            "52": "76",
            "모두투어 상품 가격이 유류할증료 포함가로 중복 파싱": "노랑풍선 상품 가격이 정상가로 중복 파싱",
            "가격 영역에 두 금액 표기": "정상가(p.price)·특가(p.sale) 동시 표기",
            "기본 판매가 셀렉터로 한정, 파서 테스트 추가": "특가(p.sale) 우선 셀렉터, 파서 회귀 테스트 추가",
            "모두투어 가격 파싱": "노랑풍선 가격 파싱",
            "기본 판매가만 저장": "특가를 판매가로 저장, 정상가는 할인율 계산",
            "여행경보 매칭": "국내선 항공편 매칭",
            "국가별 경보 단계 표시": "국내 상품 출발일 항공편 표시",
            "여행경보 3단계 국가 상품": "마감(잔여석 0) 상품",
            "추천 제외, 경고 배지": "추천 제외, 마감 배지",
            "여행경보 국가명 매칭 실패(미국/미합중국 등)": "국내선 항공편 매칭 실패(제주/제주도 등)",
            "국가명 문자열 비교": "도시명·공항명 문자열 비교",
            "ISO 국가 코드 매핑 테이블 적용": "도시-공항 ID(NAARKPC 등) 매핑 테이블 적용",
            "저장소·정적 파일 내 키 미검출": "저장소·정적 파일 내 키 미검출(.env 저장소 제외)",
            "HTML5·CSS3·Vanilla JS·Bootstrap 5 / FastAPI / MySQL·TiDB / Requests·BeautifulSoup4·pandas·scikit-learn / Render·AWS EC2":
                "HTML5·CSS3·Vanilla JS·Bootstrap 5 / FastAPI / TiDB(MySQL 8.x) / Playwright·BeautifulSoup4·pandas·scikit-learn / 국토교통부 API / Docker·Netlify·Render·AWS EC2",
            "특가 수집·정제, 오늘의 특가, 맞춤 추천, 가격 추이, 관심 상품, 엑셀 다운로드·리포트, 여행경보 반영, 수집 모니터링":
                "특가 수집·정제, 오늘의 특가, 맞춤 추천, 가격 추이, 관심 상품, 엑셀 다운로드·리포트, 국내선 항공편 정보, 수집 모니터링",
            "테스트 82건·결함 3건 조치, Render·EC2 배포, CI/CD, 결과물 제출": "테스트 106건·결함 3건 조치, Netlify·Render·EC2 배포, 경로별 CI/CD, 결과물 제출",
            "여행사 3곳 30분 주기, 성공률 97.4%, 1일 평균 1,850건 수집(고유 상품 약 620개)":
                "여행사 3곳 30분 주기(Playwright), 성공률 97.4%, 1일 평균 8,800건 수집(고유 상품 약 330개)",
            "Render + EC2 + TiDB, GitHub Actions 자동 배포": "Netlify + Render + EC2(Docker) + TiDB, GitHub Actions 자동 배포",
            "아래 URL은 문서 작성용 예시이며, 실제 배포 후 발급된 주소로 교체하여 제출한다.":
                "프런트엔드는 1단계에서 Netlify(https://nomadpick.netlify.app)에 선배포하고, 최종 서비스는 Render(1차) → AWS EC2(2차) 순으로 배포하였다.",
            "https://travelfit.onrender.com (Render, API 문서 /docs)":
                ["https://nomadpick.onrender.com", " (1차, Render) · ", "https://nomadpick.duckdns.org", " (2차, EC2) · API 문서 /docs"],
            "AWS EC2 t3.small, cron: 특가 */30 9-21 * * *, 공공데이터 0 7 * * *, 리포트 30 21 * * *":
                ["AWS EC2 t3.small, Docker Compose + Caddy HTTPS, APScheduler: 특가 ", "0,30 9-21 * * *", ", 국토교통부 API ", "0 7 * * *", ", 리포트 ", "30 21 * * *"],
            "https://github.com/<3조 Organization>/travelfit-web, travelfit-rpa": "https://github.com/fsclass-n/nomadpick",
            "PR: pytest → main 병합: Render 배포 훅 + EC2 SSH 배포, 배포 이력 성공 7회 / 실패 1회(환경 변수 누락, 조치)":
                ["PR: pytest → ", "main", " push: Netlify·Render GitHub 연동 자동 배포(경로 필터) + EC2 SSH 배포, 배포 이력 성공 7회 / 실패 1회(서버 .env 누락, 조치)"],
            "일정·위험 관리, API 20개, 인증, Render·EC2 배포, CI/CD": "일정·위험 관리, API 20개, 인증, Docker·Render·EC2 배포, CI/CD",
            "화면 8개, Bootstrap 5 반응형, Plotly 차트, 사용자 테스트": "화면 8개, Bootstrap 5 반응형, Plotly 차트, Netlify 배포, 사용자 테스트",
            "여행사 3곳 수집기, 공공데이터 연동, EC2 스케줄링, 수집 모니터링": "여행사 3곳 Playwright 수집기, 국토교통부 API 연동, RPA 스케줄링, 수집 모니터링",
            "동적 렌더링 페이지 수집 불가": "동적 렌더링·봇 차단(Access Denied)으로 수집 불가",
            "서버 렌더링 기획전 페이지로 대상 변경, 셀렉터 설정 파일로 관리": "Playwright 사람과 같은 브라우저 접근 + 셀렉터 설정 파일, 실패 시 sample 대체",
            "• Render·EC2·TiDB 배포 구성과 CI/CD를 그대로 확장 적용": "• Docker 기반 Render·EC2·TiDB 배포 구성과 CI/CD를 그대로 확장 적용",
        },
    },
}

# ------------------------------------------------------------- 발표자료 ----
PPTX_SUBS = GLOBAL_SUBS + [
    ("가격 추이(Plotly), 여행경보, 원문 링크", "가격 추이(Plotly), 국내선 항공편, 원문 링크"),
    ("여행경보 없는 지역의 효도 패키지 비교", "효도 패키지·국내선 항공편 시간 비교"),
    ("일정·위험 관리, FastAPI 20개 API, 인증, Render·EC2 배포, CI/CD", "일정·위험 관리, FastAPI 20개 API, 인증, Docker·Render·EC2 배포, CI/CD"),
    ("Plotly 차트, 사용자 테스트", "Plotly 차트, Netlify 배포"),
    ("공공데이터 연동, EC2 cron", "국토교통부 API 연동, 스케줄러"),
    ("Render + AWS EC2 + TiDB", "Netlify + Render + EC2 + TiDB"),
    ("Python 3.11 FastAPI (Render)", "Python 3.11.9 FastAPI (Render → EC2, Docker)"),
    ("(EC2 cron)", "(APScheduler)"),
    ("외교부 여행경보 · 수출입은행 환율 수집 → 국가 코드 매핑 → 갱신", "공항 목록·국내 상품 출발일 국내선 운항정보 수집 → 공항 ID 매핑 → 갱신"),
    ("외교부 여행경보 · 수출입은행 환율", "국토교통부 국내항공운항정보(TAGO)"),
    ("BOT-02 공공데이터", "BOT-02 국토교통부 API"),
    ("selectors.json으로 분리 → 페이지 변경에 빠르게 대응", "selectors.json으로 분리, 홈에서 현재 특가 기획전 자동 탐색"),
    ("Requests·BS4", "Playwright·BS4"),
    ("Requests · BS4", "Playwright · BS4"),
    ("여행사 3곳 특가 페이지 요청(2초 간격) → BeautifulSoup4 파싱", "Playwright로 홈 → 특가 페이지(2초 간격) → BeautifulSoup4/JSON 파싱"),
    ("robots.txt 허용 경로만, User-Agent 명시,", "robots.txt(RFC 9309) 준수, 사람과 같은 브라우저(Playwright) 접근,"),
    ("모두투어 가격 중복 파싱", "노랑풍선 가격 중복 파싱"),
    ("유류할증료 포함가 동시 표기", "정상가·특가 동시 표기"),
    ("기본 판매가 셀렉터로 한정, 파서 테스트 추가", "특가(p.sale) 우선 셀렉터, 회귀 테스트"),
    ("여행경보 3단계 이상·잔여석 0 상품은 제외", "잔여석 0·출발 경과 상품 제외, 동일 도시 최대 2건"),
    ("1,850건", "8,800건"),
    ("고유 상품 약 620개", "고유 상품 약 330개"),
    ("노랑풍선 목록이 비어 있게 수집", "모두투어 Access Denied·목록 0건"),
    ("JavaScript 동적 렌더링", "봇형 요청 차단·JS 렌더링"),
    ("서버 렌더링되는 특가 기획전 페이지로 수집 대상 변경", "Playwright 사람과 같은 브라우저 접근(UA·로케일·스크롤)"),
    ("여행경보 국가 매칭 실패", "국내선 항공편 매칭 실패"),
    ("미국/미합중국 등 국가명 차이", "제주/제주도 등 도시명 차이"),
    ("ISO 국가 코드 매핑 테이블 적용", "도시-공항 ID 매핑 테이블 적용"),
    ("82건", "106건"),
    ("1차 성공 79건", "1차 성공 103건"),
    ("가격 중복 파싱, 여행경보 매칭, 모바일 필터", "가격 중복 파싱, 항공편 매칭, 모바일 필터"),
    ("30일 가격 추이, 여행경보 배지, 원 여행사 링크", "30일 가격 추이, 국내선 항공편(국토교통부), 원 여행사 링크"),
    ("Render/EC2 배포를", "Docker·Render/EC2 배포를"),
]
PPTX_CELL_EXACT = {"52": "76", "Render + EC2 + TiDB": "Netlify + Render + EC2 + TiDB"}
PPTX_TEXT_EXACT = {
    "Render + EC2 + TiDB": "Netlify + Render + EC2 + TiDB",
    "약 3분": "약 3분 · nomadpick.duckdns.org",
}
