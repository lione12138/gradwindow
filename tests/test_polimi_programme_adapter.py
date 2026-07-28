import pytest

from gradwindow.programme_adapters.polimi import PolimiAdapter

PAGE = """
<a class="link" href="/en/education/laurea-magistrale-programmes/programme-detail/aeronautical-engineering">
  <div class="localised-title"><div class="localised-title-title"><p class="strong">Aeronautical Engineering</p></div>
  <span class="campusName">Milano Bovisa</span><span>ENG</span></div>
</a>
<a class="link" href="/en/education/laurea-magistrale-programmes/programme-detail/architecture">
  <div class="localised-title"><div class="localised-title-title"><p class="strong">Architecture</p></div>
  <span class="campusName">Milano Leonardo</span><span>ITA</span></div>
</a>
"""


def test_polimi_adapter_reads_laurea_magistrale_programmes() -> None:
    catalog = PolimiAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.name for item in catalog.programmes] == [
        "Aeronautical Engineering",
        "Architecture",
    ]
    assert catalog.programmes[0].department == "Milano Bovisa"
    assert all(item.degree_type == "Laurea Magistrale" for item in catalog.programmes)


def test_polimi_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        PolimiAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
