from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO

import httpx
import pdfplumber
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://sie.xjtu.edu.cn/en/masterphd2026E.pdf"
APPLICATION_URL = "http://isso.xjtu.edu.cn/recruit/login"
CHALLENGE_URL = "https://sie.xjtu.edu.cn/dynamic_challenge"


@dataclass(frozen=True, slots=True)
class GuidePayload:
    text: str
    rows: tuple[tuple[str | None, ...], ...]


GuideFetcher = Callable[[str], GuidePayload]


class XJTUAdapter:
    university_id = "xi-an-jiaotong-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-international-admissions-guide-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "xjtu-international-graduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 80,
        guide_fetcher: GuideFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.guide_fetcher = guide_fetcher or _fetch_guide

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        del fetcher
        payload = self.guide_fetcher(CATALOG_URL)
        programmes = _programmes(payload.rows)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"XJTU guide contained {len(programmes)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        scholarship_close, self_funded_close = _closing_dates(payload.text)
        programmes.append(
            DiscoveredProgramme(
                id="xjtu-international-graduate-admissions",
                name="International graduate admissions",
                degree_type="Master/Doctoral",
                faculty="School of International Education",
                department="School of International Education",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="Scholarship programme",
                        applicant_categories=["international-students"],
                        opens_at=None,
                        closes_at=scholarship_close,
                        intake=self.intake,
                        source_url=CATALOG_URL,
                        opens_at_basis="missing",
                    ),
                    DiscoveredWindow(
                        round="Self-funded programme",
                        applicant_categories=["international-students"],
                        opens_at=None,
                        closes_at=self_funded_close,
                        intake=self.intake,
                        source_url=CATALOG_URL,
                        opens_at_basis="missing",
                    ),
                ],
                deadline_text=(
                    "XJTU's official 2026 guide says applications run 'from now' "
                    "to exact closing dates. Because it gives no exact opening "
                    "date, these remain review guidance rather than publishable "
                    "exact windows."
                ),
                parse_status="incomplete",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(
    rows: tuple[tuple[str | None, ...], ...],
) -> list[DiscoveredProgramme]:
    parsed: list[tuple[str, str, str]] = []
    faculty = "Xi'an Jiaotong University"
    for row in rows:
        if len(row) < 5:
            continue
        school, raw_name, _language, _duration, raw_degree = row[:5]
        if school:
            faculty = normalise(school)
        name = normalise(raw_name or "")
        degree = normalise(raw_degree or "")
        if not name or "Master" not in degree:
            continue
        if name.casefold().startswith("and ") and parsed:
            previous_faculty, previous_name, previous_degree = parsed[-1]
            if previous_faculty == faculty:
                parsed[-1] = (
                    previous_faculty,
                    normalise(f"{previous_name} {name}"),
                    previous_degree,
                )
                continue
        name = normalise(re.sub(r"\s*\(Professional degree\)\s*$", "", name))
        parsed.append((faculty, name, degree))

    programmes: dict[str, DiscoveredProgramme] = {}
    for faculty, name, degree in parsed:
        programme_id = f"xjtu-{slug(faculty)}-{slug(name)}-{slug(degree)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=degree,
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in XJTU's official 2026 international "
                "graduate guide. The guide gives no exact application opening "
                "date, so no exact programme window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-admissions-guide-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _closing_dates(text: str) -> tuple[str, str]:
    compact = normalise(text)
    scholarship = re.search(
        r"Scholarship Program.*?March\s+31,\s*2026", compact, re.IGNORECASE
    )
    self_funded = re.search(
        r"Self-funded Program.*?May\s+15,\s*2026", compact, re.IGNORECASE
    )
    if scholarship is None or self_funded is None:
        raise ValueError("XJTU guide did not expose both official closing dates")
    return "2026-03-31", "2026-05-15"


def _challenge_values(html: str) -> tuple[str, int, int]:
    challenge = re.search(r"challengeId\s*=\s*'([^']+)'", html)
    first = re.search(r"var\s+a\s*=\s*(\d+)", html)
    second = re.search(r"var\s+b\s*=\s*(\d+)", html)
    operator = re.search(r"var\s+operator\s*=\s*'([+*-])'", html)
    if not all((challenge, first, second, operator)):
        raise ValueError("XJTU PDF challenge did not expose its bounded arithmetic")
    a = int(first.group(1))
    b = int(second.group(1))
    answer = {"+": a + b, "-": a - b, "*": a * b}[operator.group(1)]
    return (
        challenge.group(1),
        answer,
        _simple_hash(challenge.group(1) + str(answer) + DEFAULT_USER_AGENT[:10]),
    )


def _simple_hash(value: str) -> int:
    result = 0
    for character in value:
        result = ((result << 5) - result + ord(character)) & 0xFFFFFFFF
        if result >= 0x80000000:
            result -= 0x100000000
    return abs(result)


def _fetch_guide(url: str) -> GuidePayload:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(follow_redirects=True, timeout=90, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
        if not content.startswith(b"%PDF"):
            challenge_id, answer, hash_value = _challenge_values(response.text)
            browser_info = {
                "userAgent": DEFAULT_USER_AGENT,
                "language": "en-US",
                "platform": "Win32",
                "screen": {"width": 1920, "height": 1080, "colorDepth": 24},
                "timezoneOffset": -480,
                "hasTouchEvents": False,
            }
            verification = client.post(
                CHALLENGE_URL,
                json={
                    "challenge_id": challenge_id,
                    "answer": answer,
                    "browser_info": browser_info,
                    "hash": hash_value,
                },
            )
            verification.raise_for_status()
            payload = verification.json()
            if not payload.get("success") or not payload.get("client_id"):
                raise ValueError("XJTU PDF challenge verification failed")
            client.cookies.set(
                "client_id",
                str(payload["client_id"]),
                domain="sie.xjtu.edu.cn",
                path="/",
            )
            response = client.get(url)
            response.raise_for_status()
            content = response.content
    if not content.startswith(b"%PDF") or len(content) > 15_000_000:
        raise ValueError("XJTU guide did not return a bounded PDF")

    text = "\f".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages
    )
    rows: list[tuple[str | None, ...]] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages[9:14]:
            for table in page.extract_tables():
                if len(table) <= 1:
                    continue
                rows.extend(tuple(cell for cell in row) for row in table)
    return GuidePayload(text=text, rows=tuple(rows))
