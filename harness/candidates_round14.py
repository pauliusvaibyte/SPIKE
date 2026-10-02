"""Round-14 WATCH-autopsy derivatives — declared in manifest.yaml
`round14_batch` BEFORE execution (2026-09-28).

The episode-gate autopsy (a33 postmortem) showed which WATCH names are
nearest the bar and which legs carry the skill:

  oi_price_divergence   ep_wilson 0.426 is the ONLY failing gate
                        (DSR 1.00, placebo .029, t_skill +1.71 pass) —
                        and +224bp short-side vs -8bp long-side skill.
  equity_lead_btc_5d    same signature: +250bp short vs -30bp long,
                        ep_wilson 0.426, t_skill 1.59 (~at bar).
  funding_carry_24h     clears ep-gate + t_skill 2.40 but DSR .631
                        fails the 74-trial bar at Sharpe 0.22.

R14 tests whether the observable edges are the asymmetric/conditional
cores of those mechanisms. Each is a new declared trial — derivation
from autopsy evidence is exactly what multiple-testing accounting is
for; nothing here is declared post-hoc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness import candidates_round9 as C9
from harness.candidates_round4 import _daily_rows


# ── 1. SHORT-LEG ONLY: OI-divergence ─────────────────────────────────────

def oi_price_divergence_short(df: pd.DataFrame, pctile_win: int = 252,
                              horizon: int = 5, cooldown: int = 5
                              ) -> pd.DataFrame:
    """Short leg ONLY of C4.oi_price_divergence: OI-collapse (oi_chg <=
    rolling p10) + 5d price rise -> SHORT +5d. The parent emitted LONG
    on OI-surge+price-drop (squeeze fuel) — that leg carried -8bp of
    skill; dropped entirely. Same inputs and lag (oi_binance shift(2),
    bgeo OI publishes d+1)."""
    oi = df["oi_binance"].shift(2)
    px = df["btc_price"]
    oi_chg = (oi / oi.shift(5) - 1.0).to_numpy()
    ret5 = (px / px.shift(5) - 1.0).to_numpy()
    p10 = (pd.Series(oi_chg).rolling(pctile_win, min_periods=120)
           .quantile(0.10).to_numpy())
    sig = np.where((oi_chg <= p10) & (ret5 > 0), -1.0, 0.0).astype(float)
    ok = np.isfinite(oi_chg) & np.isfinite(ret5) & np.isfinite(p10)
    sig[~ok] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


# ── 2. SHORT-LEG ONLY: equity lead ───────────────────────────────────────

def equity_lead_btc_5d_short(df: pd.DataFrame, pctile_win: int = 252,
                             horizon: int = 5, cooldown: int = 5
                             ) -> pd.DataFrame:
    """Short leg ONLY of C6.equity_lead_btc_5d: fred_nasdaq 5d return
    <= -rolling-p90(|ret|) -> SHORT BTC +5d. Parent's long leg
    (nasdaq-up -> long BTC) carried -30bp skill; dropped. Same
    publish-lag: FRED prints ~21:00Z on day D, entry is ~00:00Z, so the
    series is ffill<=4 then shift(1) (provably-published close)."""
    nas = df["fred_nasdaq"].astype(float).ffill(limit=4).shift(1)
    ret5 = (nas / nas.shift(5) - 1.0).to_numpy()
    thr = (pd.Series(np.abs(ret5)).rolling(pctile_win, min_periods=120)
           .quantile(0.90).to_numpy())
    sig = np.where(ret5 <= -thr, -1.0, 0.0).astype(float)
    sig[~(np.isfinite(ret5) & np.isfinite(thr) & (thr > 0))] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


# ── 3. UNION EPISODE: either risk-off trigger shorts ─────────────────────

def riskoff_cluster_5d(df: pd.DataFrame, pctile_win: int = 252,
                       horizon: int = 5, cooldown: int = 5
                       ) -> pd.DataFrame:
    """Fires -1 on days where EITHER short trigger is active:
    (oi_binance 5d chg <= p10 AND btc 5d ret > 0) OR
    (fred_nasdaq 5d ret <= -p90(|ret|)).
    Union semantics: a missing input contributes no fires (NaN
    comparisons are False), so pre-2020 rows can still fire on the
    nasdaq leg — the union cannot know a missing leg would have fired,
    which is the honest reading. Tests whether the two risk-off
    mechanisms compound or collapse to one shared shock (the episode
    merger makes that visible in n_eff)."""
    oi = df["oi_binance"].shift(2)
    px = df["btc_price"]
    oi_chg = (oi / oi.shift(5) - 1.0).to_numpy()
    ret5px = (px / px.shift(5) - 1.0).to_numpy()
    p10 = (pd.Series(oi_chg).rolling(pctile_win, min_periods=120)
           .quantile(0.10).to_numpy())
    oi_short = (oi_chg <= p10) & (ret5px > 0)

    nas = df["fred_nasdaq"].astype(float).ffill(limit=4).shift(1)
    ret5n = (nas / nas.shift(5) - 1.0).to_numpy()
    thr = (pd.Series(np.abs(ret5n)).rolling(pctile_win, min_periods=120)
           .quantile(0.90).to_numpy())
    nas_short = (ret5n <= -thr) & np.isfinite(thr) & (thr > 0)

    sig = np.where(oi_short | nas_short, -1.0, 0.0).astype(float)
    return _daily_rows(df, sig, horizon, cooldown)


# ── 4. CONCENTRATED CARRY: extreme-funding only ──────────────────────────

def funding_carry_extreme(fund: pd.DataFrame, bars4h: pd.DataFrame,
                          asset: str, pct_win: int = 8760,
                          min_p: int = 2880, horizon_bars: int = 6,
                          cooldown: int = 24) -> pd.DataFrame:
    """C9.funding_carry_24h confined to outer-5% funding (q=0.05 instead
    of 0.10): the parent clears the episode gate and t_skill but its
    Sharpe 0.22 cannot survive the 74-trial DSR bar. Hypothesis: the
    carry edge concentrates in the extreme tail; a higher-Sharpe,
    lower-frequency variant either survives DSR or dies honestly.
    Roughly halves the episode count — declared with that cost known."""
    return C9.funding_carry_24h(fund, bars4h, asset,
                                pct_win=pct_win, min_p=min_p,
                                horizon_bars=horizon_bars,
                                cooldown=cooldown, q=0.05)
