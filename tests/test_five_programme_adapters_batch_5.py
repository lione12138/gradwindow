from __future__ import annotations

import json

from gradwindow.programme_adapters.asu import ASUAdapter
from gradwindow.programme_adapters.georgia_tech import GeorgiaTechAdapter
from gradwindow.programme_adapters.mcmaster import McMasterAdapter
from gradwindow.programme_adapters.science_tokyo import ScienceTokyoAdapter
from gradwindow.programme_adapters.western import WesternAdapter


def test_science_tokyo_filters_doctoral_only_department() -> None:
    adapter = ScienceTokyoAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table>
        <tr><td>School of Science</td><td><a href="#department-math">Mathematics</a></td>
        <td>MS, MA, ScD, PhD</td></tr>
        <tr><td><a href="#department-innovation">Innovation Science</a></td>
        <td>EngD, PhD, MTD</td></tr>
        <tr><td><a href="#department-tim">Technology and Innovation Management</a></td>
        <td>MTM</td></tr></table>"""
    ).programmes

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Mathematics", "MS"),
        ("Technology and Innovation Management", "MTM"),
    ]


def test_georgia_tech_preserves_incomplete_official_deadline() -> None:
    adapter = GeorgiaTechAdapter()
    adapter.minimum_expected_programmes = 1
    payload = {
        "row": [
            {
                "guid": "official-guid",
                "name": "Computer Science",
                "unit": "Computer Science",
                "unit_college": "College of Computing",
                "campus": "Atlanta",
                "level": "Masters",
                "terms": [{"ayt_guid": "fall", "name": "Fall 2027"}],
                "deadlines": [{"ayt_guid": "fall", "date": "02/01/2027"}],
            }
        ]
    }

    programme = adapter.parse_catalog(json.dumps(payload)).programmes[0]

    assert programme.id == "gatech-computer-science-ms"
    assert programme.parse_status == "incomplete"
    assert programme.windows[0].opens_at is None
    assert programme.windows[0].closes_at == "2027-02-01"
    assert programme.windows[0].intake == "Fall 2027"


def test_western_preserves_distinct_degrees_and_existing_id() -> None:
    adapter = WesternAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table id="programTable">
        <tr class="MASTERS"><td>Computer Science</td><td>
        <a href="program.cfm?p=37">Master of Science</a></td></tr>
        <tr class="MASTERS"><td>Advanced Health Care Practice</td><td>
        <a href="program.cfm?p=318">Master of Health Sciences</a></td></tr>
        <tr class="DOCTORAL"><td>Computer Science</td><td>
        <a href="program.cfm?p=37">Doctor of Philosophy</a></td></tr>
        </table>"""
    ).programmes

    assert len(programmes) == 2
    assert next(item for item in programmes if item.name == "Computer Science").id == (
        "western-computer-science-msc"
    )


def test_mcmaster_filters_non_masters_and_preserves_existing_id() -> None:
    adapter = McMasterAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<div class="card"><h3 class="card-title">Computing and Software</h3>
        <a class="card-link" href="/program/computing-and-software/">Details</a>
        <span class="badge">MSc</span><span class="badge">PhD</span>
        <span class="badge">MSc/PhD</span></div>"""
    ).programmes

    assert [item.id for item in programmes] == ["mcmaster-computer-science-msc"]
    assert programmes[0].degree_type == "MSc"


def test_asu_uses_official_degree_title_to_filter_masters() -> None:
    adapter = ASUAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table>
        <tr id="master"><td><a class="majorUrl"
        href="/masters-phd/major/ASU00/LAACTMS/actuarial-science-ms">
        Actuarial Science, MS</a></td><td class="degree">
        <span title="Master of Science"><span>MS</span></span></td></tr>
        <tr id="certificate"><td><a class="majorUrl"
        href="/masters-phd/major/ASU00/CERT/certificate">Certificate</a></td>
        <td class="degree"><span title="Graduate Certificate">Certificate</span></td></tr>
        </table>"""
    ).programmes

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Actuarial Science, MS", "MS")
    ]
