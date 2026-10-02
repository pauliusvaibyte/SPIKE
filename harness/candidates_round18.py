"""Round-18 candidates — DVOL (Deribit options vol index) family.

Declared pre-execution in manifest `round18_dvol`. Both specs are billed
to MACRO-VOL (crypto-native port of round-8 vix_spike_btc_long).

Input frame is the INNER JOIN of Deribit DVOL daily and BTC daily candles
on day timestamp: {t, dvol_c, btc_c}. DVOL close has no publication lag
(unlike FRED VIX), so signals read the same-bar close — the repo's
standard close-close convention.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates_round8 import _sig_events


def merged_dvol_btc(dvol: pd.DataFrame, btc: pd.DataFrame) -> pd.DataFrame:
    """Inner-join DVOL daily close onto BTC daily close by day timestamp."""
    d = dvol[["t", "c"]].rename(columns={"c": "dvol_c"})
    b = btc[["t", "c"]].rename(columns={"c": "btc_c"})
    out = d.merge(b, on="t", how="inner").sort_values("t").reset_index(drop=True)
    return out


def dvol_spike_btc_long(df: pd.DataFrame, pctile_win: int = 252,
                        horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """DVOL 5d change >= rolling-252d p90 -> BTC LONG +5d (port of vix spec)."""
    chg5 = (df["dvol_c"].astype(float) - df["dvol_c"].astype(float).shift(5))
    thr = chg5.rolling(pctile_win, min_periods=120).quantile(0.90)
    sig = np.where(chg5 >= thr, 1.0, 0.0).astype(float)
    sig[~(np.isfinite(chg5) & np.isfinite(thr))] = np.nan
    bars = pd.DataFrame({"t": df["t"], "c": df["btc_c"]})
    return _sig_events(bars, sig, horizon, cooldown, "BTC")


def dvol_level_long(df: pd.DataFrame, pctile_win: int = 252,
                    horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """DVOL close >= rolling-252d p95 -> BTC LONG +5d (sustained-stress)."""
    lvl = df["dvol_c"].astype(float)
    thr = lvl.rolling(pctile_win, min_periods=120).quantile(0.95)
    sig = np.where(lvl >= thr, 1.0, 0.0).astype(float)
    sig[~(np.isfinite(lvl) & np.isfinite(thr))] = np.nan
    bars = pd.DataFrame({"t": df["t"], "c": df["btc_c"]})
    return _sig_events(bars, sig, horizon, cooldown, "BTC")
