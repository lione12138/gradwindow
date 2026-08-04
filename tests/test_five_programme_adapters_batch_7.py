from __future__ import annotations

import json

from gradwindow.programme_adapters.khalifa import KhalifaAdapter
from gradwindow.programme_adapters.nanjing import NanjingAdapter
from gradwindow.programme_adapters.osaka import OsakaAdapter
from gradwindow.programme_adapters.tohoku import TohokuAdapter
from gradwindow.programme_adapters.tongji import TongjiAdapter


def test_nanjing_requires_masters_evidence_from_official_detail_page() -> None:
    adapter = NanjingAdapter()
    adapter.minimum_expected_programmes = 1
    items = [
        {
            "title": "085404 Master's Program in Computer Technology",
            "url": "https://hwxy.nju.edu.cn/English/program-1.html",
        },
        {
            "title": "Doctoral-only listing",
            "url": "https://hwxy.nju.edu.cn/English/program-2.html",
        },
    ]
    index = f"<script>var dataList={json.dumps([{'infolist': items}])};</script>"
    programmes = adapter.parse_catalog(
        index,
        {
            items[0]["url"]: "<p>This is a two-year master's degree.</p>",
            items[1]["url"]: "<p>This is a doctoral degree.</p>",
        },
    ).programmes

    assert [item.name for item in programmes] == [
        "Master's Program in Computer Technology"
    ]


def test_osaka_expands_each_official_masters_degree_cell() -> None:
    adapter = OsakaAdapter()
    adapter.minimum_expected_programmes = 1
    catalog = adapter.parse_catalog(
        """<table><tr><th>Graduate School</th><th>Master's Degree</th></tr>
        <tr><td>Economics</td><td>Economics | Applied Economics |
        Business Administration</td></tr></table>"""
    )

    assert len(catalog.programmes) == 3
    assert all(
        item.faculty == "Graduate School of Economics" for item in catalog.programmes
    )


def test_tohoku_keeps_master_and_master_doctor_courses_only() -> None:
    adapter = TohokuAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<ul>
        <li><a href="/master"><h4>International Master Course</h4></a>
        Degree: Master</li>
        <li><a href="/both"><h4>Combined Course</h4></a>
        Degree: Master / Doctor</li>
        <li><a href="/doctor"><h4>Doctor Course</h4></a>
        Degree: Doctor</li></ul>"""
    ).programmes

    assert [item.name for item in programmes] == [
        "Combined Course",
        "International Master Course",
    ]


def test_tongji_parses_two_official_fall_2026_rounds() -> None:
    adapter = TongjiAdapter()
    catalog = adapter.parse_catalog(
        """<h1>Tongji University Master Student Enrollment Guide for
        International Students in 2026</h1>
        <p>Applicants for a master’s program must have a bachelor's degree.</p>
        <h2>Fall 2026 (August/September) admission</h2>
        <p>Chinese Government Scholarship (High-Level Postgraduate Program)
        and self-funded: October 25, 2025 - December 20, 2025</p>
        <p>Shanghai Municipal Government Scholarship and Self-funded:
        January 10, 2026-March 20, 2026</p>"""
    )

    assert catalog.application_opens_at == "2025-10-25"
    assert [window.closes_at for window in catalog.programmes[0].windows] == [
        "2025-12-20",
        "2026-03-20",
    ]
    assert all(
        window.applicant_categories == ["international-students"]
        for window in catalog.programmes[0].windows
    )


def test_khalifa_filters_doctorates_and_deduplicates_shared_masters() -> None:
    adapter = KhalifaAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<h3>College of Engineering</h3><ul>
        <li><a href="/msc-ece">Msc in Electrical and Computer Engineering</a></li>
        <li><a href="/phd-ece">PhD in Electrical Engineering</a></li></ul>
        <h3>College of Computing</h3><ul>
        <li><a href="/msc-ece">MSc in Electrical and Computer Engineering</a></li>
        <li><a href="/mph">Master of Public Health - NEW</a></li></ul>"""
    ).programmes

    assert {(item.name, item.degree_type) for item in programmes} == {
        ("MSc in Electrical and Computer Engineering", "MSc"),
        ("Master of Public Health", "MPH"),
    }
