"""Short-lived public-page checkpoints; never a source of published deadlines."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path


class BrowserCache:
    def __init__(self, directory: str, ttl: float = 21600) -> None:
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.path = Path(directory) / "pages.sqlite3"
        self.ttl = max(0, ttl)
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS pages (key TEXT PRIMARY KEY, expires REAL, body TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS cooldown (account TEXT PRIMARY KEY, until REAL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS metrics (run TEXT, name TEXT, value REAL, PRIMARY KEY(run,name))"
            )
            db.execute("DELETE FROM pages WHERE expires <= ?", (time.time(),))

    @contextmanager
    def connect(self):
        # Site-build environments can omit _sqlite3; only fetching needs it.
        import sqlite3

        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def key(account: str, endpoint: str, body: dict) -> str:
        return hashlib.sha256(
            json.dumps([account, endpoint, body], sort_keys=True).encode()
        ).hexdigest()

    def get(self, key: str) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT body FROM pages WHERE key=? AND expires>?", (key, time.time())
            ).fetchone()
        return row[0] if row else None

    def put(self, key: str, body: str) -> None:
        now = time.time()
        # A resumed page must never masquerade as a fresh verification on a new UTC day.
        expires = min(now + self.ttl, (int(now // 86400) + 1) * 86400)
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO pages VALUES (?,?,?)", (key, expires, body)
            )

    def defer(self, account: str, until: float) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO cooldown VALUES (?,?) ON CONFLICT(account) DO UPDATE SET until=max(until,excluded.until)",
                (account, until),
            )

    def blocked_until(self, account: str) -> float:
        with self.connect() as db:
            row = db.execute(
                "SELECT until FROM cooldown WHERE account=?", (account,)
            ).fetchone()
        return row[0] if row else 0

    def count(self, name: str, value: float = 1) -> None:
        run = (
            os.environ.get("GITHUB_RUN_ID", "local")
            + ":"
            + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        )
        with self.connect() as db:
            db.execute(
                "INSERT INTO metrics VALUES (?,?,?) ON CONFLICT(run,name) DO UPDATE SET value=value+excluded.value",
                (run, name, value),
            )

    def summary(self) -> dict:
        run = (
            os.environ.get("GITHUB_RUN_ID", "local")
            + ":"
            + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        )
        with self.connect() as db:
            return dict(
                db.execute("SELECT name,value FROM metrics WHERE run=?", (run,))
            )


if __name__ == "__main__":
    directory = os.environ.get("CLOUDFLARE_BROWSER_CACHE_DIR")
    print(
        json.dumps(
            BrowserCache(directory).summary() if directory else {}, sort_keys=True
        )
    )
