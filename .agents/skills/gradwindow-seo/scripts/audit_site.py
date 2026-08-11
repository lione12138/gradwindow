#!/usr/bin/env python3
"""Audit a built GradWindow site for deterministic SEO invariants."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self.robots = ""
        self.canonical = ""
        self.h1_count = 0
        self.links: list[str] = []
        self.og: set[str] = set()
        self.twitter: set[str] = set()
        self.json_ld: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._json_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""
        elif tag == "meta":
            name = values.get("name") or ""
            prop = values.get("property") or ""
            if name == "description":
                self.description = values.get("content") or ""
            elif name == "robots":
                self.robots = values.get("content") or ""
            elif name.startswith("twitter:"):
                self.twitter.add(name)
            if prop.startswith("og:"):
                self.og.add(prop)
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._json_parts).strip())

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_parts.append(data)


def normalized_url(value: str) -> str:
    parts = urlsplit(value)
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") + "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def read_sitemap(site_dir: Path) -> set[str]:
    root = ET.parse(site_dir / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        normalized_url(node.text or "")
        for node in root.findall("s:url/s:loc", namespace)
        if node.text
    }


def audit(site_dir: Path, base_url: str | None) -> list[str]:
    errors: list[str] = []
    sitemap = read_sitemap(site_dir)
    if not sitemap:
        return ["sitemap.xml contains no URLs"]
    resolved_base = normalized_url(base_url or min(sitemap, key=len)).rstrip("/")
    pages: dict[str, PageParser] = {}

    for path in sorted(site_dir.rglob("*.html")):
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        relative = path.relative_to(site_dir)
        label = relative.as_posix()
        if "noindex" in parser.robots.lower():
            if parser.canonical and normalized_url(parser.canonical) in sitemap:
                errors.append(f"{label}: noindex page appears in sitemap")
            continue
        if not parser.canonical:
            errors.append(f"{label}: missing canonical")
            continue
        canonical = normalized_url(parser.canonical)
        if not canonical.startswith(f"{resolved_base}/") and canonical != resolved_base:
            errors.append(f"{label}: canonical is outside {resolved_base}")
        if canonical in pages:
            errors.append(f"{label}: duplicate canonical {canonical}")
        pages[canonical] = parser
        if canonical not in sitemap:
            errors.append(f"{label}: canonical missing from sitemap")
        if not (10 <= len(parser.title.strip()) <= 100):
            errors.append(f"{label}: title length is {len(parser.title.strip())}")
        if not (120 <= len(parser.description.strip()) <= 180):
            errors.append(
                f"{label}: description length is {len(parser.description.strip())}"
            )
        if parser.h1_count != 1:
            errors.append(f"{label}: expected one H1, found {parser.h1_count}")
        missing_og = {
            "og:title",
            "og:description",
            "og:type",
            "og:url",
            "og:image",
        } - parser.og
        if missing_og:
            errors.append(f"{label}: missing Open Graph fields {sorted(missing_og)}")
        missing_twitter = {
            "twitter:card",
            "twitter:title",
            "twitter:description",
            "twitter:image",
        } - parser.twitter
        if missing_twitter:
            errors.append(f"{label}: missing Twitter fields {sorted(missing_twitter)}")
        if not parser.json_ld:
            errors.append(f"{label}: missing JSON-LD")
        for payload in parser.json_ld:
            try:
                json.loads(payload)
            except json.JSONDecodeError as exc:
                errors.append(f"{label}: invalid JSON-LD ({exc})")

    for url in sorted(sitemap - pages.keys()):
        errors.append(f"sitemap URL has no indexable HTML page: {url}")

    inbound = dict.fromkeys(pages, 0)
    for canonical, parser in pages.items():
        for href in parser.links:
            target = normalized_url(urljoin(canonical, href))
            if target in inbound and target != canonical:
                inbound[target] += 1
    home = f"{resolved_base}/"
    for canonical, count in sorted(inbound.items()):
        if canonical not in {resolved_base, home} and count == 0:
            errors.append(f"orphan indexable page: {canonical}")

    robots = (site_dir / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap:" not in robots:
        errors.append("robots.txt does not declare the sitemap")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_dir", type=Path)
    parser.add_argument("--base-url")
    args = parser.parse_args()
    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        parser.error(f"site directory does not exist: {site_dir}")
    errors = audit(site_dir, args.base_url)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"SEO audit failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"SEO audit passed for {site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
