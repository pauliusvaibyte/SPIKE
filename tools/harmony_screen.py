"""Systematic Harmony screen — declared two-stage discovery protocol.

Universe: every numeric column of upstream/harmony_data_store/
harmony_master_clean.parquet (~5.5k series). Signal = column value lagged
1 day (conservative: daily series dated t-1 are assumed known by day-t
open; FRED/BIS publication lag is a recorded caveat, not modeled).
Return = btc_price[t+H] / btc_price[t] - 1 (open-to-open, H=21d primary,
7d secondary).

Stage 1 DISCOVERY (<= 2024-12-31): Spearman IC per column, two-sided
p-value, Benjamini-Hochberg FDR at q=0.10 across the tested universe.
Stage 2 HOLDOUT (>= 2025-01-01): same-sign IC + one-sided p < 0.10 in the
predicted direction -> CONFIRMED lead for family declaration.

Output: reports/harmony_screen.md. This is a SCREEN — outputs feed future
declared hypotheses, never direct verdicts.

Run with the upstream repo venv (pyarrow):
  ../upstream/.venv/Scripts/python.exe tools/harmony_screen.py
"""
from __future__ import annotations

import os

from pathlib import Path

import numpy as np
import pandas as pd

SPIKE = Path(__file__).resolve().parents[1]
IND = Path(os.environ.get("UPSTREAM_DIR", "upstream"))
PARQ = IND / "harmony_data_store" / "harmony_master_clean.parquet"
OUT = SPIKE / "reports" / "harmony_screen.md"

HORIZONS = (21, 7)
DISCOVERY_END = pd.Timestamp("2024-12-31", tz="UTC")
HOLDOUT_START = pd.Timestamp("2025-01-01", tz="UTC")
MIN_OBS = 250
Q_FDR = 0.10
P_HOLDOUT = 0.10

PRICE_PAT = ("market-price", "pricebtc", "btc_price")


def _spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Spearman rho + two-sided p via t-approx (screen-level precision)."""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 60 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    r = float((rx * ry).mean())
    if abs(r) >= 1:
        return r, 0.0
    t = r * np.sqrt((n - 2) / (1 - r * r))
    from math import erfc, sqrt
    p = erfc(abs(t) / sqrt(2))          # normal approx of t dist, n large
    return r, p


def main() -> int:
    df = pd.read_parquet(PARQ)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    px_col = next((c for c in df.columns if "market-price" in c), None)
    if px_col is None:
        px_col = next(c for c in df.columns if "pricebtc" in c)
    px = df[px_col].astype(float)
    print(f"matrix {df.shape}, price col: {px_col}")

    cols = [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and c != px_col]
    print(f"numeric predictors: {len(cols)}")

    rows = []
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1.0           # ret over [t, t+h], open-to-open
        disc = df.index <= DISCOVERY_END
        hold = df.index >= HOLDOUT_START
        for c in cols:
            sig = df[c].shift(1).astype(float)  # lag-1: known by day-t open
            r_d, p_d = _spearman(sig[disc].to_numpy(), fwd[disc].to_numpy())
            if not np.isfinite(r_d):
                continue
            r_h, p_h = _spearman(sig[hold].to_numpy(), fwd[hold].to_numpy())
            n_d = int((np.isfinite(sig[disc]) & np.isfinite(fwd[disc])).sum())
            if n_d < MIN_OBS:
                continue
            rows.append({"col": c, "horizon": h, "ic_disc": r_d,
                         "p_disc": p_d, "n_disc": n_d,
                         "ic_hold": r_h, "p_hold": p_h})
        print(f"horizon {h}d: screened {len(cols)} -> {len(rows)} usable")

    res = pd.DataFrame(rows)
    if res.empty:
        OUT.write_text("# Harmony screen — no usable columns\n", encoding="utf-8")
        return 0

    # BH-FDR per horizon (universe = columns actually tested).
    # Step-up: largest rank k where p_(k) <= q*k/m (not a raw count —
    # non-contiguous satisfaction must not inflate the rejection set).
    res["fdr_pass"] = False
    for h in HORIZONS:
        sub = res["horizon"] == h
        p = res.loc[sub, "p_disc"].sort_values().to_numpy()
        m = len(p)
        thresh = Q_FDR * np.arange(1, m + 1) / m
        ok = np.nonzero(p <= thresh)[0]
        if len(ok):
            crit = float(p[ok.max()])
            res.loc[sub, "fdr_pass"] = res.loc[sub, "p_disc"] <= crit

    res["sign_ok"] = np.sign(res["ic_disc"]) == np.sign(res["ic_hold"])
    res["hold_ok"] = res["sign_ok"] & (res["p_hold"] < P_HOLDOUT)
    res["confirmed"] = res["fdr_pass"] & res["hold_ok"]
    res = res.sort_values("ic_disc", key=abs, ascending=False)

    L = ["# Harmony systematic screen — two-stage with holdout", "",
         (f"Universe: {len(cols)} numeric columns of harmony_master_clean "
          f"({df.index.min().date()} -> {df.index.max().date()})."),
         "Signal lagged 1d. Return open-to-open. Discovery <=2024-12-31,",
         (f"holdout >=2025-01-01. BH-FDR q={Q_FDR}; holdout needs same-sign "
          f"IC + p<{P_HOLDOUT}. Caveat: provider publication lag (FRED/BIS)"),
         "not modeled — treat confirmed FRED hits as leads requiring a",
         "lag-shifted re-declaration before any family is built.", ""]
    for h in HORIZONS:
        s = res[res.horizon == h]
        L.append(f"## horizon {h}d — tested {len(s)}, FDR-pass "
                 f"{int(s.fdr_pass.sum())}, CONFIRMED {int(s.confirmed.sum())}")
        L.append("")
        L.append("| column | ic_disc | p_disc | ic_hold | p_hold | status |")
        L.append("|---|---|---|---|---|---|")
        for _, r in s.head(40).iterrows():
            tag = ("**CONFIRMED**" if r.confirmed else
                   "fdr-pass,holdout-fail" if r.fdr_pass else
                   "holdout-only" if r.hold_ok else "")
            L.append(f"| {r.col} | {r.ic_disc:+.4f} | {r.p_disc:.2e} | "
                     f"{r.ic_hold:+.4f} | {r.p_hold:.2e} | {tag} |")
        L.append("")
    # ── factor view: confirmed columns are massively collinear (the same
    # underlying signal lives in thousands of provider variants). Collapse
    # to one representative per coarse key for interpretability.
    L.append("## Distinct factors among CONFIRMED (dedup by dataset-group)")
    L.append("")
    conf = res[res.confirmed].copy()
    conf["grp"] = conf["col"].str.extract(r"^([a-z]+_[a-z]+(?:_[a-z]+)?)")[0]
    rep = (conf.sort_values("ic_disc", key=abs, ascending=False)
               .groupby(["horizon", "grp"]).first().reset_index()
               .sort_values("ic_disc", key=abs, ascending=False))
    L.append("| horizon | group | representative | ic_disc | ic_hold | n_group_cols |")
    L.append("|---|---|---|---|---|---|")
    sizes = conf.groupby(["horizon", "grp"]).size().rename("k")
    for _, r in rep.head(50).iterrows():
        L.append(f"| {r.horizon} | {r.grp} | {r.col} | {r.ic_disc:+.3f} | "
                 f"{r.ic_hold:+.3f} | {sizes.loc[(r.horizon, r.grp)]} |")
    L.append("")
    L.append("Interpretation: groups sharing the same sign/mechanism are ONE "
             "factor, not independent leads. The dominant confirmed factor is "
             "valuation-level mean reversion (price/AUM/TVL levels high -> "
             "21d reversion). Independent leads require residualization "
             "against that factor before declaration.")
    OUT.write_text("\n".join(L), encoding="utf-8")
    res.to_csv(SPIKE / "reports" / "harmony_screen.csv", index=False)
    print(f"\nwrote {OUT.name} + csv; confirmed={int(res.confirmed.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
