"""Apply the nine official IOE former-name pairs reviewed on 2026-10-11."""

from datetime import datetime, timezone
from pathlib import Path

from gradwindow.io import read_json, write_json
from gradwindow.programme_adapters.ucl import REVIEWED_IOE_IDENTITIES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.ucl.ac.uk/ioe/courses/graduate-taught"


def apply_reviewed_renames(identities, sources):
    programs_path = ROOT / "data/programs.json"
    candidates_path = ROOT / "data/ops/programme-candidates.json"
    programs = read_json(programs_path)
    candidates = read_json(candidates_path)
    known = {p["id"]: p for p in programs["programs"]}
    changes = []
    for name, existing_id in identities.items():
        matches = [
            c
            for c in candidates["items"]
            if c.get("universityId") == "ucl-university-college-london"
            and c.get("programme", {}).get("name") == name
            and c.get("status") == "pending"
        ]
        if not matches:
            continue
        assert len(matches) == 1, name
        candidate = matches[0]
        current = candidate["programme"]
        assert not candidate["windows"] and existing_id in known
        assert current["id"] not in known, "Already public: explicit merge required"
        previous = known[existing_id]
        assert previous["degreeType"] == current["degreeType"]
        changes.append((candidate, previous, current))
    for candidate, previous, current in changes:
        for field in ("name", "sourceUrl", "applicationUrl"):
            if field in current:
                previous[field] = current[field]
        candidate.update(
            status="rejected",
            reviewedBy="Codex official-source review",
            reviewedAt=datetime.now(timezone.utc).isoformat(),
            reviewNotes=f"Official rename of {previous['id']}; retain existing identity. Identity evidence: {sources[current['name']]}",
        )
    if changes:
        write_json(programs_path, programs)
        write_json(candidates_path, candidates)
    print(f"Updated {len(changes)} existing programmes; added 0 programmes/windows.")


if __name__ == "__main__":
    apply_reviewed_renames(
        REVIEWED_IOE_IDENTITIES, dict.fromkeys(REVIEWED_IOE_IDENTITIES, SOURCE)
    )
