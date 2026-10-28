"""UCL's paginated 2027+ directory; no application dates inferred from cards."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .base import (
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
    InconsistentCatalogueError,
)
from .official_catalog import normalise, slug
from .ucl import (
    _EXISTING_IDS,
    CATALOG_URL,
    REVIEWED_PROGRAMME_IDENTITIES,
    programme_name_key,
)

_MASTER = re.compile(r"^(?:Master of .+?|International Master of Arts) \((.+)\)$")
# Explicit non-master labels exposed by the current graduate directory.
# Keep exact matches so an unfamiliar degree still requires review.
_OTHER_REVIEWED_DEGREES = frozenset(
    {"Bachelor of Science (BSc)", "Graduate Diploma (Grad Dip)"}
)


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
    intake_review: list[str] = []
    warnings: list[dict[str, object]] = []
    master_cards = 0
    option_count = 0
    visited_urls: list[str] = []
    while True:
        visited_urls.append(url)
        soup = BeautifulSoup(html, "html.parser")
        counter = soup.select_one(".course-feed-listing-view__result-count")
        match = re.fullmatch(
            r"(\d+) courses found",
            normalise(counter.get_text(" ", strip=True)) if counter else "",
        )
        if not match:
            raise ValueError(
                f"UCL current directory result count missing: page={pages + 1}, url={url}"
            )
        total = int(match[1])
        if expected is None:
            expected = total
        if total != expected or total < minimum_courses:
            raise InconsistentCatalogueError(
                "UCL current directory total changed or is below the expected minimum: "
                f"page={pages + 1}, url={url}, total={total}, "
                f"first_page_total={expected}, minimum={minimum_courses}",
                visited_urls,
            )
        cards = soup.select("article.course-feed-listing-item")
        if not cards:
            raise ValueError(
                f"UCL current directory page has no course cards: page={pages + 1}, url={url}"
            )
        for card in cards:
            heading = card.select_one(".course-feed-listing-item__heading--main")
            badge = card.select_one(".course-feed-listing-item__degree-level")
            title = normalise(heading.get_text(" ", strip=True)) if heading else ""
            degree_label = normalise(badge.get_text(" ", strip=True)) if badge else ""
            context = f"page={pages + 1}, url={url}, title={title!r}"
            if not degree_label and _explicit_unlabelled_doctoral_card(card, title):
                # Match labelled PhD cards for duplicate detection, but never emit
                # this combined doctoral route as a standalone master's programme.
                degree_label = "Doctor of Philosophy (PhD)"
            if not title or not degree_label:
                raise ValueError(f"UCL course card lacks title or degree: {context}")
            key = (title.casefold(), degree_label)
            if key in seen_cards:
                raise InconsistentCatalogueError(
                    f"UCL directory repeated a course card across pages: {context}",
                    visited_urls,
                )
            seen_cards.add(key)
            count += 1
            degree = _MASTER.fullmatch(degree_label)
            if degree is None:
                if not (
                    degree_label.startswith(("Doctor", "Postgraduate"))
                    or degree_label in _OTHER_REVIEWED_DEGREES
                ):
                    raise ValueError(
                        f"UCL unknown degree label: {degree_label}, {context}"
                    )
                continue
            master_cards += 1
            faculty_node = card.select_one(".course-feed-listing-item__faculty")
            faculty = (
                normalise(faculty_node.get_text(" ", strip=True))
                if faculty_node
                else ""
            )
            if not faculty:
                raise ValueError(f"UCL master's card lacks faculty: {context}")
            links = card.select("a[href]")
            coming = "course-feed-listing-item--coming-soon-restricted" in card.get(
                "class", []
            )
            if not links and not coming:
                raise ValueError(
                    f"UCL master's card has no link or explicit coming-soon status: {context}"
                )
            intake_node = card.select_one(".course-feed-listing-item__start-dates")
            intakes = re.findall(
                r"(?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d{2}",
                normalise(intake_node.get_text(" ", strip=True)) if intake_node else "",
            )
            if coming:
                pending.append(title)
            routes = (
                [(title, CATALOG_URL)]
                if not links
                else [
                    (
                        normalise(link.get_text(" ", strip=True)),
                        _course_url(str(link["href"]), context=context),
                    )
                    for link in links
                ]
            )
            option_count += max(0, len(routes) - 1)
            for name, source in routes:
                if not name:
                    raise ValueError(f"UCL empty course route name: {context}")
                path_slug = urlparse(source).path.rsplit("/", 1)[-1]
                option = parse_qs(urlparse(source).query).get("option", [None])[0]
                default_id = (
                    f"ucl-{slug(name)}"
                    if coming
                    else _EXISTING_IDS.get(path_slug, f"ucl-{path_slug}")
                )
                if option:
                    default_id += f"-option-{option.lower()}"
                programme_id = REVIEWED_PROGRAMME_IDENTITIES.get(
                    name
                ) or previous_ids.get(programme_name_key(name), default_id)
                if programme_id in programmes:
                    raise ValueError(
                        f"UCL current directory generated duplicate programme IDs: {context}"
                    )
                if links and not intakes:
                    intake_review.append(programme_id)
                    warnings.append({"sourceUrl": source, "reason": "missing-intake"})
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree[1],
                    faculty=faculty,
                    department="",
                    source_url=source,
                    application_url=source,
                    windows=[],
                    available_intakes=intakes,
                    deadline_text=(
                        "UCL explicitly marks this course Coming soon; its new-cycle detail page and dates are not published."
                        if coming
                        else "UCL's current directory confirms this course but does not specify its intake. The intake requires review before application dates can be checked; no intake or dates were inferred."
                        if not intakes
                        else "UCL's current directory confirms this course and intake. Application dates require programme-specific detail review; directory availability does not mean applications are open."
                    ),
                    parse_status="needs-review"
                    if links and not intakes
                    else "no-deadline",
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
        raise InconsistentCatalogueError(
            f"UCL incomplete pagination: read {count} of {expected} course cards",
            visited_urls,
        )
    if len(programmes) < minimum_programmes:
        raise ValueError("UCL current directory has too few master's programmes")
    return DiscoveredCatalog(
        application_opens_at=None,
        programmes=sorted(programmes.values(), key=lambda p: p.id),
        warnings=warnings,
        diagnostics={
            "directoryPages": pages,
            "directoryCourses": count,
            "masterCourseCards": master_cards,
            "additionalStudyOptions": option_count,
            "comingSoonCourses": pending,
            "intakeReviewProgrammeIds": sorted(intake_review),
            "detailWindowDiscovery": "pending",
            "catalogueComplete": True,
        },
    )


def _explicit_unlabelled_doctoral_card(card: Tag, title: str) -> bool:
    """Accept only an unambiguous combined doctoral route when its badge is absent."""
    if not title.endswith(" MPhil/PhD"):
        return False
    headings = card.select(".course-feed-listing-item__heading--main")
    links = card.select("a[href]")
    if len(headings) != 1 or len(links) != 1:
        return False
    heading_links = headings[0].select("a[href]")
    if (
        len(heading_links) != 1
        or heading_links[0] is not links[0]
        or normalise(links[0].get_text(" ", strip=True)) != title
    ):
        return False
    try:
        url = _course_url(str(links[0]["href"]))
    except ValueError:
        return False
    parsed = urlparse(url)
    return parsed.path.endswith("-mphilphd") and not parsed.query


def _course_url(href: str, *, context: str = "") -> str:
    url = urljoin(CATALOG_URL, href)
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.ucl.ac.uk"
        or parsed.fragment
        or not parsed.path.startswith(urlparse(CATALOG_URL).path + "/")
    ):
        raise ValueError(
            f"UCL current directory has a non-official course URL: {context}"
        )
    query = parse_qs(parsed.query)
    if query and (
        set(query) != {"option"}
        or len(query["option"]) != 1
        or not re.fullmatch(r"[A-Z0-9]+", query["option"][0])
    ):
        raise ValueError(f"UCL course route has an unexpected option query: {context}")
    return url
