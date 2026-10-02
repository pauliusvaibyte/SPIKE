"""Round-6 clean-room candidates — declared in manifest.yaml
`round6_candidates` BEFORE execution on the expanded 7-asset universe
(BTC, SOL, ETH, XRP, DOGE, AVAX, LINK).

Same event contract as earlier rounds: rows carry t, asset, dir, t_eval,
ret_bp (net of FEE_RT_BP), gross_bp; unevaluable events emit NaN with
exit_reason="uncovered". Entry convention follows round 3: the close of
the eval bar ending at/before the signal instant (causal).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _bar_index, _events_to_df
from harness.candidates_round3 import _row
from harness.candidates_round4 import _daily_rows

H1_MS = 3_600_000
H4_MS = 14_400_000


def _entry_close(bars: pd.DataFrame, ts_ms: int, bar_ms: int):
    """Index of the first bar whose CLOSE is at/after ts_ms, or -1.

    Signals carry +ms write latency, so ts is floored to the second.
    Bar-aligned ts -> the bar ending at ts (entry = close at the signal
    instant); mid-bar ts -> the containing bar (entry = first close after
    the signal, up to bar_ms stale but always causal). The old
    floor-then-minus-one form entered up to bar_ms BEFORE the signal for
    non-aligned timestamps — hourly funding prints on the 4h grid leaked
    up to 3h of pre-signal drift into ret_bp (A23)."""
    bt = bars["t"].astype("int64").to_numpy()
    ts = ts_ms - (ts_ms % 1000)
    ei = int(np.searchsorted(bt, ts - bar_ms, side="left"))
    # The bar must contain or end at ts (bt[ei] <= ts). Without this bound a
    # signal predating coverage returns ei=0 and pins the event onto the
    # first bars of the file — ~16k phantom "covered" rows measured months
    # after their signals (A24). Gap/before-coverage -> uncovered.
    if ei < len(bt) and bt[ei] <= ts:
        return ei
    return -1


def _emit(rows, ts, asset, d, bars, entry_i, horizon_bars, extra=None):
    bc = bars["c"].to_numpy()
    if entry_i < 0 or entry_i + horizon_bars > len(bc) - 1:
        rows.append(_row(ts, asset, d, bars["t"], -1, None, extra))
        return
    xi = entry_i + horizon_bars
    fwd = (bc[xi] / bc[entry_i] - 1.0
           if bc[entry_i] > 0 and np.isfinite(bc[xi]) and bc[xi] > 0
           else None)
    rows.append(_row(ts, asset, d, bars["t"], xi, fwd, extra))


# ── 1. XASSET-LEADLAG: BTC leads alts ────────────────────────────────────

def xasset_btc_leads_alts(btc_bars: pd.DataFrame, alt_bars: pd.DataFrame,
                        asset: str, pctile_win: int = 2160,
                        horizon_bars: int = 1) -> pd.DataFrame:
    """BTC 1h |ret| >= rolling p90 -> alt same-direction next-1h."""
    m = alt_bars[["t", "c"]].merge(btc_bars[["t", "c"]], on="t",
                                  suffixes=("_alt", "_btc"))
    t, ac, bc = m["t"], m["c_alt"].to_numpy(), m["c_btc"].to_numpy()
    bret = np.concatenate([[np.nan], bc[1:] / bc[:-1] - 1.0])
    thr = (pd.Series(np.abs(bret)).rolling(pctile_win, min_periods=720)
           .quantile(0.90).to_numpy())
    rows = []
    for i in range(1, len(ac)):
        if (not np.isfinite(thr[i]) or thr[i] <= 0
                or not np.isfinite(bret[i]) or abs(bret[i]) < thr[i]):
            continue
        d = 1.0 if bret[i] > 0 else -1.0
        if i + horizon_bars > len(ac) - 1:
            rows.append(_row(t.iloc[i], asset, d, t, -1, None))
            continue
        fwd = (ac[i + horizon_bars] / ac[i] - 1.0
               if (ac[i] > 0 and np.isfinite(ac[i])
                   and np.isfinite(ac[i + horizon_bars])) else None)
        rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars, fwd,
                         {"btc_ret_bp": float(bret[i]) * 1e4}))
    return _events_to_df(rows)


# ── 2. XASSET-FUNDING-RV: funding vs basket median ───────────────────────

def funding_xasset_rv(fund: pd.DataFrame, med_others: pd.Series,
                    bars4h: pd.DataFrame, asset: str, pctile_win: int = 2160,
                    horizon_bars: int = 6, cooldown: int = 6) -> pd.DataFrame:
    """spread = rate - median(other coins' rate at t); |spread| >= rolling
    p90 -> dir=-sign(spread); eval +24h on 4h bars."""
    med = fund[["t"]].merge(med_others, on="t", how="left")["med"]
    spread = (fund["rate"] - med).to_numpy()
    thr = (pd.Series(np.abs(spread)).rolling(pctile_win, min_periods=720)
           .quantile(0.90).to_numpy())
    rows, last_i = [], -cooldown - 1
    for i in range(len(fund)):
        if (not np.isfinite(thr[i]) or thr[i] <= 0
                or not np.isfinite(spread[i])
                or abs(spread[i]) < thr[i] or i - last_i <= cooldown):
            continue
        ts = fund["t"].iloc[i]
        entry_i = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
        _emit(rows, ts, asset, -float(np.sign(spread[i])), bars4h, entry_i,
              horizon_bars, {"spread": float(spread[i])})
        last_i = i
    return _events_to_df(rows)


# ── 3. MARK-DISLOC: HL premium sample extremes ───────────────────────────

def hl_premium_disloc(fund: pd.DataFrame, bars4h: pd.DataFrame, asset: str,
                      pctile_win: int = 2160, horizon_bars: int = 2,
                      cooldown: int = 2) -> pd.DataFrame:
    """|premium| >= rolling p90 -> dir=-sign(premium); eval +8h."""
    prem = fund["premium"].to_numpy(dtype=float)
    thr = (pd.Series(np.abs(prem)).rolling(pctile_win, min_periods=720)
           .quantile(0.90).to_numpy())
    rows, last_i = [], -cooldown - 1
    for i in range(len(fund)):
        if (not np.isfinite(thr[i]) or thr[i] <= 0
                or not np.isfinite(prem[i])
                or abs(prem[i]) < thr[i] or i - last_i <= cooldown):
            continue
        ts = fund["t"].iloc[i]
        entry_i = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
        _emit(rows, ts, asset, -float(np.sign(prem[i])), bars4h, entry_i,
              horizon_bars, {"premium": float(prem[i])})
        last_i = i
    return _events_to_df(rows)


# ── 4. FUNDING-DURATION: same-sign streak continuation ───────────────────

def funding_run_persistence(fund: pd.DataFrame, bars4h: pd.DataFrame,
                            asset: str, min_streak: int = 24,
                            horizon_bars: int = 6) -> pd.DataFrame:
    """Same-sign streak >= min_streak hourly prints -> at streak end,
    dir=sign(streak); eval +24h. Zero/NaN rate breaks a streak."""
    rate = fund["rate"].to_numpy(dtype=float)
    sign = np.where(np.isfinite(rate), np.sign(rate), 0.0)
    rows = []
    n = len(fund)
    i = 0
    while i < n:
        if sign[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < n and sign[j + 1] == sign[i]:
            j += 1
        streak_len = j - i + 1
        if streak_len >= min_streak:
            ts = fund["t"].iloc[j]
            entry_i = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
            _emit(rows, ts, asset, float(sign[i]), bars4h, entry_i,
                  horizon_bars, {"streak": float(streak_len)})
        i = j + 1
    return _events_to_df(rows)


# ── 5. MICRO-BOUNCE: 15m serial reversion ────────────────────────────────

def serialcorr_15m_bounce(bars15m: pd.DataFrame, asset: str,
                        pctile_win: int = 2880, min_periods: int = 960,
                        horizon_bars: int = 1) -> pd.DataFrame:
    """15m |ret| >= rolling p90 -> next-15m opposite direction."""
    c = bars15m["c"].to_numpy()
    t = bars15m["t"]
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    thr = (pd.Series(np.abs(ret)).rolling(pctile_win, min_periods=min_periods)
           .quantile(0.90).to_numpy())
    rows = []
    for i in range(1, len(c)):
        if (not np.isfinite(thr[i]) or thr[i] <= 0
                or not np.isfinite(ret[i]) or abs(ret[i]) < thr[i]):
            continue
        d = -1.0 if ret[i] > 0 else 1.0
        if i + horizon_bars > len(c) - 1:
            rows.append(_row(t.iloc[i], asset, d, t, -1, None))
            continue
        fwd = (c[i + horizon_bars] / c[i] - 1.0
               if (c[i] > 0 and np.isfinite(c[i])
                   and np.isfinite(c[i + horizon_bars])) else None)
        rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars, fwd,
                         {"sig_ret_bp": float(ret[i]) * 1e4}))
    return _events_to_df(rows)


# ── 6. MACRO-BETA: Nasdaq leads BTC (daily) ──────────────────────────────

def equity_lead_btc_5d(df: pd.DataFrame, pctile_win: int = 252,
                       horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """|fred_nasdaq 5d ret| >= rolling-252d p90 -> BTC same-dir next 5d.
    Nasdaq is weekday-only on the daily grid; ffill <=4 rows carries the
    close over weekends/holidays (convention note: gaps >4d stay NaN)."""
    # publish-lag: FRED's day-D equity close prints ~21:00Z on day D —
    # ~21h AFTER the modeled ~00:00Z day-D entry. shift(1) puts the
    # signal on the provably-published D-1 close (mirror of the round-4
    # lag convention; A31 audit).
    nas = df["fred_nasdaq"].astype(float).ffill(limit=4).shift(1)
    ret5 = (nas / nas.shift(5) - 1.0).to_numpy()
    thr = (pd.Series(np.abs(ret5)).rolling(pctile_win, min_periods=120)
           .quantile(0.90).to_numpy())
    sig = np.where(ret5 >= thr, 1.0, np.where(ret5 <= -thr, -1.0, 0.0))
    sig = sig.astype(float)
    # thr==0 (flat/ffill-degenerate window) would fire on ret5==0 —
    # a zero-move is not a signal
    sig[~(np.isfinite(ret5) & np.isfinite(thr) & (thr > 0))] = np.nan
    return _daily_rows(df, sig, horizon, cooldown)


# ── 7. OI-CROWD: OI surge + extreme funding -> fade ──────────────────────

def oi_crowding_fade(oi: pd.DataFrame, bn_fund: pd.DataFrame,
                    bars4h: pd.DataFrame, asset: str, oi_win: int = 480,
                    fund_win: int = 2160, horizon_bars: int = 6) -> pd.DataFrame:
    """oi_chg24h >= rolling p90 AND |bn_rate| >= its rolling p90 jointly ->
    dir=-sign(rate); eval +24h on 4h bars."""
    oi_chg = (oi["oi"] / oi["oi"].shift(24) - 1.0).to_numpy()
    thr_oi = (pd.Series(oi_chg).rolling(oi_win, min_periods=120)
              .quantile(0.90).to_numpy())
    thr_f = (bn_fund["rate"].abs().rolling(fund_win, min_periods=720)
             .quantile(0.90))
    ff = pd.DataFrame({"t": bn_fund["t"], "rate": bn_fund["rate"],
                       "thr": thr_f})
    # BN funding cadence is 8h — a print older than that is stale, not a
    # valid join key (untoleranced merge_asof propagates it indefinitely).
    m = pd.merge_asof(oi[["t"]], ff, on="t", direction="backward",
                      tolerance=pd.Timedelta(hours=8))
    rows = []
    for i in range(len(oi)):
        if (not np.isfinite(thr_oi[i]) or not np.isfinite(oi_chg[i])
                or oi_chg[i] < thr_oi[i]):
            continue
        r = m["rate"].iloc[i]; tf = m["thr"].iloc[i]
        if not (np.isfinite(r) and np.isfinite(tf) and tf > 0) \
                or abs(r) < tf:
            continue
        ts = oi["t"].iloc[i]
        entry_i = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
        _emit(rows, ts, asset, -float(np.sign(r)), bars4h, entry_i,
              horizon_bars, {"oi_chg": float(oi_chg[i])})
    return _events_to_df(rows)


# ── 8. TOXIC-FLOW: taker buy/sell ratio extremes fade ────────────────────

def taker_toxicity_1h(taker: pd.DataFrame, bars1h: pd.DataFrame, asset: str,
                      win: int = 480, min_periods: int = 240,
                      horizon_bars: int = 1) -> pd.DataFrame:
    """ratio >= rolling p95 -> SHORT next-1h; <= p5 -> LONG.
    Conservative timing: the 1h bucket is treated as known at ts+1h, so
    entry = close of the bar ending at ts+H1."""
    ratio = taker["ratio"].to_numpy(dtype=float)
    hi = (pd.Series(ratio).rolling(win, min_periods=min_periods)
          .quantile(0.95).to_numpy())
    lo = (pd.Series(ratio).rolling(win, min_periods=min_periods)
          .quantile(0.05).to_numpy())
    rows = []
    for i in range(len(taker)):
        if not np.isfinite(hi[i]):
            continue
        if ratio[i] >= hi[i]:
            d = -1.0
        elif ratio[i] <= lo[i]:
            d = 1.0
        else:
            continue
        ts = taker["t"].iloc[i]
        ts_ms = int(ts.timestamp() * 1000) + H1_MS   # bucket end
        entry_i = _entry_close(bars1h, ts_ms, H1_MS)
        _emit(rows, ts, asset, d, bars1h, entry_i, horizon_bars,
              {"ratio": float(ratio[i])})
    return _events_to_df(rows)
