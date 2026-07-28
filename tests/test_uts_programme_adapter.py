import pytest

from gradwindow.programme_adapters.uts import UTSAdapter

SITEMAP = """
<urlset>
  <url><loc>https://www.uts.edu.au/courses/master-of-information-technology</loc></url>
  <url><loc>https://www.uts.edu.au/courses/master-of-science</loc></url>
  <url><loc>https://www.uts.edu.au/courses/majors/artificial-intelligence</loc></url>
</urlset>
"""


def test_uts_adapter_reads_master_pages_and_reuses_existing_id() -> None:
    catalog = UTSAdapter(minimum_expected_programmes=2).parse_sitemap(SITEMAP)

    assert [item.name for item in catalog.programmes] == [
        "Master of Information Technology",
        "Master of Science",
    ]
    assert catalog.programmes[0].id == "uts-information-technology-master"
    assert all(item.windows == [] for item in catalog.programmes)


def test_uts_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        UTSAdapter(minimum_expected_programmes=3).parse_sitemap(SITEMAP)
