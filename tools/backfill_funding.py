"""Backfill Hyperliquid fundingHistory to launch (~Jun 2023) via /info API.

500 rows per call, paginated forward from a start time. Writes one JSON per
coin to data_extended/funding/{coin}_funding_full.json.

The frozen data_snapshot/ is never touched — extended data is a new, separately
versioned dataset.

Usage: .venv/Scripts/python.exe tools/backfill_funding.py [BTC SOL ...]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_extended" / "funding"
API = "https://api.hyperliquid.xyz/info"
LAUNCH_MS = 1685577600000  # 2023-06-01 — verified: fundingHistory serves from here


def info(payload: dict, retries: int = 4) -> list:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def backfill(coin: str) -> list[dict]:
    rows, start = [], LAUNCH_MS
    while True:
        page = info({"type": "fundingHistory", "coin": coin, "startTime": start})
        if not page:
            break
        new = [r for r in page if r["time"] >= start]
        rows.extend(new)
        last = page[-1]["time"]
        if len(page) < 500:
            break
        start = last + 1
        time.sleep(0.4)  # be polite to the public endpoint
    # dedupe + sort (defensive)
    seen = {}
    for r in rows:
        seen[r["time"]] = r
    return [seen[k] for k in sorted(seen)]


def main() -> int:
    coins = [c.upper() for c in sys.argv[1:]] or ["BTC", "SOL"]
    OUT.mkdir(parents=True, exist_ok=True)
    for coin in coins:
        rows = backfill(coin)
        p = OUT / f"{coin.lower()}_funding_full.json"
        p.write_text(json.dumps(rows))
        if rows:
            t0 = datetime.fromtimestamp(rows[0]["time"] / 1000, timezone.utc)
            t1 = datetime.fromtimestamp(rows[-1]["time"] / 1000, timezone.utc)
            span = (rows[-1]["time"] - rows[0]["time"]) / 86400000
            print(f"{coin}: n={len(rows)}  {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}  "
                  f"({span:.0f}d)  -> {p.name}")
        else:
            print(f"{coin}: EMPTY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
