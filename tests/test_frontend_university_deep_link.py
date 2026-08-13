from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

MODULE_URI = (
    (Path(__file__).parents[1] / "web" / "university-deep-link.js").resolve().as_uri()
)


def run_node(script: str) -> dict:
    node = shutil.which("node")
    assert node is not None, "Node.js is required for frontend deep-link tests"
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_university_deep_link_validates_school_and_save_action() -> None:
    script = """
      import {
        searchWithoutDeepLinkAction,
        universityDeepLink,
      } from __MODULE__;
      const known = new Set(["national-university-of-singapore-nus"]);
      console.log(JSON.stringify({
        save: universityDeepLink(
          "?university=national-university-of-singapore-nus&action=save",
          known,
        ),
        unknown: universityDeepLink("?university=unknown&action=save", known),
        unsupportedAction: universityDeepLink(
          "?university=national-university-of-singapore-nus&action=delete",
          known,
        ),
        consumed: searchWithoutDeepLinkAction(
          "?university=national-university-of-singapore-nus&action=save",
        ),
      }));
    """.replace("__MODULE__", json.dumps(MODULE_URI))
    assert run_node(script) == {
        "save": {
            "universityId": "national-university-of-singapore-nus",
            "action": "save",
        },
        "unknown": {"universityId": "", "action": ""},
        "unsupportedAction": {
            "universityId": "national-university-of-singapore-nus",
            "action": "",
        },
        "consumed": "?university=national-university-of-singapore-nus",
    }
