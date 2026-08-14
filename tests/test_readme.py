from __future__ import annotations

from datetime import date

from gradwindow.readme import _table, generate_readmes


def test_generate_bilingual_result_readmes(monkeypatch, tmp_path) -> None:
    english = tmp_path / "README.md"
    chinese = tmp_path / "README.zh-CN.md"
    monkeypatch.setattr("gradwindow.readme.README_PATH", english)
    monkeypatch.setattr("gradwindow.readme.README_ZH_PATH", chinese)

    generate_readmes(date(2026, 6, 15))

    english_text = english.read_text(encoding="utf-8")
    chinese_text = chinese.read_text(encoding="utf-8")
    assert "## Open Now" in english_text
    assert "## Opening Within 30 Days" in english_text
    assert "[中文](README.zh-CN.md)" in english_text
    assert "[Code](LICENSE)" in english_text
    assert "[data](DATA_LICENSE.md)" in english_text
    assert "CC BY-NC 4.0" in english_text
    assert "## 正在开放" in chinese_text
    assert "## 30 天内即将开放" in chinese_text
    assert "[English](README.md)" in chinese_text
    assert "[代码](LICENSE)" in chinese_text
    assert "[数据](DATA_LICENSE.md)" in chinese_text
    assert "top-200 universities across major global rankings" in english_text
    assert "THE and ARWU top-200 views are live" in english_text
    assert "U.S. News coverage is not presented as live yet" in english_text
    assert "全球主流排名前 200 大学" in chinese_text
    assert "U.S. News 暂不标为已上线" in chinese_text
    assert "web/og-image-multiranking.png" in english_text


def test_readme_table_groups_programme_windows_by_university() -> None:
    university = {
        "id": "example-university",
        "rankDisplay": "1",
        "school": "Example University",
        "schoolZh": "示例大学",
        "homepageUrl": "https://example.edu/",
        "admissionsUrl": "https://example.edu/admissions/",
    }
    records = [
        {
            "universityId": university["id"],
            "scopeType": "programme",
            "scopeId": "programme-a",
            "opensAt": "2026-06-01",
            "closesAt": "2026-08-20",
            "dataStatus": "official",
        },
        {
            "universityId": university["id"],
            "scopeType": "programme",
            "scopeId": "programme-b",
            "opensAt": "2026-06-15",
            "closesAt": "2026-08-10",
            "dataStatus": "official",
        },
    ]

    table = _table(records, {university["id"]: university}, "en", "open")

    assert table.count("| 1 | Example University |") == 1
    assert "2 open windows" in table
    assert "2026-08-10" in table
    assert "programme-a" not in table
    assert "programme-b" not in table


def test_readme_table_prefers_an_institution_level_window() -> None:
    university = {
        "id": "example-university",
        "rankDisplay": "1",
        "school": "Example University",
        "schoolZh": "示例大学",
        "homepageUrl": "https://example.edu/",
        "admissionsUrl": "https://example.edu/admissions/",
    }
    records = [
        {
            "universityId": university["id"],
            "scopeType": "programme",
            "scopeId": "programme-a",
            "opensAt": "2026-06-01",
            "closesAt": "2026-08-10",
            "dataStatus": "official",
        },
        {
            "universityId": university["id"],
            "scopeType": "institution",
            "scopeId": university["id"],
            "opensAt": "2026-07-01",
            "closesAt": "2026-09-30",
            "dataStatus": "official",
        },
    ]

    table = _table(records, {university["id"]: university}, "zh", "open")

    assert "学校级窗口" in table
    assert "2026-09-30" in table
    assert "2026-08-10" not in table
