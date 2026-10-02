"""CoinMetrics community API pull (no key, rate-limited) -> refreshes the
on-chain/flow layer that unfreezes the flagship N-leg and extends coverage.

Endpoint: community-api.coinmetrics.io/v4/timeseries/asset-metrics
Declared metrics (BTC): FlowInExUSD, FlowOutExUSD (exchange flows — the
N-leg source), CapMVRVCur (MVRV), SOPR, AdrActCnt, NVTAdj,
CapMrktCurUSD, CapRealUSD, TxCnt.

Writes data_extended/coinmetrics/btc_metrics_daily.json — one row per day,
wide format. Never touches data_snapshot/.

Usage: .venv/Scripts/python.exe tools/backfill_coinmetrics.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_extended" / "coinmetrics"
API = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = ["PriceUSD", "FlowInExUSD", "FlowOutExUSD", "CapMVRVCur",
           "CapMrktCurUSD", "AdrActCnt", "TxCnt", "HashRate", "SplyCur",
           "SOPR", "NVTAdj", "CapRealUSD"]   # last three probed paid-tier; skipped loudly


def get(url: str, retries: int = 5) -> dict:
    """urllib gets Cloudflare-403'd on this host; curl's TLS fingerprint
    passes. Public endpoint, no key."""
    import subprocess
    for attempt in range(retries):
        try:
            r = subprocess.run(
                ["curl", "-s", "-H", "Accept: application/json", url],
                capture_output=True, timeout=60, check=True)
            return json.loads(r.stdout)
        except Exception as e:
            if attempt == retries - 1:
                print("FAIL", e, url[:120])
                return {}
            time.sleep(min(30, 3 ** attempt))
    return {}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    by_date: dict[str, dict] = {}
    skipped = []
    for m in METRICS:
        url = (f"{API}?assets=btc&metrics={m}"
               "&frequency=1d&page_size=10000&pretty=false")
        got = 0
        while url:
            r = get(url)
            if "error" in r:
                skipped.append(m)
                break
            for row in r.get("data", []):
                d = row["time"][:10]
                rec = by_date.setdefault(d, {"t": d})
                if m in row:
                    rec[m.lower()] = float(row[m])
                    got += 1
            url = r.get("next_page_url")
            time.sleep(0.5)
        print(f"  {m}: {got} rows" + ("  [PAID-TIER — skipped]" if m in skipped else ""))
    rows = [by_date[k] for k in sorted(by_date)]
    path = OUT / "btc_metrics_daily.json"
    # fail-safe write: a half-failed pull must not overwrite a healthy
    # file — refuse when empty, shrunk >10%, or when the tail regresses.
    try:
        old = json.loads(path.read_text())
    except Exception:
        old = []
    if not rows:
        print(f"btc_metrics_daily: REFUSE write — empty pull "
              f"(keeping {len(old)} rows)"); return 1
    # Per-field union merge: a metric that returns nothing today
    # (paid-tier skip, upstream outage) must not erase its accrued
    # column — fresh fields win, absent fields keep prior values.
    merged = {r["t"]: dict(r) for r in old}
    for r in rows:
        cur = merged.setdefault(r["t"], {"t": r["t"]})
        cur.update({k: v for k, v in r.items() if k != "t"})
    # phantom rows: a date carrying no metric value at all is a writer
    # artifact, not an observation
    rows = [r for t, r in sorted(merged.items()) if len(r) > 1]
    if old:
        missing_cols = {c for r in old for c in r if c != "t"} - \
                       {c for r in rows for c in r if c != "t"}
        if len(rows) < len(old) * 0.9 or rows[-1]["t"] < old[-1]["t"]:
            print(f"btc_metrics_daily: REFUSE write — n {len(old)}->"
                  f"{len(rows)}, tail {old[-1]['t']}->{rows[-1]['t']}")
            return 1
        if missing_cols:
            print(f"btc_metrics_daily: WARN columns vanished: "
                  f"{sorted(missing_cols)}")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rows))
    tmp.replace(path)
    print(f"btc_metrics_daily: n={len(rows)} {rows[0]['t']} -> {rows[-1]['t']}"
          + (f" | skipped: {skipped}" if skipped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
