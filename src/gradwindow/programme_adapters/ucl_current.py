"""UCL's paginated 2027+ directory; no application dates inferred from cards."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug
from .ucl import _EXISTING_IDS, CATALOG_URL

_MASTER = re.compile(r"^(?:Master of .+?|International Master of Arts) \((.+)\)$")


def discover_current_catalogue(
    first_html: str,
    fetcher: Fetcher,
    *,
    previous_ids: dict[str, str],
    minimum_courses: int,
    minimum_programmes: int,
) -> DiscoveredCatalog:
    url, html = CATALOG_URL, first_html
    pages, count, expected = 0, 0, None
    seen_cards: set[tuple[str, str]] = set()
    programmes: dict[str, DiscoveredProgramme] = {}
    pending: list[str] = []
    master_cards = 0
    option_count = 0
    while True:
        soup = BeautifulSoup(html, "html.parser")
        counter = soup.select_one(".course-feed-listing-view__result-count")
        match = re.fullmatch(
            r"(\d+) courses found",
            normalise(counter.get_text(" ", strip=True)) if counter else "",
        )
        if not match:
            raise ValueError("UCL current directory result count missing")
        total = int(match[1])
        if expected is None:
            expected = total
        if total != expected or total < minimum_courses:
            raise ValueError(
                "UCL current directory total changed or is below the expected minimum"
            )
        cards = soup.select("article.course-feed-listing-item")
        if not cards:
            raise ValueError("UCL current directory page has no course cards")
        for card in cards:
            heading = card.select_one(".course-feed-listing-item__heading--main")
            badge = card.select_one(".course-feed-listing-item__degree-level")
            title = normalise(heading.get_text(" ", strip=True)) if heading else ""
            degree_label = normalise(badge.get_text(" ", strip=True)) if badge else ""
            if not title or not degree_label:
                raise ValueError("UCL course card lacks title or degree")
            key = (title.casefold(), degree_label)
            if key in seen_cards:
                raise ValueError("UCL directory repeated a course card across pages")
            seen_cards.add(key)
            count += 1
            degree = _MASTER.fullmatch(degree_label)
            if degree is None:
                if not degree_label.startswith(("Doctor", "Postgraduate")):
                    raise ValueError(f"UCL unknown degree label: {degree_label}")
                continue
            master_cards += 1
            faculty_node = card.select_one(".course-feed-listing-item__faculty")
            faculty = (
                normalise(faculty_node.get_text(" ", strip=True))
                if faculty_node
                else ""
            )
            if not faculty:
                raise ValueError("UCL master's card lacks faculty")
            links = card.select("a[href]")
            coming = "course-feed-listing-item--coming-soon-restricted" in card.get(
                "class", []
            )
            if not links and not coming:
                raise ValueError(
                    "UCL master's card has no link or explicit coming-soon status"
                )
            intake_node = card.select_one(".course-feed-listing-item__start-dates")
            intakes = re.findall(
                r"(?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d{2}",
                normalise(intake_node.get_text(" ", strip=True)) if intake_node else "",
            )
            if links and not intakes:
                raise ValueError("UCL linked master's course has no explicit intake")
            if coming:
                pending.append(title)
            routes = (
                [(title, CATALOG_URL)]
                if not links
                else [
                    (
                        normalise(link.get_text(" ", strip=True)),
                        _course_url(str(link["href"])),
                    )
                    for link in links
                ]
            )
            option_count += max(0, len(routes) - 1)
            for name, source in routes:
                if not name:
                    raise ValueError("UCL empty course route name")
                path_slug = urlparse(source).path.rsplit("/", 1)[-1]
                option = parse_qs(urlparse(source).query).get("option", [None])[0]
                default_id = (
                    f"ucl-{slug(name)}"
                    if coming
                    else _EXISTING_IDS.get(path_slug, f"ucl-{path_slug}")
                )
                if option:
                    default_id += f"-option-{option.lower()}"
                programme_id = previous_ids.get(name.casefold(), default_id)
                if programme_id in programmes:
                    raise ValueError(
                        "UCL current directory generated duplicate programme IDs"
                    )
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree[1],
                    faculty=faculty,
                    department=faculty,
                    source_url=source,
                    application_url=source,
                    windows=[],
                    available_intakes=intakes,
                    deadline_text=(
                        "UCL explicitly marks this course Coming soon; its new-cycle detail page and dates are not published."
                        if coming
                        else "UCL's current directory confirms this course and intake. Application dates require programme-specific detail review; directory availability does not mean applications are open."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-current-graduate-directory-html",
                    evidence_quality="official-full-text",
                )
        pages += 1
        next_link = soup.select_one('nav.pager a[rel="next"]')
        if next_link is None:
            break
        if pages >= 40:
            raise ValueError("UCL directory exceeded the reviewed 40-page budget")
        next_url = urljoin(url, str(next_link.get("href", "")))
        parsed = urlparse(next_url)
        if (parsed.scheme, parsed.netloc, parsed.path) != (
            "https",
            "www.ucl.ac.uk",
            urlparse(CATALOG_URL).path,
        ) or parse_qs(parsed.query) != {"page": [str(pages)]}:
            raise ValueError("UCL directory has an unexpected next-page URL")
        url = next_url
        html = fetcher(url)
    if count != expected:
        raise ValueError(
            f"UCL incomplete pagination: read {count} of {expected} course cards"
        )
    if len(programmes) < minimum_programmes:
        raise ValueError("UCL current directory has too few master's programmes")
    return DiscoveredCatalog(
        application_opens_at=None,
        programmes=sorted(programmes.values(), key=lambda p: p.id),
        diagnostics={
            "directoryPages": pages,
            "directoryCourses": count,
            "masterCourseCards": master_cards,
            "additionalStudyOptions": option_count,
            "comingSoonCourses": pending,
            "detailWindowDiscovery": "pending",
        },
    )


def _course_url(href: str) -> str:
    url = urljoin(CATALOG_URL, href)
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.ucl.ac.uk"
        or parsed.fragment
        or not parsed.path.startswith(urlparse(CATALOG_URL).path + "/")
    ):
        raise ValueError("UCL current directory has a non-official course URL")
    query = parse_qs(parsed.query)
    if query and (
        set(query) != {"option"}
        or len(query["option"]) != 1
        or not re.fullmatch(r"[A-Z0-9]+", query["option"][0])
    ):
        raise ValueError("UCL course route has an unexpected option query")
    return url
