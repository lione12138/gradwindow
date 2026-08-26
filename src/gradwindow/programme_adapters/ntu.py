from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from http.cookiejar import CookieJar
from urllib.parse import quote, urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

from bs4 import BeautifulSoup

from ..browser_rendering import browser_content_fetcher_from_environment
from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    OfficialSourceTransportError,
    ParserZeroResultError,
)

UNIVERSITY_ID = "nanyang-technological-university-singapore-ntu-singapore"
CATALOG_ENDPOINT = (
    "https://www.ntu.edu.sg/admissions/graduate/programme-listing/GetProgrammes/"
)
APPLICATION_URL = (
    "https://www.ntu.edu.sg/admissions/graduate/cwadmissionguide/apply-now"
)
WINDOW_URL = "https://apps.ntu.edu.sg/COAL/ListProgrammeIframe"
WINDOW_ROOT = "https://apps.ntu.edu.sg"
WINDOW_API_PATH = (
    "/COAL/screenservices/COAL/MainFlow/ProgramList/DataActionGetAdmControlList"
)
PROGRAM_LIST_SCRIPT_PATH = "/COAL/scripts/COAL.MainFlow.ProgramList.mvc.js"
OUTSYSTEMS_SCRIPT_PATH = "/COAL/scripts/OutSystems.js"
SITE_ROOT = "https://www.ntu.edu.sg"
APPLICATION_PROGRAMME_ALIASES = {
    "master of public administration chinese": "executive mpa march intake",
    "msc managerial economics chinese": (
        "managerial economics executive mme march intake"
    ),
}
PROGRAMME_ID_ALIASES = {
    "ntu-integrated-circuits-microelectronics-msc": (
        "ntu-integrated-circuits-and-microelectronics-msc"
    ),
    "ntu-signal-processing-machine-learning-msc": (
        "ntu-signal-processing-and-machine-learning-msc"
    ),
}


def catalog_page_url(page: int) -> str:
    return (
        f"{CATALOG_ENDPOINT}?{urlencode({'programmelevels': 'master', 'page': page})}"
    )


CATALOG_URL = catalog_page_url(1)


def _fetch_application_windows_api() -> str:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    headers = {
        "Accept": "application/json, text/plain, */*",
        "OutSystems-client-env": "browser",
        "User-Agent": (
            "Mozilla/5.0 (compatible; GradWindow/1.0; "
            "+https://gradwindow.com/methodology/)"
        ),
    }

    shell = _open_text(opener, Request(WINDOW_URL, headers=headers))
    index_version = _required_match(
        shell,
        r'OSManifestLoader\.indexVersionToken\s*=\s*"([^"]+)"',
        "index version token",
    )
    manifest_url = (
        urljoin(WINDOW_URL, "moduleservices/moduleinfo?")
        + "?"
        + quote(index_version, safe="")
    )
    manifest = _json_object(
        _open_text(opener, Request(manifest_url, headers=headers)),
        "module manifest",
    )
    manifest_data = manifest.get("manifest")
    if not isinstance(manifest_data, dict):
        raise ValueError("NTU OutSystems manifest is missing manifest metadata")
    module_version = str(manifest_data.get("versionToken") or "").strip()
    url_versions = manifest_data.get("urlVersions")
    if not module_version or not isinstance(url_versions, dict):
        raise ValueError("NTU OutSystems manifest is missing version metadata")

    program_version = str(url_versions.get(PROGRAM_LIST_SCRIPT_PATH) or "")
    runtime_version = str(url_versions.get(OUTSYSTEMS_SCRIPT_PATH) or "")
    if not program_version or not runtime_version:
        raise ValueError("NTU OutSystems manifest is missing required scripts")
    controller = _open_text(
        opener,
        Request(
            urljoin(WINDOW_ROOT, PROGRAM_LIST_SCRIPT_PATH) + program_version,
            headers=headers,
        ),
    )
    runtime = _open_text(
        opener,
        Request(
            urljoin(WINDOW_ROOT, OUTSYSTEMS_SCRIPT_PATH) + runtime_version,
            headers=headers,
        ),
    )
    api_version = _required_match(
        controller,
        (
            r'DataActionGetAdmControlList"\s*,\s*"'
            r"screenservices/COAL/MainFlow/ProgramList/"
            r'DataActionGetAdmControlList"\s*,\s*"([^"]+)"'
        ),
        "application service API version",
    )
    csrf_token = _required_match(
        runtime,
        r'AnonymousCSRFToken\s*=\s*"([^"]+)"',
        "anonymous CSRF token",
    )
    body = json.dumps(
        {
            "versionInfo": {
                "moduleVersion": module_version,
                "apiVersion": api_version,
            },
            "viewName": "MainFlow.ListProgrammeIframe",
            "screenData": {"variables": {}},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        urljoin(WINDOW_ROOT, WINDOW_API_PATH),
        data=body,
        method="POST",
        headers={
            **headers,
            "Content-Type": "application/json; charset=UTF-8",
            "X-CSRFToken": csrf_token,
        },
    )
    return _open_text(opener, request)


def _open_text(opener, request: Request) -> str:
    with opener.open(request, timeout=45) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def _required_match(value: str, pattern: str, label: str) -> str:
    match = re.search(pattern, value)
    if not match:
        raise ValueError(f"NTU OutSystems source is missing {label}")
    return match.group(1)


def _json_object(value: str, label: str) -> dict:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"NTU {label} did not return JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"NTU {label} returned an invalid payload")
    return payload


class NTUAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_url = WINDOW_URL
    intake = "Academic Year 2026-27"
    application_opens_at_basis = "official"
    replace_pending_candidates = True

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        *,
        window_api_fetcher: Callable[[], str] | None = _fetch_application_windows_api,
        browser_content_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.window_api_fetcher = window_api_fetcher
        self.browser_content_fetcher = (
            browser_content_fetcher or browser_content_fetcher_from_environment()
        )

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        first = _catalog_payload(fetcher(catalog_page_url(1)))
        total_pages = _positive_int(first.get("totalPages"), "totalPages")
        total_items = _positive_int(first.get("totalItems"), "totalItems")
        items = list(first.get("items") or [])
        for page in range(2, total_pages + 1):
            payload = _catalog_payload(fetcher(catalog_page_url(page)))
            items.extend(payload.get("items") or [])

        programmes = {
            programme.id: programme
            for item in items
            if (programme := _programme_from_item(item)) is not None
        }
        if (
            len(items) != total_items
            or len(programmes) < self.minimum_expected_programmes
        ):
            raise ValueError(
                "NTU coursework catalogue only contained "
                f"{len(programmes)} unique master's programmes from {len(items)} "
                f"items; expected at least {self.minimum_expected_programmes} and "
                f"an API total of {total_items}"
            )

        windows_by_key, evidence_by_key, window_retrieval_method = (
            self._load_application_windows(fetcher)
        )
        unmatched = set(windows_by_key).difference(
            _catalog_key(programme.name) for programme in programmes.values()
        )
        warnings = []
        if unmatched:
            count = len(unmatched)
            warnings.append(
                {
                    "reason": "PROGRAMME_ID_MISMATCH",
                    "message": (
                        "NTU's official application table contains "
                        f"{count} {'row' if count == 1 else 'rows'} that could not "
                        "be matched to the official coursework catalogue."
                    ),
                    "sourceUrl": self.application_url,
                    "programmeKeys": sorted(unmatched),
                }
            )

        discovered = []
        for programme in programmes.values():
            key = _catalog_key(programme.name)
            windows = windows_by_key.get(key, [])
            if windows:
                programme.windows = windows
                programme.parse_status = "parsed"
                programme.deadline_text = evidence_by_key[key]
                programme.retrieval_method = window_retrieval_method
            discovered.append(programme)
        discovered.sort(key=lambda item: item.id)
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=discovered,
            warnings=warnings,
        )

    def _load_application_windows(
        self,
        fetcher: Callable[[str], str],
    ) -> tuple[dict[str, list[DiscoveredWindow]], dict[str, str], str]:
        documents: list[str] = []
        errors: list[str] = []
        if self.window_api_fetcher is not None:
            try:
                api_payload = self.window_api_fetcher()
            except Exception as exc:
                errors.append(f"application service {type(exc).__name__}: {exc}")
            else:
                try:
                    windows, evidence = _application_windows_from_api(api_payload)
                except ValueError as exc:
                    errors.append(f"application service parser: {exc}")
                else:
                    if windows:
                        return windows, evidence, "official-outsystems-api"

        try:
            direct = fetcher(self.window_url)
        except Exception as exc:
            direct = ""
            errors.append(f"direct {type(exc).__name__}: {exc}")
        else:
            documents.append(direct)
            try:
                windows, evidence = _application_windows(direct)
            except ValueError as exc:
                errors.append(f"direct parser: {exc}")
            else:
                if windows:
                    return windows, evidence, "official-live-application-table"

        if self.browser_content_fetcher is not None:
            try:
                rendered = self.browser_content_fetcher(self.window_url)
            except Exception as exc:
                errors.append(f"browser {type(exc).__name__}: {exc}")
            else:
                documents.append(rendered)
                try:
                    windows, evidence = _application_windows(rendered)
                except ValueError as exc:
                    errors.append(f"browser parser: {exc}")
                else:
                    if windows:
                        return windows, evidence, "cloudflare-browser-rendering"

        if any(_explicit_no_open_programmes(document) for document in documents):
            return {}, {}, "official-live-application-table"
        if any(_has_application_date_signals(document) for document in documents):
            raise ParserZeroResultError(
                "NTU official application page contains application date signals "
                "but the parser produced zero windows."
            )
        if errors and not documents:
            raise OfficialSourceTransportError(
                "NTU official application-window source was unavailable: "
                + "; ".join(errors)
            )
        raise ParserZeroResultError(
            "NTU official application page produced zero windows without an "
            "explicit no-programmes-open notice."
        )


def _catalog_payload(value: str) -> dict:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("NTU catalogue endpoint did not return JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("NTU catalogue endpoint returned an invalid payload")
    return payload


def _positive_int(value, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NTU catalogue payload has invalid {label}") from exc
    if parsed < 1:
        raise ValueError(f"NTU catalogue payload has invalid {label}")
    return parsed


def _programme_from_item(item) -> DiscoveredProgramme | None:
    if not isinstance(item, dict):
        return None
    title = _normalise(str(item.get("title") or ""))
    path = str(item.get("url") or "").strip()
    if not title or not path:
        return None
    degree_type, core_title = _degree_and_core_title(title)
    programme_id = _programme_id(core_title, degree_type)
    if _catalog_key(core_title) == "applied ai":
        programme_id = "ntu-applied-artificial-intelligence-mcomp"
    faculty = _normalise(str(item.get("tag") or ""))
    department = faculty.split(" | ", 1)[0]
    return DiscoveredProgramme(
        id=programme_id,
        name=title,
        degree_type=degree_type,
        faculty=faculty,
        department=department,
        source_url=urljoin(SITE_ROOT, path),
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "Programme found in NTU's official coursework master's catalogue, "
            "but it is not listed in the current live application-window table."
        ),
        parse_status="no-deadline",
        retrieval_method="official-api",
        evidence_quality="official-full-text",
    )


def _application_windows(
    html: str,
) -> tuple[dict[str, list[DiscoveredWindow]], dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    windows: dict[str, list[DiscoveredWindow]] = {}
    evidence = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr")[1:]:
            cells = [
                _normalise(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"])
            ]
            if len(cells) < 5:
                continue
            period, admission_date, programme_name, opens, closes = cells[:5]
            key = _application_catalog_key(programme_name)
            window = DiscoveredWindow(
                round=_round_name(period),
                intake=_intake(admission_date),
                opens_at=_date(opens),
                closes_at=_date(closes),
                applicant_categories=["all"],
                source_url=APPLICATION_URL,
            )
            windows.setdefault(key, []).append(window)
            evidence[key] = (
                "NTU's official live application table lists "
                f"{programme_name} for {window.intake}: applications open "
                f"{window.opens_at} and close {window.closes_at}."
            )
    if not windows:
        _application_card_windows(soup, windows, evidence)
    return windows, evidence


def _application_windows_from_api(
    value: str,
) -> tuple[dict[str, list[DiscoveredWindow]], dict[str, str]]:
    payload = _json_object(value, "application service")
    data = payload.get("data")
    outer_list = data.get("List") if isinstance(data, dict) else None
    groups = outer_list.get("List") if isinstance(outer_list, dict) else None
    if not isinstance(groups, list):
        raise ValueError("NTU application service returned an invalid list payload")

    windows: dict[str, list[DiscoveredWindow]] = {}
    evidence: dict[str, str] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        admission_date = str(group.get("AdmissionDate") or "").strip()
        rows_wrapper = group.get("AdmControlList")
        rows = rows_wrapper.get("List") if isinstance(rows_wrapper, dict) else None
        if not admission_date or not isinstance(rows, list):
            continue
        period = _api_round_name(group)
        for row in rows:
            if not isinstance(row, dict):
                continue
            programme_name = _normalise(str(row.get("ProgramName") or ""))
            opens_at = str(row.get("OpenDate") or "").strip()
            closes_at = str(row.get("CloseDate") or "").strip()
            if not programme_name or not opens_at or not closes_at:
                continue
            key = _application_catalog_key(programme_name)
            window = DiscoveredWindow(
                round=period,
                intake=_intake(admission_date),
                opens_at=_date(opens_at),
                closes_at=_date(closes_at),
                applicant_categories=["all"],
                source_url=APPLICATION_URL,
            )
            windows.setdefault(key, []).append(window)
            evidence[key] = (
                "NTU's official live application service lists "
                f"{programme_name} for {window.intake}: applications open "
                f"{window.opens_at} and close {window.closes_at}."
            )
    return windows, evidence


def _api_round_name(group: dict) -> str:
    semester = str(group.get("Sem") or "").strip()
    term_type = str(group.get("Term") or "").strip().upper()
    if term_type == "T" and semester:
        return f"Trimester {semester}"
    if term_type == "S" and semester:
        return f"Semester {semester}"
    return f"Intake {semester}" if semester else "Main intake"


def _application_card_windows(
    soup: BeautifulSoup,
    windows: dict[str, list[DiscoveredWindow]],
    evidence: dict[str, str],
) -> None:
    for group in soup.select(".table-grid"):
        headings = [
            _normalise(item.get_text(" ", strip=True))
            for item in group.select(".mainContainer")
        ]
        if len(headings) < 2:
            continue
        period = headings[0]
        admission_match = re.search(
            r"Admission Date\s*:\s*(.+)$",
            headings[1],
            re.I,
        )
        if not admission_match:
            continue
        admission_date = admission_match.group(1)
        cells = [
            _normalise(item.get_text(" ", strip=True))
            for item in group.select(".innerList")
        ]
        for programme_name, application_period in zip(
            cells[0::2], cells[1::2], strict=False
        ):
            dates = re.fullmatch(
                r"(.+?)\s+-\s+(.+)",
                application_period,
            )
            if not dates:
                continue
            key = _application_catalog_key(programme_name)
            window = DiscoveredWindow(
                round=_round_name(period),
                intake=_intake(admission_date),
                opens_at=_date(dates.group(1)),
                closes_at=_date(dates.group(2)),
                applicant_categories=["all"],
                source_url=APPLICATION_URL,
            )
            windows.setdefault(key, []).append(window)
            evidence[key] = (
                "NTU's official live application list shows "
                f"{programme_name} for {window.intake}: applications open "
                f"{window.opens_at} and close {window.closes_at}."
            )


def _has_application_date_signals(html: str) -> bool:
    text = _normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    lowered = text.lower()
    has_period_labels = (
        "opening date" in lowered and "closing date" in lowered
    ) or "application period" in lowered
    return (
        "the following programme(s) are open for application" in lowered
        and has_period_labels
    )


def _explicit_no_open_programmes(html: str) -> bool:
    text = _normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "no programmes are currently open for application",
            "no programme is currently open for application",
            "there are currently no programmes open for application",
            "no programs for entered year, sem and term type",
        )
    )


def _round_name(period: str) -> str:
    parts = [part.strip() for part in period.split("/", 1)]
    return parts[-1] if parts[-1] else "Main intake"


def _intake(value: str) -> str:
    return _parse_date(value).strftime("%B %Y")


def _date(value: str) -> str:
    return _parse_date(value).date().isoformat()


def _parse_date(value: str) -> datetime:
    clean = re.sub(r"-Sept-", "-Sep-", value.strip(), flags=re.I)
    for pattern in ("%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, pattern)
        except ValueError:
            continue
    raise ValueError(f"Invalid date in NTU live application list: {value}")


def _degree_and_core_title(title: str) -> tuple[str, str]:
    rules = (
        (r"^.*?Master of Science(?:\s+in)?\s*", "MSc"),
        (r"^Master of Arts(?:\s+in)?\s*", "MA"),
        (r"^Master of Computing(?:\s+in)?\s*", "MComp"),
        (r"^Master of Education\s*", "MEd"),
        (r"^Master of Public Administration\s*", "MPA"),
        (r"^Master of Social Sciences(?:\s+in)?\s*", "MSocSci"),
        (r"^Master of Media and Communication\s*", "MMC"),
        (r"^Master of Teaching\s*", "MTeach"),
        (r"^Master in Management\s*", "MiM"),
    )
    for pattern, degree_type in rules:
        if re.search(pattern, title, re.I):
            return degree_type, re.sub(pattern, "", title, count=1, flags=re.I)
    if re.search(r"\bMBA\b", title, re.I):
        return "MBA", re.sub(r"\bMBA\b", "", title, flags=re.I)
    return "Master", title


def _programme_id(core_title: str, degree_type: str) -> str:
    programme_id = f"ntu-{_slug(core_title)}-{_slug(degree_type)}"
    return PROGRAMME_ID_ALIASES.get(programme_id, programme_id)


def _catalog_key(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    clean = ascii_value.decode()
    clean = re.sub(r"^\s*\d+\s*-\s*", "", clean)
    clean = re.sub(
        r"\((?:MCAAI|MSDS|MSAI|MSBBB|MSCMED|MMC|IS|MSIS|KM|HOPE)\)",
        " ",
        clean,
        flags=re.I,
    )
    clean = clean.lower().replace("&", " and ")
    clean = re.sub(
        r"\b(?:executive\s+)?master(?: of)? "
        r"(?:science|arts|public administration|social sciences)\b",
        " ",
        clean,
    )
    clean = re.sub(r"\bmsc\b", " ", clean)
    clean = re.sub(r"\bmgt\b", "management", clean)
    clean = re.sub(r"\bprogramme\b", " ", clean)
    clean = re.sub(r"\b(?:in|the)\b", " ", clean)
    return " ".join(re.findall(r"[a-z0-9]+", clean))


def _application_catalog_key(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    clean = ascii_value.decode()
    clean = re.sub(r"^\s*\d+\s*-\s*", "", clean).lower()
    exact_label = " ".join(re.findall(r"[a-z0-9]+", clean))
    return APPLICATION_PROGRAMME_ALIASES.get(exact_label, _catalog_key(value))


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.decode().lower()).strip("-")


def _normalise(value: str) -> str:
    return re.sub(
        r"\s+", " ", value.replace("\u200b", "").replace("\ufeff", "")
    ).strip()
