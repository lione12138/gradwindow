import pytest

from gradwindow.programme_adapters.adelaide import AdelaideAdapter

SITEMAP = """
<urlset>
  <url><loc>https://adelaide.edu.au/study/degrees/master-of-computer-science/</loc></url>
  <url><loc>https://adelaide.edu.au/study/degrees/online/master-of-business-administration/</loc></url>
  <url><loc>https://adelaide.edu.au/study/degrees/master-of-business-administration/</loc></url>
  <url><loc>https://adelaide.edu.au/study/degrees/graduate-certificate-in-business/</loc></url>
</urlset>
"""


def test_adelaide_adapter_reads_master_pages_and_reuses_existing_id() -> None:
    catalog = AdelaideAdapter(minimum_expected_programmes=3).parse_sitemap(SITEMAP)

    assert [item.name for item in catalog.programmes] == [
        "Master of Business Administration",
        "Master of Business Administration (Online)",
        "Master of Computer Science",
    ]
    assert catalog.programmes[2].id == "adelaide-computer-science-master"
    assert all(item.windows == [] for item in catalog.programmes)


def test_adelaide_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 4"):
        AdelaideAdapter(minimum_expected_programmes=4).parse_sitemap(SITEMAP)
