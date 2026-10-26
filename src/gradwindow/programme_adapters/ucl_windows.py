"""Strict parsing of UCL's scoped, current application-date panels."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from .base import DiscoveredProgramme, DiscoveredWindow
from .official_catalog import normalise
from .ucl import programme_name_key

_CATEGORIES = {
    "Applicants who require a visa": "requires-uk-study-visa",
    "Applicants who do not require a visa": "does-not-require-uk-study-visa",
    "All applicants": "all",
}
_MONTHS = "January February March April May June July August September October November December".split()
_DATE = r"\d{1,2} [A-Za-z]+ 20\d{2}"


def _date(text: str) -> date:
    day, month, year = text.split()
    matches = [i for i, name in enumerate(_MONTHS, 1) if month in (name, name[:3])]
    if len(matches) != 1:
        raise ValueError("UCL unrecognised calendar month")
    return date(int(year), matches[0], int(day))


def _gate_dates(node) -> set[tuple[str, str]]:
    """Check UTC timestamps against printed UK dates without inferring dates."""
    result = set()
    for pair in node.get("data-application-windows", "").split(","):
        if not re.fullmatch(r"\d{10}:\d{10}", pair):
            raise ValueError("UCL application gate lacks exact dates")
        start, end = [
            datetime.fromtimestamp(int(v), timezone.utc) for v in pair.split(":")
        ]
        if start >= end:
            raise ValueError("UCL application gate dates are reversed")
        # UCL opens at midnight UK time: 23:00 UTC during BST, 00:00 during GMT.
        if (start.hour, start.minute, start.second) not in ((23, 0, 0), (0, 0, 0)):
            raise ValueError("UCL application opening time needs review")
        start_date = (start + timedelta(hours=1) if start.hour == 23 else start).date()
        if (end.hour, end.minute, end.second) not in ((16, 0, 0), (17, 0, 0)):
            raise ValueError("UCL application closing time needs review")
        result.add((start_date.isoformat(), end.date().isoformat()))
    return result


def exact_windows(
    key_information, apply, programme: DiscoveredProgramme
) -> list[DiscoveredWindow]:
    """Accept only identical study-mode panels and a matching official apply gate."""
    if len(programme.available_intakes) != 1:
        raise ValueError("UCL exact windows require one unambiguous intake")
    intake = programme.available_intakes[0]
    if not re.fullmatch(r"[A-Za-z]+ 20\d{2}", intake):
        raise ValueError("UCL intake is not an explicit month and year")
    intake_start = _date("1 " + intake)
    panels = []
    for item in key_information.select(".key-info-item"):
        label = item.select_one(".key-info-item__label")
        if (
            not label
            or normalise(label.get_text(" ", strip=True)) != "Application deadlines"
        ):
            continue
        value = item.select_one(".key-info-item__value")
        groups = value.select(".key-info-item__group") if value else []
        if not groups:
            raise ValueError("UCL deadline groups are missing")
        panel = {}
        for group in groups:
            label = group.select_one(".key-info-item__group-label")
            category = _CATEGORIES.get(
                normalise(label.get_text(" ", strip=True)) if label else ""
            )
            if not category or category in panel:
                raise ValueError("UCL applicant scope is unknown or duplicated")
            text = normalise(group.get_text(" ", strip=True))
            match = re.fullmatch(
                re.escape(normalise(label.get_text(" ", strip=True)))
                + rf" ({_DATE}) [-–] ({_DATE}) Applications close at 5pm UK time",
                text,
            )
            if not match:
                raise ValueError("UCL deadline wording needs review")
            opens, closes = _date(match[1]), _date(match[2])
            if (
                opens > closes
                or opens >= intake_start
                or closes.year not in (intake_start.year - 1, intake_start.year)
            ):
                raise ValueError("UCL application dates do not match the intake")
            panel[category] = (opens.isoformat(), closes.isoformat())
        if "all" in panel and len(panel) != 1:
            raise ValueError("UCL overlapping applicant scopes")
        badges = item.select("[data-application-windows]")
        if not badges or any(
            node.get("data-application-rolling") != "0"
            or _gate_dates(node) != set(panel.values())
            for node in badges
        ):
            raise ValueError("UCL printed dates disagree with the deadline badge")
        panels.append(panel)
    if not panels or any(panel != panels[0] for panel in panels):
        raise ValueError("UCL study modes have different or missing deadlines")
    gates = apply.select(".apply-chooser__controls[data-application-windows]")
    if len(gates) != 1 or _gate_dates(gates[0]) != set(panels[0].values()):
        raise ValueError("UCL apply gate disagrees with the deadline panel")
    routes = apply.select("a.apply-chooser__fallback-link[href]") or apply.select(
        "a.apply-chooser__button[href]"
    )
    if not routes:
        raise ValueError("UCL official application routes are unavailable")
    for route in routes:
        parsed = urlparse(route["href"])
        route_label = route.get("aria-label") or route.get_text(" ", strip=True)
        route_match = re.fullmatch(
            r"(?:Apply for this course: )?(.+) (Full-time|Part-time|Flexible), (.+)",
            normalise(route_label),
        )
        if (
            parsed.scheme != "https"
            or parsed.netloc != "evision.ucl.ac.uk"
            or not route_match
            or route_match[3] != intake
            or programme_name_key(route_match[1]) != programme_name_key(programme.name)
        ):
            raise ValueError("UCL application route does not identify this intake")
    return [
        DiscoveredWindow(
            round="Application period",
            opens_at=opens,
            closes_at=closes,
            applicant_categories=[category],
            intake=intake,
            source_url=programme.source_url,
            opens_at_basis="official",
        )
        for category, (opens, closes) in sorted(panels[0].items())
    ]
