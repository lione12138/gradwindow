from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deadline_semantics_preserve_before_wording_in_both_languages() -> None:
    node = shutil.which("node")
    assert node is not None, "Node.js is required for frontend semantic date tests"
    module_uri = (ROOT / "web" / "deadline-semantics.js").resolve().as_uri()
    script = f"""
      import {{ deadlineDaysRemaining, formatDeadlineDate, formatDeadlineRange }} from {json.dumps(module_uri)};
      const record = {{ deadlineSemantics: "before" }};
      console.log(JSON.stringify({{
        en: formatDeadlineDate(record, "1 Jul 2027", "en"),
        zh: formatDeadlineDate(record, "2027年7月1日", "zh"),
        range: formatDeadlineRange(record, "1 Oct 2026", "1 Jul 2027", "en"),
        daysRemaining: deadlineDaysRemaining(record, 10)
      }}));
    """

    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "en": "Before 1 Jul 2027",
        "zh": "2027年7月1日前",
        "range": "1 Oct 2026 – Before 1 Jul 2027",
        "daysRemaining": 9,
    }
