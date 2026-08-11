from __future__ import annotations

from gradwindow.programme_adapters.baylor import BaylorAdapter
from gradwindow.programme_adapters.cu_anschutz import CUAnschutzAdapter
from gradwindow.programme_adapters.hebrew import HebrewAdapter
from gradwindow.programme_adapters.ntnu import NTNUAdapter
from gradwindow.programme_adapters.tel_aviv import TelAvivAdapter


def test_ntnu_reads_master_tables_and_uses_official_fallback_for_partner_link() -> None:
    html = """
      <table><tr><th>Programme of study</th></tr>
        <tr><td><a href="/studies/biology">Biology</a></td><td>Trondheim</td></tr>
        <tr><td><a href="https://partner.example/master">Joint Robotics</a></td></tr>
      </table>
    """

    rows = NTNUAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [row.name for row in rows] == ["Biology", "Joint Robotics"]
    joint = next(row for row in rows if row.name == "Joint Robotics")
    assert joint.source_url == NTNUAdapter.catalog_url


def test_hebrew_keeps_only_explicit_master_labels() -> None:
    html = """
      <table>
        <tr><td><a href="https://international.huji.ac.il/ma">M.A. in History</a></td></tr>
        <tr><td><a href="https://international.huji.ac.il/msc">MSc in Biology</a></td></tr>
        <tr><td><a href="https://international.huji.ac.il/phd">Ph.D. in Biology</a></td></tr>
      </table>
    """

    rows = HebrewAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("M.A. in History", "MA"),
        ("MSc in Biology", "MSc"),
    ]


def test_tel_aviv_reads_only_the_graduate_fee_table() -> None:
    html = """
      <table>
        <tr><th>Graduate Degrees</th></tr>
        <tr><td>MA in <a href="https://international.tau.ac.il/history">History</a></td></tr>
        <tr><td>MSc in <a href="https://international.tau.ac.il/data">Data Science</a></td></tr>
      </table>
      <table><tr><td>BA in <a href="/undergraduate">History</a></td></tr></table>
    """

    rows = TelAvivAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science", "MSc"),
        ("History", "MA"),
    ]


def test_cu_anschutz_reads_only_the_dedicated_masters_table() -> None:
    html = """
      <table><tr><td>all programmes</td></tr></table>
      <table><tr><td><a href="/phd">Biology</a></td><td>PhD</td></tr></table>
      <table>
        <tr><th>Program</th><th>Degree</th></tr>
        <tr><td><a href="https://cuanschutz.edu/ms">Biostatistics</a></td><td>MS</td></tr>
        <tr><td><a href="https://cuanschutz.edu/cert">Bioethics</a></td><td>Certificate</td></tr>
      </table>
    """

    rows = (
        CUAnschutzAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [("Biostatistics", "MS")]


def test_baylor_reads_four_registrar_master_degree_requirements() -> None:
    html = """
      <a href="/biomedical/">Graduate School of Biomedical Sciences Degree Requirements</a>
      <a href="/pa/">Master of Science in Physician Assistant Program Degree Requirements</a>
      <a href="/op/">Master of Science in Orthotics and Prosthetics Degree Requirements</a>
      <a href="/gc/">Master of Science in Genetic Counseling Degree Requirements</a>
      <a href="/medicine/">School of Medicine Course Degree Requirements</a>
    """

    rows = BaylorAdapter().parse_catalog(html).programmes

    assert [row.name for row in rows] == [
        "Biomedical Sciences",
        "Genetic Counseling",
        "Orthotics and Prosthetics",
        "Physician Assistant",
    ]
