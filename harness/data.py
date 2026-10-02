"""Snapshot data loaders — read-only against data_snapshot/.

All data is the frozen 2026-09-23T02:20:28Z snapshot (SNAPSHOT_MANIFEST.json).
Nothing here touches the live bot directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SNAPSHOT = Path(__file__).resolve().parent.parent / "data_snapshot"


def _to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    for col in ("o", "h", "l", "c", "v"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def candles(asset: str, interval: str, span: str) -> pd.DataFrame:
    """Load data_cache/{asset}_{interval}_{span}.json -> OHLCV df."""
    p = SNAPSHOT / "data_cache" / f"{asset.lower()}_{interval}_{span}.json"
    return _to_df(json.loads(p.read_text()))


def candles_15m(asset: str) -> pd.DataFrame:
    """Load the .cache_{asset}_candles.json 15m store (older schema)."""
    p = SNAPSHOT / f".cache_{asset.lower()}_candles.json"
    return _to_df(json.loads(p.read_text()))


def funding(asset: str, span: str = "90d") -> pd.DataFrame:
    """Load data_cache/funding/{asset}_funding_{span}.json.

    Rows: {time ms, fundingRate str, premium str, coin}. Hourly cadence.
    """
    p = SNAPSHOT / "data_cache" / "funding" / f"{asset.lower()}_funding_{span}.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    if "premium" in df.columns:
        df["premium"] = df["premium"].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def funding_journal(asset: str) -> pd.DataFrame:
    """Self-accrued journal (the rolling-3000 basis production uses)."""
    p = SNAPSHOT / "funding_journal" / f"{asset.upper()}_funding.jsonl"
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    df = pd.DataFrame(rows)
    # journal schema: {"time" (ms), "fundingRate", "coin"} (aliases tolerated)
    tcol = next(c for c in ("ts", "t", "time") if c in df.columns)
    df["t"] = pd.to_datetime(df[tcol].astype("int64"), unit="ms", utc=True)
    rcol = next(c for c in ("rate", "fundingRate") if c in df.columns)
    df["rate"] = df[rcol].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def l2_journal(asset: str) -> pd.DataFrame:
    """L2 order-book journal rows: {t, mid, imbalance, bids, asks, ...}."""
    p = SNAPSHOT / "l2_journal" / f"{asset.upper()}_l2_testnet.jsonl"
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    return df.sort_values("t").reset_index(drop=True)


def shadow_journal() -> list[dict]:
    p = SNAPSHOT / "shadow_fra_momentum.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


# ── extended dataset (data_extended/, fetched 2026-09-23) ────────────────
# Separate versioned dataset — the frozen snapshot stays immutable.

EXTENDED = Path(__file__).resolve().parent.parent / "data_extended"


def funding_full(asset: str) -> pd.DataFrame:
    """Extended funding: fundingHistory backfilled to launch (~3.3y, hourly)."""
    p = EXTENDED / "funding" / f"{asset.lower()}_funding_full.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    if "premium" in df.columns:
        df["premium"] = df["premium"].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def candles_full(asset: str, interval: str) -> pd.DataFrame:
    """Extended candles: 1d/4h to ~launch, 1h ~208d, 15m ~52d (API cap)."""
    p = EXTENDED / "candles" / f"{asset.lower()}_{interval}_full.json"
    return _to_df(json.loads(p.read_text()))


_BINANCE_SYM = {"btc": "btcusdt", "sol": "solusdt", "eth": "ethusdt",
                "xrp": "xrpusdt", "doge": "dogeusdt", "avax": "avaxusdt",
                "link": "linkusdt"}


def binance_funding(asset: str) -> pd.DataFrame:
    """Binance USD-M funding history (8h epochs, since 2019)."""
    p = EXTENDED / "binance" / f"{_BINANCE_SYM[asset.lower()]}_funding.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def binance_klines(asset: str, interval: str = "1h") -> pd.DataFrame:
    """Binance USD-M klines {t,o,h,l,c,v,taker_buy_vol,n_trades} (~2y at 1h)."""
    p = EXTENDED / "binance" / f"{_BINANCE_SYM[asset.lower()]}_klines_{interval}.json"
    return _to_df(json.loads(p.read_text()))


def binance_oi(asset: str) -> pd.DataFrame:
    """Binance USD-M openInterestHist (~30d): {timestamp, sumOpenInterest,...}."""
    p = EXTENDED / "binance" / f"{_BINANCE_SYM[asset.lower()]}_oi_hist_1h.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["oi"] = df["sumOpenInterest"].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def binance_taker_ls(asset: str) -> pd.DataFrame:
    """Binance takerlongshortRatio (~30d): {timestamp, buySellRatio,...}."""
    p = EXTENDED / "binance" / f"{_BINANCE_SYM[asset.lower()]}_taker_ls_1h.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["ratio"] = df["buySellRatio"].astype(float)
    return df.sort_values("t").reset_index(drop=True)


def binance_premium(asset: str) -> pd.DataFrame:
    """Binance premiumIndexKlines daily: mark-index premium (basis proxy)
    back to contract listing (~2019+)."""
    p = EXTENDED / "binance" / f"{_BINANCE_SYM[asset.lower()]}_premium_1d.json"
    return _to_df(json.loads(p.read_text()))


def harmony_extended() -> pd.DataFrame:
    """Wide Sentinely-warehouse export (59 cols): multi-venue daily clocks,
    cross-venue funding aggregates, per-exchange OI, liquidations USD,
    DVOL + ATM IV + 25d skew by tenor, on-chain valuation/flow set.
    See tools/export_harmony_extended.py for the declared column map and
    per-column provenance/spans."""
    p = EXTENDED / "harmony" / "harmony_extended.csv"
    df = pd.read_csv(p, parse_dates=["t"])
    df = df.sort_values("t").reset_index(drop=True)

    # ── A32 provenance masks (upstream placeholder artifacts — the
    # export faithfully reproduced them; consumers must not read them) ──
    # 1. exchange_balance_total: zeros through 2011-06 plus exact float64
    #    repeats (same bit pattern on different days = fill artifacts)
    #    dominating until 2012-08-13. Mask any value that is 0 or whose
    #    exact float appears on >2 days — a physical balance never
    #    repeats to 12 decimals.
    if "exchange_balance_total" in df.columns:
        eb = df["exchange_balance_total"]
        vc = eb.value_counts()
        placeholder = set(vc[vc > 2].index) | {0.0}
        df.loc[eb.isin(placeholder), "exchange_balance_total"] = pd.NA
    # 2. oi_futures_hyperliquid: nonzero values from 2020-04 — 3.5 years
    #    before the venue existed (~late 2023). Mislabeled/backfilled
    #    upstream; no trustworthy pre-2023 values.
    if "oi_futures_hyperliquid" in df.columns:
        df.loc[df["t"] < pd.Timestamp("2023-01-01"),
               "oi_futures_hyperliquid"] = pd.NA
    # 3. oi_futures_{cme,hyperliquid}: leading zero-run is placeholder
    #    padding (siblings printed real OI the same days) — zero OI on a
    #    live market is impossible; map the contiguous leading zeros to
    #    NaN.
    for c in ("oi_futures_cme", "oi_futures_hyperliquid"):
        if c not in df.columns:
            continue
        nz = df.index[df[c].fillna(0) > 0]
        if len(nz):
            df.loc[: nz[0], c] = df.loc[: nz[0], c].where(
                df.loc[: nz[0], c] != 0, other=pd.NA)
    return df


def coinmetrics_daily() -> pd.DataFrame:
    """CoinMetrics community-tier BTC daily (refreshed): priceusd, flowin/
    flowoutexusd (N-leg source), capmvrvcur, capmrktcurusd, adractcnt,
    txcnt, hashrate, splycur. Paid-tier metrics (sopr, nvtadj, caprealusd)
    are probed and skipped loudly."""
    p = EXTENDED / "coinmetrics" / "btc_metrics_daily.json"
    df = pd.DataFrame(json.loads(p.read_text()))
    df["t"] = pd.to_datetime(df["t"])
    return df.sort_values("t").reset_index(drop=True)


def harmony_daily() -> pd.DataFrame:
    """Curated macro/on-chain daily export from the upstream repo's
    Harmony warehouse (data_extended/harmony/macro_daily.parquet).
    Columns: t (date), btc_price, mvrv, fng, etf_flow_usd_m, oi_binance,
    funding_coc, sopr, fred_* — plus 'c' alias on btc_price for the
    falsify stack's price-frame convention."""
    p = EXTENDED / "harmony" / "macro_daily.csv"
    df = pd.read_csv(p, parse_dates=["date"])
    df = df.rename(columns={df.columns[0]: "t"})
    df["c"] = df["btc_price"]
    return df.sort_values("t").reset_index(drop=True)


# ── forward-lead input/drift probes ─────────────────────────────────────
# Shared evaluation of the DECLARED spec maps in candidates_forward
# (LEAD_INPUT_SPECS / LEAD_DRIFT_SPECS): run_forward_eval uses them for
# report labels and the verdict path; verify_integrity uses the same
# probes for the freshness gate and report reconciliation, so a wrong
# answer can never disagree between the two.

FORWARD_ASSETS = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def _last_t(df) -> "pd.Timestamp":
    if df is None or getattr(df, "empty", True) or "t" not in df.columns:
        return pd.NaT
    return pd.to_datetime(df["t"], utc=True).max()


def _last_col(df, col: str) -> "pd.Timestamp":
    if df is None or col not in df.columns:
        return pd.NaT
    s = df.loc[df[col].notna(), "t"]
    return pd.to_datetime(s, utc=True).max() if len(s) else pd.NaT


def forward_assets() -> list[str]:
    """Assets with the full HL trio (funding + 4h + 1h) — the runner's
    own enumeration rule."""
    ext = EXTENDED
    return [a for a in FORWARD_ASSETS
            if (ext / "funding" / f"{a}_funding_full.json").exists()
            and (ext / "candles" / f"{a}_4h_full.json").exists()
            and (ext / "candles" / f"{a}_1h_full.json").exists()]


def basis_assets() -> list[str]:
    ext = EXTENDED
    return [a for a in FORWARD_ASSETS
            if (ext / "binance" / f"{a}usdt_premium_1d.json").exists()]


def _probe(spec: tuple, hd, he, assets, bassets) -> "pd.Timestamp":
    src, arg = spec
    if src == "macro":
        return min(_last_col(hd, c) for c in arg)
    if src == "hext":
        return min(_last_col(he, c) for c in arg)
    if src == "hl_funding":
        return min((_last_t(funding_full(a)) for a in assets),
                   default=pd.NaT)
    if src == "bn_funding":
        return min((_last_t(binance_funding(a)) for a in assets),
                   default=pd.NaT)
    if src == "candles":
        who, iv = arg
        pool = assets if who == "all" else [who]
        return min((_last_t(candles_full(a, iv)) for a in pool),
                   default=pd.NaT)
    if src == "bn_klines":
        who, iv = arg
        pool = bassets if who == "all" else [who]
        return min((_last_t(binance_klines(a, iv)) for a in pool),
                   default=pd.NaT)
    if src == "bn_premium":
        pool = bassets if arg == "all" else [arg]
        return min((_last_t(binance_premium(a)) for a in pool),
                   default=pd.NaT)
    raise ValueError(f"unknown probe source {src}")


def forward_input_probes() -> dict:
    """{lead: (label, last_valid_ts)} — min over each lead's declared
    input specs. A lead can only accrue when the whole spec is fresh."""
    from harness import candidates_forward as CF
    hd, he = harmony_daily(), harmony_extended()
    assets, bassets = forward_assets(), basis_assets()
    out = {}
    for lead, (label, specs) in CF.LEAD_INPUT_SPECS.items():
        out[lead] = (label, min(_probe(s, hd, he, assets, bassets)
                                for s in specs))
    return out


def prem_merged(a: str) -> pd.DataFrame:
    """kline close merged with premiumIndex close — fwd_premium_basis_
    converge's input frame (same construction the runner uses)."""
    kl = binance_klines(a, "1d")[["t", "c"]].copy()
    pr = binance_premium(a)[["t", "c"]].rename(columns={"c": "prem"})
    for d in (kl, pr):
        d["t"] = pd.to_datetime(d["t"])
        if getattr(d["t"].dt, "tz", None) is not None:
            d["t"] = d["t"].dt.tz_convert(None)
    return kl.merge(pr, on="t").sort_values("t").reset_index(drop=True)


def he_price_frame() -> pd.DataFrame:
    """harmony_extended with the runner's he['c'] = px_bitstamp alias."""
    he = harmony_extended()
    he["t"] = pd.to_datetime(he["t"])
    if getattr(he["t"].dt, "tz", None) is not None:
        he["t"] = he["t"].dt.tz_convert(None)
    he = he.sort_values("t").reset_index(drop=True)
    he["c"] = pd.to_numeric(he["px_bitstamp"], errors="coerce")
    return he


def forward_drift_prices() -> dict:
    """{lead: price frame(s)} evaluated per LEAD_DRIFT_SPECS — identical
    clocks for the runner's verdicts and the verifier's recomputation."""
    from harness import candidates_forward as CF
    assets, bassets = forward_assets(), basis_assets()
    out = {}
    for lead, (kind, arg) in CF.LEAD_DRIFT_SPECS.items():
        if kind == "macro":
            out[lead] = harmony_daily()[["t", "c"]]
        elif kind == "hext":
            out[lead] = he_price_frame()[["t", "c"]]
        elif kind == "candles_dict":
            out[lead] = {a.upper(): candles_full(a, arg)[["t", "c"]]
                         for a in assets}
        elif kind == "candles":
            who, iv = arg
            out[lead] = candles_full(who, iv)[["t", "c"]]
        elif kind == "prem_dict":
            out[lead] = {a.upper(): prem_merged(a)[["t", "c"]]
                         for a in bassets}
        else:
            raise ValueError(f"unknown drift spec {kind}")
    return out
