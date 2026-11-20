from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "peking-university"
CATALOG_URL = (
    "https://www.isd.pku.edu.cn/cn/graduate_do.php?act=majorQuery&termid=2"
    "&departmentid=0&major=&direction=&language=0&degreetype=0&kw="
)
APPLICATION_URL = "https://www.studyatpku.com"
STANDARD_GUIDE_URL = "https://www.isd.pku.edu.cn/cn/detail.php?id=725"
CURRENT_STANDARD_GUIDE_URL = "https://www.isd.pku.edu.cn/en/detail.php?id=839"
YENCHING_PROGRAMME_ID = "pku-yenching-china-studies-master"
YENCHING_SOURCE_URL = "https://yenchingacademy.pku.edu.cn/ADMISSIONS.htm"
YENCHING_APPLICATION_URL = "https://apply.yca.pku.edu.cn/"

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_MONTH_PATTERN = "|".join(month.title() for month in _MONTHS)
_ENGLISH_DATE = rf"(?:{_MONTH_PATTERN})\s+\d{{1,2}},\s*20\d{{2}}"
_ENGLISH_RANGE = re.compile(
    rf"(?P<sm>{_MONTH_PATTERN})\s+(?P<sd>\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*"
    rf"(?P<sy>20\d{{2}})\s*(?:-|–|—|to|until)\s*"
    rf"(?P<em>{_MONTH_PATTERN})\s+(?P<ed>\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*"
    rf"(?P<ey>20\d{{2}})",
    re.I,
)
_CHINESE_RANGE = re.compile(
    r"(?P<sy>20\d{2})\s*年\s*(?P<sm>\d{1,2})\s*月\s*"
    r"(?P<sd>\d{1,2})\s*日?\s*(?:-|–|—|至|到)+\s*"
    r"(?P<ey>20\d{2})\s*年\s*(?P<em>\d{1,2})\s*月\s*"
    r"(?P<ed>\d{1,2})\s*日?"
)


class PekingAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CURRENT_STANDARD_GUIDE_URL, YENCHING_SOURCE_URL)

    def __init__(self, minimum_expected_programmes: int = 180) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        rows = _catalog_rows(fetcher(self.catalog_url))
        masters = [row for row in rows if _is_master(row)]
        variants = _deduplicated_variants(masters)
        language_counts = Counter(
            (variant["department_name"], variant["major"]) for variant in variants
        )
        mode_counts = Counter(
            (
                variant["department_name"],
                variant["major"],
                variant["language_text"],
            )
            for variant in variants
        )

        guide_cache: dict[str, str | None] = {}
        programmes = []
        yenching_rows = [
            variant for variant in variants if variant["department_name"] == "燕京学堂"
        ]
        if yenching_rows:
            programmes.append(_yenching_programme(fetcher))

        for variant in variants:
            if variant["department_name"] == "燕京学堂":
                continue
            programmes.append(
                _programme(
                    variant,
                    show_language=(
                        language_counts[(variant["department_name"], variant["major"])]
                        > 1
                    ),
                    show_mode=(
                        mode_counts[
                            (
                                variant["department_name"],
                                variant["major"],
                                variant["language_text"],
                            )
                        ]
                        > 1
                    ),
                    fetcher=fetcher,
                    guide_cache=guide_cache,
                )
            )

        programmes.sort(key=lambda item: item.name)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "Peking official international-student catalogue only contained "
                f"{len(programmes)} unique master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _catalog_rows(value: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Peking catalogue endpoint did not return JSON") from exc
    rows = payload.get("info", {}).get("list") if isinstance(payload, dict) else None
    if payload.get("code") != 1 or not isinstance(rows, list):
        raise ValueError("Peking catalogue endpoint returned an invalid payload")
    return [row for row in rows if isinstance(row, dict)]


def _is_master(row: dict[str, str]) -> bool:
    return (
        str(row.get("degreetype") or "") == "1" or row.get("degreetype_text") == "硕士"
    )


def _deduplicated_variants(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    variants = {}
    for row in rows:
        required = (
            _normalise(row.get("department_name")),
            _normalise(row.get("major")),
            _normalise(row.get("language_text")),
            _normalise(row.get("learningstyle_text")),
        )
        if not all(required[:3]):
            continue
        variants.setdefault(required, row)
    return list(variants.values())


def _programme(
    row: dict[str, str],
    *,
    show_language: bool,
    show_mode: bool,
    fetcher: Callable[[str], str],
    guide_cache: dict[str, str | None],
) -> DiscoveredProgramme:
    department = _normalise(row.get("department_name"))
    major = _normalise(row.get("major"))
    language = _normalise(row.get("language_text"))
    mode = _normalise(row.get("learningstyle_text"))
    guide_url = _normalise(row.get("recruitment1")) or CATALOG_URL
    if _is_standard_guide(guide_url):
        guide_url = CURRENT_STANDARD_GUIDE_URL
    name = major
    qualifiers = []
    if show_language:
        qualifiers.append(f"{language}授课")
    if show_mode:
        qualifiers.append(mode)
    if qualifiers:
        name = f"{name}（{'，'.join(qualifiers)}）"

    windows, deadline_text = _windows_for_guide(
        guide_url,
        language=language,
        fetcher=fetcher,
        guide_cache=guide_cache,
    )
    canonical = "|".join((department, major, language, mode))
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
    return DiscoveredProgramme(
        id=f"pku-master-{digest}",
        name=name,
        degree_type="Master",
        faculty=department,
        department="",
        source_url=guide_url,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=deadline_text,
        parse_status="parsed" if windows else "no-deadline",
        retrieval_method="official-api+page",
        evidence_quality="official-full-text",
    )


def _yenching_programme(
    fetcher: Callable[[str], str],
) -> DiscoveredProgramme:
    text = _page_text(fetcher(YENCHING_SOURCE_URL))
    windows = _yenching_windows(text)
    deadline_text = (
        " ".join(
            f"{w.applicant_categories[0]}, {w.intake}: {w.opens_at} to {w.closes_at}, Beijing time."
            for w in windows
        )
        or "The official Yenching page lacks a complete audience-specific application period."
    )
    return DiscoveredProgramme(
        id=YENCHING_PROGRAMME_ID,
        name="Yenching Academy Master's in China Studies",
        degree_type="Master",
        faculty="Yenching Academy",
        department="",
        source_url=YENCHING_SOURCE_URL,
        application_url=YENCHING_APPLICATION_URL,
        windows=windows,
        deadline_text=deadline_text,
        parse_status="parsed" if windows else "no-deadline",
        retrieval_method="official-api+page",
        evidence_quality="official-full-text",
    )


def _yenching_windows(text: str) -> list[DiscoveredWindow]:
    text = re.sub(r"\ba\s+pplications\b", "applications", text, flags=re.I)
    sections = re.split(
        r"For (Mainland Chinese Candidates|International Candidates|Candidates from China[’']s Hong Kong, Macao and Taiwan Regions)\s*:",
        text,
        flags=re.I,
    )
    windows = []
    for heading, section in zip(sections[1::2], sections[2::2], strict=True):
        if heading.casefold().startswith("mainland"):
            continue
        opening = re.search(
            rf"applications for the (20\d{{2}}) cohort of Yenching Scholars starting ({_ENGLISH_DATE})",
            section,
            re.I,
        )
        closing = (
            re.match(
                rf"\s*\.?\s*Application deadline\s*:\s*({_ENGLISH_DATE})",
                section[opening.end() :],
                re.I,
            )
            if opening
            else None
        )
        if not opening or not closing:
            continue
        year = int(opening[1])
        opens_at = datetime.strptime(opening[2], "%B %d, %Y").date()
        closes_at = datetime.strptime(closing[1], "%B %d, %Y").date()
        if not (
            opens_at.year == year - 1
            and opens_at <= closes_at
            and closes_at.year in {year - 1, year}
        ):
            continue
        category = (
            "international-students"
            if heading.casefold().startswith("international")
            else "pku-hong-kong-macao-taiwan"
        )
        windows.append(
            DiscoveredWindow(
                round="Main round",
                intake=f"Autumn {year}",
                opens_at=opens_at.isoformat(),
                closes_at=closes_at.isoformat(),
                applicant_categories=[category],
                source_url=YENCHING_SOURCE_URL,
                opens_at_basis="official",
            )
        )
    return windows


def _is_standard_guide(url: str) -> bool:
    return _is_isd_page(url) and urlparse(url).query in {"id=725", "id=839"}


def standard_international_period(html: str) -> tuple[str, str, str]:
    text = _page_text(html)
    title = re.search(
        r"(20\d{2}) Application Information for International Students", text, re.I
    )
    period = re.search(
        r"Application Period \(Beijing time\)\s+(.+?)\s+(?:Note:|\d+\. Application Materials)",
        text,
        re.I,
    )
    ranges = _date_ranges(period[1], "中文") if period else []
    if not title or len(ranges) != 1:
        raise ValueError(
            "PKU standard guide lacks a single official international application period"
        )
    opens, closes = ranges[0]
    if (
        opens > closes
        or opens[:4] != str(int(title[1]) - 1)
        or closes[:4] not in {opens[:4], title[1]}
    ):
        raise ValueError("PKU standard guide dates do not match the intake")
    return f"Autumn {title[1]}", opens, closes


def _windows_for_guide(
    guide_url: str,
    *,
    language: str,
    fetcher: Callable[[str], str],
    guide_cache: dict[str, str | None],
) -> tuple[list[DiscoveredWindow], str]:
    if not _is_isd_page(guide_url):
        return [], (
            "The official catalogue links to a separate PKU programme site. No "
            "fully explicit opening-and-closing date range was parsed from the "
            "central catalogue, so this programme remains monitored."
        )
    if guide_url not in guide_cache:
        try:
            guide_cache[guide_url] = fetcher(guide_url)
        except Exception:
            guide_cache[guide_url] = None
    html = guide_cache[guide_url]
    if not html:
        return [], (
            "The official programme guide could not be retrieved during this "
            "run. No application dates were inferred."
        )

    text = _page_text(html)
    if _is_standard_guide(guide_url) and language != "中文":
        return [], (
            "PKU's standard international guide explicitly says English-taught "
            "master's programmes use their own deadlines; no separate exact "
            "range was found for this catalogue record."
        )
    if guide_url == CURRENT_STANDARD_GUIDE_URL:
        intake, opens_at, closes_at = standard_international_period(html)
        ranges = [(opens_at, closes_at)]
    else:
        intake = None
        ranges = _date_ranges(text, language)
    if not ranges:
        return [], (
            "The official programme guide was checked, but it did not provide a "
            "fully explicit opening-and-closing date range. No dates were inferred."
        )

    intake = intake or _intake_from_guide(text)
    windows = [
        DiscoveredWindow(
            round=("Main round" if len(ranges) == 1 else f"Round {index}"),
            intake=intake,
            opens_at=opens_at,
            closes_at=closes_at,
            applicant_categories=["international-students"],
            source_url=guide_url,
        )
        for index, (opens_at, closes_at) in enumerate(ranges, start=1)
    ]
    evidence = "; ".join(f"{start} to {end}" for start, end in ranges)
    return windows, (
        "PKU's official programme guide provides the following fully explicit "
        f"application period(s): {evidence}."
    )


def _intake_from_guide(text: str) -> str:
    patterns = (
        r"北京大学[^。]{0,120}?(20\d{2})\s*年[^。]{0,100}(?:招生简章|招生说明)",
        r"(?:for|Fall|Entry|Intake)\s+(20\d{2})",
        r"(20\d{2})\s+(?:Entry|Admission|Intake|Application)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match is not None:
            return f"Autumn {match.group(1)}"
    raise ValueError(
        "PKU official programme guide contained exact application dates but no "
        "explicit intake year"
    )


def _date_ranges(text: str, language: str) -> list[tuple[str, str]]:
    ranges = []
    for match in _CHINESE_RANGE.finditer(text):
        context = text[max(0, match.start() - 100) : match.start()]
        if not _language_matches(context, language):
            continue
        ranges.append(
            (
                _iso_date(match, "s", chinese=True),
                _iso_date(match, "e", chinese=True),
            )
        )
    for match in _ENGLISH_RANGE.finditer(text):
        context = text[max(0, match.start() - 100) : match.start()]
        if not _language_matches(context, language):
            continue
        ranges.append(
            (
                _iso_date(match, "s", chinese=False),
                _iso_date(match, "e", chinese=False),
            )
        )
    return sorted(set(ranges))


def _language_matches(context: str, language: str) -> bool:
    lower = context.lower()
    english_positions = (lower.rfind("english-taught"), context.rfind("英文项目"))
    chinese_positions = (lower.rfind("chinese-taught"), context.rfind("中文项目"))
    english_label = max(english_positions)
    chinese_label = max(chinese_positions)
    if english_label >= 0 or chinese_label >= 0:
        closest_language = "英文" if english_label > chinese_label else "中文"
        return language == closest_language
    return True


def _iso_date(match: re.Match[str], prefix: str, *, chinese: bool) -> str:
    year = int(match.group(f"{prefix}y"))
    month_value = match.group(f"{prefix}m")
    month = int(month_value) if chinese else _MONTHS[month_value.lower()]
    day = int(match.group(f"{prefix}d"))
    return date(year, month, day).isoformat()


def _is_isd_page(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "isd.pku.edu.cn" or host == "www.isd.pku.edu.cn"


def _page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    text = _normalise(main.get_text(" ", strip=True))
    return re.sub(r"(?<=\d)\s+(?=\d)", "", text)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
