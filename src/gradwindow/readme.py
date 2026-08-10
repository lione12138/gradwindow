from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import quote

from .io import read_json
from .paths import (
    APPLICATIONS_PATH,
    PREDICTIONS_PATH,
    ROOT,
    UNIVERSITIES_PATH,
)

SITE_URL = "https://gradwindow.com/"
README_PATH = ROOT / "README.md"
README_ZH_PATH = ROOT / "README.zh-CN.md"


def application_status(record: dict, today: date) -> str:
    opens = date.fromisoformat(record["opensAt"])
    closes = date.fromisoformat(record["closesAt"])
    if today > closes:
        return "closed"
    if today >= opens:
        return "open"
    return "upcoming" if (opens - today).days <= 30 else "future"


def generate_readmes(today: date | None = None) -> tuple[Path, Path]:
    today = today or date.today()
    universities = read_json(UNIVERSITIES_PATH)["universities"]
    applications = read_json(APPLICATIONS_PATH)["applications"]
    predictions = read_json(PREDICTIONS_PATH)["predictions"]

    university_by_id = {item["id"]: item for item in universities}
    records = [{**item, "dataStatus": "official"} for item in applications] + [
        {**item, "dataStatus": "predicted"} for item in predictions
    ]
    records.sort(
        key=lambda item: (
            university_by_id[item["universityId"]].get("qsPosition") or 10_000,
            item["opensAt"],
        )
    )

    active = [item for item in records if application_status(item, today) == "open"]
    upcoming = [
        item for item in records if application_status(item, today) == "upcoming"
    ]
    README_PATH.write_text(
        _render_readme(
            active,
            upcoming,
            university_by_id,
            today,
            language="en",
        ),
        encoding="utf-8",
        newline="\n",
    )
    README_ZH_PATH.write_text(
        _render_readme(
            active,
            upcoming,
            university_by_id,
            today,
            language="zh",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return README_PATH, README_ZH_PATH


def _table(
    records: list[dict],
    university_by_id: dict[str, dict],
    language: str,
    window_state: str,
) -> str:
    if language == "en":
        date_heading = "Next deadline" if window_state == "open" else "Next opening"
        header = (
            f"| QS | University | Coverage | {date_heading} | Data | Links |\n"
            "|---:|---|---|---|---|---|"
        )
        empty = "_No matching windows today._"
        official = "Official"
        estimate = "Estimate"
        institution_window = "Institution-level window"
        state_label = "open" if window_state == "open" else "upcoming"
        admissions_link = "Admissions"
        details_link = "All programme details"
    else:
        date_heading = "最近截止" if window_state == "open" else "最近开放"
        header = (
            f"| QS | 大学 | 覆盖范围 | {date_heading} | 数据类型 | 链接 |\n"
            "|---:|---|---|---|---|---|"
        )
        empty = "_今天没有符合条件的窗口。_"
        official = "官网核验"
        estimate = "预测参考"
        institution_window = "学校级窗口"
        state_label = "当前开放" if window_state == "open" else "即将开放"
        admissions_link = "招生官网"
        details_link = "查看全部项目"

    if not records:
        return empty

    grouped: dict[str, list[dict]] = {}
    for item in records:
        grouped.setdefault(item["universityId"], []).append(item)

    rows = [header]
    for university_id, university_records in grouped.items():
        university = university_by_id[university_id]
        university_name = (
            f"{university['school']} / {university['schoolZh']}"
            if language == "zh" and university.get("schoolZh")
            else university["school"]
        ).replace("|", "\\|")
        institution_records = [
            item for item in university_records if item["scopeType"] == "institution"
        ]
        display_records = institution_records or university_records
        if institution_records:
            coverage = institution_window
        elif language == "en":
            suffix = "" if len(university_records) == 1 else "s"
            coverage = f"{len(university_records)} {state_label} window{suffix}"
        else:
            coverage = f"{len(university_records)} 个{state_label}窗口"
        date_field = "closesAt" if window_state == "open" else "opensAt"
        nearest_date = min(item[date_field] for item in display_records)
        statuses = {item["dataStatus"] for item in display_records}
        data_label = (
            official
            if statuses == {"official"}
            else estimate
            if statuses == {"predicted"}
            else f"{official} + {estimate}"
        )
        admissions_url = university.get("admissionsUrl") or university["homepageUrl"]
        details_url = f"{SITE_URL}?q={quote(university['school'])}"
        links = (
            f"[{admissions_link}]({admissions_url}) · [{details_link}]({details_url})"
        )
        rows.append(
            f"| {university.get('rankDisplay') or '—'} | {university_name} | "
            f"{coverage} | {nearest_date} | {data_label} | {links} |"
        )
    return "\n".join(rows)


def _render_readme(
    active: list[dict],
    upcoming: list[dict],
    university_by_id: dict[str, dict],
    today: date,
    language: str,
) -> str:
    if language == "en":
        language_link = "[中文](README.zh-CN.md)"
        license_notice = (
            "**Licensing:** [Code](LICENSE) and [data](DATA_LICENSE.md) are "
            "licensed separately. Reuse of the curated admissions dataset "
            "requires attribution to GradWindow and is limited to "
            "noncommercial use under CC BY-NC 4.0. Official university "
            "pages remain the authoritative source."
        )
        intro = (
            "A QS Top 200 master's application tracker using official "
            "university sources. The tables below summarize each university "
            "once; full programme-level windows remain available on the website."
        )
        open_heading = "## Open Now"
        upcoming_heading = "## Opening Within 30 Days"
        note = (
            "> **Estimate** means the date is shifted from the latest "
            "verified cycle and is not an official forecast. Always confirm "
            "dates on the linked university source."
        )
        updated = f"Status date: **{today.isoformat()}**"
    else:
        language_link = "[English](README.md)"
        license_notice = (
            "**许可说明：**[代码](LICENSE)与[数据](DATA_LICENSE.md)采用不同"
            "许可证。复用 GradWindow 整理的申请数据集必须署名，并仅限 "
            "CC BY-NC 4.0 允许的非商业用途。大学官网始终是权威信息来源。"
        )
        intro = (
            "基于大学官网数据的 QS 前 200 硕士申请追踪项目。下面只展示"
            "每所大学的汇总信息；完整的项目级申请窗口请前往网站查看。"
        )
        open_heading = "## 正在开放"
        upcoming_heading = "## 30 天内即将开放"
        note = (
            "> **预测参考**表示日期由最近一个官网核验周期平移一年得到，"
            "不是学校官方预测。申请前请始终核对表格中的官网来源。"
        )
        updated = f"状态日期：**{today.isoformat()}**"

    return f"""# GradWindow

[![Tests](https://github.com/lione12138/qs-master-applications/actions/workflows/tests.yml/badge.svg)](https://github.com/lione12138/qs-master-applications/actions/workflows/tests.yml)
[![Website](https://img.shields.io/badge/Website-GradWindow-1e6548)]({SITE_URL})

{language_link} · [Live website]({SITE_URL})

{license_notice}

{intro}

{updated}

{note}

{open_heading}

{_table(active, university_by_id, language, "open")}

{upcoming_heading}

{_table(upcoming, university_by_id, language, "upcoming")}
"""
