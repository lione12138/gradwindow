from __future__ import annotations

import pytest

from gradwindow.programme_adapters.helsinki import (
    APPLICATION_URL,
    CATALOG_URL,
    INTERNATIONAL_PROGRAMMES_URL,
    HelsinkiAdapter,
)

SITEMAP_URL = "https://www.helsinki.fi/sitemap-degree-programmes.xml"
DATA_SCIENCE_URL = (
    "https://www.helsinki.fi/en/degree-programmes/data-science-masters-programme"
)
FINNISH_URL = (
    "https://www.helsinki.fi/en/degree-programmes/"
    "finnish-and-finno-ugrian-languages-and-cultures-masters-programme"
)
ESCAPED_DATA_SCIENCE_URL = DATA_SCIENCE_URL.replace("/", "\\/")

SITEMAP_INDEX = f"""
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>{SITEMAP_URL}</loc></sitemap>
</sitemapindex>
"""
PROGRAMME_SITEMAP = f"""
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{DATA_SCIENCE_URL}</loc></url>
  <url><loc>{FINNISH_URL}</loc></url>
</urlset>
"""
INTERNATIONAL_LIST = f"""
<html><body>
  <hy-link-list data-items='[{{&quot;heading&quot;:&quot;Learn more&quot;,
    &quot;url&quot;:&quot;{ESCAPED_DATA_SCIENCE_URL}&quot;}}]'>
  </hy-link-list>
</body></html>
"""
APPLICATION_PAGE = """
<html><body>
  <p>The application period for studies starting in autumn 2027 is from
  5 to 19 Jan 2027.</p>
  <p>International Master's Programmes only have one intake per academic year.</p>
</body></html>
"""


def _adapter() -> HelsinkiAdapter:
    adapter = HelsinkiAdapter()
    adapter.minimum_expected_programmes = 2
    adapter.minimum_expected_international_programmes = 1
    return adapter


def _fetcher(url: str) -> str:
    documents = {
        CATALOG_URL: SITEMAP_INDEX,
        SITEMAP_URL: PROGRAMME_SITEMAP,
        INTERNATIONAL_PROGRAMMES_URL: INTERNATIONAL_LIST,
        APPLICATION_URL: APPLICATION_PAGE,
    }
    return documents[url]


def test_helsinki_attaches_central_window_only_to_international_masters() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)

    assert len(catalog.programmes) == 2
    data_science = next(
        item for item in catalog.programmes if "Data Science" in item.name
    )
    finnish = next(item for item in catalog.programmes if "Finnish" in item.name)

    assert data_science.admission_route == "direct-master"
    assert data_science.parse_status == "parsed"
    assert len(data_science.windows) == 1
    assert data_science.windows[0].opens_at == "2027-01-05"
    assert data_science.windows[0].closes_at == "2027-01-19"
    assert data_science.windows[0].intake == "Autumn 2027"
    assert data_science.windows[0].source_url == APPLICATION_URL
    assert data_science.windows[0].opens_at_basis == "official"
    assert finnish.windows == []
    assert finnish.parse_status == "no-deadline"


def test_helsinki_rejects_a_truncated_international_programme_list() -> None:
    adapter = _adapter()
    adapter.minimum_expected_international_programmes = 2

    with pytest.raises(ValueError, match="only contained 1 International"):
        adapter.parse_catalog_from_fetcher(_fetcher)


def test_helsinki_requires_exact_central_application_dates() -> None:
    def fetcher(url: str) -> str:
        if url == APPLICATION_URL:
            return APPLICATION_PAGE.replace("5 to 19 Jan 2027", "January 2027")
        return _fetcher(url)

    with pytest.raises(ValueError, match="exact application period"):
        _adapter().parse_catalog_from_fetcher(fetcher)


def test_helsinki_rejects_international_urls_outside_the_catalogue() -> None:
    def fetcher(url: str) -> str:
        if url == INTERNATIONAL_PROGRAMMES_URL:
            return INTERNATIONAL_LIST.replace(
                "data-science-masters-programme",
                "missing-masters-programme",
            )
        return _fetcher(url)

    with pytest.raises(ValueError, match="did not match the sitemap catalogue"):
        _adapter().parse_catalog_from_fetcher(fetcher)
