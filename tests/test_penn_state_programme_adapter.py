import pytest

from gradwindow.programme_adapters.penn_state import PennStateAdapter

PAGE = """
<ul class="isotope">
  <li class="item"><a href="/graduate/programs/majors/computer-science-engineering/">
    <div class="item-container"><span class="title">Computer Science and Engineering</span>
    <span class="keyword">Doctoral Degrees</span><span class="keyword">Master's Degrees</span></div></a></li>
  <li class="item"><a href="/graduate/programs/majors/public-administration/">
    <div class="item-container"><span class="title">Public Administration</span>
    <span class="keyword">Master's Degrees</span></div></a></li>
  <li class="item"><a href="/graduate/programs/certificates/data-science/">
    <div class="item-container"><span class="title">Data Science Certificate</span>
    <span class="keyword">Graduate Certificate Programs</span></div></a></li>
</ul>
"""


def test_penn_state_adapter_keeps_master_programmes_and_reuses_existing_id() -> None:
    catalog = PennStateAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.name for item in catalog.programmes] == [
        "Computer Science and Engineering",
        "Public Administration",
    ]
    assert catalog.programmes[0].id == "penn-state-computer-science-engineering-ms"
    assert all(item.windows == [] for item in catalog.programmes)


def test_penn_state_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        PennStateAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
