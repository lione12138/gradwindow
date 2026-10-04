import json

import httpx
import pytest

from gradwindow.programme_adapters import uppsala

WRAPPER = (
    "AppRegistry.registerInitialState('12.masters',"
    '{"displayMode":"search","categoryId":"educationInternationalMastersProgrammes"});'
)


def programme(name):
    return {
        "title": f"Master's Programme in {name}",
        "uri": f"/en/study/programme/{name.lower()}",
        "type": "programme",
    }


def run_adapter(monkeypatch, pages, wrapper=WRAPPER):
    requests = []
    fetches = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["category"] == "educationInternationalMastersProgrammes"
        assert request.url.params["sv.target"] == "12.masters"
        return httpx.Response(200, json={"result": pages[len(requests) - 1]})

    original_client = httpx.Client
    monkeypatch.setattr(
        uppsala.httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handle), **kwargs
        ),
    )

    def fetch(url):
        fetches.append(url)
        return wrapper if url == uppsala.CATALOG_URL else "Official application guide"

    adapter = uppsala.UppsalaAdapter()
    adapter.minimum_expected_programmes = 1
    return adapter.parse_catalog_from_fetcher(fetch), requests, fetches


def test_new_masters_category_paginates_without_inventing_windows(monkeypatch):
    catalog, requests, fetches = run_adapter(
        monkeypatch,
        [
            {"count": 2, "hits": [programme("Biology")]},
            {"count": 2, "hits": [programme("Chemistry")]},
        ],
    )
    assert [r["start"] for r in requests] == [0, 1]
    assert len(catalog.programmes) == 2
    assert all(not p.windows for p in catalog.programmes)
    assert all(
        p.source_url.startswith("https://www.uu.se/") for p in catalog.programmes
    )
    assert uppsala.APPLICATION_URL in fetches


@pytest.mark.parametrize(
    "second_page, message",
    [
        ({"count": 2, "hits": []}, "incomplete pagination"),
        ({"count": 3, "hits": [programme("Chemistry")]}, "count changed"),
        ({"count": 2, "hits": [programme("Biology")]}, "duplicate/missing"),
        (
            {"count": 2, "hits": [{**programme("Chemistry"), "type": "course"}]},
            "non-programmes",
        ),
    ],
)
def test_rejects_partial_or_wrong_catalogue(monkeypatch, second_page, message):
    with pytest.raises(ValueError, match=message):
        run_adapter(
            monkeypatch, [{"count": 2, "hits": [programme("Biology")]}, second_page]
        )


def test_does_not_accept_unfiltered_course_search(monkeypatch):
    with pytest.raises(ValueError, match="portlet was not found"):
        run_adapter(
            monkeypatch,
            [],
            WRAPPER.replace(
                "educationInternationalMastersProgrammes",
                "educationCoursesAndProgrammes",
            ),
        )
