"""Backfill/refresh Hyperliquid candles via /info candleSnapshot.

API constraint (probed 2026-09-23): ~5000-bar lookback cap — requests for bars
older than ~5000 bars ago return empty. Effective depths:
  1d  -> full history (launch Jun 2023)
  4h  -> ~830d
  1h  -> ~208d
  15m -> ~52d

Paginates backward from now in 5000-bar windows until empty/launch.
Writes data_extended/candles/{asset}_{interval}_full.json (never touches
the frozen data_snapshot/).

Usage: .venv/Scripts/python.exe tools/backfill_candles.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_extended" / "candles"
API = "https://api.hyperliquid.xyz/info"
LAUNCH_MS = 1685577600000
BAR_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
MAX_BARS = 5000


def info(payload: dict, retries: int = 4) -> list:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def backfill(coin: str, interval: str) -> list[dict]:
    bar = BAR_MS[interval]
    end = int(time.time() * 1000)
    rows: list[dict] = []
    while end > LAUNCH_MS:
        start = max(LAUNCH_MS, end - MAX_BARS * bar)
        page = info({"type": "candleSnapshot", "req": {
                    "coin": coin, "interval": interval,
                    "startTime": start, "endTime": end}})
        if not page:
            break                      # hit the lookback cap
        rows.extend(page)
        earliest = min(r["t"] for r in page)
        if earliest <= start + bar or len(page) < 10:
            end = earliest - bar
            if earliest <= LAUNCH_MS:
                break
        else:
            end = earliest
        time.sleep(0.4)
    seen = {}
    for r in rows:
        seen[r["t"]] = r
    now_ms = int(time.time() * 1000)
    out = []
    for k in sorted(seen):
        if k + bar > now_ms:
            continue            # still-open bar — partial OHLC would freeze
        r = seen[k]
        out.append({"t": r["t"], "o": float(r["o"]), "h": float(r["h"]),
                    "l": float(r["l"]), "c": float(r["c"]), "v": float(r["v"])})
    return out


def _write_safe(path, rows: list[dict]) -> None:
    """Same fail-closed contract as backfill_binance._write_safe: refuse
    empty/shrunk/tail-regressing payloads, write via tmp+replace."""
    try:
        old = json.loads(path.read_text())
    except Exception:
        old = []
    if not rows:
        print(f"{path.name}: REFUSE write — empty payload "
              f"(keeping {len(old)} rows)")
        return
    if old:
        if len(rows) < len(old) * 0.9 or rows[-1]["t"] < old[-1]["t"]:
            print(f"{path.name}: REFUSE write — n {len(old)}->{len(rows)}, "
                  f"tail {old[-1]['t']}->{rows[-1]['t']} (keeping existing)")
            return
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rows))
    tmp.replace(path)


def main() -> int:
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    coins = [c.upper() for c in sys.argv[1:]] or ["BTC", "SOL"]
    for coin in coins:
        for interval in ("1d", "4h", "1h", "15m"):
            try:
                rows = backfill(coin, interval)
            except Exception as e:
                print(f"{coin} {interval}: FAIL {e} (existing untouched)")
                continue
            p = OUT / f"{coin.lower()}_{interval}_full.json"
            _write_safe(p, rows)
            if rows:
                span = (rows[-1]["t"] - rows[0]["t"]) / 86400000
                print(f"{coin} {interval}: n={len(rows)} span={span:.0f}d -> {p.name}")
            else:
                print(f"{coin} {interval}: EMPTY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
