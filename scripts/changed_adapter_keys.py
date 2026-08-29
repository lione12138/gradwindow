from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from gradwindow.changed_adapters import adapter_keys_for_paths


def changed_paths(base: str, head: str) -> list[str]:
    if not base or set(base) == {"0"}:
        base = f"{head}^"
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    adapters = adapter_keys_for_paths(changed_paths(args.base, args.head))
    matrix = json.dumps(adapters, separators=(",", ":"))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"adapters={matrix}\n")
            handle.write(f"count={len(adapters)}\n")
    print(matrix)


if __name__ == "__main__":
    main()
