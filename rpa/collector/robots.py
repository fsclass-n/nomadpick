"""robots.txt 판단 (RFC 9309).

- 2xx       : 규칙 파싱 후 준수
- 4xx       : 'unavailable' → 접근 제한 없음으로 간주 (RFC 9309 2.3.1.3, 예: 모두투어 robots.txt 403)
- 5xx·오류  : 'unreachable' → 전체 Disallow 로 간주 (수집하지 않음)
"""
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    def __init__(self, status: int | None, text: str = "") -> None:
        self.status = status
        self.parser: RobotFileParser | None = None
        if status is not None and 200 <= status < 300 and "<html" not in text[:300].lower():
            self.parser = RobotFileParser()
            self.parser.parse(text.splitlines())

    @property
    def mode(self) -> str:
        if self.parser is not None:
            return "rules"
        if self.status is not None and 400 <= self.status < 500:
            return "unavailable"
        return "unreachable"

    def allowed(self, url: str, user_agent: str = "*") -> bool:
        if self.mode == "rules":
            return self.parser.can_fetch(user_agent, url)
        return self.mode == "unavailable"


def robots_url(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/robots.txt"
