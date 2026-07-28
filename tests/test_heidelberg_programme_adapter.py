import pytest

from gradwindow.programme_adapters.heidelberg import HeidelbergAdapter

PAGE = """
<section class="Wrapper_IlVNZ"><div class="InnerWrapper_R5x-V">
  <a title="Data and Computer Science"><h4>Data and Computer Science</h4></a>
  <a href="/en/study/all-subjects/data-and-computer-science/data-and-computer-science-master">
    <div class="Name_cpcKu">Master, consecutive</div></a>
  <a href="/en/study/all-subjects/data-and-computer-science/data-and-computer-science-bachelor">
    <div class="Name_cpcKu">Bachelor 100%</div></a>
</div></section>
<section class="Wrapper_IlVNZ"><div class="InnerWrapper_R5x-V">
  <a title="American Studies"><h4>American Studies</h4></a>
  <a href="/en/study/all-subjects/american-studies/american-studies-master">
    <div class="Name_cpcKu">Master, consecutive</div></a>
</div></section>
"""


def test_heidelberg_adapter_reads_master_variants_and_reuses_existing_id() -> None:
    catalog = HeidelbergAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.name for item in catalog.programmes] == [
        "American Studies — Master, consecutive",
        "Data and Computer Science — Master, consecutive",
    ]
    assert catalog.programmes[1].id == "heidelberg-data-and-computer-science-master"


def test_heidelberg_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        HeidelbergAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
