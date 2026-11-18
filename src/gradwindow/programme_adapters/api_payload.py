"""Decode public APIs retrieved directly or as browser-rendered JSON documents."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup


def decode_api_json(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        soup = BeautifulSoup(content, "html.parser")
        # Chromium wraps JSON responses in a single pre element. Do not extract
        # embedded script data or JSON fragments from ordinary/error pages.
        blocks = soup.find_all("pre")
        if len(blocks) != 1 or soup.find(["script", "form", "iframe"]):
            raise ValueError(
                "API response was neither JSON nor a JSON document"
            ) from None
        body = soup.body or soup
        if body.get_text(strip=True) != blocks[0].get_text(strip=True):
            raise ValueError(
                "API response contained content outside its JSON document"
            ) from None
        return json.loads(blocks[0].get_text())
