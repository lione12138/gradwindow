from __future__ import annotations

import html
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

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
    "status.js",
    "intake-filter.js",
    "ranking-filter.js",
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
    "og-image.png",
    "favicon.svg",
    "cat-avatar.svg",
)
LEGACY_SITE_URL = "https://lione12138.github.io/qs-master-applications"
DEFAULT_SITE_URL = "https://gradwindow.com"
UPCOMING_WINDOW_DAYS = 30
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
        render_home_snapshot(index_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    data_dir = output_dir / "data"
    data_dir.mkdir()
    for source in PUBLIC_DATA:
        shutil.copy2(source, data_dir / source.name)

    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    (output_dir / "sources.html").write_text(
        render_sources_page(public_site_url), encoding="utf-8"
    )
    generated_urls = generate_index_pages(output_dir, public_site_url)
    sitemap_urls = [
        public_site_url,
        f"{public_site_url}/calendar.html",
        f"{public_site_url}/contact.html",
        f"{public_site_url}/roadmap.html",
        f"{public_site_url}/privacy.html",
        f"{public_site_url}/sources.html",
        *generated_urls,
    ]
    (output_dir / "sitemap.xml").write_text(
        render_sitemap(sitemap_urls), encoding="utf-8"
    )
    (output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {public_site_url}/sitemap.xml\n",
        encoding="utf-8",
    )
    return output_dir / "index.html"


def application_status(item: dict, today: date) -> str:
    opens_at = date.fromisoformat(item["opensAt"])
    closes_at = date.fromisoformat(item["closesAt"])
    if today > closes_at:
        return "closed"
    if today >= opens_at:
        return "open"
    if (opens_at - today).days <= UPCOMING_WINDOW_DAYS:
        return "upcoming"
    return "future"


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

    qs_universities = [
        item for item in universities if item.get("qsPosition") is not None
    ]
    qs_ids = {item["id"] for item in qs_universities}
    rows = [*applications, *recurring_windows, *predictions]
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
    university_names = {item["id"]: item["school"] for item in universities}
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

    checked_at = monitor.get("meta", {}).get("checkedAt")
    updated_at = checked_at or application_payload["meta"]["updatedAt"]
    updated_date = date.fromisoformat(updated_at[:10])
    updated_label = "Official pages checked" if checked_at else "Official data updated"
    updated_month = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[
        updated_date.month - 1
    ]

    return {
        "updated_at": (
            f"{updated_label} {updated_date.day} {updated_month} {updated_date.year}"
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
    }


def render_home_snapshot(source: str, today: date | None = None) -> str:
    snapshot = home_snapshot(today)
    rendered = source
    for key, value in snapshot.items():
        rendered = rendered.replace(
            f"{{{{GRADWINDOW_{key.upper()}}}}}",
            html.escape(value, quote=True),
        )
    unresolved = sorted(set(re.findall(r"\{\{GRADWINDOW_[A-Z_]+\}\}", rendered)))
    if unresolved:
        raise ValueError(f"Unresolved home snapshot tokens: {', '.join(unresolved)}")
    return rendered


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "other"


def generate_index_pages(output_dir: Path, public_site_url: str) -> list[str]:
    universities = read_json(UNIVERSITIES_PATH)["universities"]
    applications = read_json(APPLICATIONS_PATH)["applications"]
    predictions = read_json(PREDICTIONS_PATH)["predictions"]
    recurring_windows = read_json(RECURRING_WINDOWS_PATH)["recurringWindows"]
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
    generated_urls: list[str] = []

    for university in universities:
        university_dir = output_dir / "university" / university["id"]
        university_dir.mkdir(parents=True, exist_ok=True)
        official = [
            item for item in applications if item["universityId"] == university["id"]
        ]
        estimated = [
            item for item in predictions if item["universityId"] == university["id"]
        ]
        recurring = [
            item
            for item in recurring_windows
            if item["universityId"] == university["id"]
        ]
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
            + render_window_list(
                official,
                "Verified official windows",
                program_names,
                group_names,
            )
            + render_window_list(
                recurring,
                "Official recurring policies (cycle year mapped by GradWindow)",
                program_names,
                group_names,
                recurring=True,
            )
            + render_window_list(
                estimated,
                "Next-cycle calendar-shift references",
                program_names,
                group_names,
                predicted=True,
            )
        )
        (university_dir / "index.html").write_text(
            render_static_page(
                f"{university['school']} master's application dates",
                (
                    "Browse verified master's application dates, deadlines, "
                    "official links, and clearly labelled next-cycle estimates "
                    f"for {university['school']}."
                ),
                body,
                canonical,
                [
                    ("GradWindow", f"{public_site_url}/"),
                    (university["school"], canonical),
                ],
            ),
            encoding="utf-8",
        )
        generated_urls.append(canonical)

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
        generated_urls.append(canonical)

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
            f"<strong>{html.escape(item['closesAt'])}</strong> "
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
        generated_urls.append(canonical)
    return generated_urls


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
    predicted: bool = False,
    recurring: bool = False,
) -> str:
    if not items:
        return (
            f"<section><h2>{html.escape(heading)}</h2><p>No records yet.</p></section>"
        )
    rows = "".join(
        "<li>"
        f'<strong><a href="../../deadline/{html.escape(item["closesAt"][:7])}/">'
        f"{html.escape(item['opensAt'])} to "
        f"{html.escape(item['closesAt'])}</a></strong><br>"
        f"{html.escape(scope_name(item, program_names, group_names))} · "
        f"{html.escape(item['intake'])}"
        + (
            "<br><small>Shifted by one calendar year; not an official published date.</small>"
            if predicted
            else (
                "<br><small>Official recurring day/month policy; the cycle year is mapped by GradWindow.</small>"
                if recurring
                else ""
            )
        )
        + f'<br><a href="{html.escape(item["sourceUrl"], quote=True)}">Official source</a>'
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
) -> str:
    escaped_title = html.escape(title)
    escaped_description = html.escape(description, quote=True)
    escaped_canonical = html.escape(canonical, quote=True)
    public_site_url = canonical.split("/", 3)[:3]
    public_site_url = "/".join(public_site_url)
    social_image = f"{public_site_url}/og-image.png"
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
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{escaped_canonical}">
  <link rel="icon" href="{public_site_url}/favicon.svg" type="image/svg+xml">
  <meta property="og:title" content="{escaped_title} · GradWindow">
  <meta property="og:description" content="{escaped_description}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="GradWindow">
  <meta property="og:url" content="{escaped_canonical}">
  <meta property="og:image" content="{social_image}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="GradWindow master's application deadline tracker">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escaped_title} · GradWindow">
  <meta name="twitter:description" content="{escaped_description}">
  <meta name="twitter:image" content="{social_image}">
  <script type="application/ld+json">{structured_data}</script>
  <style>
    body {{ margin: 0; background: #f7f5ef; color: #17231d; font: 16px/1.65 system-ui, sans-serif; }}
    main {{ width: min(820px, calc(100% - 32px)); margin: 48px auto; }}
    h1 {{ line-height: 1.2; }}
    h2 {{ margin-top: 36px; }}
    li {{ margin: 12px 0; }}
    a {{ color: #1e6548; }}
    small {{ color: #68736d; }}
    .back {{ margin-bottom: 28px; }}
    .breadcrumbs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; color: #68736d; font-size: 14px; }}
    .site-links {{ display: flex; gap: 18px; flex-wrap: wrap; padding-top: 28px; margin-top: 42px; border-top: 1px solid #d9ddd7; font-size: 14px; }}
  </style>
</head>
<body><main>
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


def render_sitemap(urls: list[str]) -> str:
    entries = "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in urls)
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
    country_links = "".join(
        f'<li><a href="country/{slugify(country)}/">'
        f"QS Top 200 universities in {html.escape(country)}</a></li>"
        for country in countries
    )
    deadline_links = "".join(
        f'<li><a href="deadline/{month}/">{month} master\'s application deadlines</a></li>'
        for month in deadline_months
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
  <meta property="og:image" content="{public_site_url}/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{public_site_url}/og-image.png">
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
