from __future__ import annotations

import json

from gradwindow.programme_adapters.arizona import (
    CATALOG_URL as ARIZONA_CATALOG_URL,
)
from gradwindow.programme_adapters.arizona import (
    DEADLINES_URL as ARIZONA_DEADLINES_URL,
)
from gradwindow.programme_adapters.arizona import ArizonaAdapter
from gradwindow.programme_adapters.mayo_clinic import (
    BIOMEDICAL_CATALOG_URL,
    HEALTH_CATALOG_URL,
    POSTDOCTORAL_CATALOG_URL,
    PROFESSIONAL_CATALOG_URL,
    RESIDENT_CATALOG_URL,
    MayoClinicAdapter,
)
from gradwindow.programme_adapters.nwpu import CATALOG_URL as NPU_CATALOG_URL
from gradwindow.programme_adapters.nwpu import GUIDE_URL as NPU_GUIDE_URL
from gradwindow.programme_adapters.nwpu import NPUAdapter
from gradwindow.programme_adapters.tianjin import CATALOG_URL as TIANJIN_CATALOG_URL
from gradwindow.programme_adapters.tianjin import GUIDE_URL as TIANJIN_GUIDE_URL
from gradwindow.programme_adapters.tianjin import TianjinAdapter
from gradwindow.programme_adapters.ulb import (
    APPLICATION_URL as ULB_APPLICATION_URL,
)
from gradwindow.programme_adapters.ulb import DEADLINES_URL as ULB_DEADLINES_URL
from gradwindow.programme_adapters.ulb import ULBAdapter, catalog_page_url


def test_nwpu_parses_rowspans_and_four_exact_batches() -> None:
    catalogue = """
      <table>
        <tr><th>School</th><th>Major</th><th>Medium</th><th>Requirement</th></tr>
        <tr><td rowspan="2">航空学院 School of Aeronautics</td>
          <td>飞行器设计 ✭ Flight Vehicle Design ✭</td><td>英文 English</td>
          <td rowspan="2">/</td></tr>
        <tr><td>流体力学 ✭ Fluid Mechanics ✭</td><td>英文 English</td></tr>
        <tr><td>管理学院 School of Management</td>
          <td>工商管理 Business Administration</td><td>英文 English</td><td>/</td></tr>
      </table>
    """
    guide = """
      <p>Application Period:</p>
      <p>The first batch: November 1, 2025 - January 15, 2026, 17:00.</p>
      <p>The second batch: January 16, 2026 - February 28, 2026, 17:00.</p>
      <p>The third batch: March 1, 2026 - March 31, 2026, 17:00.</p>
      <p>The fourth batch: April 1, 2026 - April 30, 2026, 17:00.</p>
    """
    pages = {NPU_CATALOG_URL: catalogue, NPU_GUIDE_URL: guide}

    catalog = NPUAdapter(
        minimum_expected_programmes=3, maximum_expected_programmes=3
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 4
    assert [window.closes_at for window in catalog.programmes[-1].windows] == [
        "2026-01-15",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]


def test_tianjin_reads_master_workbook_and_shared_window() -> None:
    workbook = json.dumps(
        {
            "worksheets": [
                {
                    "name": "MASTER",
                    "rows": [
                        [
                            "序号",
                            "专业名称",
                            "Majors",
                            "所属学院",
                            "School",
                            "学制",
                            "学生类别",
                            "Level",
                            "中文",
                            "Taught Language",
                        ],
                        [
                            1,
                            "材料学",
                            "Material Science",
                            "材料学院",
                            "School of Materials",
                            3,
                            "硕士",
                            "Master's Degree",
                            "中文",
                            "Chinese",
                        ],
                        [
                            2,
                            "控制科学与工程",
                            "Control Science and Engineering",
                            "自动化学院",
                            "School of Automation",
                            3,
                            "硕士",
                            "Master's Degree",
                            "英文",
                            "English",
                        ],
                    ],
                }
            ]
        }
    )
    guide = "<p>Application Schedule: October 15th, 202 5 - May 31st, 202 6.</p>"
    pages = {TIANJIN_CATALOG_URL: workbook, TIANJIN_GUIDE_URL: guide}

    catalog = TianjinAdapter(
        minimum_expected_programmes=2, maximum_expected_programmes=2
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert catalog.programmes[0].name.endswith(("(Chinese)", "(English)"))
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2025-10-15", "2026-05-31")


def test_ulb_crawls_filtered_pages_and_keeps_recurring_policy_separate() -> None:
    page_one = """
      <div class="search-result__result-item">
        <a class="item-title__element_title" href="https://www.ulb.be/fr/programme/ma-admp">
          <strong class="search-result__structure-intitule">Master en administration publique</strong>
        </a>
        <span class="search-result__structure-rattachement">Faculté de Philosophie</span>
        <span class="search-result__mnemonique">MA-ADMP</span>
      </div>
      <a href="/servlet/search?limit=100&amp;page=2">Page suivante</a>
    """
    page_two = """
      <div class="search-result__result-item">
        <a class="item-title__element_title" href="https://www.ulb.be/fr/programme/ma-antr">
          <strong class="search-result__structure-intitule">Master en anthropologie</strong>
        </a>
        <span class="search-result__structure-rattachement">Faculté de Philosophie</span>
        <span class="search-result__mnemonique">MA-ANTR</span>
      </div>
    """
    deadlines = """
      <p>Master and Specialized Masters From 1 April to 30 September</p>
      <p>Non-European students For all programs From 16 February to 31 March</p>
    """
    enrolment = "<p>Academic year 2026–2027</p>"
    pages = {
        catalog_page_url(1): page_one,
        catalog_page_url(2): page_two,
        ULB_DEADLINES_URL: deadlines,
        ULB_APPLICATION_URL: enrolment,
    }

    catalog = ULBAdapter(
        minimum_expected_programmes=2, maximum_expected_programmes=2
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 3
    windows = catalog.programmes[-1].windows
    assert [window.opens_at_basis for window in windows] == [
        "official-recurring-policy",
        "official-recurring-policy",
    ]
    assert windows[1].closes_at == "2026-03-31"


def test_arizona_reads_public_graphql_catalogue_without_inventing_years() -> None:
    script_url = f"{ARIZONA_CATALOG_URL}admissions-guides.fixture.js"
    app = '<script src="/admissions-guides/admissions-guides.fixture.js"></script>'
    script = (
        'fetch("https://fixture.execute-api.us-west-2.amazonaws.com/",'
        '{headers:{"X-API-Key":"public-fixture-key"}})'
    )
    policy = (
        "<p>The Graduate College does not have specific application deadlines, "
        "allowing each department to set their own.</p>"
    )
    payload = json.dumps(
        {
            "data": {
                "admissionsGuides": [
                    {
                        "uacadPlan": "ACCTMAC",
                        "acadPlanType": "MAJ",
                        "displayName": "Accounting (MAC)",
                        "degreeName": "Master of Accounting",
                        "degreeType": "Masters",
                        "lastAdmitTerm": "",
                        "acadCareer": "GRAD",
                        "admissionsDeadlines": "<ul><li>January 15: international fall applicants</li></ul>",
                        "planOwners": [
                            {
                                "academicUnit": "School of Accountancy",
                                "college": "Eller College of Management",
                            }
                        ],
                    },
                    {
                        "uacadPlan": "OLDMS",
                        "acadPlanType": "MAJ",
                        "displayName": "Old Program (MS)",
                        "degreeName": "Master of Science",
                        "degreeType": "Masters",
                        "lastAdmitTerm": "2251",
                        "acadCareer": "GRAD",
                        "admissionsDeadlines": "",
                        "planOwners": [],
                    },
                ]
            }
        }
    )
    pages = {
        ARIZONA_CATALOG_URL: app,
        script_url: script,
        ARIZONA_DEADLINES_URL: policy,
    }
    adapter = ArizonaAdapter(
        minimum_expected_programmes=1,
        maximum_expected_programmes=1,
        api_fetcher=lambda endpoint, key: payload,
    )

    catalog = adapter.parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 1
    assert catalog.programmes[0].windows == []
    assert "January 15" in catalog.programmes[0].deadline_text


def test_mayo_combines_health_and_restricted_biomedical_catalogues() -> None:
    pa_minnesota = (
        "https://college.mayo.edu/academics/health-sciences-education/"
        "physician-assistant-program-minnesota/"
    )
    pa_joint = (
        "https://college.mayo.edu/academics/health-sciences-education/"
        "physician-assistant-program-mayo-clinicuniversity-of-wisconsin-la-crosse/"
    )
    health = f"""
      <h4 id="master">Master's</h4>
      <a href="{pa_minnesota}">Physician Assistant Program</a>
      <a href="{pa_joint}">Physician Assistant Program</a>
      <h4 id="doctoral">Doctoral</h4>
    """
    professional = """
      PROFESSIONAL MASTER'S DEGREE PROGRAMS
      • Artificial Intelligence in Health Care (AIHC) – Professional Master's
      (https://catalog.mayo.edu/graduate-biomedical-sciences/employee-\nprofessional-masters-degree-programs/artificial-intelligence/)
      Application
    """
    resident = """
      RESIDENT MASTER'S DEGREE PROGRAMS
      • Orthopedics (ORS) - Resident Master’s Degree
      (https://catalog.mayo.edu/graduate-biomedical-sciences/clinical-\nmasters-degree-programs/orthopedics/)
      Eligibility
    """
    postdoctoral = """
      POSTDOCTORAL MASTER'S DEGREE PROGRAMS
      • Immunology (IMM) – Postdoctoral Masters
      (https://catalog.mayo.edu/graduate-biomedical-sciences/postdoctoral-\nbasic-science-masters-degree-programs/immunology/)
      Application
    """
    pages = {
        BIOMEDICAL_CATALOG_URL: "<p>Master’s of Science Degree Programs</p>",
        HEALTH_CATALOG_URL: health,
        PROFESSIONAL_CATALOG_URL: professional,
        RESIDENT_CATALOG_URL: resident,
        POSTDOCTORAL_CATALOG_URL: postdoctoral,
        pa_minnesota: (
            "<p>1 Pre-PA seat available for the class starting in July/August "
            "2027 (Class of 2029). Application window: April 30, 2026 - "
            "Aug. 1, 2026</p>"
        ),
        pa_joint: "<p>Application deadline is Aug. 1 for the following summer.</p>",
    }

    catalog = MayoClinicAdapter(
        minimum_expected_programmes=5, maximum_expected_programmes=5
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 5
    exact = [window for programme in catalog.programmes for window in programme.windows]
    assert len(exact) == 1
    assert (exact[0].opens_at, exact[0].closes_at) == (
        "2026-04-30",
        "2026-08-01",
    )
