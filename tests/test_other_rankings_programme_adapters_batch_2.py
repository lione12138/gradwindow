from gradwindow.programme_adapters.paris_cite import ParisCiteAdapter
from gradwindow.programme_adapters.pittsburgh import PittsburghAdapter
from gradwindow.programme_adapters.ucas import UCASAdapter
from gradwindow.programme_adapters.umd import UMDAdapter
from gradwindow.programme_adapters.utsw import (
    HEALTH_ADMISSIONS_URL,
    HEALTH_CATALOG_URL,
    PUBLIC_HEALTH_ADMISSIONS_URL,
    PUBLIC_HEALTH_CATALOG_URL,
    UTSWAdapter,
)


def test_ucas_deduplicates_subject_codes_and_reads_latest_exact_call() -> None:
    majors = """
      <a href="/major/5822?subjectcode=071007">Genetics</a>
      <a href="/major/5822?subjectcode=071007">Genetics</a>
      <a href="/major/5822?subjectcode=083001">Environmental Science</a>
    """
    notices = """
      <a href="/notice/old">Call for 2025 Master's/Doctoral Degree Programs
      for International Students</a>
      <a href="/notice/current">Call for 2026 Master's/Doctoral Degree Programs
      for International Students</a>
    """
    call = """
      <h3>Call for 2026 Master's/Doctoral Degree Programs</h3>
      <h4>3. Application Deadline</h4>
      <p>October 15th, 2025–April 15th, 2026.</p>
    """
    pages = {
        UCASAdapter.catalog_url: majors,
        UCASAdapter.admissions_url: notices,
        "https://english.ucas.ac.cn/notice/current": call,
    }
    rows = (
        UCASAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.id for row in rows[:-1]] == ["ucas-083001", "ucas-071007"]
    assert rows[-1].id == "ucas-international-masters-admissions"
    assert rows[-1].windows[0].opens_at == "2025-10-15"
    assert rows[-1].windows[0].closes_at == "2026-04-15"


def test_umd_uses_official_master_filters_and_ignores_certificates() -> None:
    catalogue = """
      <ul class="isotope">
        <li class="item filter_23"><a href="/graduate/programs/accounting/">
          <span class="title">Accounting (BMAC)</span>
          <span class="keyword">Master</span>
          <span class="keyword">The Robert H. Smith School of Business</span>
        </a></li>
        <li class="item filter_44"><a href="/graduate/programs/public-health/">
          <span class="title">Public Health (MPPH)</span>
          <span class="keyword">Master of Public Health</span>
          <span class="keyword">School of Public Health</span>
        </a></li>
        <li class="item filter_26"><a href="/graduate/programs/certificate/">
          <span class="title">Data Science Certificate</span>
          <span class="keyword">Certificate (non-degree)</span>
        </a></li>
      </ul>
    """
    rows = UMDAdapter(minimum_expected_programmes=2).parse_catalog(catalogue).programmes

    assert [row.name for row in rows] == ["Accounting (BMAC)", "Public Health (MPPH)"]
    assert rows[1].degree_type == "Master of Public Health"
    assert all(row.windows == [] for row in rows)


def test_pittsburgh_reads_only_the_official_masters_section() -> None:
    html = """
      <p><strong>Doctoral</strong></p>
      <ul class="program-list"><li><a href="preview_program.php?poid=1">Physics, PhD</a></li></ul>
      <p><strong>Master’s</strong></p>
      <ul class="program-list">
        <li><a href="preview_program.php?poid=2">Accounting, MS</a></li>
        <li><a href="preview_program.php?poid=3">Public Administration, MPA</a></li>
      </ul>
      <p><strong>Micro-Credential</strong></p>
      <ul class="program-list"><li><a href="preview_program.php?poid=4">Finance</a></li></ul>
    """
    rows = (
        PittsburghAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes
    )

    assert [row.name for row in rows] == [
        "Accounting, MS",
        "Public Administration, MPA",
    ]
    assert all(row.windows == [] for row in rows)


def test_utsw_combines_health_professions_and_public_health() -> None:
    health = """
      <main>
        <a href="/programs/clinical-nutrition/">Master of Clinical Nutrition</a>
        <a href="/programs/physician-assistant/">Master of Physician Assistant Studies</a>
        <a href="/programs/physical-therapy/">Doctor of Physical Therapy</a>
      </main>
    """
    public_health = """
      <main>
        <a href="/degree-programs/mph.html">Master of Public Health</a>
        <a href="/degree-programs/health-informatics/">Master of Science in Health Informatics</a>
      </main>
    """
    pages = {
        HEALTH_CATALOG_URL: health,
        PUBLIC_HEALTH_CATALOG_URL: public_health,
        HEALTH_ADMISSIONS_URL: "Application costs, deadlines, and processes vary by program.",
        PUBLIC_HEALTH_ADMISSIONS_URL: "Application Deadlines",
    }
    rows = (
        UTSWAdapter(minimum_expected_programmes=4)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.name for row in rows] == [
        "Master of Clinical Nutrition",
        "Master of Physician Assistant Studies",
        "Master of Public Health",
        "Master of Science in Health Informatics",
    ]
    assert all(row.windows == [] for row in rows)


def test_paris_cite_keeps_english_catalogue_separate_from_mon_master_scope() -> None:
    catalogue = """
      <article>
        <a href="https://u-paris.fr/master-chemistry/">MASTER FRONTIERS IN CHEMISTRY</a>
        <a href="https://u-paris.fr/master-neuroscience/">MASTER IN NEUROSCIENCES</a>
        <a href="https://u-paris.fr/phd/">PhD programmes</a>
      </article>
    """
    calendar = """
      <h2>Le calendrier 2026, en bref</h2>
      <p>Entre le 17 février et le 16 mars soumettez vos candidatures</p>
    """
    pages = {
        ParisCiteAdapter.catalog_url: catalogue,
        ParisCiteAdapter.admissions_url: calendar,
    }
    rows = (
        ParisCiteAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.name for row in rows[:-1]] == [
        "MASTER FRONTIERS IN CHEMISTRY",
        "MASTER IN NEUROSCIENCES",
    ]
    assert rows[-1].id == "paris-cite-mon-master-admissions"
    assert rows[-1].windows[0].opens_at == "2026-02-17"
    assert rows[-1].windows[0].closes_at == "2026-03-16"
    assert ParisCiteAdapter.catalogue_status == "partial"
