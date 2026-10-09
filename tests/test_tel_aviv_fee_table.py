import pytest

from gradwindow.programme_adapters.tel_aviv import TelAvivAdapter

TABLE = '<table><tr><th>Graduate Degrees</th><th>Annual Tuition</th></tr><tr><td>MA in <a href="/ma_environmental_studies">Environmental Studies</a></td><td>$12,640</td></tr></table>'


def test_fee_table_is_selected_by_header_not_position():
    html = (
        '<table><tr><td>MA in <a href="/unrelated">Unrelated</a></td></tr></table>'
        + TABLE
    )
    rows = TelAvivAdapter(1).parse_catalog(html).programmes
    assert len(rows) == 1
    assert rows[0].name == "Environmental Studies"
    assert (
        rows[0].source_url == "https://international.tau.ac.il/ma_environmental_studies"
    )
    assert rows[0].windows == []


@pytest.mark.parametrize(
    "html",
    [
        TABLE + TABLE,
        TABLE.replace("Graduate Degrees", "Undergraduate Degrees"),
        TABLE.replace(
            '<a href="/ma_environmental_studies">Environmental Studies</a>',
            "Environmental Studies",
        ),
        TABLE.replace(
            "/ma_environmental_studies", "https://tau.ac.il.example.org/course"
        ),
    ],
)
def test_ambiguous_or_damaged_fee_table_fails_closed(html):
    with pytest.raises(ValueError, match="Tel Aviv"):
        TelAvivAdapter(1).parse_catalog(html)


def test_degree_in_other_columns_is_not_a_programme():
    html = TABLE.replace(
        "</table>",
        '<tr><td><a href="/notes">Notes</a></td><td>MA fee supplement</td></tr></table>',
    )
    assert len(TelAvivAdapter(1).parse_catalog(html).programmes) == 1
