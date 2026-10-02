"""Live accrual collector — one-shot snapshot for scheduled execution.

Accrues the domains the round-17 coverage audit flagged as missing:
HL-native OI + venue-native premium (metaAndAssetCtxs), orderbook depth
(l2Book top levels), and Deribit DVOL/perp-funding spot checks.

Append-only JSONL under data_live/ — each feed is an independent append
so one failing source cannot starve the others. Runs are idempotent:
re-running within the same minute replaces nothing, just appends a row.

Usage: .venv/Scripts/python.exe tools/collect_live.py
Schedule: hourly via schtasks (see manifest round17b_data_acquisition).
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_live"
HL_INFO = "https://api.hyperliquid.xyz/info"
DERIBIT = "https://www.deribit.com/api/v2"
ASSETS = ["BTC", "SOL", "ETH", "XRP", "DOGE", "AVAX", "LINK"]


def _post(payload: dict, retries: int = 3) -> object:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                HL_INFO, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def _get(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _last_t(path: Path) -> int:
    """Last recorded timestamp in an append-only journal (0 if absent)."""
    try:
        last = ""
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        return int(json.loads(last).get("t", 0)) if last else 0
    except Exception:
        return 0


def _f(v: object) -> float | None:
    try:
        x = float(v)  # type: ignore[arg-type]
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def collect_hl_ctx(now_ms: int) -> int:
    """metaAndAssetCtxs: venue-native OI/mark/oracle/premium/funding."""
    resp = _post({"type": "metaAndAssetCtxs"})
    if not isinstance(resp, list) or len(resp) != 2:
        return 0
    universe = [u["name"] for u in resp[0]["universe"]]
    wrote = 0
    for asset in ASSETS:
        if asset not in universe:
            continue
        ctx = resp[1][universe.index(asset)]
        _append(OUT / f"hl_ctx_{asset.lower()}.jsonl", {
            "t": now_ms, "asset": asset, "src": "hl_meta_ctx",
            "oi": _f(ctx.get("openInterest")),
            "mark_px": _f(ctx.get("markPx")),
            "oracle_px": _f(ctx.get("oraclePx")),
            "mid_px": _f(ctx.get("midPx")),
            "premium": _f(ctx.get("premium")),
            "funding_pred": _f(ctx.get("funding")),
            "day_ntl_vlm": _f(ctx.get("dayNtlVlm")),
            "prev_day_px": _f(ctx.get("prevDayPx")),
        })
        wrote += 1
    return wrote


def collect_hl_book(now_ms: int) -> int:
    """l2Book: raw 20-level depth + computed depth-bands/spread."""
    wrote = 0
    for asset in ASSETS:
        try:
            resp = _post({"type": "l2Book", "coin": asset})
        except Exception:
            continue
        levels = (resp or {}).get("levels")  # type: ignore[union-attr]
        if not levels or len(levels) != 2 or not levels[0]:
            continue
        bids = [[_f(l["px"]), _f(l["sz"])] for l in levels[0]]
        asks = [[_f(l["px"]), _f(l["sz"])] for l in levels[1]]
        mid = (bids[0][0] + asks[0][0]) / 2 if bids[0][0] and asks[0][0] else None
        row: dict = {"t": now_ms, "asset": asset, "src": "hl_l2book",
                     "mid": mid, "bids": bids, "asks": asks}
        if mid:
            for bps, tag in ((10, "d10"), (25, "d25"), (50, "d50")):
                lim_dn, lim_up = mid * (1 - bps / 1e4), mid * (1 + bps / 1e4)
                row[f"bid_{tag}"] = round(sum(s for p, s in bids
                                            if p and s and p >= lim_dn), 6)
                row[f"ask_{tag}"] = round(sum(s for p, s in asks
                                            if p and s and p <= lim_up), 6)
            row["spread_bps"] = round((asks[0][0] - bids[0][0]) / mid * 1e4, 4)
        _append(OUT / f"hl_book_{asset.lower()}.jsonl", row)
        wrote += 1
        time.sleep(0.2)
    return wrote


def collect_deribit(now_ms: int) -> int:
    """DVOL latest print + perp funding spot check (BTC/ETH)."""
    wrote = 0
    for cur in ("BTC", "ETH"):
        path = OUT / f"deribit_dvol_live_{cur.lower()}.jsonl"
        try:
            resp = _get(f"{DERIBIT}/public/get_volatility_index_data?"
                        f"currency={cur}&resolution=1D&start_timestamp={now_ms - 3*86400000}"
                        f"&end_timestamp={now_ms}")
            data = (resp.get("result") or {}).get("data") or []
            for r in data:
                if int(r[0]) > _last_t(path):
                    _append(path,
                            {"t": int(r[0]), "asset": cur, "src": "deribit_dvol",
                             "o": float(r[1]), "h": float(r[2]),
                             "l": float(r[3]), "c": float(r[4])})
                    wrote += 1
        except Exception:
            continue
    path = OUT / "deribit_funding_live_btc.jsonl"
    try:
        resp = _get(f"{DERIBIT}/public/get_funding_rate_history?"
                    f"instrument_name=BTC-PERPETUAL&start_timestamp={now_ms - 86400000}"
                    f"&end_timestamp={now_ms}")
        rows = resp.get("result") or []
        for r in rows:
            if int(r["timestamp"]) > _last_t(path):
                _append(path,
                        {"t": int(r["timestamp"]), "asset": "BTC",
                         "src": "deribit_funding",
                         "interest_8h": float(r["interest_8h"]),
                         "index_price": float(r["index_price"])})
                wrote += 1
    except Exception:
        pass
    return wrote


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    now_ms = int(time.time() * 1000)
    n_ctx = n_book = n_der = 0
    try:
        n_ctx = collect_hl_ctx(now_ms)
    except Exception as e:
        print(f"hl_ctx FAIL: {e}")
    try:
        n_book = collect_hl_book(now_ms)
    except Exception as e:
        print(f"hl_book FAIL: {e}")
    try:
        n_der = collect_deribit(now_ms)
    except Exception as e:
        print(f"deribit FAIL: {e}")
    print(f"collect_live: hl_ctx={n_ctx} hl_book={n_book} deribit={n_der}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
