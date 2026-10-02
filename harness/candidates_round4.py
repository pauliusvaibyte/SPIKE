"""Round-4 clean-room candidates — daily-frequency macro/on-chain families
declared in manifest.yaml `round4_candidates` BEFORE execution.

Daily bars: events keyed to the daily close; eval = close-to-close over
horizon_days. Same event contract; uncovered tail events emit NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _events_to_df


def _daily_rows(df: pd.DataFrame, sig: np.ndarray, horizon: int,
                cooldown: int, asset: str = "BTC") -> pd.DataFrame:
    """sig: +1/-1/0/NaN positionally aligned to df rows. Fires on nonzero
    sig with cooldown spacing; eval = close[i] -> close[i+horizon]."""
    c = df["btc_price"].to_numpy(); t = df["t"]
    rows, last_i = [], -cooldown - 1
    for i in range(len(df)):
        d = sig[i]
        if not np.isfinite(d) or d == 0 or i - last_i <= cooldown:
            continue
        if not np.isfinite(c[i]) or c[i] <= 0:
            continue
        if (i + horizon > len(c) - 1 or not np.isfinite(c[i + horizon])
                or c[i + horizon] <= 0):
            rows.append({"t": t.iloc[i], "asset": asset, "dir": float(d),
                         "t_eval": t.iloc[i], "ret_bp": float("nan"),
                         "gross_bp": float("nan"), "exit_reason": "uncovered"})
        else:
            g = float(d) * (c[i + horizon] / c[i] - 1.0) * 1e4
            rows.append({"t": t.iloc[i], "asset": asset, "dir": float(d),
                         "t_eval": t.iloc[i + horizon],
                         "ret_bp": g - FEE_RT_BP, "gross_bp": g})
        last_i = i
    return _events_to_df(rows)


def onchain_mvrv_regime(df: pd.DataFrame, pctile_win: int = 730,
                        horizon: int = 30, cooldown: int = 30) -> pd.DataFrame:
    """MVRV rolling-730d percentile extremes -> contrarian 30d.
    Publish-lag (2026-09-25 audit): capmvrvcur[D] finalizes ~03:20Z D+1,
    but the eval entry is the ~00:00Z day-i blockchain price — at that
    instant only rows <= i-2 are public, so the signal lags 2 days."""
    pct = df["mvrv"].shift(2).rolling(pctile_win, min_periods=365).rank(pct=True).to_numpy()
    sig = np.where(pct >= 0.90, -1.0, np.where(pct <= 0.10, 1.0, 0.0))
    sig[~np.isfinite(pct)] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


def fng_extreme_sentiment(df: pd.DataFrame, fear: int = 10, greed: int = 90,
                          horizon: int = 7, cooldown: int = 7) -> pd.DataFrame:
    """Fear<=10 LONG / greed>=90 SHORT, 7d forward.
    alternative.me publishes the day-D value ~00:0xZ on day D — minutes
    after the modeled ~00:00Z entry, so lag 1 day (publish-lag audit)."""
    v = df["fng"].shift(1).to_numpy()
    sig = np.where(v <= fear, 1.0, np.where(v >= greed, -1.0, 0.0)).astype(float)
    sig[~np.isfinite(v)] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


def etf_flow_5d(df: pd.DataFrame, pctile_win: int = 252,
                horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """5d net ETF flow >= rolling-252d p90 LONG / <=p10 SHORT, 5d fwd."""
    # Farside publishes day-D flows overnight (~04Z D+1) — at the ~00:00Z
    # day-i entry only <= i-2 is public (publish-lag audit)
    raw = df["etf_flow_usd_m"].shift(2)
    era = raw.notna().cummax()                       # ETF era: after first obs
    flow = raw.where(~era, raw.fillna(0.0))          # weekends = zero flow;
    # pre-launch stays NaN (nonexistence is not zero)
    flow5 = flow.rolling(5, min_periods=5).sum()
    p90 = flow5.rolling(pctile_win, min_periods=120).quantile(0.90).to_numpy()
    p10 = flow5.rolling(pctile_win, min_periods=120).quantile(0.10).to_numpy()
    f5 = flow5.to_numpy()
    sig = np.where(f5 >= p90, 1.0, np.where(f5 <= p10, -1.0, 0.0)).astype(float)
    sig[~(np.isfinite(p90) & np.isfinite(f5))] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


def cal_weekend_drift(df: pd.DataFrame) -> pd.DataFrame:
    """Long Fri->Mon (3 bars) every week — weekend liquidity absence drift."""
    dow = df["t"].dt.dayofweek.to_numpy()
    sig = np.where(dow == 4, 1.0, 0.0).astype(float)
    sig[~np.isfinite(df["btc_price"].to_numpy())] = np.nan
    return _daily_rows(df, sig, horizon=3, cooldown=3)


def oi_price_divergence(df: pd.DataFrame, pctile_win: int = 252,
                        horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """OI-surge + price-drop -> LONG squeeze fuel; OI-collapse + price-rise
    -> SHORT deleveraging. 5d forward."""
    # bgeo OI row D publishes ~12Z D+1 — at the ~00:00Z day-i entry only
    # <= i-2 is public (publish-lag audit)
    oi = df["oi_binance"].shift(2)
    px = df["btc_price"]
    oi_chg = (oi / oi.shift(5) - 1.0).to_numpy()
    ret5 = (px / px.shift(5) - 1.0).to_numpy()
    oi_s = pd.Series(oi_chg)
    p90 = oi_s.rolling(pctile_win, min_periods=120).quantile(0.90).to_numpy()
    p10 = oi_s.rolling(pctile_win, min_periods=120).quantile(0.10).to_numpy()
    sig = np.where((oi_chg >= p90) & (ret5 < 0), 1.0,
                   np.where((oi_chg <= p10) & (ret5 > 0), -1.0, 0.0)).astype(float)
    ok = np.isfinite(oi_chg) & np.isfinite(ret5) & np.isfinite(p90) & np.isfinite(p10)
    sig[~ok] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)
