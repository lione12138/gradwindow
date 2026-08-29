from __future__ import annotations

from gradwindow.programme_adapters.caltech import (
    AEROSPACE_ADMISSIONS_URL,
    AEROSPACE_URL,
    APPLICATION_URL,
    ELECTRICAL_ENGINEERING_URL,
    CaltechAdapter,
)

AEROSPACE_HTML = """
<html><body><main>
  <h1>Aerospace (AE)</h1>
  <h2>Admission</h2>
  <p>Students whose highest qualification is a baccalaureate degree are
  eligible to seek admission to work toward the master's degree.</p>
  <h2>Master's Degree in Aeronautics and Master's Degree in Space Engineering</h2>
  <p>The master's degree program in aeronautics or space engineering is a
  one-year program.</p>
</main></body></html>
"""

ELECTRICAL_ENGINEERING_HTML = """
<html><body><main>
  <h1>Electrical Engineering (EE)</h1>
  <h2>EE Master's Degree</h2>
  <p>The principal criteria for evaluating applicants for the MSEE are the
  excellence of their preparation.</p>
  <p>Students who have been admitted to the M.S.-only program must reapply if
  they are interested in the Ph.D. program.</p>
</main></body></html>
"""

APPLICATION_HTML = """
<html><body><main>
  <h1>Apply Online</h1>
  <p>Our application for the 2027-2028 academic year will be available in
  early October.</p>
  <p>Check the Application Deadlines for the particular academic program.</p>
  <p>Deadlines vary by program from December 1 to December 15.</p>
</main></body></html>
"""

AEROSPACE_ADMISSIONS_HTML = """
<html><body><main>
  <h1>Admissions</h1>
  <p>Students are admitted only for the academic year beginning in September;
  the deadline for applications is December 15.</p>
</main></body></html>
"""


def _fetcher(url: str) -> str:
    if url == AEROSPACE_URL:
        return AEROSPACE_HTML
    if url == ELECTRICAL_ENGINEERING_URL:
        return ELECTRICAL_ENGINEERING_HTML
    if url == APPLICATION_URL:
        return APPLICATION_HTML
    if url == AEROSPACE_ADMISSIONS_URL:
        return AEROSPACE_ADMISSIONS_HTML
    raise AssertionError(url)


def test_caltech_adapter_keeps_only_direct_entry_masters_programmes() -> None:
    catalog = CaltechAdapter().parse_catalog_from_fetcher(_fetcher)

    assert catalog.application_opens_at is None
    assert [programme.id for programme in catalog.programmes] == [
        "caltech-aeronautics-ms",
        "caltech-electrical-engineering-ms",
        "caltech-space-engineering-ms",
    ]
    assert [programme.name for programme in catalog.programmes] == [
        "MS Aeronautics",
        "MS Electrical Engineering",
        "MS Space Engineering",
    ]
    programmes = {programme.id: programme for programme in catalog.programmes}
    assert programmes["caltech-electrical-engineering-ms"].windows == []
    assert programmes["caltech-electrical-engineering-ms"].parse_status == "no-deadline"
    for programme_id in ("caltech-aeronautics-ms", "caltech-space-engineering-ms"):
        programme = programmes[programme_id]
        assert programme.parse_status == "incomplete"
        assert len(programme.windows) == 1
        assert programme.windows[0].intake == "Fall 2027"
        assert programme.windows[0].opens_at is None
        assert programme.windows[0].closes_at == "2026-12-15"


def test_caltech_does_not_fetch_the_blocked_xml_sitemap() -> None:
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        assert not url.endswith(".xml")
        return _fetcher(url)

    CaltechAdapter().parse_catalog_from_fetcher(fetcher)

    assert fetched == [
        AEROSPACE_URL,
        ELECTRICAL_ENGINEERING_URL,
        APPLICATION_URL,
        AEROSPACE_ADMISSIONS_URL,
    ]


def test_caltech_adapter_rejects_missing_direct_admission_evidence() -> None:
    def fetcher(url: str) -> str:
        if url == ELECTRICAL_ENGINEERING_URL:
            return "<html><body><h1>Electrical Engineering</h1></body></html>"
        return _fetcher(url)

    try:
        CaltechAdapter().parse_catalog_from_fetcher(fetcher)
    except ValueError as exc:
        assert "direct-entry master's programmes" in str(exc)
    else:
        raise AssertionError("Incomplete Caltech catalogue was accepted")
