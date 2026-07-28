import pytest

from gradwindow.programme_adapters.uwa import UWAAdapter

SITEMAP = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.uwa.edu.au/sitecore/content/uwafs/home/courses/master-of-information-technology</loc></url>
  <url><loc>https://www.uwa.edu.au/sitecore/content/uwafs/home/courses/master-of-agricultural-science</loc></url>
  <url><loc>https://www.uwa.edu.au/sitecore/content/uwafs/home/courses/bachelor-of-science</loc></url>
</urlset>
"""


def test_uwa_adapter_reads_master_pages_and_reuses_existing_id() -> None:
    catalog = UWAAdapter(minimum_expected_programmes=2).parse_sitemap(SITEMAP)

    assert [item.name for item in catalog.programmes] == [
        "Master of Agricultural Science",
        "Master of Information Technology",
    ]
    assert catalog.programmes[1].id == "uwa-information-technology-master"
    assert catalog.programmes[0].source_url.startswith("https://www.uwa.edu.au/study/")


def test_uwa_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        UWAAdapter(minimum_expected_programmes=3).parse_sitemap(SITEMAP)
