"""Reduced fixtures from UCL's 2027/28 directory, inspected 2026-10-10."""

import pytest

from gradwindow.programme_adapters.ucl import (
    CATALOG_URL,
    UCLAdapter,
    programme_name_key,
)


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
    return UCLAdapter(minimum_expected_courses=3, minimum_expected_programmes=2)


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
        not p.windows and p.parse_status == "no-deadline" for p in catalog.programmes
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
        minimum_expected_courses=1, minimum_expected_programmes=1
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
        minimum_expected_courses=3, minimum_expected_programmes=1
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
    instance = UCLAdapter(minimum_expected_courses=1, minimum_expected_programmes=1)
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
