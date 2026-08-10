from __future__ import annotations

from gradwindow.programme_adapters.icahn import IcahnAdapter
from gradwindow.programme_adapters.karolinska import KarolinskaAdapter
from gradwindow.programme_adapters.minnesota import MinnesotaAdapter
from gradwindow.programme_adapters.rockefeller import RockefellerAdapter
from gradwindow.programme_adapters.ucsf import UCSFAdapter


def test_ucsf_reads_slate_masters_table_without_inventing_closing_dates() -> None:
    html = """
      <table>
        <thead><tr><th>Program</th><th>Level</th>
          <th>Application Open Date</th><th>Application Close Date</th></tr></thead>
        <tbody>
          <tr><td>Biomedical Imaging, MS</td><td>MS</td><td></td><td></td></tr>
          <tr><td>Regulatory Science and Digital Innovation, MS</td><td>MS</td>
            <td>August 01, 2026</td><td></td></tr>
          <tr><td>Biomedical Sciences, PhD</td><td>PhD</td>
            <td>September 01, 2026</td><td>December 01, 2026</td></tr>
        </tbody>
      </table>
    """
    rows = UCSFAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [row.name for row in rows] == [
        "Biomedical Imaging, MS",
        "Regulatory Science and Digital Innovation, MS",
    ]
    assert all(row.windows == [] for row in rows)
    assert "August 01, 2026" in rows[1].deadline_text


def test_rockefeller_records_official_doctoral_only_scope() -> None:
    html = """
      <h1>The David Rockefeller Graduate Program</h1>
      <p>The Rockefeller University is accredited to grant the doctoral degree only.</p>
    """

    catalog = RockefellerAdapter().parse_catalog(html)

    assert catalog.programmes == []
    assert RockefellerAdapter.catalogue_status == "not-applicable"


def test_icahn_uses_officially_linked_heartbeat_without_copying_stale_programmes() -> (
    None
):
    html = """
      <h1>Graduate School of Biomedical Sciences</h1>
      <p>Learn with a Master's degree or PhD from a leading academic medical center.</p>
      <a href="https://icahn.mssm.edu/education/masters">master's programs</a>
    """

    rows = IcahnAdapter().parse_catalog(html).programmes

    assert [row.id for row in rows] == ["icahn-masters-programmes"]
    assert rows[0].parse_status == "no-deadline"
    assert IcahnAdapter.catalogue_status == "blocked"


def test_karolinska_reads_programmes_and_one_shared_exact_window() -> None:
    catalogue = """
      <div class="ladok-filter-search__result">
        <h2><a href="/programmes/biomedicine">Master's Programme in Biomedicine</a></h2>
        <p>On Campus Master Autumn 2027 English Programme</p>
      </div>
      <div class="ladok-filter-search__result">
        <h2><a href="/programmes/public-health">Master's Programme in Public Health Sciences</a></h2>
        <p>On Campus Master Autumn 2027 English Programme</p>
      </div>
      <div class="ladok-filter-search__result">
        <h2><a href="/courses/immunology">Advanced Immunology</a></h2>
        <p>Master Autumn 2027 English Course</p>
      </div>
    """
    admissions = """
      <h1>Apply for a master's programme</h1>
      <p>Application period 16 October 2026-15 January 2027:
      Application period for studies starting in autumn 2027.</p>
    """
    pages = {
        KarolinskaAdapter.catalog_url: catalogue,
        KarolinskaAdapter.admissions_url: admissions,
    }
    rows = (
        KarolinskaAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.name for row in rows[:-1]] == [
        "Master's Programme in Biomedicine",
        "Master's Programme in Public Health Sciences",
    ]
    assert rows[-1].id == "karolinska-international-masters-admissions"
    assert rows[-1].windows[0].opens_at == "2026-10-16"
    assert rows[-1].windows[0].closes_at == "2027-01-15"


def test_minnesota_filters_doctoral_certificates_and_duluth_routes() -> None:
    html = """
      <ul>
        <li><a href="at_a_glance.aspx?p=1019600">Computer Science M S</a></li>
        <li><a href="at_a_glance.aspx?p=1019600">Computer Science Ph D</a></li>
        <li><a href="at_a_glance.aspx?p=101520X">Business Administration M B A</a></li>
        <li><a href="at_a_glance.aspx?p=1058000">Music D M A</a></li>
        <li><a href="at_a_glance.aspx?p=1213800">Integrated Biosciences M S (Duluth)</a></li>
        <li><a href="at_a_glance.aspx?p=120410X">Public Health Postbaccalaureate Certificate</a></li>
      </ul>
    """

    rows = (
        MinnesotaAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes
    )

    assert [row.name for row in rows] == [
        "Business Administration M B A",
        "Computer Science M S",
    ]
    assert all(row.windows == [] for row in rows)
