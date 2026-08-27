from __future__ import annotations

import re

from gradwindow import __version__
from gradwindow.paths import ROOT


def test_package_version_matches_project_metadata() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_section = pyproject.split("[project]", 1)[1].split("[", 1)[0]
    match = re.search(r'^version = "([^"]+)"$', project_section, re.MULTILINE)

    assert match
    assert __version__ == match.group(1)


def test_public_sources_use_current_repository_url() -> None:
    paths = (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "DATA_LICENSE.md",
        ROOT / "SECURITY.md",
        ROOT / "src" / "gradwindow" / "readme.py",
        ROOT / "web" / "index.html",
        ROOT / "web" / "calendar.html",
        ROOT / "web" / "contact.html",
        ROOT / "web" / "roadmap.html",
    )

    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "github.com/lione12138/qs-master-applications" not in content
        assert "github.com/lione12138/gradwindow" in content
