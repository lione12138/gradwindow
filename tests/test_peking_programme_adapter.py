from __future__ import annotations

import json

from gradwindow.programme_adapters.peking import (
    APPLICATION_URL,
    CATALOG_URL,
    CURRENT_STANDARD_GUIDE_URL,
    YENCHING_SOURCE_URL,
    PekingAdapter,
    _date_ranges,
)

STANDARD_GUIDE = "https://www.isd.pku.edu.cn/cn/detail.php?id=725"
COMPUTER_GUIDE = "https://www.isd.pku.edu.cn/cn/detail.php?id=739"
YENCHING_GUIDE = "https://www.isd.pku.edu.cn/en/detail.php?id=756"

CATALOG = {
    "code": 1,
    "msg": "数据获取成功",
    "info": {
        "list": [
            {
                "id": "1",
                "departmentid": "10",
                "major": "计算机科学与技术",
                "direction": "计算理论",
                "learningstyle": "1",
                "language": "1",
                "degreetype": "1",
                "department_name": "计算机学院",
                "language_text": "中文",
                "learningstyle_text": "全日制",
                "degreetype_text": "硕士",
                "recruitment1": STANDARD_GUIDE,
            },
            {
                "id": "2",
                "departmentid": "10",
                "major": "计算机科学与技术",
                "direction": "软件工程",
                "learningstyle": "1",
                "language": "1",
                "degreetype": "1",
                "department_name": "计算机学院",
                "language_text": "中文",
                "learningstyle_text": "全日制",
                "degreetype_text": "硕士",
                "recruitment1": STANDARD_GUIDE,
            },
            {
                "id": "3",
                "departmentid": "10",
                "major": "计算机科学与技术",
                "direction": "人工智能",
                "learningstyle": "1",
                "language": "2",
                "degreetype": "1",
                "department_name": "计算机学院",
                "language_text": "英文",
                "learningstyle_text": "全日制",
                "degreetype_text": "硕士",
                "recruitment1": COMPUTER_GUIDE,
            },
            {
                "id": "4",
                "departmentid": "28",
                "major": "中国学（哲学与宗教）",
                "direction": "不区分研究方向",
                "learningstyle": "1",
                "language": "2",
                "degreetype": "1",
                "department_name": "燕京学堂",
                "language_text": "英文",
                "learningstyle_text": "全日制",
                "degreetype_text": "硕士",
                "recruitment1": YENCHING_GUIDE,
            },
            {
                "id": "5",
                "departmentid": "28",
                "major": "中国学（经济与管理）",
                "direction": "不区分研究方向",
                "learningstyle": "1",
                "language": "2",
                "degreetype": "1",
                "department_name": "燕京学堂",
                "language_text": "英文",
                "learningstyle_text": "全日制",
                "degreetype_text": "硕士",
                "recruitment1": YENCHING_GUIDE,
            },
            {
                "id": "6",
                "departmentid": "10",
                "major": "计算机科学与技术",
                "direction": "机器学习",
                "learningstyle": "1",
                "language": "2",
                "degreetype": "2",
                "department_name": "计算机学院",
                "language_text": "英文",
                "learningstyle_text": "全日制",
                "degreetype_text": "博士",
                "recruitment1": COMPUTER_GUIDE,
            },
        ]
    },
}

STANDARD_HTML = """
<main>
  <h1>2027 Application Information for International Students</h1>
  <p>4. Application Period (Beijing time)</p>
  <p>October 26, 2026 – December 25, 2026</p>
  <p>Note: For English-taught programmes see the individual guide.</p>
  <p>Scholarships: January 1, 2027 – March 1, 2027</p>
</main>
"""

COMPUTER_HTML = """
<main>
  <h1>2026 Application Guide for International Graduate Students</h1>
  <p>Application Period (Beijing time)</p>
  <p>Chinese-taught Program: October 20, 2025 - December 23, 2025</p>
  <p>English-taught Program: October 20, 2025 - January 10, 2026</p>
</main>
"""

YENCHING_HTML = """
<main>
  <h2>For Candidates from China’s Hong Kong, Macao and Taiwan Regions:</h2>
  <p>We accept a pplications for the 202 7 cohort of Yenching Scholars starting September 1, 202 6.</p>
  <p>Application deadline: January 8, 2027</p>
  <h2>For International Candidates:</h2>
  <p>We accept applications for the 2027 cohort of Yenching Scholars starting September 1, 2026.</p>
  <p>Application deadline: November 30, 2026</p>
</main>
"""


def _fetcher(url: str) -> str:
    if url == CATALOG_URL:
        return json.dumps(CATALOG, ensure_ascii=False)
    if url == CURRENT_STANDARD_GUIDE_URL:
        return STANDARD_HTML
    if url == COMPUTER_GUIDE:
        return COMPUTER_HTML
    if url == YENCHING_SOURCE_URL:
        return YENCHING_HTML
    raise AssertionError(url)


def test_peking_adapter_deduplicates_directions_and_keeps_language_variants() -> None:
    catalog = PekingAdapter(minimum_expected_programmes=3).parse_catalog_from_fetcher(
        _fetcher
    )

    assert len(catalog.programmes) == 3
    assert catalog.application_opens_at is None
    assert [programme.name for programme in catalog.programmes] == [
        "Yenching Academy Master's in China Studies",
        "计算机科学与技术（中文授课）",
        "计算机科学与技术（英文授课）",
    ]
    assert catalog.programmes[0].id == "pku-yenching-china-studies-master"
    assert catalog.programmes[1].application_url == APPLICATION_URL


def test_peking_adapter_uses_only_fully_explicit_official_date_ranges() -> None:
    catalog = PekingAdapter(minimum_expected_programmes=3).parse_catalog_from_fetcher(
        _fetcher
    )
    by_name = {programme.name: programme for programme in catalog.programmes}

    chinese = by_name["计算机科学与技术（中文授课）"]
    assert chinese.parse_status == "parsed"
    assert [
        (
            window.intake,
            window.opens_at,
            window.closes_at,
            window.applicant_categories,
        )
        for window in chinese.windows
    ] == [
        (
            "Autumn 2027",
            "2026-10-26",
            "2026-12-25",
            ["international-students"],
        )
    ]

    english = by_name["计算机科学与技术（英文授课）"]
    assert english.windows[0].opens_at == "2025-10-20"
    assert english.windows[0].closes_at == "2026-01-10"

    yenching = by_name["Yenching Academy Master's in China Studies"]
    assert yenching.parse_status == "parsed"
    assert [
        (w.opens_at, w.closes_at, w.applicant_categories) for w in yenching.windows
    ] == [
        ("2026-09-01", "2027-01-08", ["pku-hong-kong-macao-taiwan"]),
        ("2026-09-01", "2026-11-30", ["international-students"]),
    ]


def test_peking_adapter_rejects_a_truncated_or_invalid_catalogue() -> None:
    try:
        PekingAdapter(minimum_expected_programmes=4).parse_catalog_from_fetcher(
            _fetcher
        )
    except ValueError as exc:
        assert "only contained 3" in str(exc)
    else:
        raise AssertionError("Truncated Peking catalogue was accepted")


def test_peking_date_ranges_select_the_nearest_language_label() -> None:
    text = (
        "Chinese-taught Program: October 20, 2025 - December 23, 2025 "
        "English-taught Program: October 20, 2025 - January 10, 2026"
    )

    assert _date_ranges(text, "中文") == [("2025-10-20", "2025-12-23")]
    assert _date_ranges(text, "英文") == [("2025-10-20", "2026-01-10")]
