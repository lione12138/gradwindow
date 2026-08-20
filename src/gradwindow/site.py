from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from .frontend import build_frontend_payloads, write_compact_json
from .io import read_json
from .paths import (
    APPLICANT_CATEGORIES_PATH,
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    COVERAGE_PATH,
    GLOBAL_RANKINGS_PATH,
    MONITOR_STATE_PATH,
    PREDICTIONS_PATH,
    PROGRAMME_GROUPS_PATH,
    PROGRAMS_PATH,
    RECURRING_WINDOWS_PATH,
    REFRESH_STATUS_PATH,
    ROOT,
    SITE_DIR,
    UNIVERSITIES_PATH,
    WEB_DIR,
    WINDOW_POLICIES_PATH,
)

PUBLIC_FILES = (
    "CNAME",
    "ffcdfa5871ff4d52aed733120c248bf8.txt",
    "index.html",
    "calendar.html",
    "contact.html",
    "roadmap.html",
    "admin.html",
    "privacy.html",
    "app.js",
    "calendar.js",
    "contact.js",
    "roadmap.js",
    "admin.js",
    "exception-status.js",
    "frontend-data.js",
    "deadline-semantics.js",
    "status.js",
    "intake-filter.js",
    "ranking-filter.js",
    "university-deep-link.js",
    "window-grouping.js",
    "window-provenance.js",
    "localization.js",
    "i18n.js",
    "dom.js",
    "state.js",
    "strings.js",
    "calendar-export.js",
    "turnstile.js",
    "auth.js",
    "review.js",
    "styles.css",
    "og-image-multiranking.png",
    "favicon.svg",
    "cat-avatar.svg",
)
LEGACY_SITE_URL = "https://lione12138.github.io/qs-master-applications"
DEFAULT_SITE_URL = "https://gradwindow.com"
UPCOMING_WINDOW_DAYS = 30
MIN_SEARCH_LANDING_RECORDS = 3
FEATURED_UNIVERSITY_LIMIT = 8
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
CLOUDFLARE_ANALYTICS_TOKEN = "02939949076c423f953d11db0caade78"
CLOUDFLARE_ANALYTICS = (
    '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
    f'data-cf-beacon=\'{{"token":"{CLOUDFLARE_ANALYTICS_TOKEN}"}}\'>'
    "</script>"
)
PUBLIC_DATA = (
    UNIVERSITIES_PATH,
    APPLICATIONS_PATH,
    PREDICTIONS_PATH,
    RECURRING_WINDOWS_PATH,
    REFRESH_STATUS_PATH,
    MONITOR_STATE_PATH,
    PROGRAMS_PATH,
    PROGRAMME_GROUPS_PATH,
    APPLICANT_CATEGORIES_PATH,
    ROOT / "data" / "programme-translations.json",
    WINDOW_POLICIES_PATH,
    COVERAGE_PATH,
    GLOBAL_RANKINGS_PATH,
    APPLICATION_SOURCE_STATE_PATH,
    ROOT / "data" / "roadmap-proposals.json",
)


def site_url() -> str:
    return os.environ.get("GRADWINDOW_SITE_URL", DEFAULT_SITE_URL).rstrip("/")


def _safe_build_output_dir(output_dir: Path) -> Path:
    resolved_output = output_dir.expanduser().resolve()
    resolved_root = ROOT.resolve()
    resolved_site = SITE_DIR.resolve()

    if resolved_output == resolved_root or resolved_root.is_relative_to(
        resolved_output
    ):
        raise ValueError(
            f"Refusing to build into project root or its ancestor: {resolved_output}"
        )
    if resolved_output.is_relative_to(resolved_root) and not (
        resolved_output == resolved_site
        or resolved_output.is_relative_to(resolved_site)
    ):
        raise ValueError(
            f"Refusing to build over project source files: {resolved_output}"
        )
    return resolved_output


def build_site(output_dir: Path = SITE_DIR) -> Path:
    output_dir = _safe_build_output_dir(output_dir)
    public_site_url = site_url()
    build_date = date.today()
    public_config = {
        "subscribeUrl": os.environ.get("GRADWINDOW_SUBSCRIBE_URL", "").rstrip("/"),
        "turnstileSiteKey": os.environ.get(
            "GRADWINDOW_TURNSTILE_SITE_KEY",
            "",
        ),
        "roadmapUrl": os.environ.get("GRADWINDOW_ROADMAP_URL", "").rstrip("/"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    for filename in PUBLIC_FILES:
        shutil.copy2(WEB_DIR / filename, output_dir / filename)
    for page_name in (
        "index.html",
        "calendar.html",
        "contact.html",
        "roadmap.html",
        "admin.html",
        "privacy.html",
    ):
        page_path = output_dir / page_name
        page_path.write_text(
            page_path.read_text(encoding="utf-8")
            .replace(
                f"{LEGACY_SITE_URL}/",
                f"{public_site_url}/",
            )
            .replace(
                f"{DEFAULT_SITE_URL}/",
                f"{public_site_url}/",
            )
            .replace(
                "window.GRADWINDOW_CONFIG = {};",
                f"window.GRADWINDOW_CONFIG = {json.dumps(public_config)};",
            ),
            encoding="utf-8",
        )
    index_path = output_dir / "index.html"
    index_path.write_text(
        render_home_snapshot(index_path.read_text(encoding="utf-8"), build_date),
        encoding="utf-8",
    )
    data_dir = output_dir / "data"
    data_dir.mkdir()
    for source in PUBLIC_DATA:
        shutil.copy2(source, data_dir / source.name)
    frontend_index, frontend_closed, university_details = build_frontend_payloads(
        build_date
    )
    write_compact_json(data_dir / "frontend-index.json", frontend_index)
    write_compact_json(data_dir / "frontend-closed.json", frontend_closed)
    university_data_dir = data_dir / "university"
    for university_id, details in university_details.items():
        write_compact_json(university_data_dir / f"{university_id}.json", details)

    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    (output_dir / "sources.html").write_text(
        render_sources_page(public_site_url), encoding="utf-8"
    )
    generated_urls = generate_index_pages(output_dir, public_site_url, build_date)
    data_lastmod = public_data_lastmod()
    sitemap_urls: list[str | tuple[str, str | None]] = [
        (public_site_url, data_lastmod),
        (f"{public_site_url}/calendar.html", data_lastmod),
        f"{public_site_url}/contact.html",
        f"{public_site_url}/roadmap.html",
        f"{public_site_url}/privacy.html",
        (f"{public_site_url}/sources.html", data_lastmod),
        *generated_urls,
    ]
    (output_dir / "sitemap.xml").write_text(
        render_sitemap(sitemap_urls), encoding="utf-8"
    )
    (output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {public_site_url}/sitemap.xml\n",
        encoding="utf-8",
    )
    version_public_assets(output_dir)
    return output_dir / "index.html"


def version_public_assets(output_dir: Path) -> str:
    assets = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix in {".js", ".css"}
    )
    digest = hashlib.sha256()
    for asset in assets:
        digest.update(asset.name.encode("utf-8"))
        digest.update(asset.read_bytes())
    version = digest.hexdigest()[:12]
    pattern = re.compile(
        r'(?P<quote>["\'])(?P<path>\./[^"\'?#]+\.(?:js|css))'
        r'(?:\?v=[^"\']*)?(?P=quote)'
    )
    for path in [*output_dir.glob("*.html"), *output_dir.glob("*.js")]:
        source = path.read_text(encoding="utf-8")
        versioned = pattern.sub(
            lambda match: (
                f"{match.group('quote')}{match.group('path')}?v={version}"
                f"{match.group('quote')}"
            ),
            source,
        )
        path.write_text(versioned, encoding="utf-8")
    return version


def application_status(item: dict, today: date) -> str:
    opens_at = date.fromisoformat(item["opensAt"])
    closes_at = date.fromisoformat(item["closesAt"])
    if today > closes_at or (
        item.get("deadlineSemantics") == "before" and today >= closes_at
    ):
        return "closed"
    if today >= opens_at:
        return "open"
    if (opens_at - today).days <= UPCOMING_WINDOW_DAYS:
        return "upcoming"
    return "future"


def iso_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    return match.group(1) if match else None


def latest_date(*values: str | None) -> str | None:
    dates = [value for value in (iso_date(item) for item in values) if value]
    return max(dates, default=None)


def record_lastmod(item: dict) -> str | None:
    return latest_date(
        item.get("verifiedAt"),
        item.get("policyCheckedAt"),
        item.get("basedOnVerifiedAt"),
    )


def records_lastmod(items: list[dict]) -> str | None:
    return max(
        (value for item in items if (value := record_lastmod(item))),
        default=None,
    )


def public_data_lastmod() -> str:
    applications = read_json(APPLICATIONS_PATH)["meta"]
    recurring = read_json(RECURRING_WINDOWS_PATH)["meta"]
    monitor = read_json(MONITOR_STATE_PATH, {}).get("meta", {})
    return (
        latest_date(
            applications.get("updatedAt"),
            recurring.get("updatedAt"),
            monitor.get("checkedAt"),
        )
        or date.today().isoformat()
    )


def human_date(value: str) -> str:
    parsed = date.fromisoformat(value[:10])
    return f"{MONTH_NAMES[parsed.month - 1]} {parsed.day}, {parsed.year}"


def deadline_text(item: dict, *, human: bool = False) -> str:
    value = human_date(item["closesAt"]) if human else item["closesAt"]
    return f"Before {value}" if item.get("deadlineSemantics") == "before" else value


def month_label(value: str) -> str:
    year, month = (int(part) for part in value.split("-", 1))
    return f"{MONTH_NAMES[month - 1]} {year}"


def intake_slug(item: dict) -> str | None:
    details = item.get("intakeDetails") or {}
    cycle_year = details.get("cycleYear")
    term = details.get("term")
    if cycle_year and term in {"fall", "spring"}:
        return f"{cycle_year}-{term}"
    return None


def intake_page_label(slug: str) -> str:
    year, term = slug.split("-", 1)
    return f"{term.title()} {year}"


def primary_cycle_year(predictions: list[dict], today: date) -> int:
    cycle_counts = Counter(
        details["cycleYear"]
        for item in predictions
        if (details := item.get("intakeDetails") or {}).get("cycleYear")
        and details["cycleYear"] >= today.year
    )
    if not cycle_counts:
        return today.year + 1
    return max(cycle_counts, key=lambda year: (cycle_counts[year], -year))


def featured_university_links(
    items: list[dict],
    universities_by_id: dict[str, dict],
) -> str:
    university_ids = sorted(
        {item["universityId"] for item in items},
        key=lambda university_id: (
            universities_by_id.get(university_id, {}).get("qsPosition") is None,
            universities_by_id.get(university_id, {}).get("qsPosition") or 10_000,
            universities_by_id.get(university_id, {}).get("school", university_id),
        ),
    )[:FEATURED_UNIVERSITY_LIMIT]
    return "".join(
        f'<li><a href="./university/{university_id}/">'
        f"{html.escape(universities_by_id[university_id]['school'])}</a></li>"
        for university_id in university_ids
        if university_id in universities_by_id
    )


def search_landing_links(
    rows: list[dict],
    target_cycle_year: int,
    today: date,
) -> str:
    opening_counts = Counter(item["opensAt"][:7] for item in rows)
    current_month = today.isoformat()[:7]
    future_opening_months = sorted(
        month
        for month, count in opening_counts.items()
        if month > current_month and count >= MIN_SEARCH_LANDING_RECORDS
    )
    links: list[tuple[str, str]] = []
    if future_opening_months:
        month = future_opening_months[0]
        links.append(
            (
                f"./opening/{month}/",
                f"{month_label(month)} application openings",
            )
        )
    intake_counts = Counter(
        slug for item in rows if (slug := intake_slug(item)) is not None
    )
    for term in ("fall", "spring"):
        slug = f"{target_cycle_year}-{term}"
        if intake_counts[slug] >= MIN_SEARCH_LANDING_RECORDS:
            links.append((f"./intake/{slug}/", f"{intake_page_label(slug)} intake"))
    links.extend(
        [
            ("./calendar.html", f"{target_cycle_year} application calendar"),
            ("./sources.html", "Official sources and coverage"),
        ]
    )
    return "".join(
        f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
        for url, label in links
    )


def home_snapshot(today: date | None = None) -> dict[str, str]:
    today = today or date.today()
    university_payload = read_json(UNIVERSITIES_PATH)
    application_payload = read_json(APPLICATIONS_PATH)
    universities = university_payload["universities"]
    applications = application_payload["applications"]
    predictions = read_json(PREDICTIONS_PATH)["predictions"]
    recurring_windows = read_json(RECURRING_WINDOWS_PATH)["recurringWindows"]
    policies = read_json(WINDOW_POLICIES_PATH)["policies"]
    coverage = read_json(COVERAGE_PATH)["universities"]
    monitor = read_json(MONITOR_STATE_PATH, {})
    refresh_status = read_json(REFRESH_STATUS_PATH, {})

    qs_universities = [
        item for item in universities if item.get("qsPosition") is not None
    ]
    qs_ids = {item["id"] for item in qs_universities}
    rows = [*applications, *recurring_windows, *predictions]
    target_cycle_year = primary_cycle_year(predictions, today)
    ranked_rows = [item for item in rows if item["universityId"] in qs_ids]
    rows_by_status = {
        status: [
            item for item in ranked_rows if application_status(item, today) == status
        ]
        for status in ("open", "upcoming", "future", "closed")
    }
    university_counts = {
        status: len({item["universityId"] for item in items})
        for status, items in rows_by_status.items()
    }

    coverage_by_university = {item["universityId"]: item for item in coverage}
    policies_by_university = {item["universityId"]: item for item in policies}
    manual_policy_statuses = {
        "official-entry-protected",
        "dynamic-listing-dates-not-captured",
        "official-route-current-dates-not-captured",
    }

    def needs_manual_check(university: dict) -> bool:
        university_id = university["id"]
        next_action = coverage_by_university.get(university_id, {}).get("nextAction")
        policy_status = (
            policies_by_university.get(university_id, {})
            .get("cycleGuidance", {})
            .get("status", "")
        )
        return (
            next_action in {"locate-official-entry", "verify-window-policy"}
            or university.get("admissionsDiscovery")
            in {"low-confidence", "not-found", "pending", "error"}
            or policy_status in manual_policy_statuses
        )

    next_deadline = min(
        (
            item
            for item in applications
            if date.fromisoformat(item["closesAt"]) >= today
        ),
        key=lambda item: item["closesAt"],
        default=None,
    )
    universities_by_id = {item["id"]: item for item in universities}
    university_names = {
        university_id: item["school"]
        for university_id, item in universities_by_id.items()
    }
    if next_deadline:
        deadline_date = date.fromisoformat(next_deadline["closesAt"])
        deadline_day = f"{deadline_date.day:02d}"
        deadline_month = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()[
            deadline_date.month - 1
        ]
        deadline_school = university_names[next_deadline["universityId"]]
        deadline_mobile_date = (
            f"{deadline_date.day} {deadline_month.title()} {deadline_date.year}"
        )
        deadline_url = next_deadline["applicationUrl"]
        deadline_note = "Official application deadline"
    else:
        deadline_day = str(len(qs_universities))
        deadline_month = "SCHOOLS"
        deadline_school = "Official admissions directory"
        deadline_mobile_date = f"TOP {len(qs_universities)}"
        deadline_url = "#application-groups"
        deadline_note = ""

    data_refreshed_at = (
        refresh_status.get("dataRefreshedAt")
        or application_payload["meta"]["updatedAt"]
    )
    page_checked_at = refresh_status.get("pageCheckedAt") or monitor.get(
        "meta", {}
    ).get("checkedAt")
    monitoring_run_at = refresh_status.get("lastSuccessfulMonitoringRun")
    refreshed_date = date.fromisoformat(data_refreshed_at[:10])
    refresh_age_days = max((today - refreshed_date).days, 0)
    refresh_summary = (
        "Updated today"
        if refresh_age_days == 0
        else f"Updated {refresh_age_days} day{'s' if refresh_age_days != 1 else ''} ago"
    )
    monitoring_age_days = (
        max((today - date.fromisoformat(monitoring_run_at[:10])).days, 0)
        if monitoring_run_at
        else None
    )
    official_start = min(item["opensAt"] for item in applications)
    official_end = max(item["closesAt"] for item in applications)

    return {
        "data_refreshed_at": f"Data refreshed: {human_date(data_refreshed_at)}",
        "page_checked_at": (
            f"Page checked: {human_date(page_checked_at)}"
            if page_checked_at
            else "Page checked: unavailable"
        ),
        "monitoring_run_at": (
            f"Last successful monitoring run: {human_date(monitoring_run_at)}"
            if monitoring_run_at
            else "Last successful monitoring run: unavailable"
        ),
        "refresh_summary": refresh_summary,
        "monitoring_health": (
            "Monitoring healthy"
            if monitoring_age_days is not None and monitoring_age_days <= 2
            else "Monitoring delayed"
        ),
        "deadline_day": deadline_day,
        "deadline_month": deadline_month,
        "deadline_school": deadline_school,
        "deadline_mobile_date": deadline_mobile_date,
        "deadline_url": deadline_url,
        "deadline_note": deadline_note,
        "total_universities": str(len(universities)),
        "official_windows": str(len(applications)),
        "estimated_windows": str(len(predictions)),
        "open_universities": str(university_counts["open"]),
        "upcoming_universities": str(university_counts["upcoming"]),
        "future_universities": str(university_counts["future"]),
        "closed_universities": str(university_counts["closed"]),
        "manual_check_universities": str(
            sum(needs_manual_check(item) for item in qs_universities)
        ),
        "directory_universities": str(len(qs_universities)),
        "open_windows": str(len(rows_by_status["open"])),
        "target_cycle_year": str(target_cycle_year),
        "dataset_date_modified": iso_date(application_payload["meta"]["updatedAt"])
        or today.isoformat(),
        "dataset_temporal_coverage": f"{official_start}/{official_end}",
        "featured_open_links": featured_university_links(
            rows_by_status["open"], universities_by_id
        ),
        "featured_upcoming_links": featured_university_links(
            rows_by_status["upcoming"], universities_by_id
        ),
        "search_landing_links": search_landing_links(rows, target_cycle_year, today),
    }


def render_home_snapshot(source: str, today: date | None = None) -> str:
    snapshot = home_snapshot(today)
    rendered = source
    raw_html_keys = {
        "featured_open_links",
        "featured_upcoming_links",
        "search_landing_links",
    }
    for key, value in snapshot.items():
        rendered = rendered.replace(
            f"{{{{GRADWINDOW_{key.upper()}}}}}",
            value if key in raw_html_keys else html.escape(value, quote=True),
        )
    unresolved = sorted(set(re.findall(r"\{\{GRADWINDOW_[A-Z_]+\}\}", rendered)))
    if unresolved:
        raise ValueError(f"Unresolved home snapshot tokens: {', '.join(unresolved)}")
    return rendered


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "other"


def generate_index_pages(
    output_dir: Path,
    public_site_url: str,
    today: date | None = None,
) -> list[tuple[str, str | None]]:
    today = today or date.today()
    universities = read_json(UNIVERSITIES_PATH)["universities"]
    applications = read_json(APPLICATIONS_PATH)["applications"]
    predictions = read_json(PREDICTIONS_PATH)["predictions"]
    recurring_windows = read_json(RECURRING_WINDOWS_PATH)["recurringWindows"]
    monitor_entries = read_json(MONITOR_STATE_PATH, {"universities": {}}).get(
        "universities", {}
    )
    programs = read_json(PROGRAMS_PATH)["programs"]
    groups = read_json(PROGRAMME_GROUPS_PATH)["groups"]
    applicant_categories = read_json(APPLICANT_CATEGORIES_PATH)["categories"]
    program_names = {item["id"]: item["name"] for item in programs}
    group_names = {item["id"]: item["name"] for item in groups}
    applicant_category_names = {
        item["id"]: item["labelEn"] for item in applicant_categories
    }
    university_names = {item["id"]: item["school"] for item in universities}
    indexed_countries = {
        item["country"] for item in universities if item.get("qsPosition") is not None
    }
    target_cycle_year = primary_cycle_year(predictions, today)
    generated_urls: list[tuple[str, str | None]] = []
    all_records = [*applications, *recurring_windows, *predictions]
    intake_counts = Counter(
        slug for item in all_records if (slug := intake_slug(item)) is not None
    )
    valid_intake_slugs = {
        slug
        for slug, count in intake_counts.items()
        if count >= MIN_SEARCH_LANDING_RECORDS
    }
    official_by_university: dict[str, list[dict]] = defaultdict(list)
    recurring_by_university: dict[str, list[dict]] = defaultdict(list)
    predicted_by_university: dict[str, list[dict]] = defaultdict(list)
    for item in applications:
        official_by_university[item["universityId"]].append(item)
    for item in recurring_windows:
        recurring_by_university[item["universityId"]].append(item)
    for item in predictions:
        predicted_by_university[item["universityId"]].append(item)

    for university in universities:
        university_dir = output_dir / "university" / university["id"]
        university_dir.mkdir(parents=True, exist_ok=True)
        university_id = university["id"]
        official = official_by_university[university_id]
        estimated = predicted_by_university[university_id]
        recurring = recurring_by_university[university_id]
        all_records = [*official, *recurring, *estimated]
        calendar_records = [
            item
            for item in [*official, *recurring]
            if date.fromisoformat(item["closesAt"]) >= today
        ]
        if calendar_records:
            (university_dir / "deadlines.ics").write_text(
                render_university_calendar(
                    university["school"],
                    calendar_records,
                    program_names,
                    group_names,
                ),
                encoding="utf-8",
                newline="",
            )
        indexable = bool(all_records)
        canonical = f"{public_site_url}/university/{university['id']}/"
        ranking_label = (
            f"QS {university['rankDisplay']}"
            if university.get("rankDisplay")
            else "THE / ARWU / U.S. News monitored university"
        )
        country_label = html.escape(university["country"])
        if university["country"] in indexed_countries:
            country_label = (
                f'<a href="../../country/{slugify(university["country"])}/">'
                f"{country_label}</a>"
            )
        monitor_item = monitor_entries.get(university_id, {})
        body = (
            f'<p class="back"><a href="../../index.html">Back to tracker</a></p>'
            f"<p>{html.escape(ranking_label)} · "
            f"{country_label}</p>"
            f'<p><a href="{html.escape(university["homepageUrl"], quote=True)}">'
            "University website</a>"
            + (
                f' · <a href="{html.escape(university["admissionsUrl"], quote=True)}">'
                "Graduate application entry</a>"
                if university.get("admissionsUrl")
                else ""
            )
            + "</p>"
            + render_university_product_actions(
                university_id,
                university["school"],
                has_calendar=bool(calendar_records),
            )
            + render_university_summary(
                official,
                recurring,
                estimated,
                monitor_item,
                today,
                valid_intake_slugs,
            )
            + render_window_list(
                official,
                "Verified official windows",
                program_names,
                group_names,
                applicant_category_names,
                valid_intake_slugs,
            )
            + render_window_list(
                recurring,
                "Official recurring policies (cycle year mapped by GradWindow)",
                program_names,
                group_names,
                applicant_category_names,
                valid_intake_slugs,
                recurring=True,
            )
            + render_window_list(
                estimated,
                "Next-cycle calendar-shift references",
                program_names,
                group_names,
                applicant_category_names,
                valid_intake_slugs,
                predicted=True,
            )
        )
        if indexable:
            title = university_page_title(university["school"], target_cycle_year)
            description = university_meta_description(
                university["school"], official, recurring, estimated, target_cycle_year
            )
        else:
            title = f"{university['school']} Graduate Admissions Sources"
            description = (
                f"Official website and graduate admissions entry for {university['school']}. "
                "GradWindow has no verified or estimated application-window records for this university yet."
            )
        (university_dir / "index.html").write_text(
            render_static_page(
                title,
                description,
                body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (university["school"], canonical),
                ],
                indexable=indexable,
                date_modified=latest_date(
                    records_lastmod(all_records), monitor_item.get("checkedAt")
                ),
            ),
            encoding="utf-8",
        )
        if indexable:
            generated_urls.append((canonical, records_lastmod(all_records)))

    by_country: dict[str, list[dict]] = {}
    for university in universities:
        if university.get("qsPosition") is None:
            continue
        by_country.setdefault(university["country"], []).append(university)
    for country, items in by_country.items():
        country_slug = slugify(country)
        country_dir = output_dir / "country" / country_slug
        country_dir.mkdir(parents=True, exist_ok=True)
        rows = "".join(
            "<li>"
            f"<strong>QS {html.escape(item['rankDisplay'])}</strong> "
            f'<a href="../../university/{item["id"]}/">'
            f"{html.escape(item['school'])}</a></li>"
            for item in sorted(items, key=lambda value: value["qsPosition"])
        )
        canonical = f"{public_site_url}/country/{country_slug}/"
        body = (
            '<p class="back"><a href="../../index.html">Back to tracker</a></p>'
            f"<p>{len(items)} QS Top 200 universities.</p><ul>{rows}</ul>"
        )
        (country_dir / "index.html").write_text(
            render_static_page(
                f"QS Top 200 master's applications in {country}",
                (
                    f"Explore {len(items)} QS Top 200 universities in {country}, "
                    "with official university and graduate admissions links plus "
                    "verified master's application windows and deadlines."
                ),
                body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (country, canonical),
                ],
            ),
            encoding="utf-8",
        )
        generated_urls.append(
            (
                canonical,
                records_lastmod([*applications, *recurring_windows, *predictions]),
            )
        )

    by_month: dict[str, list[tuple[dict, str]]] = {}
    for item in applications:
        by_month.setdefault(item["closesAt"][:7], []).append((item, "official"))
    for item in recurring_windows:
        by_month.setdefault(item["closesAt"][:7], []).append((item, "recurring"))
    for item in predictions:
        by_month.setdefault(item["closesAt"][:7], []).append((item, "predicted"))
    for month, items in by_month.items():
        month_dir = output_dir / "deadline" / month
        month_dir.mkdir(parents=True, exist_ok=True)
        rows = "".join(
            "<li>"
            f"<strong>{html.escape(deadline_text(item))}</strong> "
            f'<a href="../../university/{item["universityId"]}/">'
            f"{html.escape(university_names[item['universityId']])}</a>"
            f" · {html.escape(scope_name(item, program_names, group_names))}"
            f" · Applicants: {html.escape(', '.join(applicant_category_names.get(category, category) for category in item['applicantCategories']))}"
            f"{' · unofficial calendar-shift reference' if data_status == 'predicted' else ''}"
            f"{' · official recurring policy; cycle year mapped by GradWindow' if data_status == 'recurring' else ''}</li>"
            for item, data_status in sorted(
                items, key=lambda pair: (pair[0]["closesAt"], pair[0]["universityId"])
            )
        )
        canonical = f"{public_site_url}/deadline/{month}/"
        body = (
            '<p class="back"><a href="../../index.html">Back to tracker</a></p>'
            f"<ul>{rows}</ul>"
        )
        (month_dir / "index.html").write_text(
            render_static_page(
                f"{month} master's application deadlines",
                (
                    f"Review {len(items)} verified official and clearly labelled "
                    f"estimated master's application deadlines for {month}, with "
                    "university, programme, intake, and source details."
                ),
                body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (f"Deadlines in {month}", canonical),
                ],
            ),
            encoding="utf-8",
        )
        generated_urls.append((canonical, records_lastmod([item for item, _ in items])))

    by_opening_month: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    by_intake: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for data_status, records in (
        ("official", applications),
        ("recurring", recurring_windows),
        ("predicted", predictions),
    ):
        for item in records:
            by_opening_month[item["opensAt"][:7]].append((item, data_status))
            if slug := intake_slug(item):
                by_intake[slug].append((item, data_status))

    for month, items in sorted(by_opening_month.items()):
        if len(items) < MIN_SEARCH_LANDING_RECORDS:
            continue
        opening_dir = output_dir / "opening" / month
        opening_dir.mkdir(parents=True, exist_ok=True)
        canonical = f"{public_site_url}/opening/{month}/"
        label = month_label(month)
        body = render_landing_summary(
            items,
            university_names,
            mode="opening",
        )
        description = (
            f"Explore {len(items)} master's application windows opening in {label}, "
            "grouped by university with verified dates, official recurring policies, "
            "and clearly labelled estimates."
        )
        (opening_dir / "index.html").write_text(
            render_static_page(
                f"{label} Master's Applications Opening Dates",
                description,
                '<p class="back"><a href="../../index.html">Back to tracker</a></p>'
                + body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (f"Applications opening in {label}", canonical),
                ],
                date_modified=records_lastmod([item for item, _ in items]),
            ),
            encoding="utf-8",
        )
        generated_urls.append((canonical, records_lastmod([item for item, _ in items])))

    for slug, items in sorted(by_intake.items()):
        if len(items) < MIN_SEARCH_LANDING_RECORDS:
            continue
        intake_dir = output_dir / "intake" / slug
        intake_dir.mkdir(parents=True, exist_ok=True)
        canonical = f"{public_site_url}/intake/{slug}/"
        label = intake_page_label(slug)
        body = render_landing_summary(items, university_names, mode="intake")
        description = (
            f"Compare {len(items)} master's application deadlines for {label}, grouped "
            "by university with verified dates, official recurring policies, and clearly "
            "labelled estimates."
        )
        (intake_dir / "index.html").write_text(
            render_static_page(
                f"{label} Master's Application Deadlines",
                description,
                '<p class="back"><a href="../../index.html">Back to tracker</a></p>'
                + body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (f"{label} intake", canonical),
                ],
                date_modified=records_lastmod([item for item, _ in items]),
            ),
            encoding="utf-8",
        )
        generated_urls.append((canonical, records_lastmod([item for item, _ in items])))
    return generated_urls


def trim_description(value: str, limit: int = 180) -> str:
    if len(value) <= limit:
        return value
    shortened = value[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return f"{shortened}…"


def university_meta_description(
    school: str,
    official: list[dict],
    recurring: list[dict],
    estimated: list[dict],
    target_cycle_year: int,
) -> str:
    return trim_description(
        f"Track {len(official)} verified, {len(recurring)} recurring-policy, and "
        f"{len(estimated)} estimated master's application windows for {school}, "
        f"including {target_cycle_year} opening dates, deadlines, intakes, and official sources."
    )


def university_page_title(school: str, target_cycle_year: int) -> str:
    title = f"{school} Master's Application Deadlines {target_cycle_year}"
    if len(f"{title} · GradWindow") <= 100:
        return title
    return f"{school} Master's Deadlines {target_cycle_year}"


def render_university_product_actions(
    university_id: str,
    school: str,
    *,
    has_calendar: bool,
) -> str:
    escaped_id = html.escape(university_id, quote=True)
    escaped_school = html.escape(school)
    calendar_action = (
        '<a href="deadlines.ics" download>Add deadlines to calendar</a>'
        if has_calendar
        else (
            f'<a href="../../calendar.html?university={escaped_id}">'
            "View dates in calendar</a>"
        )
    )
    return (
        '<section class="product-actions" aria-label="GradWindow actions">'
        '<p class="product-actions-kicker">Continue in GradWindow</p>'
        f'<a class="primary-action" href="../../?university={escaped_id}#application-board">'
        f'View {escaped_school} in GradWindow <span aria-hidden="true">→</span></a>'
        '<div class="secondary-actions">'
        f"{calendar_action}"
        f'<a href="../../?university={escaped_id}&amp;action=save#application-board">Save university</a>'
        f'<a href="../../?university={escaped_id}#subscribe">Get opening alerts</a>'
        "</div></section>"
    )


def render_university_calendar(
    school: str,
    records: list[dict],
    program_names: dict[str, str],
    group_names: dict[str, str],
) -> str:
    events = []
    for item in sorted(records, key=lambda value: (value["closesAt"], value["id"])):
        closes_at = date.fromisoformat(item["closesAt"])
        end_at = closes_at + timedelta(days=1)
        recurring = bool(item.get("recurrence"))
        scope = scope_name(item, program_names, group_names)
        provenance = " (recurring policy)" if recurring else ""
        deadline_wording = (
            "submit before" if item.get("deadlineSemantics") == "before" else "deadline"
        )
        evidence_note = (
            "Official recurring day/month policy mapped to this cycle by GradWindow."
            if recurring
            else "Verified official application deadline."
        )
        verified_at = iso_date(item.get("verifiedAt")) or item["closesAt"]
        events.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_ics_escape(item['id'])}-deadline@gradwindow.com",
                f"DTSTAMP:{verified_at.replace('-', '')}T000000Z",
                f"DTSTART;VALUE=DATE:{closes_at.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end_at.strftime('%Y%m%d')}",
                f"SUMMARY:{_ics_escape(f'{school}: {scope} application {deadline_wording}{provenance}')}",
                "DESCRIPTION:"
                + _ics_escape(
                    f"{evidence_note}\nApplication: {item['applicationUrl']}\n"
                    f"Official source: {item['sourceUrl']}"
                ),
                f"URL:{_ics_escape(item['applicationUrl'])}",
                "END:VEVENT",
            ]
        )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GradWindow//University Application Deadlines//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_ics_escape(f'{school} application deadlines')}",
        *events,
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def _ics_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def render_university_summary(
    official: list[dict],
    recurring: list[dict],
    estimated: list[dict],
    monitor_item: dict,
    today: date,
    valid_intake_slugs: set[str],
) -> str:
    all_records = [*official, *recurring, *estimated]
    if not all_records:
        checked_at = iso_date(monitor_item.get("checkedAt"))
        checked_note = (
            f" The official admissions route was last checked on {human_date(checked_at)}."
            if checked_at
            else ""
        )
        return (
            '<section class="record-summary"><h2>Application-window coverage</h2>'
            "<p>GradWindow has no verified, recurring-policy, or estimated application "
            f"windows for this university yet.{checked_note}</p>"
            "<p>Use the official links above for current admissions information. This "
            "directory page remains available for discovery but is excluded from search indexing.</p>"
            "</section>"
        )

    official_status_rows = [*official, *recurring]
    open_now = sum(
        application_status(item, today) == "open" for item in official_status_rows
    )
    opening_soon = sum(
        application_status(item, today) == "upcoming" for item in official_status_rows
    )
    future_official = [
        item
        for item in official_status_rows
        if date.fromisoformat(item["closesAt"]) >= today
    ]
    next_deadline = min(
        future_official, key=lambda item: item["closesAt"], default=None
    )
    next_opening = min(
        (
            item
            for item in official_status_rows
            if date.fromisoformat(item["opensAt"]) > today
        ),
        key=lambda item: item["opensAt"],
        default=None,
    )
    opening_basis = "verified or recurring-policy"
    if next_opening is None:
        next_opening = min(
            (item for item in estimated if date.fromisoformat(item["opensAt"]) > today),
            key=lambda item: item["opensAt"],
            default=None,
        )
        opening_basis = "unofficial calendar-shift reference"
    checked_at = latest_date(
        monitor_item.get("checkedAt"),
        records_lastmod(all_records),
    )
    intake_slugs = sorted(
        {
            slug
            for item in all_records
            if (slug := intake_slug(item)) in valid_intake_slugs
        }
    )
    intake_links = "".join(
        f'<a href="../../intake/{slug}/">{html.escape(intake_page_label(slug))}</a>'
        for slug in intake_slugs
    )
    facts = [
        f"<li><strong>{len(all_records)}</strong> tracked windows: "
        f"{len(official)} verified, {len(recurring)} recurring-policy, "
        f"{len(estimated)} estimated.</li>",
        f"<li><strong>{open_now}</strong> official or recurring-policy windows open now; "
        f"<strong>{opening_soon}</strong> opening within {UPCOMING_WINDOW_DAYS} days.</li>",
    ]
    if next_deadline:
        facts.append(
            "<li>Next official or recurring-policy deadline: "
            f"<strong>{html.escape(deadline_text(next_deadline, human=True))}</strong>.</li>"
        )
    if next_opening:
        facts.append(
            f"<li>Next opening ({opening_basis}): "
            f"<strong>{human_date(next_opening['opensAt'])}</strong>.</li>"
        )
    if checked_at:
        facts.append(f"<li>Last checked or verified: {human_date(checked_at)}.</li>")
    intake_html = (
        f'<p class="intake-links"><strong>Browse intakes:</strong> {intake_links}</p>'
        if intake_links
        else ""
    )
    return (
        '<section class="record-summary"><h2>Application-window summary</h2>'
        f"<ul>{''.join(facts)}</ul>{intake_html}</section>"
    )


def render_landing_summary(
    items: list[tuple[dict, str]],
    university_names: dict[str, str],
    mode: str,
) -> str:
    grouped: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for item, data_status in items:
        grouped[item["universityId"]].append((item, data_status))
    cards = []
    for university_id, records in sorted(
        grouped.items(), key=lambda pair: university_names[pair[0]]
    ):
        rows = [item for item, _ in records]
        status_counts = Counter(data_status for _, data_status in records)
        opening_start = min(item["opensAt"] for item in rows)
        opening_end = max(item["opensAt"] for item in rows)
        deadline_start_item = min(rows, key=lambda item: item["closesAt"])
        deadline_end_item = max(rows, key=lambda item: item["closesAt"])
        deadline_start = deadline_start_item["closesAt"]
        deadline_end = deadline_end_item["closesAt"]
        openings = (
            human_date(opening_start)
            if opening_start == opening_end
            else f"{human_date(opening_start)} to {human_date(opening_end)}"
        )
        deadlines = (
            deadline_text(deadline_start_item, human=True)
            if deadline_start == deadline_end
            else (
                f"{deadline_text(deadline_start_item, human=True)} to "
                f"{deadline_text(deadline_end_item, human=True)}"
            )
        )
        intake_labels = sorted({item["intake"] for item in rows})
        visible_intakes = ", ".join(intake_labels[:4])
        if len(intake_labels) > 4:
            visible_intakes += f", and {len(intake_labels) - 4} more"
        source = next(
            (item["sourceUrl"] for item, status in records if status != "predicted"),
            rows[0]["sourceUrl"],
        )
        status_parts = []
        if status_counts["official"]:
            status_parts.append(f"{status_counts['official']} verified")
        if status_counts["recurring"]:
            status_parts.append(f"{status_counts['recurring']} recurring-policy")
        if status_counts["predicted"]:
            status_parts.append(
                f"{status_counts['predicted']} unofficial calendar-shift reference"
            )
        lead = "Opening date" if mode == "opening" else "Opening dates"
        cards.append(
            '<article class="landing-card">'
            f'<h2><a href="../../university/{university_id}/">'
            f"{html.escape(university_names[university_id])}</a></h2>"
            f"<p><strong>{len(records)} windows</strong> · "
            f"{html.escape(', '.join(status_parts))}</p>"
            f"<p>{lead}: {html.escape(openings)}<br>"
            f"Deadlines: {html.escape(deadlines)}</p>"
            f"<p>Intakes: {html.escape(visible_intakes)}</p>"
            f'<p><a href="{html.escape(source, quote=True)}">Official source</a></p>'
            "</article>"
        )
    trust_note = (
        "Verified dates come from official university pages. Recurring-policy dates "
        "map an official day/month rule to a cycle year; estimates are non-official "
        "calendar shifts and must be checked before applying."
    )
    return (
        f'<p class="trust-note">{trust_note}</p>'
        f'<div class="landing-grid">{"".join(cards)}</div>'
    )


def scope_name(
    item: dict,
    program_names: dict[str, str],
    group_names: dict[str, str],
) -> str:
    if item["scopeType"] == "programme":
        return program_names.get(item["scopeId"], item["scopeId"])
    if item["scopeType"] == "programme-group":
        return group_names.get(item["scopeId"], item["scopeId"])
    return "Institution-level window"


def render_window_list(
    items: list[dict],
    heading: str,
    program_names: dict[str, str],
    group_names: dict[str, str],
    applicant_category_names: dict[str, str],
    valid_intake_slugs: set[str],
    predicted: bool = False,
    recurring: bool = False,
) -> str:
    if not items:
        return ""
    rows = "".join(
        "<li>"
        f'<strong><a href="../../deadline/{html.escape(item["closesAt"][:7])}/">'
        f"{html.escape(item['opensAt'])} to "
        f"{html.escape(deadline_text(item))}</a></strong><br>"
        f"{html.escape(scope_name(item, program_names, group_names))} · "
        + (
            f'<a href="../../intake/{slug}/">{html.escape(item["intake"])}</a>'
            if (slug := intake_slug(item)) in valid_intake_slugs
            else html.escape(item["intake"])
        )
        + f" · Round: {html.escape(item['round'])}"
        + " · Applicants: "
        + html.escape(
            ", ".join(
                applicant_category_names.get(category, category)
                for category in item["applicantCategories"]
            )
        )
        + (
            "<br><small>Shifted by one calendar year; not an official published date.</small>"
            if predicted
            else (
                "<br><small>Official recurring day/month policy; the cycle year is mapped by GradWindow.</small>"
                if recurring
                else ""
            )
        )
        + f'<br><a href="{html.escape(item["applicationUrl"], quote=True)}">Application page</a>'
        + " · "
        + f'<a href="{html.escape(item["sourceUrl"], quote=True)}">Official source</a>'
        "</li>"
        for item in sorted(items, key=lambda value: value["closesAt"])
    )
    return f"<section><h2>{html.escape(heading)}</h2><ul>{rows}</ul></section>"


def render_static_page(
    title: str,
    description: str,
    body: str,
    canonical: str,
    breadcrumbs: list[tuple[str, str]],
    *,
    indexable: bool = True,
    date_modified: str | None = None,
) -> str:
    escaped_title = html.escape(title)
    escaped_description = html.escape(description, quote=True)
    escaped_canonical = html.escape(canonical, quote=True)
    public_site_url = canonical.split("/", 3)[:3]
    public_site_url = "/".join(public_site_url)
    social_image = f"{public_site_url}/og-image-multiranking.png"
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": url,
            }
            for position, (name, url) in enumerate(breadcrumbs, start=1)
        ],
    }
    web_page_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {
            "@type": "WebSite",
            "name": "GradWindow",
            "url": f"{public_site_url}/",
        },
    }
    if date_modified:
        web_page_schema["dateModified"] = date_modified
    structured_data = json.dumps(
        [web_page_schema, breadcrumb_schema],
        ensure_ascii=False,
    ).replace("</", "<\\/")
    breadcrumb_links = '<span aria-hidden="true">/</span>'.join(
        f'<a href="{html.escape(url, quote=True)}">{html.escape(name)}</a>'
        for name, url in breadcrumbs
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title} · GradWindow</title>
  <meta name="description" content="{escaped_description}">
  <meta name="robots" content="{"index, follow, max-image-preview:large" if indexable else "noindex, follow"}">
  <link rel="canonical" href="{escaped_canonical}">
  <link rel="icon" href="{public_site_url}/favicon.svg" type="image/svg+xml">
  <meta property="og:title" content="{escaped_title} · GradWindow">
  <meta property="og:description" content="{escaped_description}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="GradWindow">
  <meta property="og:url" content="{escaped_canonical}">
  <meta property="og:image" content="{social_image}">
  <meta property="og:image:width" content="1731">
  <meta property="og:image:height" content="909">
  <meta property="og:image:alt" content="GradWindow master's application deadline tracker">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escaped_title} · GradWindow">
  <meta name="twitter:description" content="{escaped_description}">
  <meta name="twitter:image" content="{social_image}">
  <script type="application/ld+json">{structured_data}</script>
  <style>
    body {{ margin: 0; background: #f7f5ef; color: #17231d; font: 16px/1.65 system-ui, sans-serif; }}
    .static-header {{ display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 16px max(16px, calc((100% - 820px) / 2)); border-bottom: 1px solid #d9ddd7; background: #fffef9; }}
    .brand {{ display: inline-flex; gap: 10px; align-items: center; color: #17231d; font-weight: 750; text-decoration: none; }}
    .brand-mark {{ display: grid; width: 32px; height: 32px; place-items: center; border-radius: 10px; background: #1e6548; color: white; }}
    .header-links {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 14px; }}
    main {{ width: min(820px, calc(100% - 32px)); margin: 32px auto 48px; }}
    h1 {{ line-height: 1.2; }}
    h2 {{ margin-top: 36px; }}
    li {{ margin: 12px 0; }}
    a {{ color: #1e6548; }}
    small {{ color: #68736d; }}
    .back {{ margin-bottom: 28px; }}
    .record-summary, .trust-note {{ padding: 18px 22px; border: 1px solid #d9ddd7; border-radius: 12px; background: #fffef9; }}
    .record-summary h2 {{ margin-top: 0; }}
    .product-actions {{ margin: 28px 0; padding: 22px; border-radius: 16px; background: #173f31; color: #f8fbf8; box-shadow: 0 14px 34px rgba(23, 63, 49, .16); }}
    .product-actions-kicker {{ margin: 0 0 10px; color: #bbd9cb; font-size: 13px; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }}
    .primary-action {{ display: inline-block; color: white; font-size: 20px; font-weight: 750; text-underline-offset: 4px; }}
    .secondary-actions {{ display: flex; gap: 10px 18px; flex-wrap: wrap; margin-top: 16px; }}
    .secondary-actions a {{ color: #dff2e8; }}
    .intake-links {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .landing-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 24px; }}
    .landing-card {{ padding: 18px 20px; border: 1px solid #d9ddd7; border-radius: 12px; background: #fffef9; }}
    .landing-card h2 {{ margin-top: 0; font-size: 19px; }}
    .landing-card p {{ margin: 8px 0; }}
    .breadcrumbs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; color: #68736d; font-size: 14px; }}
    .site-links {{ display: flex; gap: 18px; flex-wrap: wrap; padding-top: 28px; margin-top: 42px; border-top: 1px solid #d9ddd7; font-size: 14px; }}
    @media (max-width: 680px) {{ .static-header {{ align-items: flex-start; flex-direction: column; }} .landing-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body><header class="static-header">
  <a class="brand" href="{public_site_url}/"><span class="brand-mark" aria-hidden="true">G</span><span>GradWindow</span></a>
  <nav class="header-links" aria-label="Main navigation">
    <a href="{public_site_url}/#application-board">Tracker</a>
    <a href="{public_site_url}/calendar.html">Calendar</a>
    <a href="{public_site_url}/#subscribe">Alerts</a>
  </nav>
</header><main>
  <nav class="breadcrumbs" aria-label="Breadcrumb">{breadcrumb_links}</nav>
  <h1>{escaped_title}</h1>{body}
  <nav class="site-links" aria-label="GradWindow pages">
    <a href="{public_site_url}/">Application tracker</a>
    <a href="{public_site_url}/calendar.html">Application calendar</a>
    <a href="{public_site_url}/sources.html">Sources and coverage</a>
  </nav>
</main>{CLOUDFLARE_ANALYTICS}</body>
</html>
"""


def render_sitemap(urls: list[str | tuple[str, str | None]]) -> str:
    entries = ""
    for entry in urls:
        url, lastmod = entry if isinstance(entry, tuple) else (entry, None)
        lastmod_xml = f"<lastmod>{html.escape(lastmod)}</lastmod>" if lastmod else ""
        entries += f"  <url><loc>{html.escape(url)}</loc>{lastmod_xml}</url>\n"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )


def render_sources_page(public_site_url: str) -> str:
    universities = read_json(UNIVERSITIES_PATH)["universities"]
    applications = read_json(APPLICATIONS_PATH)["applications"]
    predictions = read_json(PREDICTIONS_PATH)["predictions"]
    recurring_windows = read_json(RECURRING_WINDOWS_PATH)["recurringWindows"]
    monitor = read_json(MONITOR_STATE_PATH, {"universities": {}})
    monitor_entries = monitor.get("universities", {})
    countries = sorted(
        {
            university["country"]
            for university in universities
            if university.get("qsPosition") is not None
        }
    )
    deadline_months = sorted(
        {
            item["closesAt"][:7]
            for item in [*applications, *predictions, *recurring_windows]
        }
    )
    all_window_records = [*applications, *predictions, *recurring_windows]
    opening_counts = Counter(item["opensAt"][:7] for item in all_window_records)
    opening_months = sorted(
        month
        for month, count in opening_counts.items()
        if count >= MIN_SEARCH_LANDING_RECORDS
    )
    intake_counts = Counter(
        slug for item in all_window_records if (slug := intake_slug(item)) is not None
    )
    intake_slugs = sorted(
        slug
        for slug, count in intake_counts.items()
        if count >= MIN_SEARCH_LANDING_RECORDS
    )
    country_links = "".join(
        f'<li><a href="country/{slugify(country)}/">'
        f"QS Top 200 universities in {html.escape(country)}</a></li>"
        for country in countries
    )
    deadline_links = "".join(
        f'<li><a href="deadline/{month}/">{month} master\'s application deadlines</a></li>'
        for month in deadline_months
    )
    opening_links = "".join(
        f'<li><a href="opening/{month}/">Master\'s applications opening in '
        f"{html.escape(month_label(month))}</a></li>"
        for month in opening_months
    )
    intake_links = "".join(
        f'<li><a href="intake/{slug}/">{html.escape(intake_page_label(slug))} '
        "master's application deadlines</a></li>"
        for slug in intake_slugs
    )
    rows = []
    for university in sorted(
        universities,
        key=lambda item: (
            item.get("qsPosition") is None,
            item.get("qsPosition") or 10_000,
            item["school"],
        ),
    ):
        monitor_item = monitor_entries.get(university["id"], {})
        admissions_url = university.get("admissionsUrl")
        admissions = (
            f'<a href="{html.escape(admissions_url, quote=True)}">Application entry</a>'
            if admissions_url
            else "Not located"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(university.get('rankDisplay') or '—')}</td>"
            f'<td><a href="university/{university["id"]}/">'
            f"{html.escape(university['school'])}</a>"
            f'<br><a class="official-link" href="{html.escape(university["homepageUrl"], quote=True)}">'
            "Official university website</a></td>"
            f"<td>{html.escape(university['country'])}</td>"
            f"<td>{html.escape(university['admissionsDiscovery'])}</td>"
            f"<td>{admissions}</td>"
            f"<td>{html.escape(monitor_item.get('status', 'not-checked'))}</td>"
            "</tr>"
        )
    title = "Sources and coverage · GradWindow"
    description = (
        "Review GradWindow's official university sources, graduate application "
        "entry discovery status, and latest monitoring results across supported rankings."
    )
    canonical = f"{public_site_url}/sources.html"
    structured_data = json.dumps(
        [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Sources and coverage",
                "description": description,
                "url": canonical,
                "isPartOf": {
                    "@type": "WebSite",
                    "name": "GradWindow",
                    "url": f"{public_site_url}/",
                },
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "GradWindow",
                        "item": f"{public_site_url}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Sources and coverage",
                        "item": canonical,
                    },
                ],
            },
        ],
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="{public_site_url}/favicon.svg" type="image/svg+xml">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="GradWindow">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{public_site_url}/og-image-multiranking.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{public_site_url}/og-image-multiranking.png">
  <script type="application/ld+json">{structured_data}</script>
  <style>
    body {{ margin: 0; background: #f7f5ef; color: #17231d; font: 14px/1.6 system-ui, sans-serif; }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 48px auto; }}
    a {{ color: #1e6548; }}
    .breadcrumbs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; color: #68736d; font-size: 14px; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 36px; }}
    p {{ color: #68736d; }}
    .browse-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }}
    .browse-list {{ columns: 2; padding-left: 20px; }}
    .browse-list li {{ break-inside: avoid; margin: 6px 0; }}
    .official-link {{ color: #68736d; font-size: 12px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9ddd7; border-radius: 10px; background: #fffef9; }}
    table {{ width: 100%; min-width: 900px; border-collapse: collapse; }}
    th, td {{ padding: 11px 14px; border-bottom: 1px solid #e7e9e5; text-align: left; }}
    th {{ background: #f1f4ef; font-size: 11px; text-transform: uppercase; color: #68736d; }}
    @media (max-width: 760px) {{ .browse-grid {{ grid-template-columns: 1fr; }} .browse-list {{ columns: 1; }} }}
  </style>
</head>
<body>
  <main>
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <a href="index.html">GradWindow</a><span aria-hidden="true">/</span><span>Sources and coverage</span>
    </nav>
    <h1>Sources and coverage</h1>
    <p>Public list of {len(universities)} monitored universities, official websites, admissions-entry discovery status, and latest monitoring result.</p>
    <section class="browse-grid" aria-label="Browse application deadline pages">
      <div>
        <h2>Browse by country or region</h2>
        <ul class="browse-list">{country_links}</ul>
      </div>
      <div>
        <h2>Browse by deadline month</h2>
        <ul class="browse-list">{deadline_links}</ul>
      </div>
      <div>
        <h2>Browse by opening month</h2>
        <ul class="browse-list">{opening_links}</ul>
      </div>
      <div>
        <h2>Browse by intake</h2>
        <ul class="browse-list">{intake_links}</ul>
      </div>
    </section>
    <h2>University directory and official sources</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>QS</th><th>University</th><th>Country/region</th><th>Entry status</th><th>Application page</th><th>Monitoring</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
  </main>
  {CLOUDFLARE_ANALYTICS}
</body>
</html>
"""
