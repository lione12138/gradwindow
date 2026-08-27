from __future__ import annotations

import json

import pytest

import gradwindow.programme_adapters.kcl as kcl_module
from gradwindow.programme_adapters.base import OfficialSourceTransportError
from gradwindow.programme_adapters.kcl import (
    CATALOG_URL,
    SITEMAP_URL,
    KCLAdapter,
    _HostRateLimiter,
    _programme_from_slug,
)

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.kcl.ac.uk/sitemaps/study</loc></sitemap>
</sitemapindex>
"""

STUDY_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.kcl.ac.uk/study/postgraduate-taught/courses/clinical-pharmacology-msc</loc></url>
  <url><loc>https://www.kcl.ac.uk/study/postgraduate-taught/courses/advanced-clinical-practice-msc-pg-dip-pg-cert</loc></url>
  <url><loc>https://www.kcl.ac.uk/study/postgraduate-taught/courses/clinical-pharmacology-msc/fees</loc></url>
  <url><loc>https://www.kcl.ac.uk/study/undergraduate/courses/pharmacology-bsc</loc></url>
</urlset>
"""

CLINICAL_PHARMACOLOGY = """
<html><head><title>Clinical Pharmacology MSc - Entry Requirements | King's College London</title></head>
<body>
  <h2>Application closing date guidance</h2>
  <p>The final application deadlines for this programme are:</p>
  <ul>
    <li>Overseas (international) fee status: 25 July 2026 (23:59 UK time)</li>
    <li>Home fee status: 25 August 2026 (23:59 UK time)</li>
  </ul>
  <h2>Taught in</h2><a>Faculty of Life Sciences &amp; Medicine</a>
  <a>School of Cancer &amp; Pharmaceutical Sciences</a>
  <h2>Base campus</h2>
</body></html>
"""

ADVANCED_CLINICAL_PRACTICE = """
<html><head><title>Advanced Clinical Practice MSc, PG Dip - Entry Requirements | King's College London</title></head>
<body>
  <h2>Application closing date guidance</h2>
  <h3>January 2026 intake:</h3>
  <p>Overseas (international) fee status: 20 October 2025 (23:59 UK time)</p>
  <p>Home fee status: 20 November 2025 (23:59 UK time)</p>
  <h3>September 2026 intake:</h3>
  <p>Our first application deadline is on 9 March 2026 (23:59 UK time).</p>
  <p>Overseas (international) fee status: 25 July 2026 (23:59 UK time)</p>
  <p>Home fee status: 25 August 2026 (23:59 UK time)</p>
  <h2>Key Links</h2>
</body></html>
"""

SINGLE_FACULTY = """
<html><head><title>Accounting &amp; Finance - Entry Requirements | King's College London</title></head>
<body>
  <div class="FacultiesAndDepartmentsstyled__FacultiesAndDepartmentsStyled-sc-test">
    <h2>Taught in</h2><a>King’s Business School</a>
  </div>
  <footer><a>Degree courses Footer navigation link</a></footer>
</body></html>
"""

ENDODONTICS = """
<html><head><title>Endodontics MSc | King's College London</title></head>
<body>
  <h2>Application closing date guidance</h2>
  <p>Our first application deadline is on 1 October 2026 (23:59 UK time).
  Where the programme remains open beyond this date, no further applications
  will be accepted after 20 November 2026 (23:59 UK time).</p>
  <p>Please note the course details including entry requirements, fees and
  application deadlines apply to January 2027 entry.</p>
  <h2>Base campus</h2>
</body></html>
"""


def _adapter(**kwargs) -> KCLAdapter:
    return KCLAdapter(
        minimum_interval_seconds=0,
        retry_backoff_seconds=0,
        browser_content_fetcher=None,
        use_environment_browser=False,
        **kwargs,
    )


def test_kcl_defaults_to_three_detail_workers() -> None:
    assert (
        KCLAdapter(
            browser_content_fetcher=None, use_environment_browser=False
        ).detail_workers
        == 3
    )


@pytest.mark.parametrize(
    ("path", "title", "expected_id"),
    [
        (
            "applied-neuroscience-msc",
            "Applied Neuroscience (Online)",
            "kcl-applied-neuroscience-msc-pg-dip-online",
        ),
        (
            "global-security-ma-pg-dip-pg-cert",
            "Global Security (Online)",
            "kcl-global-security-ma-pg-dip-pg-cert-online-ma",
        ),
    ],
)
def test_kcl_keeps_published_ids_when_delivery_titles_change(
    path: str,
    title: str,
    expected_id: str,
) -> None:
    programme = _programme_from_slug(
        f"https://www.kcl.ac.uk/study/postgraduate-taught/courses/{path}",
        catalogue_title=title,
    )

    assert programme is not None
    assert programme.id == expected_id


def test_kcl_rate_limiter_spaces_requests_per_host() -> None:
    now = [10.0]
    sleeps = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = _HostRateLimiter(
        minimum_interval=1.0,
        sleep=sleep,
        monotonic=lambda: now[0],
    )

    limiter.wait("https://www.kcl.ac.uk/one")
    limiter.wait("https://www.kcl.ac.uk/two")
    limiter.wait("https://api-kcl.cloud.contensis.com/three")

    assert sleeps == [1.0]


def test_kcl_retries_transient_detail_failure_before_parsing() -> None:
    adapter = _adapter(
        minimum_expected_programmes=1,
        detail_workers=1,
        detail_attempts=3,
    )
    course_url = (
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/"
        "clinical-pharmacology-msc"
    )
    sitemap = f"<urlset><url><loc>{course_url}</loc></url></urlset>"
    detail_calls = 0

    def fetcher(url: str) -> str:
        nonlocal detail_calls
        if url == SITEMAP_URL:
            return sitemap
        if url == course_url:
            detail_calls += 1
            if detail_calls < 3:
                raise RuntimeError("temporary rate limit")
            return CLINICAL_PHARMACOLOGY
        raise AssertionError(url)

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    assert detail_calls == 3
    assert catalogue.diagnostics["detailRetries"] == 2
    assert catalogue.diagnostics["browserFallbacks"] == 0
    assert catalogue.programmes[0].retrieval_method == "official-html"


def test_kcl_uses_browser_fallback_only_after_detail_retries_fail() -> None:
    course_url = (
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/"
        "clinical-pharmacology-msc"
    )
    detail_url = course_url
    browser_calls = []
    adapter = KCLAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
        detail_attempts=2,
        minimum_interval_seconds=0,
        retry_backoff_seconds=0,
        browser_content_fetcher=lambda url: (
            browser_calls.append(url) or CLINICAL_PHARMACOLOGY
        ),
    )
    sitemap = f"<urlset><url><loc>{course_url}</loc></url></urlset>"
    detail_calls = 0

    def fetcher(url: str) -> str:
        nonlocal detail_calls
        if url == SITEMAP_URL:
            return sitemap
        if url == detail_url:
            detail_calls += 1
            raise RuntimeError("blocked")
        raise AssertionError(url)

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    assert detail_calls == 2
    assert browser_calls == [detail_url]
    assert catalogue.diagnostics["browserFallbacks"] == 1
    assert catalogue.programmes[0].retrieval_method == "cloudflare-browser-rendering"


def test_kcl_prefers_complete_delivery_api_entries_over_detail_crawl() -> None:
    adapter = _adapter(
        minimum_expected_programmes=1,
        minimum_expected_delivery_windows=1,
        detail_workers=1,
    )
    course_url = (
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/endodontics-msc"
    )
    sitemap = f"<urlset><url><loc>{course_url}</loc></url></urlset>"
    catalogue_html = (
        '<html><script src="/_assets/static/startup-1.23.0.js"></script></html>'
    )
    startup_script = """
    var alias = "kcl";
    var config = {api: "https://api-" + alias + ".cloud.contensis.com"};
    context.DELIVERY_API_CONFIG = {accessToken: "public-browser-token"};
    """
    api_payload = json.dumps(
        {
            "totalCount": 1,
            "items": [
                {
                    "sys": {
                        "uri": "/study/postgraduate-taught/courses/endodontics-msc"
                    },
                    "entryTitle": "Endodontics MSc",
                    "applicationClosingDateInfoOverride": (
                        "<h2>Application closing date guidance</h2>"
                        "<p>Our first application deadline is on 1 October 2026. "
                        "No further applications will be accepted after "
                        "20 November 2026.</p>"
                    ),
                    "detailsDisclaimerOverride": (
                        "Application deadlines apply to January 2027 entry."
                    ),
                    "orgUnits": [
                        {
                            "entryTitle": (
                                "Faculty of Dentistry, Oral & Craniofacial Sciences"
                            )
                        }
                    ],
                }
            ],
        }
    )
    calls = []

    def fetcher(url: str) -> str:
        calls.append(url)
        if url == SITEMAP_URL:
            return sitemap
        if url == CATALOG_URL:
            return catalogue_html
        if "startup-1.23.0.js" in url:
            return startup_script
        if "api-kcl.cloud.contensis.com" in url:
            assert "fields=" not in url
            return api_payload
        raise AssertionError(f"detail crawl should not run: {url}")

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalogue.diagnostics["deliveryApiProgrammes"] == 1
    assert catalogue.diagnostics["deliveryApiWindows"] == 2
    assert calls.count(course_url) == 0
    programme = catalogue.programmes[0]
    assert programme.retrieval_method == "official-api"
    assert programme.faculty == "Faculty of Dentistry, Oral & Craniofacial Sciences"
    assert [(window.closes_at, window.intake) for window in programme.windows] == [
        ("2026-10-01", "January 2027"),
        ("2026-11-20", "January 2027"),
    ]


def test_kcl_adapter_reads_sitemap_and_course_specific_deadlines() -> None:
    adapter = _adapter(minimum_expected_programmes=2, detail_workers=1)

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return SITEMAP_INDEX
        if url.endswith("/study"):
            return STUDY_SITEMAP
        if "clinical-pharmacology-msc" in url:
            return CLINICAL_PHARMACOLOGY
        if "advanced-clinical-practice" in url:
            return ADVANCED_CLINICAL_PRACTICE
        raise AssertionError(url)

    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalog.application_opens_at is None
    assert [programme.id for programme in catalog.programmes] == [
        "kcl-advanced-clinical-practice-msc-pg-dip",
        "kcl-clinical-pharmacology-msc",
    ]
    clinical = catalog.programmes[1]
    assert clinical.name == "Clinical Pharmacology MSc"
    assert clinical.degree_type == "MSc"
    assert clinical.parse_status == "incomplete"
    assert clinical.faculty == "Faculty of Life Sciences & Medicine"
    assert [
        (window.applicant_categories, window.closes_at, window.intake)
        for window in clinical.windows
    ] == [
        (["international"], "2026-07-25", "September 2026"),
        (["home"], "2026-08-25", "September 2026"),
    ]

    advanced = catalog.programmes[0]
    assert [
        (window.round, window.applicant_categories, window.closes_at, window.intake)
        for window in advanced.windows
    ] == [
        ("Final application deadline", ["international"], "2025-10-20", "January 2026"),
        ("Final application deadline", ["home"], "2025-11-20", "January 2026"),
        ("First application deadline", ["all"], "2026-03-09", "September 2026"),
        (
            "Final application deadline",
            ["international"],
            "2026-07-25",
            "September 2026",
        ),
        ("Final application deadline", ["home"], "2026-08-25", "September 2026"),
    ]


def test_kcl_reads_single_entry_label_after_deadlines_and_final_cutoff() -> None:
    adapter = _adapter(minimum_expected_programmes=1, detail_workers=1)
    course_url = (
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/endodontics-msc"
    )
    sitemap = f"<urlset><url><loc>{course_url}</loc></url></urlset>"

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return sitemap
        if url == course_url:
            return ENDODONTICS
        raise AssertionError(url)

    programme = adapter.parse_catalog_from_fetcher(fetcher).programmes[0]

    assert [
        (window.round, window.closes_at, window.intake) for window in programme.windows
    ] == [
        ("First application deadline", "2026-10-01", "January 2027"),
        ("Final application deadline", "2026-11-20", "January 2027"),
    ]


def test_kcl_adapter_fails_when_detail_transport_errors_exceed_ten_percent() -> None:
    adapter = _adapter(minimum_expected_programmes=1, detail_workers=1)
    sitemap = """<urlset><url><loc>https://www.kcl.ac.uk/study/postgraduate-taught/courses/artificial-intelligence-msc</loc></url></urlset>"""

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return sitemap
        raise RuntimeError("temporary block")

    with pytest.raises(OfficialSourceTransportError, match="1 of 1.*10%"):
        adapter.parse_catalog_from_fetcher(fetcher)


def test_kcl_adapter_warns_and_lists_small_detail_failure_set() -> None:
    adapter = _adapter(minimum_expected_programmes=10, detail_workers=1)
    urls = [
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/"
        f"example-course-{index}-msc"
        for index in range(10)
    ]
    sitemap = (
        "<urlset>"
        + "".join(f"<url><loc>{url}</loc></url>" for url in urls)
        + "</urlset>"
    )

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return sitemap
        if url == urls[0]:
            raise RuntimeError("temporary block")
        if url in urls:
            number = url.split("example-course-", 1)[1].split("-msc", 1)[0]
            return f"<title>Example Course {number} MSc | King's</title>"
        raise AssertionError(url)

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    assert len(catalogue.programmes) == 10
    assert catalogue.warnings == [
        {
            "reason": "TRANSPORT_ERROR",
            "message": (
                "1 of 10 KCL programme detail pages failed during "
                "discovery; affected programmes were retained without deadlines."
            ),
            "sourceUrl": urls[0],
            "detailFailures": 1,
            "totalDetailPages": 10,
            "failedProgrammeIds": ["kcl-example-course-0-msc"],
        }
    ]


def test_kcl_adapter_classifies_parser_failures_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter(minimum_expected_programmes=10, detail_workers=1)
    urls = [
        "https://www.kcl.ac.uk/study/postgraduate-taught/courses/"
        f"example-course-{index}-msc"
        for index in range(10)
    ]
    sitemap = (
        "<urlset>"
        + "".join(f"<url><loc>{url}</loc></url>" for url in urls)
        + "</urlset>"
    )
    original_parser = kcl_module._parse_programme

    def parser_with_one_dom_failure(course_url: str, *args, **kwargs):
        if course_url == urls[0]:
            raise ValueError("KCL requirements DOM changed")
        return original_parser(course_url, *args, **kwargs)

    monkeypatch.setattr(kcl_module, "_parse_programme", parser_with_one_dom_failure)

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return sitemap
        if url in urls:
            number = url.split("example-course-", 1)[1].split("-msc", 1)[0]
            return f"<title>Example Course {number} MSc | King's</title>"
        raise AssertionError(url)

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    warning = next(
        item for item in catalogue.warnings if item["reason"] == "PARSER_ERROR"
    )
    assert warning["parserFailures"] == 1
    assert warning["failedProgrammeIds"] == ["kcl-example-course-0-msc"]
    assert catalogue.diagnostics["detailFailures"] == 1
    assert catalogue.diagnostics["transportFailures"] == 0
    assert catalogue.diagnostics["parserFailures"] == 1


def test_kcl_adapter_uses_dynamic_delivery_catalogue_when_sitemap_is_stale() -> None:
    adapter = _adapter(minimum_expected_programmes=2, detail_workers=1)
    stale_sitemap = """<urlset><url><loc>https://www.kcl.ac.uk/study-legacy/postgraduate/</loc></url></urlset>"""
    catalogue_html = """
    <html><body>
      <script src="/_assets/static/startup-1.23.0.js"></script>
      <a href="/study/postgraduate-taught/courses/clinical-pharmacology-msc">Clinical Pharmacology</a>
    </body></html>
    """
    startup_script = """
    var alias = "kcl";
    var config = {api: "https://api-" + alias + ".cloud.contensis.com"};
    context.DELIVERY_API_CONFIG = {accessToken: "public-browser-token"};
    """
    api_payload = json.dumps(
        {
            "totalCount": 2,
            "items": [
                {
                    "sys": {
                        "uri": "/study/postgraduate-taught/courses/clinical-pharmacology-msc"
                    },
                    "entryTitle": "Clinical Pharmacology",
                },
                {
                    "sys": {
                        "uri": "/study/postgraduate-taught/courses/artificial-intelligence-msc"
                    },
                    "entryTitle": "Artificial Intelligence",
                },
            ],
        }
    )

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return stale_sitemap
        if url == CATALOG_URL:
            return catalogue_html
        if url.endswith("startup-1.23.0.js"):
            return startup_script
        if "api-kcl.cloud.contensis.com" in url:
            assert "accessToken=public-browser-token" in url
            return api_payload
        if "clinical-pharmacology-msc" in url:
            return CLINICAL_PHARMACOLOGY
        if "artificial-intelligence-msc" in url:
            return "<title>Artificial Intelligence MSc | King's</title>"
        raise AssertionError(url)

    catalogue = adapter.parse_catalog_from_fetcher(fetcher)

    assert [programme.id for programme in catalogue.programmes] == [
        "kcl-artificial-intelligence-msc",
        "kcl-clinical-pharmacology-msc",
    ]
    assert [programme.name for programme in catalogue.programmes] == [
        "Artificial Intelligence MSc",
        "Clinical Pharmacology MSc",
    ]
    assert "apiTotal=2" in adapter.sitemap_diagnostics


def test_kcl_adapter_does_not_treat_footer_links_as_departments() -> None:
    adapter = _adapter(minimum_expected_programmes=1, detail_workers=1)
    sitemap = """<urlset><url><loc>https://www.kcl.ac.uk/study/postgraduate-taught/courses/accounting-finance-msc</loc></url></urlset>"""

    def fetcher(url: str) -> str:
        if url == SITEMAP_URL:
            return sitemap
        if url.endswith("accounting-finance-msc"):
            return SINGLE_FACULTY
        raise AssertionError(url)

    programme = adapter.parse_catalog_from_fetcher(fetcher).programmes[0]

    assert programme.faculty == "King’s Business School"
    assert programme.department == ""
