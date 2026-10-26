"""산출물·발표자료용 Mermaid 다이어그램 소스 (NomadPick)."""

SERVICE_FLOW = """flowchart LR
  A[하나투어] --> R[RPA 수집기<br/>Playwright·BS4]
  B[모두투어] --> R
  C[노랑풍선] --> R
  P[국토교통부 API<br/>국내항공운항정보] --> R
  R --> N[pandas 정제<br/>중복 제거·표준화]
  N --> D[(TiDB<br/>MySQL 호환)]
  N --> X[엑셀 리포트]
  D --> F[FastAPI]
  F --> W[웹<br/>Bootstrap 5]
  W -- 맞춤 추천·엑셀 --> U[사용자]
  U -- 선호 설정 --> W
"""

GANTT = """gantt
  title 노마드픽 Semi-Project 일정
  dateFormat YYYY-MM-DD
  axisFormat %m-%d
  excludes weekends
  section 기획/분석·설계
  기획/분석 :2026-11-05, 2026-11-07
  설계 :2026-11-09, 2026-11-11
  section 구현
  프런트엔드 개발(Netlify) :2026-11-11, 2026-11-18
  백엔드 개발 :2026-11-11, 2026-11-17
  RPA 자동화 개발 :2026-11-11, 2026-11-18
  통합 연계 :2026-11-17, 2026-11-19
  section 배포
  단위·통합 테스트 :2026-11-19, 2026-11-21
  Render·EC2 배포 :2026-11-20, 2026-11-21
  결과물 제출 :2026-11-23, 2026-11-24
"""

ARCHITECTURE = """flowchart TB
  GA[GitHub main push<br/>변경 경로별 자동 배포]
  subgraph US[사용자]
    BR[웹 브라우저<br/>HTML5 · Bootstrap 5]
  end
  subgraph NL[Netlify · 1단계 프런트엔드]
    FE[정적 프런트엔드<br/>nomadpick.netlify.app]
  end
  subgraph RD[Render · 1차 운영]
    RA[Docker 컨테이너<br/>FastAPI + 정적 프런트엔드<br/>RPA 스케줄러]
  end
  subgraph EC[AWS EC2 · 2차 운영]
    CD[Caddy HTTPS<br/>nomadpick.duckdns.org] --> EA[Docker 컨테이너<br/>FastAPI + RPA 스케줄러]
  end
  DB[(TiDB Cloud<br/>MySQL 호환 · TLS)]
  AG[하나투어 · 모두투어 · 노랑풍선<br/>공개 특가 페이지]
  MO[국토교통부 공공데이터 API<br/>국내항공운항정보]
  BR -- HTTPS --> FE
  FE -- REST API /api/v1 --> RA
  BR -- HTTPS --> CD
  RA --> DB
  EA --> DB
  RA -. 요청 간격 2초 .-> AG
  EA -. 요청 간격 2초 .-> AG
  RA -.-> MO
  EA -.-> MO
  GA -- Git 연동 · frontend 변경 --> FE
  GA -- Git 연동 · 서버 파일 변경 --> RA
  GA -- Actions · SSH · docker compose --> EA
"""

SEQUENCE = """sequenceDiagram
  participant S as APScheduler (Docker)
  participant C as 수집기 (Playwright)
  participant A as 여행사 특가 페이지
  participant P as pandas 정제
  participant F as FastAPI 적재
  participant D as TiDB
  S->>C: 30분마다 실행 (09~21시)
  loop 여행사 3곳
    C->>A: Playwright · robots.txt 확인 → 홈 → 특가 페이지 (2초 간격)
    A-->>C: 렌더링 HTML / __NEXT_DATA__ JSON
    C->>C: BeautifulSoup4·JSON 파싱 (selectors.json)
  end
  Note over C,A: 사람과 같은 브라우저 (Chrome UA · ko-KR · 스크롤), 실패 시 sample 대체
  C->>P: 원시 데이터 DataFrame
  P->>P: 가격·박일·출발일 표준화, 중복 제거
  P->>F: POST /rpa/products/bulk (X-RPA-KEY)
  F->>D: 상품 upsert + 가격 스냅샷 저장
  F-->>C: 처리 건수
  C->>F: POST /rpa/logs (성공·실패 건수)
"""

ERD = """erDiagram
  agencies ||--o{ travel_products : sells
  travel_products ||--o{ price_snapshots : tracks
  users ||--o| user_preferences : has
  users ||--o{ favorites : saves
  travel_products ||--o{ favorites : saved
  airports ||--o{ flight_schedules : serves
  travel_products }o..o{ flight_schedules : "depart date"
  agencies {
    int id PK
    varchar code UK
    varchar name
    varchar base_url
  }
  travel_products {
    bigint id PK
    int agency_id FK
    varchar product_code
    varchar title
    varchar region
    varchar city
    date depart_date
    int price
    decimal discount_rate
    varchar source
  }
  price_snapshots {
    bigint id PK
    bigint product_id FK
    int price
    datetime collected_at
  }
  users {
    bigint id PK
    varchar email UK
    varchar password_hash
    varchar role
  }
  user_preferences {
    bigint user_id PK
    json regions
    int budget_max
    json depart_months
    varchar theme
  }
  favorites {
    bigint user_id FK
    bigint product_id FK
    int saved_price
  }
  airports {
    varchar airport_id PK
    varchar airport_nm
    varchar city
  }
  flight_schedules {
    bigint id PK
    date flight_date
    varchar dep_airport_id
    varchar arr_airport_id FK
    varchar flight_no
    int economy_charge
  }
  rpa_job_logs {
    bigint id PK
    varchar job_name
    varchar status
    varchar source
  }
  excel_reports {
    bigint id PK
    date report_date UK
    longblob file_blob
  }
"""
