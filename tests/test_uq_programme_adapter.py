from __future__ import annotations

from gradwindow.programme_adapters.uq import CATALOG_URL, UQAdapter

FINDER_HTML = """
<html><body>
  <p>1 - 1 of 1 results</p>
  <article><a href="/study-options/programs/master-information-technology-5581">
    Information Technology</a><span>MASTER OF</span></article>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <h1>Master of Information Technology - 2027</h1>
  <section data-student-type="international">
    <h3>Important dates</h3>
    <p>The closing date for this program is:</p>
    <ul>
      <li>To commence study in semester 2 - May 31 of the year of commencement.</li>
      <li>To commence study in semester 1 - November 30 of the previous year.</li>
    </ul>
  </section>
  <section data-student-type="domestic">
    <h3>Important dates</h3>
    <p>The closing date for this program is:</p>
    <ul>
      <li>To commence study in Semester 1 - January 31 of the year of commencement.</li>
      <li>To commence study in Semester 2 - June 30 of the year of commencement.</li>
    </ul>
  </section>
</body></html>
"""


def test_uq_adapter_discovers_2027_master_programmes_from_degree_finder() -> None:
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        assert not url.endswith(".xml")
        if url == CATALOG_URL:
            return FINDER_HTML
        return DETAIL_HTML

    adapter = UQAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
        detail_fetcher=fetcher,
    )

    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalog.application_opens_at is None
    assert [item.id for item in catalog.programmes] == [
        "uq-information-technology-master-5581"
    ]
    programme = catalog.programmes[0]
    assert programme.name == "Master of Information Technology"
    assert programme.parse_status == "incomplete"
    assert [
        (w.round, w.closes_at, w.applicant_categories, w.opens_at)
        for w in programme.windows
    ] == [
        ("Semester 2", "2027-05-31", ["international-students"], None),
        ("Semester 1", "2026-11-30", ["international-students"], None),
        ("Semester 1", "2027-01-31", ["domestic-students"], None),
        ("Semester 2", "2027-06-30", ["domestic-students"], None),
    ]
    assert fetched == [
        CATALOG_URL,
        "https://study.uq.edu.au/study-options/programs/"
        "master-information-technology-5581?year=2027",
    ]
