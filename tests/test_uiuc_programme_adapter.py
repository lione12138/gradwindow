import pytest

from gradwindow.programme_adapters.uiuc import UIUCAdapter

PAGE = """
<table class="tbl_degreeprograms"><tbody>
  <tr><td class="column0">Computer Science</td><td class="column1">ENGR</td>
    <td class="column2"><a href="/graduate/engineering/computer-science-ms/">MS</a>,
    <a href="/graduate/engineering/computer-science-phd/">PhD</a></td></tr>
  <tr><td class="column0">Architecture</td><td class="column1">FAA</td>
    <td class="column2"><a href="/graduate/faa/Architecture-MARCH/">MARCH</a>,
    <a href="/graduate/faa/concentration/design/">CONC</a></td></tr>
</tbody></table>
"""


def test_uiuc_adapter_keeps_master_awards_and_reuses_existing_id() -> None:
    catalog = UIUCAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.degree_type for item in catalog.programmes] == ["MARCH", "MS"]
    assert catalog.programmes[0].id == "uiuc-architecture-march"
    assert catalog.programmes[1].id == "uiuc-computer-science-ms"
    assert all(item.windows == [] for item in catalog.programmes)


def test_uiuc_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        UIUCAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
