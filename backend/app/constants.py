"""서비스 공통 코드값 (백엔드·RPA 공용)."""

AGENCIES = [
    {"id": 1, "code": "hanatour", "name": "하나투어", "base_url": "https://www.hanatour.com"},
    {"id": 2, "code": "modetour", "name": "모두투어", "base_url": "https://www.modetour.com"},
    {"id": 3, "code": "ybtour", "name": "노랑풍선", "base_url": "https://www.ybtour.co.kr"},
]

REGIONS = ["일본", "동남아", "중화권", "대양주", "유럽", "미주", "국내"]
THEMES = ["휴양", "관광", "골프", "효도", "자유여행"]
COMPANIONS = ["혼자", "친구", "연인", "가족"]

# 국토교통부_(TAGO)_국내항공운항정보 공항 ID
AIRPORTS = [
    {"airport_id": "NAARKSS", "airport_nm": "김포", "city": "서울"},
    {"airport_id": "NAARKSI", "airport_nm": "인천", "city": "인천"},
    {"airport_id": "NAARKPC", "airport_nm": "제주", "city": "제주"},
    {"airport_id": "NAARKPK", "airport_nm": "김해", "city": "부산"},
    {"airport_id": "NAARKTN", "airport_nm": "대구", "city": "대구"},
    {"airport_id": "NAARKJJ", "airport_nm": "광주", "city": "광주"},
    {"airport_id": "NAARKJB", "airport_nm": "무안", "city": "목포"},
    {"airport_id": "NAARKJY", "airport_nm": "여수", "city": "여수"},
    {"airport_id": "NAARKNY", "airport_nm": "양양", "city": "강릉"},
    {"airport_id": "NAARKPU", "airport_nm": "울산", "city": "울산"},
    {"airport_id": "NAARKTU", "airport_nm": "청주", "city": "청주"},
    {"airport_id": "NAARKPS", "airport_nm": "사천", "city": "통영"},
    {"airport_id": "NAARKTH", "airport_nm": "포항경주", "city": "경주"},
]

# 국내 상품 출발 공항 (김포 기준)
HOME_AIRPORT_ID = "NAARKSS"
CITY_AIRPORT = {a["city"]: a["airport_id"] for a in AIRPORTS}
