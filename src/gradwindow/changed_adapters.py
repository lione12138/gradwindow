from __future__ import annotations

from pathlib import Path

from .programme_adapters.registry import PROGRAMME_ADAPTERS

ADAPTER_ROOT = Path("src/gradwindow/programme_adapters")


def adapter_keys_for_paths(paths: list[str]) -> list[str]:
    changed_modules = {
        Path(path).stem
        for path in paths
        if Path(path).parent.as_posix() == ADAPTER_ROOT.as_posix()
        and Path(path).suffix == ".py"
    }
    return sorted(
        key
        for key, factory in PROGRAMME_ADAPTERS.items()
        if factory.__module__.rsplit(".", 1)[-1] in changed_modules
    )
