"""Export the curated macro/on-chain daily frame into
data_extended/harmony/macro_daily.csv (+ .parquet mirror) for SPIKE
falsification.

Reads the upstream parquet READ-ONLY (<workspace>\\upstream\\
harmony_data_store\\harmony_master_clean.parquet). Selection is explicit
and declared — this file was previously built ad-hoc with no producer in
the morning chain, which left macro-fed forward leads (fng, mvrv)
permanently INPUT_DEAD even while the warehouse refreshed upstream.

Provenance notes:
  - etf_flow_usd_m: the legacy file carried exactly 2x the farside
    net total (a doubled groupby-sum artifact). Corrected to x1 —
    percentile-based signals are scale-invariant, but the raw column
    was wrong.
  - funding_coc, sopr: upstream coc_* family has been dead since
    2026-02-19. Columns are still exported (stale history preserved);
    consumers see them as frozen, never substituted.
  - btc_price: blockchain.com market-price (full 2010+ coverage, exact
    match vs legacy file).

Missing columns are skipped loudly, never substituted.

Usage: .venv/Scripts/python.exe tools/export_macro_daily.py
"""
from __future__ import annotations

import os

from pathlib import Path

import pandas as pd

SRC = os.path.join(os.environ.get("HARMONY_STORE", "harmony_data_store"),
                   "harmony_master_clean.parquet")
OUT = Path(__file__).resolve().parent.parent / "data_extended" / "harmony"

# Verified against the legacy file by exact overlap (2026-09-24):
# every mapping below matched >=0.99 relative tolerance on the tail.
COLUMNS = {
    "btc_price": "blockchain_api_market-price__value",
    "mvrv": "coinmetrics_core__mvrv__capmvrvcur",
    "fng": "alternative_fng__value",
    "etf_flow_usd_m": "farside_btc_etf_flows__total_usd_m",
    "oi_binance": "bgeo_archive_oi_binance__v1",
    # Semantic renames (2026-09-25 audit): the upstream labels lie.
    # The coc confluence column is a discrete cycle-extreme FLAG, not a
    # funding rate; the coc sopr column is literally SOPR-1, not SOPR.
    # Renamed exports disarm both traps — nothing consumed the old names.
    "funding_confluence_flag": ("coc_btconchain_confluence_cycleextreme_"
                               "v2_1_cycleextreme_v2_1_light__futures_"
                               "funding_rate"),
    "sopr_minus1": ("coc_btconchain_realised_sopr_fundingrate_"
                    "sopr_fundingrate_light__sopr-1"),
    "fred_us10y": "fred_us10y",
    "fred_vix": "fred_vix",
    "fred_nasdaq": "fred_nasdaq",
    "fred_fed_funds": "fred_fed_funds",
}

# Same upstream metric via SPIKE's own daily pull (data_extended/coinmetrics
# is refreshed by tools/backfill_coinmetrics.py inside the morning chain
# BEFORE this export runs). The parquet's coinmetrics_core columns only
# refresh on the weekly --full-local harvest, leaving mvrv up to ~7d stale.
# capmvrvcur values verified bit-identical vs the parquet over all 5912
# shared rows (max|diff| 4e-16) — same CoinMetrics metric, deeper history
# (2009-01-03) and fresher tail, so this is NOT a provider substitution.
CM_LOCAL = OUT.parent / "coinmetrics" / "btc_metrics_daily.json"
# btc_price switched to SPIKE's own coinmetrics priceusd on 2026-09-27:
# blockchain_api_market-price__value vanished from the upstream parquet
# entirely (all blockchain_api_* columns dropped upstream that night).
# priceusd is live (nightly backfill), full-history (2010-07-18+), and
# overlaps px_bitstamp at 0.11% median |rel diff| (n=4287, p99 1.7%) —
# a forced provider substitution, loud via the [spike-coinmetrics] span
# tag, not a silent one.
LOCAL_SOURCES = {"mvrv": "capmvrvcur", "btc_price": "priceusd"}


def _local_series(metric: str) -> pd.Series | None:
    if not CM_LOCAL.exists():
        return None
    import json
    rows = pd.DataFrame(json.loads(CM_LOCAL.read_text(encoding="utf-8")))
    if rows.empty or metric not in rows.columns:
        return None
    t = pd.to_datetime(rows["t"])
    s = pd.Series(pd.to_numeric(rows[metric], errors="coerce").to_numpy(),
                  index=t.dt.normalize())
    return s.groupby(level=0).last()


def main() -> int:
    df = pd.read_parquet(SRC)
    idx = pd.to_datetime(df.index).normalize()
    out = pd.DataFrame(index=idx)
    missing, spans = [], []
    for name, col in COLUMNS.items():
        src = "parquet"
        s = None
        if name in LOCAL_SOURCES:
            s = _local_series(LOCAL_SOURCES[name])
            src = "spike-coinmetrics"
        if s is None:
            if col not in df.columns:
                missing.append(f"{name} <- {col}")
                continue
            s = pd.to_numeric(df[col], errors="coerce")
            s = s.groupby(level=0).last()
        if name == "btc_price":
            # Provider placeholder zeros (pre-market 2010-01-01..08-16)
            # are not prices — a 0 close poisons return math (inf/nan
            # chains) for every consumer. Mask non-positive loudly.
            n_nonpos = int((s <= 0).sum())
            if n_nonpos:
                s = s.mask(s <= 0)
                spans.append(f"  btc_price: masked {n_nonpos} "
                             "non-positive provider placeholders")
        out[name] = s
        nz = s.dropna()
        if len(nz):
            spans.append(f"  {name:20s} {nz.index.min():%Y-%m-%d} -> "
                         f"{nz.index.max():%Y-%m-%d}  n={len(nz)}"
                         f"  [{src}]")
        else:
            spans.append(f"  {name:20s} EMPTY")
    out.index.name = "date"
    out = out.sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    csv_p = OUT / "macro_daily.csv"
    for p, write in ((csv_p, lambda q: out.to_csv(q)),
                     (OUT / "macro_daily.parquet", lambda q: out.to_parquet(q))):
        tmp = p.with_name(p.name + ".tmp")
        write(tmp)
        tmp.replace(p)
    print(f"wrote {csv_p} rows={len(out)} cols={len(out.columns)}")
    print("\n".join(spans))
    if missing:
        print("\nMISSING (skipped loudly, not substituted):")
        print("\n".join(f"  {m}" for m in missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
