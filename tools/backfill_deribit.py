"""Cross-venue data pull: Deribit public REST (no key).

Feeds the options/vol domain — no options feed exists anywhere else in
owned data (coverage audit round17). Also pulls Deribit perp funding
history: a THIRD venue for xvenue funding families (HL + Binance + Deribit).

Writes data_extended/deribit/{name}.json — never touches data_snapshot/.

Endpoints:
  /public/get_volatility_index_data  DVOL OHLC (daily res back to 2021)
  /public/get_funding_rate_history   perp funding prints (8h cadence)

Usage: .venv/Scripts/python.exe tools/backfill_deribit.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_extended" / "deribit"
BASE = "https://www.deribit.com/api/v2"
START_2021 = 1609459200000  # DVOL BTC begins ~Mar-2021; this floor is safe
DVOL_CURRENCIES = ["BTC", "ETH"]
# BTC/ETH have flagship USDT-margined perps; alts exist only as USDC perps
# on Deribit (verified via get_instruments — no SOL-PERPETUAL exists).
PERP_INSTRUMENTS = ["BTC-PERPETUAL", "ETH-PERPETUAL",
                    "SOL_USDC-PERPETUAL", "XRP_USDC-PERPETUAL",
                    "DOGE_USDC-PERPETUAL", "AVAX_USDC-PERPETUAL",
                    "LINK_USDC-PERPETUAL"]
CHUNK_MS = 365 * 86400000


def get(path: str, retries: int = 4) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + path,
                                         headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def _load_existing(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _merge(existing: list[dict], new: list[dict], key: str = "t") -> list[dict]:
    seen = {r[key]: r for r in existing}
    for r in new:
        seen[r[key]] = r
    return [seen[k] for k in sorted(seen)]


def _write_safe(path: Path, rows: list[dict], key: str = "t") -> None:
    """Refuse empty/shrinking/regressing writes — never truncate accrued
    history (same contract as backfill_binance._write_safe)."""
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


def dvol_daily(currency: str) -> list[dict]:
    """DVOL OHLC at 1D resolution, chunked yearly back to START_2021."""
    path = OUT / f"{currency.lower()}_dvol_1d.json"
    existing = _load_existing(path)
    start = (max(int(r["t"]) for r in existing) + 86400000
             if existing else START_2021)
    end = int(time.time() * 1000)
    new: list[dict] = []
    while start < end:
        chunk_end = min(start + CHUNK_MS, end)
        resp = get(f"/public/get_volatility_index_data?currency={currency}"
                   f"&resolution=1D&start_timestamp={start}"
                   f"&end_timestamp={chunk_end}")
        data = (resp.get("result") or {}).get("data") or []
        new.extend({"t": int(r[0]), "o": float(r[1]), "h": float(r[2]),
                    "l": float(r[3]), "c": float(r[4])} for r in data)
        if not data or data[-1][0] >= chunk_end:
            start = chunk_end + 1
        else:
            start = int(data[-1][0]) + 86400000
        time.sleep(0.3)
    return _merge(existing, new)


def funding_history(instrument: str) -> list[dict]:
    """8h funding prints since listing; merges onto accrued file."""
    name = instrument.lower().replace("-perpetual", "")
    path = OUT / f"{name}_funding_8h.json"
    existing = _load_existing(path)
    start = (max(int(r["t"]) for r in existing) + 1
             if existing else START_2021)
    end = int(time.time() * 1000)
    new: list[dict] = []
    while start < end:
        chunk_end = min(start + CHUNK_MS, end)
        resp = get(f"/public/get_funding_rate_history?"
                   f"instrument_name={instrument}&start_timestamp={start}"
                   f"&end_timestamp={chunk_end}")
        rows = resp.get("result") or []
        new.extend({"t": int(r["timestamp"]),
                    "interest_8h": float(r["interest_8h"]),
                    "interest_1h": float(r["interest_1h"]),
                    "index_price": float(r["index_price"])}
                   for r in rows)
        if not rows or int(rows[-1]["timestamp"]) >= chunk_end:
            start = chunk_end + 1
        else:
            start = int(rows[-1]["timestamp"]) + 1
        time.sleep(0.3)
    return _merge(existing, new)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for cur in DVOL_CURRENCIES:
        try:
            _write_safe(OUT / f"{cur.lower()}_dvol_1d.json", dvol_daily(cur))
        except Exception as e:
            print(f"{cur} dvol_1d: FAIL {e} (existing file untouched)")
    for inst in PERP_INSTRUMENTS:
        try:
            _write_safe(
                OUT / f"{inst.lower().replace('-perpetual','')}_funding_8h.json",
                funding_history(inst))
        except Exception as e:
            print(f"{inst} funding_8h: FAIL {e} (existing file untouched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
