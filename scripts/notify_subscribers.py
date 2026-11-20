from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "data"
MAX_EVENTS_PER_DIGEST = 1000
# A daily run can pick up yesterday's openings after a missed run. The
# notification service already deduplicates deliveries across overlapping runs.
OPENING_LOOKBACK_DAYS = 1
sys.path.insert(0, str(ROOT / "src"))

from gradwindow.io import read_json as read_project_json  # noqa: E402
from gradwindow.paths import (  # noqa: E402
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    PROGRAMME_ADAPTER_HEALTH_PATH,
    PROGRAMME_CATALOG_STATE_PATH,
)
from gradwindow.published_data_audit import audit_published_data  # noqa: E402


def read_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def recently_opened_events(
    today: date | None = None,
    *,
    record_trust_statuses: dict[str, str] | None = None,
) -> list[dict]:
    today = today or date.today()
    earliest_opening = today - timedelta(days=OPENING_LOOKBACK_DAYS)
    if record_trust_statuses is None:
        record_trust_statuses = _current_record_trust_statuses(today)
    universities = {
        item["id"]: item for item in read_json("universities.json")["universities"]
    }
    programs = {
        item["id"]: item["name"] for item in read_json("programs.json")["programs"]
    }
    groups = {
        item["id"]: item["name"]
        for item in read_json("programme-groups.json")["groups"]
    }
    events = []
    for record in read_json("applications.json")["applications"]:
        if record_trust_statuses.get(record["id"], "current") != "current":
            continue
        opens = date.fromisoformat(record["opensAt"])
        closes = date.fromisoformat(record["closesAt"])
        if not earliest_opening <= opens <= today <= closes:
            continue
        if record.get("deadlineSemantics") == "before" and today == closes:
            continue
        university = universities[record["universityId"]]
        if record["scopeType"] == "programme":
            programme = programs.get(record["scopeId"], record["scopeId"])
        elif record["scopeType"] == "programme-group":
            programme = groups.get(record["scopeId"], record["scopeId"])
        else:
            programme = "Institution-level application window"
        events.append(
            {
                "id": record["id"],
                "school": university["school"],
                "schoolZh": university.get("schoolZh", ""),
                "program": programme,
                "opensAt": record["opensAt"],
                "closesAt": record["closesAt"],
                "applicationUrl": record["applicationUrl"],
                "sourceUrl": record["sourceUrl"],
            }
        )
    return events


def _current_record_trust_statuses(today: date) -> dict[str, str]:
    audit = audit_published_data(
        read_project_json(APPLICATIONS_PATH).get("applications", []),
        catalog_state=read_project_json(
            PROGRAMME_CATALOG_STATE_PATH,
            {"universities": {}},
        ).get("universities", {}),
        adapter_health=read_project_json(
            PROGRAMME_ADAPTER_HEALTH_PATH,
            {"universities": {}},
        ).get("universities", {}),
        source_state=read_project_json(
            APPLICATION_SOURCE_STATE_PATH,
            {"applications": {}},
        ).get("applications", {}),
        today=today,
    )
    return audit["recordTrustStatuses"]


def notify(events: list[dict]) -> bool:
    if not events:
        print("No newly opened official application windows.")
        return True
    endpoint = os.environ.get("GRADWINDOW_SUBSCRIBE_URL", "").strip().rstrip("/")
    raw_api_key = os.environ.get("GRADWINDOW_NOTIFY_API_KEY", "").strip()
    api_key = (
        raw_api_key[7:].strip()
        if raw_api_key.lower().startswith("bearer ")
        else raw_api_key
    )
    if not endpoint or not api_key:
        print("Subscriber notification service is not configured; skipping.")
        return False
    if len(events) > MAX_EVENTS_PER_DIGEST:
        print(
            f"Refusing to split {len(events)} events into multiple emails; "
            f"the digest limit is {MAX_EVENTS_PER_DIGEST}.",
            file=sys.stderr,
        )
        return False
    request = Request(
        f"{endpoint}/admin/notify",
        data=json.dumps({"events": events}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GradWindow-GitHub-Actions/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        print(
            "Notification request failed: "
            f"HTTP {exc.code} {exc.reason}; body={response_body[:1000]}",
            file=sys.stderr,
        )
        return False
    except (URLError, TimeoutError) as exc:
        print(
            f"Notification request failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return False
    if not result.get("ok"):
        print("Notification service rejected the request.", file=sys.stderr)
        return False
    total_sent = result.get("sent", 0)
    total_failed = result.get("failed", 0)
    print(
        f"Processed {len(events)} newly opened official windows; "
        f"sent {total_sent} digest emails; "
        f"{total_failed} deliveries failed."
    )
    return total_failed == 0


def main() -> None:
    events = recently_opened_events()
    if "--dry-run" in sys.argv:
        print(json.dumps({"events": events}, ensure_ascii=False, indent=2))
        return
    if not notify(events):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
