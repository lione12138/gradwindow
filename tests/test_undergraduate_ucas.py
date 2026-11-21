import pytest

from gradwindow.http_client import FetchedPage
from gradwindow.undergraduate_ucas import UcasSources, discover_undergraduate_ucas

SUBMISSION = "https://www.ucas.com/events/submission"
CONSIDERATION = "https://www.ucas.com/events/equal-consideration"
SCHOOL = "https://example.edu/undergraduate/apply"
SCHOOLS = [{"id": "example-university", "officialDomains": ["example.edu"]}]


def settings() -> UcasSources:
    return UcasSources.model_validate(
        {
            "entryYear": 2027,
            "submissionEvent": SUBMISSION,
            "equalConsiderationEvent": CONSIDERATION,
            "routes": [
                {
                    "universityId": "example-university",
                    "routeId": "standard-ucas",
                    "scope": "Standard UCAS entry",
                    "scopeZh": "本科 UCAS 常规申请",
                    "applicantScope": "international-and-domestic",
                    "sourceUrl": SCHOOL,
                    "eligibilityUrl": SCHOOL,
                    "deadlinePattern": "equal consideration is {date}",
                    "eligibilityPattern": "International applicants apply via UCAS",
                }
            ],
        }
    )


def event(heading: str, value: str, description: str) -> str:
    return (
        f'<main><h1>{heading}</h1><ul class="header__list">'
        f"<li><span>{value}</span></li></ul><p>{description}</p></main>"
    )


@pytest.fixture
def pages() -> dict[str, str]:
    return {
        SUBMISSION: event(
            "2027 entry UCAS applications can be submitted",
            "1 September 2026",
            "You can pay and send your completed application to UCAS.",
        ),
        CONSIDERATION: event(
            "2027 entry deadline for all undergraduate courses, except early deadlines",
            "13 January 2027",
            "This is our equal consideration deadline.",
        ),
        SCHOOL: """<main>
            <p>For 2027 entry, the closing date for equal consideration is
            <strong>13 January 2027</strong>.</p>
            <p>Medicine and Dentistry have an earlier 15 October 2026 deadline.</p>
            <p>International applicants apply via UCAS in the same way as UK applicants.</p>
            </main>""",
    }


def fake_fetcher(pages: dict[str, str]):
    def fetch(url: str) -> FetchedPage:
        html = pages[url]
        raw = html.encode()
        return FetchedPage(html, raw, url, 200, "text/html", "utf-8", len(raw), False)

    return fetch


def test_ucas_discovery_uses_submission_date_and_checks_school_deadline(pages):
    report = discover_undergraduate_ucas(
        settings(), SCHOOLS, [], fetcher=fake_fetcher(pages)
    )
    assert report["needsReview"] == []
    (candidate,) = report["candidates"]
    assert candidate["reviewStatus"] == "pending"
    record = candidate["record"]
    assert record["opensAt"] == "2026-09-01"
    assert record["closesAt"] == "2027-01-13"
    assert record["openingSourceUrl"] == SUBMISSION
    assert record["sourceUrl"] == SCHOOL
    assert "verifiedAt" not in record

    reviewed = {
        **record,
        "evidence": "Reviewed university evidence",
        "verifiedAt": "2026-11-21",
    }
    refreshed = discover_undergraduate_ucas(
        settings(), SCHOOLS, [reviewed], fetcher=fake_fetcher(pages)
    )
    assert refreshed["candidates"][0]["reviewStatus"] == "unchanged"


@pytest.mark.parametrize(
    ("old", "replacement", "reason"),
    [
        ("13 January 2027", "14 January 2027", "must match"),
        ("13 January 2027", "January 2027", "must match"),
        ("13 January 2027", "13 January 2026", "must match"),
        (
            "International applicants apply via UCAS",
            "UK applicants apply via UCAS",
            "no evidence",
        ),
        (
            "International applicants apply via UCAS",
            "<script>International applicants apply via UCAS</script>",
            "no evidence",
        ),
    ],
)
def test_ucas_discovery_sends_ambiguous_or_domestic_routes_to_review(
    pages, old, replacement, reason
):
    pages[SCHOOL] = pages[SCHOOL].replace(old, replacement)
    report = discover_undergraduate_ucas(
        settings(), SCHOOLS, [], fetcher=fake_fetcher(pages)
    )
    assert report["candidates"] == []
    assert reason in report["needsReview"][0]["reason"]


def test_ucas_discovery_rejects_fill_in_opening_event(pages):
    pages[SUBMISSION] = event(
        "2027 entry undergraduate applications open",
        "12 May 2026",
        "Students can start their applications.",
    )
    with pytest.raises(ValueError, match="UCAS event title"):
        discover_undergraduate_ucas(
            settings(), SCHOOLS, [], fetcher=fake_fetcher(pages)
        )
