"""요청/응답 스키마 (Pydantic v2)."""
import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    email: str = Field(max_length=100)
    password: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    has_preference: bool


class PreferenceIn(BaseModel):
    regions: list[str] = []
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    depart_months: list[str] = []
    nights_min: int | None = Field(default=None, ge=0, le=30)
    nights_max: int | None = Field(default=None, ge=0, le=30)
    theme: str | None = None
    companion: str | None = None

    @field_validator("depart_months")
    @classmethod
    def check_months(cls, v: list[str]) -> list[str]:
        for m in v:
            if not re.fullmatch(r"\d{4}-\d{2}", m):
                raise ValueError("출발월은 YYYY-MM 형식이어야 합니다.")
        return v


class PreferenceOut(PreferenceIn):
    model_config = ConfigDict(from_attributes=True)


class FavoriteIn(BaseModel):
    product_id: int


# ---------- RPA ----------
class RpaProductItem(BaseModel):
    product_code: str = Field(max_length=50)
    title: str = Field(max_length=200)
    region: str
    country_code: str | None = None
    city: str | None = None
    theme: str | None = None
    depart_date: date
    depart_end: date | None = None
    depart_anytime: bool = False  # 출발일 표기 없는 국내 상품(수집일~+60일 상시 출발)
    nights: int | None = None
    days: int | None = None
    price: int = Field(gt=0)
    original_price: int | None = None
    seats_left: int | None = None
    airline: str | None = None
    image_url: str | None = None
    detail_url: str | None = None


class RpaProductsBulkIn(BaseModel):
    agency_code: str
    collected_at: datetime
    source: str = "live"
    items: list[RpaProductItem]


class RpaFlightItem(BaseModel):
    flight_date: date
    dep_airport_id: str
    arr_airport_id: str
    dep_airport_nm: str | None = None
    arr_airport_nm: str | None = None
    airline_nm: str | None = None
    flight_no: str
    dep_time: str
    arr_time: str | None = None
    economy_charge: int | None = None
    prestige_charge: int | None = None


class RpaFlightsIn(BaseModel):
    source: str = "live"
    items: list[RpaFlightItem]


class RpaAirportItem(BaseModel):
    airport_id: str
    airport_nm: str
    city: str | None = None


class RpaAirportsIn(BaseModel):
    items: list[RpaAirportItem]


class RpaLogIn(BaseModel):
    job_name: str
    agency_code: str | None = None
    status: str
    source: str | None = None
    collected: int = 0
    failed: int = 0
    retries: int = 0
    message: str | None = None
    started_at: datetime
    ended_at: datetime | None = None


class RpaReportIn(BaseModel):
    report_date: date
    file_name: str
    file_base64: str
    chart_html: str | None = None
    summary: dict | None = None
