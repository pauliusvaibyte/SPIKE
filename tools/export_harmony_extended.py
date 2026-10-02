"""Export a wide slice of the Sentinely harmony warehouse into
data_extended/harmony/harmony_extended.csv for SPIKE falsification.

Reads the upstream parquet READ-ONLY (<workspace>\\upstream\\
harmony_data_store\\harmony_master_clean.parquet). Selection is explicit and
declared — grouped by evidence layer:

  venue clocks : bitstamp/bitfinex/coinbase/binance-spot/bybit perp+mark+
                 index+premium (multi-venue daily prices, some to 2011)
  derivatives  : bybit/binance-um/deribit funding aggregates, bybit OI,
                 archive aggregate funding, per-exchange futures OI,
                 liquidations USD (open_daily), DVOL OHLC, ATM IV by tenor,
                 25d skew by tenor
  on-chain     : capmvrvcur, mvrv-z, lth/sth mvrv, lth/sth sopr, asopr,
                 nupl, nrpl usd, realized price/profit/loss/P-L ratio,
                 lth/sth supply, exchange balance total, hashrate,
                 coinbase premium, puell, reserve risk, dormancy,
                 liveliness, nvt, cdd, fng

Values are provider-native; upstream certification/PIT status is
Sentinely's responsibility — this export does not re-certify.
Missing columns are skipped loudly, never substituted.

Usage: .venv/Scripts/python.exe tools/export_harmony_extended.py
"""
from __future__ import annotations

import os

import json
from pathlib import Path

import pandas as pd

SRC = os.path.join(os.environ.get("HARMONY_STORE", "harmony_data_store"),
                   "harmony_master_clean.parquet")
OUT = Path(__file__).resolve().parent.parent / "data_extended" / "harmony"

COLUMNS = {
    # venue daily closes (multi-venue clocks)
    "px_bitstamp": "bitstamp_btcusd_daily__close",
    "px_bitfinex": "bitfinex_btcusd_daily__close",
    "px_coinbase": "coinbase_btcusd_daily__close",
    "px_binance_spot": "binance_spot__close",
    "binance_spot_taker_buy": "binance_spot__taker_buy_base",
    "px_bybit_perp": "bybit_btcusdt_perp_daily__close",
    "px_bybit_mark": "bybit_btcusdt_mark_daily__close",
    "px_bybit_index": "bybit_btcusdt_index_daily__close",
    "bybit_premium": "bybit_btcusdt_premium_daily__close",
    # derivatives aggregates
    "funding_bybit": "bybit_btcusdt_funding__mean",
    "funding_binance_um": "binance_um_funding__last_funding_rate__mean",
    "funding_deribit_8h": "deribit_btc_funding__interest_8h__mean",
    "funding_agg_archive": "bgeo_archive_funding_rate__v1",
    "oi_bybit": "bgeo_archive_oi_bybit__v1",
    "oi_futures_binance": "coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__binance",
    "oi_futures_cme": "coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__cme",
    "oi_futures_hyperliquid": "coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__hyperliquid",
    "oi_futures_deribit": "coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__deribit",
    "liq_long_usd": "open_daily_btc_long_liquidations_usd__value",
    "liq_short_usd": "open_daily_btc_short_liquidations_usd__value",
    "liq_total_archive": "bgeo_archive_btc_liquidations_total__v1",
    # options/vol
    "dvol_close": "deribit_dvol__close",
    "iv_atm_1w": "coc_btconchain_derivatives_options_atmimpliedvolatility_options_atmimpliedvolatility_light__1_week",
    "iv_atm_1m": "coc_btconchain_derivatives_options_atmimpliedvolatility_options_atmimpliedvolatility_light__1_month",
    "iv_atm_3m": "coc_btconchain_derivatives_options_atmimpliedvolatility_options_atmimpliedvolatility_light__3_months",
    "iv_atm_6m": "coc_btconchain_derivatives_options_atmimpliedvolatility_options_atmimpliedvolatility_light__6_months",
    "skew25_1w": "coc_btconchain_derivatives_options_25deltaskew_options_25deltaskew_light__1_week",
    "skew25_1m": "coc_btconchain_derivatives_options_25deltaskew_options_25deltaskew_light__1_month",
    "skew25_3m": "coc_btconchain_derivatives_options_25deltaskew_options_25deltaskew_light__3_months",
    "rv_1w": "coc_extra_btconchain_technical_technical_realizedvolatility_technical_realizedvolatility_light__1-week",
    "rv_1m": "coc_extra_btconchain_technical_technical_realizedvolatility_technical_realizedvolatility_light__1-month",
    "rv_3m": "coc_extra_btconchain_technical_technical_realizedvolatility_technical_realizedvolatility_light__3-months",
    # on-chain valuation
    "mvrv_raw": "coinmetrics_core__mvrv__capmvrvcur",
    "mvrv_z": "bgeo_report_bitcoin_mvrv_zscore_g__mvrv_zscore",
    "lth_mvrv": "bgeo_archive_lth_mvrv__v1",
    "sth_mvrv": "bgeo_archive_sth_mvrv__v1",
    "lth_sopr": "bgeo_report_bitcoin_lthsopr_g__lth-sopr",
    # *_alfabitcoin twins verified bit-identical to base over all shared
    # rows (diff=0.0) and still publishing past the base columns' 09-18
    # death — the live lineage of the same bgeo metric, not a substitute.
    "sth_sopr": "bgeo_archive_sth_sopr_alfabitcoin__v1",
    "sopr_7sma": "bgeo_archive_sopr_7sma_alfabitcoin__v1",
    "asopr": "bgeo_report_bitcoin_asopr_g__asopr",
    "nupl": "bgeo_archive_nupl_data_alfabitcoin__v1",
    "nrpl_usd": "bgeo_archive_nrpl_usd__v1",
    "realized_price": "bgeo_archive_realized_price__v1",
    "realized_pl_ratio": "bgeo_archive_realized_profit_loss_ratio__v1",
    "realized_profit": "bgeo_archive_realized_profit__v1",
    "realized_loss": "bgeo_archive_realized_loss__v1",
    "lth_supply": "bgeo_report_bitcoin_lth_sth_g__lth_supply",
    "sth_supply": "bgeo_report_bitcoin_lth_sth_g__sth_supply",
    "exchange_balance_total": "coc_btconchain_exchange_exchange_balances_btc_exchange_balances_btc_light__total",
    # network/mining
    "hashrate": "bgeo_archive_hashrate__v1",
    "coinbase_premium": "bgeo_archive_coinbase_premium__v1",
    "puell": "bgeo_archive_puell_multiple_data__v1",
    "reserve_risk": "bgeo_archive_reserve_risk__v1",
    "dormancy": "obm_dormancy_days_daily__value",
    "liveliness": "coc_btconchain_cointime_liveliness_liveliness_light__liveliness",
    "nvt_adj90": "bgeo_archive_nvtadj90__v1",
    "cdd": "bgeo_archive_cdd__v1",
    "fng": "bgeo_archive_fear_greed__v1",
}

# Columns deliberately NOT exported — documented so nobody re-adds them
# blindly. btc_price: bgeo_archive_btc_price__v1 died 2023-12-13 (frozen
# ~1000d upstream); consumers must use px_bitstamp or macro_daily's
# btc_price (SPIKE coinmetrics priceusd since 2026-09-27 — the
# blockchain_api source column was dropped upstream entirely). Shipping
# a dead price under that name is a trap for future candidates.
DEAD_COLUMNS = {
    "btc_price": "bgeo_archive_btc_price__v1 dead 2023-12-13 "
                 "(~1000d stale); px_bitstamp covers the price leg",
}

# Upstream defects (2026-09-25 audit) — emit all-NaN, never the poisoned
# values. Quarantined columns stay in the schema so consumers die empty,
# not KeyError, and the mask is printed loudly on every export.
QUARANTINE = {
    "coinbase_premium": "bgeo col is ~100x NEXT-day BTC return "
                        "(corr .971) — mislabeled lookahead, not a premium",
    "realized_price":   "SPIKE audit flags early-stamped 2026 tail; "
                        "upstream certified live — arbitration OPEN. "
                        "Unconsumed; masked until reconciled",
}
# Dead-feed signature: a feed frozen at one float for >=3 consecutive
# days is a pin, not a market reading (bgeo_archive_sth_sopr__v1 carried
# an 11-day exact-1.0 pin). Masked rows only — history outside pins
# stays provider-native.
PIN_MASK = {"sth_sopr": (1.0, 3)}
# Non-positive price rows are writer placeholders, never real trades.
POSITIVE_ONLY: set = set()

# Upstream warehouse quarantine manifest — the audited defect ledger for
# the source parquet. Binding (not duplicating) it here so upstream
# do_not_use/unit/date-range defects propagate automatically.
UPSTREAM_MANIFEST = (Path(SRC).parent.parent / "data"
                     / "harmony_quarantine_manifest.json")


def _upstream_defects() -> tuple[dict, list]:
    """(src_col -> action dict) for column-level defects, plus the raw
    date_range list. Missing manifest = loud empty result, not silent."""
    if not UPSTREAM_MANIFEST.exists():
        return {"__missing__": {"action": "manifest_missing"}}, []
    man = json.loads(UPSTREAM_MANIFEST.read_text(encoding="utf-8"))
    cols = {d["column"]: d for d in man.get("column_defects", [])
            if "column" in d}
    return cols, man.get("date_range_defects", [])


def main() -> int:
    df = pd.read_parquet(SRC)
    idx = pd.to_datetime(df.index).normalize()
    out = pd.DataFrame(index=idx)
    up_cols, up_ranges = _upstream_defects()
    if "__missing__" in up_cols:
        print("!! upstream quarantine manifest MISSING at "
              f"{UPSTREAM_MANIFEST} — defect propagation disabled")
    missing, spans, masked = [], [], []
    for name, col in COLUMNS.items():
        if col not in df.columns:
            missing.append(f"{name} <- {col}")
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        s = s.groupby(level=0).last()
        # upstream audited defects on the SOURCE column
        up = up_cols.get(col)
        if up:
            act = up["action"]
            if act == "do_not_use":
                masked.append(f"{name}: UPSTREAM do_not_use — "
                              f"{up['defect']}")
                s = s * float("nan")
            else:
                masked.append(f"{name}: UPSTREAM {act} — {up['defect']}")
        for d in up_ranges:
            if d.get("column") == col and d.get("action") == "mask":
                lo = pd.Timestamp(d["from"])
                hi = pd.Timestamp(d["to"])
                n_rng = int(s.loc[lo:hi].notna().sum())
                s.loc[lo:hi] = float("nan")
                masked.append(f"{name}: UPSTREAM range mask "
                              f"{d['from']}..{d['to']} — {d['reason']} "
                              f"({n_rng} rows)")
        if name in QUARANTINE:
            masked.append(f"{name}: {QUARANTINE[name]} "
                          f"({s.notna().sum()} rows masked)")
            s = s * float("nan")
        if name in PIN_MASK:
            val, min_run = PIN_MASK[name]
            is_pin = s.eq(val)
            run_len = is_pin.groupby((~is_pin).cumsum()).transform("sum")
            n_pin = int((is_pin & (run_len >= min_run)).sum())
            if n_pin:
                masked.append(f"{name}: {n_pin} rows masked "
                              f"(value pinned at {val} for "
                              f">={min_run}d runs)")
            s = s.mask(is_pin & (run_len >= min_run))
        if name in POSITIVE_ONLY:
            n_bad = int((s <= 0).sum())
            if n_bad:
                masked.append(f"{name}: {n_bad} non-positive rows masked")
            s = s.mask(s <= 0)
        out[name] = s
        nz = s.dropna()
        if len(nz):
            spans.append(f"  {name:26s} {nz.index.min():%Y-%m-%d} -> "
                         f"{nz.index.max():%Y-%m-%d}  n={len(nz)}")
        else:
            spans.append(f"  {name:26s} EMPTY")
    out.index.name = "t"
    out = out.sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "harmony_extended.csv"
    tmp = OUT / "harmony_extended.csv.tmp"
    out.to_csv(tmp)
    tmp.replace(p)
    print(f"wrote {p} rows={len(out)} cols={len(out.columns)}")
    for name, why in DEAD_COLUMNS.items():
        print(f"  NOT EXPORTED  {name}: {why}")
    print("\n".join(spans))
    if missing:
        print("\nMISSING (skipped loudly, not substituted):")
        print("\n".join(f"  {m}" for m in missing))
    if masked:
        print("\nQUARANTINE-MASKED (upstream defect):")
        print("\n".join(f"  {m}" for m in masked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
