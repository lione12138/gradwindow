from __future__ import annotations

from gradwindow.programme_adapters.emory import EmoryAdapter
from gradwindow.programme_adapters.qatar import QatarAdapter
from gradwindow.programme_adapters.tamu import TAMUAdapter
from gradwindow.programme_adapters.ucsb import UCSBAdapter
from gradwindow.programme_adapters.unc import UNCAdapter


def test_qatar_keeps_master_rows_only() -> None:
    adapter = QatarAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table><tr><th>College</th><th>Level</th><th>Major (Program)</th></tr>
        <tr><td>Engineering</td><td>Master</td><td>Computing</td></tr>
        <tr><td>Engineering</td><td>Doctorate</td><td>Engineering</td></tr>
        </table>"""
    ).programmes

    assert [(item.name, item.faculty) for item in programmes] == [
        ("Computing", "Engineering")
    ]


def test_emory_keeps_master_and_combined_degree_labels() -> None:
    adapter = EmoryAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<div class="filter-results__content">
        <span class="filter-results__title">Mathematics</span>
        <span class="filter-results__types">PhD, Master</span>
        <span class="filter-results__divisions">Natural Sciences</span></div>
        <div class="filter-results__content">
        <span class="filter-results__title">Chemistry</span>
        <span class="filter-results__types">PhD</span></div>"""
    ).programmes

    assert [item.name for item in programmes] == ["Mathematics"]


def test_unc_expands_hierarchical_programme_degrees() -> None:
    adapter = UNCAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<div id="byorgtextcontainer">
        <p>Public Health –</p>
        <p style="margin-left:40px">Biostatistics –
        <a href="/bio">M.S., M.S.P.H., Ph.D.</a></p>
        <p style="margin-left:40px">Inactive –
        <a href="/inactive">M.S.</a> (not active)</p></div>"""
    ).programmes

    assert {(item.name, item.degree_type) for item in programmes} == {
        ("Public Health: Biostatistics", "M.S."),
        ("Public Health: Biostatistics", "M.S.P.H."),
    }


def test_tamu_expands_multiple_masters_columns_and_deduplicates() -> None:
    adapter = TAMUAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<h3>College of Engineering</h3><table>
        <tr><th>Degree Program</th><th>Baccalaureate</th><th>Masters</th>
        <th>Doctorate</th><th>Professional</th></tr>
        <tr><td>Computer Science</td><td>BS</td><td>MS, MCS</td>
        <td>PhD</td><td></td></tr>
        <tr><td>Computer Science</td><td>BS</td><td>MS</td>
        <td>PhD</td><td></td></tr></table>"""
    ).programmes

    assert {(item.name, item.degree_type) for item in programmes} == {
        ("Computer Science", "MS"),
        ("Computer Science", "MCS"),
    }


def test_ucsb_extracts_master_codes_from_combined_routes() -> None:
    adapter = UCSBAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<div class="views-row"><div class="views-field-title">
        <a href="/graduate-programs/departments/chemistry">Chemistry</a></div>
        <div class="views-field-field-degrees">PhD, MS/PhD, MA/PhD</div></div>
        <div class="views-row"><div class="views-field-title">
        <a href="/graduate-programs/departments/physics">Physics</a></div>
        <div class="views-field-field-degrees">PhD</div></div>"""
    ).programmes

    assert {(item.name, item.degree_type) for item in programmes} == {
        ("Chemistry", "MA"),
        ("Chemistry", "MS"),
    }
