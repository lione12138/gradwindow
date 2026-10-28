"""Reduced fixtures from UCL's 2027/28 directory, inspected 2026-10-10."""

from pathlib import Path

import httpx
import pytest

from gradwindow.browser_rendering import browser_content_fetcher_from_environment
from gradwindow.http_client import FetchFailure
from gradwindow.programme_adapters.ucl import (
    CATALOG_URL,
    REVIEWED_PROGRAMME_IDENTITIES,
    UCLAdapter,
    programme_name_key,
)
from gradwindow.programme_discovery import discover_programmes


def card(
    name,
    degree="Master of Science (MSc)",
    route="advanced-audiology-msc",
    extra="",
    coming=False,
):
    heading = name if coming else f'<a href="{CATALOG_URL}/{route}">{name}</a>'
    return f"""<article class="course-feed-listing-item {"course-feed-listing-item--coming-soon-restricted" if coming else ""}">
    <span class="course-feed-listing-item__degree-level">{degree}</span>
    <h2 class="course-feed-listing-item__heading--main">{heading}</h2>
    <div class="course-feed-listing-item__faculty">Faculty of Brain Sciences</div>
    {"" if coming else '<div class="course-feed-listing-item__start-dates">Start date: September 2027</div>'}
    {extra}</article>"""


def page(cards, total=3, next_url=None):
    return f"""<p class="course-feed-listing-view__result-count">{total} courses found</p>
    {cards}<nav class="pager">{f'<a rel="next" href="{next_url}">Next</a>' if next_url else ""}</nav>"""


def adapter():
    return UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=3,
        minimum_expected_programmes=2,
    )


def doctoral_card():
    return (
        Path(__file__).parent / "fixtures/ucl/education-integrated-doctoral-card.html"
    ).read_text(encoding="utf-8")


def catalogue_with_doctoral_card(html, total=3):
    return {
        CATALOG_URL: page(card("Advanced Audiology MSc"), total, next_url="?page=1"),
        CATALOG_URL + "?page=1": page(
            card("Environmental Anthropology MSc", coming=True) + html, total
        ),
    }


def test_unlabelled_explicit_doctoral_card_is_counted_but_not_a_masters_programme():
    catalog = adapter().parse_catalog_from_fetcher(
        catalogue_with_doctoral_card(doctoral_card()).__getitem__
    )
    assert {p.name for p in catalog.programmes} == {
        "Advanced Audiology MSc",
        "Environmental Anthropology MSc",
    }
    assert catalog.diagnostics["directoryCourses"] == 3
    assert catalog.diagnostics["masterCourseCards"] == 2
    assert catalog.diagnostics["catalogueComplete"] is True
    assert all(not p.windows for p in catalog.programmes)


@pytest.mark.parametrize(
    "change",
    [
        lambda text: text.replace("MPhil/PhD", "MSc"),
        lambda text: text.replace("MPhil/PhD", "MPhil"),
        lambda text: text.replace("MPhil/PhD", "Unknown degree"),
        lambda text: text.replace("course-feed-listing-item__heading--main", ""),
        lambda text: text.replace("href=", "data-href="),
        lambda text: text.replace('href="/study/', 'href="https://example.org/study/'),
        lambda text: text.replace('mphilphd"', 'mphilphd?option=UNKNOWN"'),
        lambda text: text.replace('mphilphd"', 'mphilphd#apply"'),
        lambda text: text.replace("training-mphilphd", "training-msc"),
        lambda text: text.replace("</a>", "</a> Extra MPhil/PhD"),
        lambda text: text.replace("</h2>", '<a href="/other">Other route</a></h2>'),
    ],
    ids=[
        "msc",
        "standalone-mphil",
        "unknown",
        "missing-heading",
        "missing-link",
        "external-link",
        "unreviewed-option",
        "fragment-link",
        "non-doctoral-route",
        "inconsistent-heading",
        "ambiguous-links",
    ],
)
def test_unlabelled_course_requires_explicit_consistent_doctoral_identity(change):
    with pytest.raises(ValueError) as error:
        adapter().parse_catalog_from_fetcher(
            catalogue_with_doctoral_card(change(doctoral_card())).__getitem__
        )
    assert "lacks title or degree" in str(error.value)
    assert f"page=2, url={CATALOG_URL}?page=1" in str(error.value)
    assert "title=" in str(error.value)


@pytest.mark.parametrize("with_badge", [False, True])
def test_unlabelled_doctoral_card_preserves_duplicate_guard(with_badge):
    duplicate = doctoral_card()
    if with_badge:
        duplicate = duplicate.replace(
            '<div class="course-feed-listing-item__content">',
            '<div class="course-feed-listing-item__content">'
            '<span class="course-feed-listing-item__degree-level">'
            "Doctor of Philosophy (PhD)</span>",
        )
    sources = catalogue_with_doctoral_card(duplicate, total=4)
    sources[CATALOG_URL] = page(
        card("Advanced Audiology MSc") + doctoral_card(), total=4, next_url="?page=1"
    )
    with pytest.raises(ValueError, match="repeated"):
        adapter().parse_catalog_from_fetcher(sources.__getitem__)


def test_unlabelled_doctoral_card_does_not_hide_missing_pages():
    with pytest.raises(ValueError, match="read 3 of 4"):
        adapter().parse_catalog_from_fetcher(
            catalogue_with_doctoral_card(doctoral_card(), total=4).__getitem__
        )


def bachelor_card():
    return (
        Path(__file__).parent / "fixtures/ucl/teacher-apprenticeship-bsc-card.html"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "html",
    [
        bachelor_card(),
        card("Diploma route", degree="Graduate Diploma (Grad Dip)"),
    ],
    ids=["official-bsc-apprenticeship", "graduate-diploma-label"],
)
def test_explicit_non_masters_labels_are_counted_without_emitting_programmes(html):
    catalog = adapter().parse_catalog_from_fetcher(
        catalogue_with_doctoral_card(html).__getitem__
    )
    assert {p.name for p in catalog.programmes} == {
        "Advanced Audiology MSc",
        "Environmental Anthropology MSc",
    }
    assert catalog.diagnostics["directoryCourses"] == 3
    assert catalog.diagnostics["masterCourseCards"] == 2
    assert catalog.diagnostics["catalogueComplete"] is True
    assert all(not p.windows for p in catalog.programmes)


def test_bachelor_card_preserves_duplicate_and_incomplete_catalogue_guards():
    sources = catalogue_with_doctoral_card(bachelor_card(), total=4)
    with pytest.raises(ValueError, match="read 3 of 4"):
        adapter().parse_catalog_from_fetcher(sources.__getitem__)
    sources[CATALOG_URL] = page(
        card("Advanced Audiology MSc") + bachelor_card(), total=4, next_url="?page=1"
    )
    with pytest.raises(ValueError, match="repeated"):
        adapter().parse_catalog_from_fetcher(sources.__getitem__)


@pytest.mark.parametrize(
    "degree",
    ["", "Bachelor", "Bachelor of Unknown Studies (Unknown)", "Graduate Unknown"],
)
def test_non_masters_course_title_cannot_replace_a_reviewed_degree_label(degree):
    html = bachelor_card().replace("Bachelor of Science (BSc)", degree)
    with pytest.raises(ValueError, match="lacks title or degree|unknown degree"):
        adapter().parse_catalog_from_fetcher(
            catalogue_with_doctoral_card(html).__getitem__
        )


@pytest.mark.parametrize("name,existing_id", REVIEWED_PROGRAMME_IDENTITIES.items())
def test_official_rename_overrides_unreviewed_snapshot_id(name, existing_id):
    instance = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=1,
        minimum_expected_programmes=1,
    )
    instance.prepare_discovery({"programmes": {"ucl-duplicate": {"name": name}}})
    catalog = instance.parse_catalog_from_fetcher(
        lambda _: page(card(name, degree="Master of Arts (MA)"), total=1)
    )
    assert catalog.programmes[0].id == existing_id
    assert not catalog.programmes[0].windows


@pytest.mark.parametrize(
    "parent,name,route,option,existing_id",
    [
        (
            "Crime Science MSc",
            "Crime Science with Policing MSc",
            "crime-science-msc",
            "TMSENG00264A",
            "ucl-policing-msc",
        ),
        (
            "Advanced Clinical Practice MSc",
            "Advanced Clinical Practice: Critical Care Practitioner MSc",
            "advanced-clinical-practice-msc",
            "TMSMDS00442A",
            "ucl-advanced-critical-care-practice-msc",
        ),
        (
            "Civil Engineering MSc",
            "Civil Engineering (Integrated Design) MSc",
            "civil-engineering-msc",
            "TMSENG00123A",
            "ucl-civil-engineering-integrated-design-msc",
        ),
        (
            "Crime Science MSc",
            "Crime Science with Serious and Organised Crime MSc",
            "crime-science-msc",
            "TMSENG00263A",
            "ucl-crime-science-serious-organised-crime-msc",
        ),
        (
            "Translation and Technology MSc",
            "Translation and Technology (Interpreting) MSc",
            "translation-and-technology-msc",
            "TMSART00032A",
            "ucl-translation-and-technology-interpreting-msc",
        ),
    ],
)
def test_reviewed_option_keeps_identity_and_route(
    parent, name, route, option, existing_id
):
    source = f"{CATALOG_URL}/{route}?option={option}"
    instance = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=1,
        minimum_expected_programmes=2,
    )
    instance.prepare_discovery(
        {"programmes": {"ucl-unreviewed-option": {"name": name}}}
    )
    catalog = instance.parse_catalog_from_fetcher(
        lambda _: page(
            card(parent, route=route, extra=f'<a href="{source}">{name}</a>'), total=1
        )
    )
    programmes = {p.id: p for p in catalog.programmes}
    assert set(programmes) == {f"ucl-{route}", existing_id}
    assert programmes[existing_id].source_url == source
    assert programmes[existing_id].application_url == source
    assert not programmes[existing_id].windows


def test_reviewed_history_and_spatial_names_keep_neighbouring_courses_separate():
    records = [
        ("East European History MA", "ucl-history-ssees-ma", "MA"),
        ("History MA", "ucl-history-ma", "MA"),
        (
            "Modern European Studies MA",
            "ucl-european-studies-modern-european-studies-ma",
            "MA",
        ),
        ("Urban and Spatial Data Science MSc", "ucl-urban-spatial-science-msc", "MSc"),
        ("Urban Spatial Science MRes", "ucl-urban-spatial-science-mres", "MRes"),
        (
            "Urban Spatial Science (Degree Apprenticeship) MSc",
            "ucl-urban-spatial-science-degree-apprenticeship-msc",
            "MSc",
        ),
    ]
    instance = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=6,
        minimum_expected_programmes=6,
    )
    instance.prepare_discovery(
        {
            "programmes": {
                pid: {"name": name}
                for i, (name, pid, _) in enumerate(records)
                if i in (1, 4, 5)
            }
        }
    )
    catalog = instance.parse_catalog_from_fetcher(
        lambda _: page(
            "".join(
                card(
                    name,
                    degree={
                        "MA": "Master of Arts (MA)",
                        "MSc": "Master of Science (MSc)",
                        "MRes": "Master of Research (MRes)",
                    }[degree],
                    route=f"course-{i}",
                )
                for i, (name, _, degree) in enumerate(records)
            ),
            total=6,
        )
    )
    assert {p.name: p.id for p in catalog.programmes} == {
        name: pid for name, pid, _ in records
    }
    assert all(not p.windows for p in catalog.programmes)


def test_physiotherapy_clinical_and_academic_routes_do_not_swap_ids():
    names = [
        "Advanced Musculoskeletal Physiotherapy MSc",
        "Advanced Musculoskeletal Physiotherapy Clinical Practice MSc",
        "Advanced Paediatric Physiotherapy Clinical Practice MSc",
    ]
    instance = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=3,
        minimum_expected_programmes=3,
    )
    instance.prepare_discovery(
        {
            "programmes": {
                f"ucl-unreviewed-{i}": {"name": n} for i, n in enumerate(names)
            }
        }
    )
    catalog = instance.parse_catalog_from_fetcher(
        lambda _: page(
            "".join(card(n, route=f"course-{i}") for i, n in enumerate(names))
        )
    )
    actual = {p.name: p.id for p in catalog.programmes}
    assert actual == {
        names[0]: "ucl-physiotherapy-studies-musculoskeletal-msc",
        names[1]: "ucl-advanced-physiotherapy-musculoskeletal-msc",
        names[2]: "ucl-advanced-physiotherapy-paediatrics-msc",
    }


def test_inconsistent_snapshot_is_evicted_before_next_run(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "ucl-test-account")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_CACHE_DIR", str(tmp_path / "cache"))
    sources = pages()
    sources[CATALOG_URL + "?page=1"] = sources[CATALOG_URL + "?page=1"].replace(
        "3 courses found", "4 courses found"
    )
    calls = []

    def post(*args, **kwargs):
        url = kwargs["json"]["url"]
        calls.append(url)
        return httpx.Response(200, json=sources[url])

    def blocked(url):
        raise FetchFailure("HTTP 403", kind="blocked", status_code=403)

    monkeypatch.setattr("gradwindow.browser_rendering.httpx.post", post)
    browser = browser_content_fetcher_from_environment()
    unrelated_url = "https://example.edu/other-school"
    sources[unrelated_url] = "Other school's official page"
    browser(unrelated_url)
    calls.clear()
    for name, value in [
        ("programs", '{"programs": []}'),
        ("applications", '{"applications": []}'),
    ]:
        (tmp_path / f"{name}.json").write_text(value)
    options = dict(
        programs_path=tmp_path / "programs.json",
        applications_path=tmp_path / "applications.json",
        candidates_path=tmp_path / "candidates.json",
        state_path=tmp_path / "state.json",
        fetcher=blocked,
        browser_fetcher=browser,
        dry_run=False,
    )
    with pytest.raises(ValueError, match=r"page=2.*total=4.*first_page_total=3"):
        discover_programmes(adapter(), **options)
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "candidates.json").exists()
    assert browser.client.cache.summary()["invalidated_pages"] == 2
    # Reconstruct the client as a subsequent job would, reading the persisted store.
    monkeypatch.setattr("gradwindow.browser_rendering._clients", {})
    browser = browser_content_fetcher_from_environment()
    options["browser_fetcher"] = browser
    options["dry_run"] = True
    assert browser(unrelated_url) == sources[unrelated_url]
    sources.update(pages())
    discover_programmes(adapter(), **options)
    assert calls == [CATALOG_URL, CATALOG_URL + "?page=1"] * 2


def pages():
    option = f'<a href="{CATALOG_URL}/advanced-audiology-msc?option=TMS00442A">Audiology specialist MSc</a>'
    return {
        CATALOG_URL: page(
            card("Advanced Audiology MSc", extra=option), next_url="?page=1"
        ),
        CATALOG_URL + "?page=1": page(
            card("Environmental Anthropology MSc", coming=True)
            + card(
                "Dentistry PGCert",
                degree="Postgraduate Certificate (PGCert)",
                route="dentistry-pgcert",
            )
        ),
    }


def test_current_directory_follows_pages_options_and_preserves_identity():
    instance = adapter()
    instance.prepare_discovery(
        {"programmes": {"ucl-existing-audiology": {"name": "Advanced Audiology MSc"}}}
    )
    catalog = instance.parse_catalog_from_fetcher(pages().__getitem__)
    assert len(catalog.programmes) == 3
    assert {p.id for p in catalog.programmes} == {
        "ucl-existing-audiology",
        "ucl-advanced-audiology-msc-option-tms00442a",
        "ucl-environmental-anthropology-msc",
    }
    assert all(
        not p.windows and p.parse_status == "catalogue-only" for p in catalog.programmes
    )
    pending = next(p for p in catalog.programmes if "Anthropology" in p.name)
    assert pending.source_url == CATALOG_URL
    assert pending.available_intakes == []
    assert "Coming soon" in pending.deadline_text
    assert catalog.diagnostics["directoryPages"] == 2
    assert catalog.diagnostics["additionalStudyOptions"] == 1


@pytest.mark.parametrize(
    "next_url", [None, "?page=0", "?page=2", "https://example.org/?page=1"]
)
def test_current_directory_rejects_missing_or_invalid_pagination(next_url):
    with pytest.raises(ValueError, match="pagination|next-page"):
        adapter().parse_catalog_from_fetcher(
            lambda _: page(card("Advanced Audiology MSc"), next_url=next_url)
        )


@pytest.mark.parametrize(
    "change, message",
    [
        (
            lambda text: text.replace("3 courses found", "4 courses found"),
            "total changed",
        ),
        (
            lambda text: text.replace(
                "Environmental Anthropology MSc", "Advanced Audiology MSc"
            ),
            "repeated",
        ),
        (
            lambda text: text.replace(
                "course-feed-listing-item--coming-soon-restricted", ""
            ),
            "no link",
        ),
    ],
)
def test_current_directory_rejects_partial_or_changed_pages(change, message):
    sources = pages()
    sources[CATALOG_URL + "?page=1"] = change(sources[CATALOG_URL + "?page=1"])
    with pytest.raises(ValueError, match=message):
        adapter().parse_catalog_from_fetcher(sources.__getitem__)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda text: text.replace("September 2027", ""), "explicit intake"),
        (
            lambda text: text.replace(CATALOG_URL + "/", "https://example.org/"),
            "non-official",
        ),
        (
            lambda text: text.replace("Master of Science (MSc)", "Unknown degree"),
            "unknown degree",
        ),
    ],
)
def test_current_directory_rejects_unreviewable_cards(change, message):
    sources = pages()
    sources[CATALOG_URL] = change(sources[CATALOG_URL])
    with pytest.raises(ValueError, match=message):
        adapter().parse_catalog_from_fetcher(sources.__getitem__)


def test_current_directory_preserves_nested_degree_label():
    source = page(
        card(
            "Education MA (International)", degree="Master of Arts (MA (International))"
        ),
        total=1,
    )
    catalog = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=1,
        minimum_expected_programmes=1,
    ).parse_catalog_from_fetcher(lambda _: source)
    assert catalog.programmes[0].degree_type == "MA (International)"


def test_same_non_master_title_with_different_degree_is_not_a_repeated_page():
    source = page(
        card("Advanced Audiology MSc")
        + card(
            "Performing Arts Medicine PG Cert",
            degree="Postgraduate Certificate (PG Cert)",
        )
        + card(
            "Performing Arts Medicine PG Cert", degree="Postgraduate Diploma (PG Dip)"
        )
    )
    catalog = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=3,
        minimum_expected_programmes=1,
    ).parse_catalog_from_fetcher(lambda _: source)
    assert len(catalog.programmes) == 1


@pytest.mark.parametrize(
    "old,new",
    [
        ("Health in Urban Development MSc", "MSc Health in Urban Development"),
        (
            "Bioscience (Research and Development) MSc",
            "Bioscience: Research & Development MSc",
        ),
        ("Translation: Translation Studies MA", "Translation (Translation Studies) MA"),
    ],
)
def test_typographical_renames_retain_previous_ids(old, new):
    instance = UCLAdapter(
        detail_refresh_budget=0,
        minimum_expected_courses=1,
        minimum_expected_programmes=1,
    )
    instance.prepare_discovery({"programmes": {"ucl-established-id": {"name": old}}})
    catalog = instance.parse_catalog_from_fetcher(lambda _: page(card(new), total=1))
    assert catalog.programmes[0].id == "ucl-established-id"
    assert catalog.programmes[0].department == ""


def test_identity_matching_does_not_merge_semantic_or_ambiguous_renames():
    assert programme_name_key(
        "Advanced Critical Care Practice MSc"
    ) != programme_name_key("Advanced Clinical Practice MSc")
    instance = adapter()
    instance.prepare_discovery(
        {
            "programmes": {
                "ucl-one": {"name": "Audiology MSc"},
                "ucl-two": {"name": "MSc Audiology"},
            }
        }
    )
    assert instance.previous_ids == {}
