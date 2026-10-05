import pytest

from gradwindow.programme_adapters.purdue import PurdueAdapter


def test_incomplete_master_card_is_not_silently_dropped():
    html = """<div class="program-card" data-category="masters west-lafayette">
    <h2>Art</h2><div class="degree_level-label">Masters</div></div>"""
    with pytest.raises(ValueError, match="missing title or admissions URL"):
        PurdueAdapter().extract_entries(html)


def test_duplicate_cards_do_not_inflate_programme_count():
    card = """<div class="program-card" data-category="masters west-lafayette">
    <h2>Biomedical Engineering</h2><div class="degree_level-label">Masters</div>
    <a href="https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/westlafayette/biomedical-engineering/">Admission Requirements</a></div>"""
    adapter = PurdueAdapter()
    adapter.minimum_expected_programmes = 2
    with pytest.raises(ValueError, match="contained 1"):
        adapter.parse_catalog(card + card)
