"""Cross-venue data pull: Binance USD-M futures public REST (no key).

Feeds new hypothesis families: funding dislocation vs HL, cross-venue
lead/lag, OI divergence, taker-flow toxicity.

Writes data_extended/binance/{name}.json — never touches data_snapshot/.

Endpoints:
  /fapi/v1/fundingRate            full history (8h cadence, since 2019)
  /fapi/v1/klines                 1h klines (paginated, 1500/call)
  /futures/data/openInterestHist  ~30d lookback only
  /futures/data/takerlongshortRatio  buy/sell taker volume ratio, ~30d

Usage: .venv/Scripts/python.exe tools/backfill_binance.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_extended" / "binance"
BASE = "https://fapi.binance.com"
SYMBOLS = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT",
           "AVAXUSDT", "LINKUSDT"]
KLINES_DAYS = 730      # 2y of 1h bars ~= 12 paginated calls/symbol
START_2019 = 1546300800000


def get(path: str, retries: int = 4) -> list:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + path,
                                         headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


INTERVAL_MS = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def _closed(kline: list, interval_ms: int) -> bool:
    """Binance returns the still-open bar as the last kline — k[6] is its
    scheduled close time. An open bar would freeze as if real (the
    2026-09-25 audit found a 39-min partial bar baked into the file)."""
    return int(kline[6]) < int(time.time() * 1000) - 60_000


def _trim_open_tail(existing: list[dict], interval_ms: int) -> list[dict]:
    """Drop the last ~2 stored bars before a pull so they get refetched
    fully closed — heals partials already baked in by past runs."""
    if not existing:
        return existing
    tail = max(int(r["t"]) for r in existing)
    return [r for r in existing
            if int(r["t"]) < tail - interval_ms]


def funding(sym: str) -> list[dict]:
    rows, start = [], START_2019
    while True:
        page = get(f"/fapi/v1/fundingRate?symbol={sym}&startTime={start}&limit=1000")
        if not page:
            break
        rows.extend(page)
        if len(page) < 1000:
            break
        start = page[-1]["fundingTime"] + 1
        time.sleep(0.3)
    return rows


def klines_1h(sym: str) -> list[dict]:
    # merge onto existing: the 730d pull window must not discard older
    # accrued history on overwrite
    existing = _trim_open_tail(
        _load_existing(OUT / f"{sym.lower()}_klines_1h.json"),
        INTERVAL_MS["1h"])
    start = int(time.time() * 1000) - KLINES_DAYS * 86400000
    end = int(time.time() * 1000)
    rows = []
    while start < end:
        page = get(f"/fapi/v1/klines?symbol={sym}&interval=1h"
                   f"&startTime={start}&endTime={end}&limit=1500")
        if not page:
            break
        rows.extend(page)
        start = page[-1][0] + 1
        if len(page) < 1500:
            break
        time.sleep(0.3)
    new = [{"t": k[0], "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
            "c": float(k[4]), "v": float(k[5]),
            "taker_buy_vol": float(k[9]), "n_trades": int(k[8])}
           for k in rows if _closed(k, INTERVAL_MS["1h"])]
    return _merge(existing, new)


def _merge(existing: list[dict], new: list[dict], key: str = "t") -> list[dict]:
    seen = {r[key]: r for r in existing}
    for r in new:
        seen[r[key]] = r
    return [seen[k] for k in sorted(seen)]


def _load_existing(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _write_safe(path: Path, rows: list[dict], key: str = "t") -> None:
    """Never let a bad pull truncate a healthy file: refuse the write when
    the payload is empty, shrinks >10%, or ends earlier than the existing
    tail. Kills the 'interrupted fetch overwrote accrued history' class."""
    existing = _load_existing(path)
    if not rows:
        print(f"{path.name}: REFUSE write — empty payload "
              f"(keeping {len(existing)} existing rows)")
        return
    if existing:
        old_max = max(int(r[key]) for r in existing)
        new_max = max(int(r[key]) for r in rows)
        if len(rows) < len(existing) * 0.9 or new_max < old_max:
            print(f"{path.name}: REFUSE write — n {len(existing)}->{len(rows)}, "
                  f"tail {old_max}->{new_max} (keeping existing)")
            return
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rows))
    tmp.replace(path)
    print(f"{path.name}: n={len(rows)}")


def klines_deep(sym: str, interval: str) -> list[dict]:
    """Incremental perp klines back to contract listing (BTC Sep-2019).
    Appends onto the existing file's last bar."""
    path = OUT / f"{sym.lower()}_klines_{interval}.json"
    existing = _trim_open_tail(_load_existing(path), INTERVAL_MS[interval])
    # max(t), not the list tail: a mis-ordered or partially-corrupted file
    # would otherwise restart the pull mid-history and truncate.
    start = (max(int(r["t"]) for r in existing) + 1) if existing else START_2019
    end = int(time.time() * 1000)
    rows = list(existing)
    while start < end:
        page = get(f"/fapi/v1/klines?symbol={sym}&interval={interval}"
                   f"&startTime={start}&endTime={end}&limit=1500")
        if not page:
            break
        rows = _merge(rows, [{"t": k[0], "o": float(k[1]), "h": float(k[2]),
                              "l": float(k[3]), "c": float(k[4]),
                              "v": float(k[5]),
                              "taker_buy_vol": float(k[9]),
                              "n_trades": int(k[8])}
                             for k in page
                             if _closed(k, INTERVAL_MS[interval])])
        start = page[-1][0] + 1
        if len(page) < 1500:
            break
        time.sleep(0.3)
    return rows


def premium_index(sym: str) -> list[dict]:
    """Mark-index premium klines (daily) — basis history back to listing."""
    path = OUT / f"{sym.lower()}_premium_1d.json"
    existing = _trim_open_tail(_load_existing(path), INTERVAL_MS["1d"])
    start = (max(int(r["t"]) for r in existing) + 1) if existing else START_2019
    end = int(time.time() * 1000)
    rows = list(existing)
    while start < end:
        page = get(f"/fapi/v1/premiumIndexKlines?symbol={sym}&interval=1d"
                   f"&startTime={start}&endTime={end}&limit=1500")
        if not page:
            break
        rows = _merge(rows, [{"t": k[0], "o": float(k[1]), "h": float(k[2]),
                              "l": float(k[3]), "c": float(k[4])}
                             for k in page
                             if _closed(k, INTERVAL_MS["1d"])])
        start = page[-1][0] + 1
        if len(page) < 1500:
            break
        time.sleep(0.3)
    return rows


def recent_window(sym: str, dataset: str, period: str = "1h") -> list:
    rows, start = [], int(time.time() * 1000) - 30 * 86400000
    period_ms = INTERVAL_MS[period]
    while True:
        page = get(f"/futures/data/{dataset}?symbol={sym}&period={period}"
                   f"&startTime={start}&limit=500")
        if not page:
            break
        # last row can be the still-open period bucket — same open-bar
        # rule as klines (timestamp + period not yet elapsed)
        now = int(time.time() * 1000) - 60_000
        page = [r for r in page
                if int(r["timestamp"]) + period_ms <= now]
        rows.extend(page)
        if len(page) < 500:
            break
        start = int(page[-1]["timestamp"]) + 1
        time.sleep(0.3)
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for sym in SYMBOLS:
        for name, fn, key in [
            ("funding", lambda: funding(sym), "fundingTime"),
            ("klines_1h", lambda: klines_1h(sym), "t"),
            ("klines_4h", lambda: klines_deep(sym, "4h"), "t"),
            ("klines_1d", lambda: klines_deep(sym, "1d"), "t"),
            ("premium_1d", lambda: premium_index(sym), "t"),
            # 30d-limited feeds: MERGE onto accrued history, never
            # overwrite — a bare write would discard everything older
            # than the window on every refresh.
            ("oi_hist_1h",
             lambda: _merge(
                 _load_existing(OUT / f"{sym.lower()}_oi_hist_1h.json"),
                 recent_window(sym, "openInterestHist"),
                 key="timestamp"), "timestamp"),
            ("taker_ls_1h",
             lambda: _merge(
                 _load_existing(OUT / f"{sym.lower()}_taker_ls_1h.json"),
                 recent_window(sym, "takerlongshortRatio"),
                 key="timestamp"), "timestamp"),
        ]:
            path = OUT / f"{sym.lower()}_{name}.json"
            try:
                rows = fn()
            except Exception as e:
                print(f"{sym} {name}: FAIL {e} (existing file untouched)")
                continue
            _write_safe(path, rows, key=key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
