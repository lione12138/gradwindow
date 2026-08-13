from __future__ import annotations

from gradwindow.programme_adapters.aix_marseille import AixMarseilleAdapter
from gradwindow.programme_adapters.montpellier import MontpellierAdapter
from gradwindow.programme_adapters.normale_superiore import NormaleSuperioreAdapter
from gradwindow.programme_adapters.soochow_china import SoochowChinaAdapter
from gradwindow.programme_adapters.virginia import VirginiaAdapter


def test_montpellier_reads_master_mentions_and_routes() -> None:
    html = """
      <li class="amytis-expanded-list__item">
        <a href="/fr/formations/master-XB/master-biologie-sante-X.html">
          MASTER BIOLOGIE SANTE
        </a>
        <a class="amytis-expanded-second-type-list__link"
           href="/fr/formations/master-XB/master-biologie-sante-X/cancer-Y.html">
          Cancer Biology
        </a>
      </li>
      <li class="amytis-expanded-list__item">
        <a href="/fr/formations/licence-Y.html">Licence Biology</a>
      </li>
    """
    rows = (
        MontpellierAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Cancer Biology", "Master route"),
        ("Master Biologie Sante", "Master"),
    ]


def test_aix_marseille_deduplicates_official_master_directory() -> None:
    html = """
      <a class="link title diplome_link" href="/fr/master/5SIN">Master Informatique</a>
      <a class="link title diplome_link" href="/fr/master/5SIN">Master Informatique</a>
      <a class="link title diplome_link" href="/fr/master/5SMA">
        Master Mathématiques et applications
      </a>
      <a class="link title diplome_link" href="/fr/licence/3SIN">Licence Informatique</a>
    """
    rows = (
        AixMarseilleAdapter(minimum_expected_programmes=2)
        .parse_catalog(html)
        .programmes
    )

    assert [row.name for row in rows] == [
        "Master Informatique",
        "Master Mathématiques et applications",
    ]
    assert all("/fr/master/" in row.source_url for row in rows)


def test_sns_second_level_fields_use_the_competition_page() -> None:
    offer = """
      <div class="sns-card__content">
        <h3>Faculty of Humanities</h3>
        <div class="sns-grid-column"><h4>Undergraduate course</h4>
          <a href="/corso-ordinario/history-first">History</a>
          <a href="/corso-ordinario/history-second">History</a>
        </div>
      </div>
      <div class="sns-card__content">
        <h3>Faculty of Sciences</h3>
        <div class="sns-grid-column"><h4>Undergraduate course</h4>
          <a href="/corso-ordinario/physics-first">Physics</a>
          <a href="/corso-ordinario/physics-second">Physics</a>
        </div>
      </div>
      <div class="sns-card__content">
        <h3>Faculty of Political and Social Sciences</h3>
        <div class="sns-grid-column"><h4>Undergraduate course</h4>
          <a href="/corso-ordinario/politics-economics">
            Politics, Economics and Sustainability
          </a>
        </div>
      </div>
    """
    competition = """
      Access to the first or the second level is possible after obtaining a
      three-years' degree or its equivalent obtained abroad. Applications can
      be forwarded in July through the online procedure.
    """
    adapter = NormaleSuperioreAdapter(minimum_expected_programmes=3)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: competition if url == adapter.application_url else offer
    ).programmes

    assert {row.name for row in rows} == {
        "History (second-level undergraduate course)",
        "Physics (second-level undergraduate course)",
        "Politics, Economics and Sustainability (second-level undergraduate course)",
    }


def test_soochow_reads_pdf_rows_and_shared_national_window() -> None:
    page = '<span class="wp_pdf_player" pdfsrc="/_upload/official-2026.pdf"></span>'
    pdf_text = """
      001 政治与公共管理学院
      010100哲学（学术学位）
      125200公共管理（MPA、专业学位）
      002 商学院
      020200应用经济学（学术学位）
    """
    guide = """
      网上报名时间为2025年10月16日至10月27日每日9:00-22:00。
      网上预报名时间：2025年10月10日至10月13日每日9:00-22:00。
    """
    adapter = SoochowChinaAdapter(
        minimum_expected_programmes=3,
        maximum_expected_programmes=3,
        pdf_text_fetcher=lambda _url: pdf_text,
    )

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: guide if url == adapter.guide_url else page
    ).programmes

    assert {row.name for row in rows if not row.windows} == {
        "哲学",
        "公共管理",
        "应用经济学",
    }
    group = next(row for row in rows if row.windows)
    assert [(window.opens_at, window.closes_at) for window in group.windows] == [
        ("2025-10-10", "2025-10-13"),
        ("2025-10-16", "2025-10-27"),
    ]


def test_virginia_combines_degree_badges_with_official_deadlines() -> None:
    catalog = """
      <div class="views-row">
        <a href="/graduate-degree-programs/environmental-sciences">Environmental Sciences</a>
        <span class="dp-badge">MA</span><span class="dp-badge">MS</span>
      </div>
      <div class="views-row">
        <a href="/graduate-degree-programs/drama">Drama</a>
        <span class="dp-badge">MFA</span>
      </div>
    """
    deadlines = """
      <p>The application portal for all degree programs opens on October 1 and
      these deadlines are for the 2025-2026 cycle.</p>
      <h2>Master of Art</h2><h3>January 15 - May 1</h3>
      <p>The following programs accept applications through May 1.</p>
      <p>Environmental Sciences</p>
      <h2>Master of Fine Arts</h2><h3>January 15</h3>
      <p>Drama (applications paused)</p>
      <h2>Master of Science</h2><h3>January 15</h3>
      <p>Environmental Sciences</p>
    """
    adapter = VirginiaAdapter(
        minimum_expected_programmes=3,
        minimum_expected_deadlines=3,
    )

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: deadlines if url.endswith("/deadlines") else catalog
    ).programmes

    assert {row.name for row in rows} == {
        "Drama MFA",
        "Environmental Sciences MA",
        "Environmental Sciences MS",
    }
    assert {
        (window.opens_at, window.closes_at) for row in rows for window in row.windows
    } == {
        ("2025-10-01", "2026-01-15"),
        ("2025-10-01", "2026-05-01"),
    }
    assert not next(row for row in rows if row.name == "Drama MFA").windows
