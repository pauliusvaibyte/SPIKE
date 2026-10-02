"""Round-9 mechanism-diverse batch — declared in manifest.yaml
`round9_batch` BEFORE execution. Ten hypotheses, deliberately NOT
momentum-themed: carry income, session timing, breadth, cross-asset
rotation, vol-regime expansion, thin-volume divergence.

Event contract unchanged. Entry convention: close of the eval bar ending
at/before the signal instant (causal).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _events_to_df
from harness.candidates_round3 import _row
from harness.candidates_round6 import _emit, _entry_close
from harness.candidates_round8 import _sig_events

H4_MS = 14_400_000


# ── 1. VOL-REGIME: compression resolves into continuing expansion ────────

def compression_breakout_4h(bars: pd.DataFrame, asset: str,
                            bw_win: int = 20, pct_win: int = 2160,
                            rv_win: int = 42, k: float = 2.0) -> pd.DataFrame:
    """BB-width <= p15 at bar i-1 AND |ret_i| >= k*RV42 -> dir=sign(ret_i)."""
    c = bars["c"].to_numpy(dtype=float)
    s = pd.Series(c)
    ma = s.rolling(bw_win).mean()
    bw = (4.0 * s.rolling(bw_win).std() / ma).to_numpy()
    p15 = (pd.Series(bw).rolling(pct_win, min_periods=720)
           .quantile(0.15).to_numpy())
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    rv = pd.Series(ret).rolling(rv_win).std().shift(1).to_numpy()
    sig = np.full(len(c), np.nan)
    for i in range(1, len(c)):
        if not (np.isfinite(bw[i - 1]) and np.isfinite(p15[i - 1])
                and np.isfinite(rv[i]) and rv[i] > 0):
            continue
        if bw[i - 1] <= p15[i - 1] and abs(ret[i]) >= k * rv[i]:
            sig[i] = 1.0 if ret[i] > 0 else -1.0
    return _sig_events(bars, sig, horizon=6, cooldown=6, asset=asset)


# ── 2. CARRY: collect extreme funding for 3 epochs ───────────────────────

def funding_carry_24h(fund: pd.DataFrame, bars4h: pd.DataFrame, asset: str,
                      pct_win: int = 8760, min_p: int = 2880,
                      horizon_bars: int = 6, cooldown: int = 24,
                      q: float = 0.10) -> pd.DataFrame:
    """rate >= rolling p(1-q) -> SHORT (collect); <= p(q) -> LONG
    (collect). gross = dir*px_ret + (-dir)*sum(next 24 realized rates).
    q is the outer-quantile cutoff (default 0.10 = p90/p10; the R14
    concentrated variant calls with q=0.05).

    NOTE: HL funding prints HOURLY (not 8h epochs) — 24 prints = 24h of
    carry; pct_win 8760 ~ 1y of prints; cooldown 24 = non-overlapping days.
    (v1 mistakenly treated prints as 8h epochs: 3 prints ~= 3h carry.)"""
    rate = fund["rate"].to_numpy(dtype=float)
    hi = (pd.Series(rate).rolling(pct_win, min_periods=min_p)
          .quantile(1.0 - q).to_numpy())
    lo = (pd.Series(rate).rolling(pct_win, min_periods=min_p)
          .quantile(q).to_numpy())
    bt = bars4h["t"].astype("int64").to_numpy()
    bc = bars4h["c"].to_numpy(dtype=float)
    rows, last_i = [], -cooldown - 1
    for i in range(len(fund)):
        if i - last_i <= cooldown:
            continue
        r = rate[i]
        if not (np.isfinite(r) and np.isfinite(hi[i])
                and np.isfinite(lo[i]) and hi[i] > lo[i]):
            continue
        if r >= hi[i]:
            d = -1.0
        elif r <= lo[i]:
            d = 1.0
        else:
            continue
        ts = fund["t"].iloc[i]
        ei = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
        # carry needs the FULL intended 24 hourly prints (~1d of wall time);
        # nansum silently zero-filled missing prints and let tail signals
        # drop instead of emitting uncovered rows.
        nxt = rate[i + 1:i + 25]
        carry_ok = (len(nxt) == 24 and np.isfinite(nxt).all()
                    and i + 24 < len(fund)
                    and (fund["t"].iloc[i + 24] - ts)
                        <= pd.Timedelta(hours=26))
        xi = ei + horizon_bars
        if (ei < 0 or xi > len(bc) - 1 or not carry_ok
                or not np.isfinite(bc[ei]) or bc[ei] <= 0
                or not np.isfinite(bc[xi]) or bc[xi] <= 0):
            rows.append(_row(ts, asset, d, bars4h["t"], -1, None))
        else:
            carry = -d * float(np.sum(nxt)) * 1e4
            px = d * (bc[xi] / bc[ei] - 1.0) * 1e4
            g = px + carry
            rows.append({"t": ts, "asset": asset, "dir": d,
                         "t_eval": bars4h["t"].iloc[xi],
                         "ret_bp": g - FEE_RT_BP, "gross_bp": g,
                         "carry_bp": float(carry)})
        last_i = i
    df = _events_to_df(rows)
    if not df.empty and "gross_bp" in df.columns:
        df["hit"] = df["gross_bp"] > 1.0
    return df


# ── 3-5. SESSION: intraday segment drift / open-bar persistence ──────────

def _session_drift(bars: pd.DataFrame, asset: str, sig_hour: int,
                   horizon: int) -> pd.DataFrame:
    h = bars["t"].dt.hour.to_numpy()
    sig = np.where(h == sig_hour, 1.0, 0.0).astype(float)
    sig[~np.isfinite(bars["c"].to_numpy(dtype=float))] = np.nan
    return _sig_events(bars, sig, horizon=horizon, cooldown=0, asset=asset)


def us_session_drift(bars4h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """Long only 12:00-24:00 UTC daily: signal on 08:00-start bar (fires at
    its 12:00 close), exit close of 20:00 bar."""
    return _session_drift(bars4h, asset, sig_hour=8, horizon=3)


def asia_session_drift(bars4h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """Long only 00:00-08:00 UTC daily: signal on 20:00-start bar, exit
    close of 04:00 bar."""
    return _session_drift(bars4h, asset, sig_hour=20, horizon=2)


def us_session_momentum(bars4h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """The 12:00-UTC-start bar's own return -> dir=sign(ret) for +24h."""
    c = bars4h["c"].to_numpy(dtype=float)
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    h = bars4h["t"].dt.hour.to_numpy()
    sig = np.where((h == 12) & np.isfinite(ret), np.sign(ret), 0.0)
    return _sig_events(bars4h, sig.astype(float), horizon=6, cooldown=0,
                       asset=asset)


# ── 6-7. BREADTH: basket unanimity persists / washout bounces ────────────

def breadth_panel(d1: dict[str, pd.DataFrame]) -> pd.Series:
    """Fraction of assets with positive daily ret, indexed by day ts."""
    rets = {}
    for a, b in d1.items():
        rets[a] = b.set_index("t")["c"].pct_change()
    panel = pd.DataFrame(rets)
    return (panel > 0).sum(axis=1) / panel.shape[1]


def breadth_thrust_1d(bars: pd.DataFrame, breadth: pd.Series,
                     asset: str) -> pd.DataFrame:
    """breadth >= 6/7 on day d -> LONG asset d -> d+1."""
    b = bars["t"].map(breadth).to_numpy()
    sig = np.where(b >= 6.0 / 7.0 - 1e-9, 1.0, 0.0).astype(float)
    sig[~np.isfinite(b)] = np.nan
    return _sig_events(bars, sig, horizon=1, cooldown=0, asset=asset)


def breadth_washout_1d(bars: pd.DataFrame, breadth: pd.Series,
                       asset: str) -> pd.DataFrame:
    """breadth <= 1/7 on day d -> LONG asset d -> d+1."""
    b = bars["t"].map(breadth).to_numpy()
    sig = np.where(b <= 1.0 / 7.0 + 1e-9, 1.0, 0.0).astype(float)
    sig[~np.isfinite(b)] = np.nan
    return _sig_events(bars, sig, horizon=1, cooldown=0, asset=asset)


# ── 8. VOLUME-CLIMAX retest: thin-volume divergence fades ────────────────

def volume_divergence_fade_1d(bars: pd.DataFrame, asset: str,
                              pct_win: int = 252, vol_win: int = 20
                              ) -> pd.DataFrame:
    """ret >= p70 AND v <= 0.5*vol20 -> SHORT; ret <= p30 AND thin -> LONG."""
    c = bars["c"].to_numpy(dtype=float)
    v = bars["v"].to_numpy(dtype=float)
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    r = pd.Series(ret)
    p70 = r.rolling(pct_win, min_periods=120).quantile(0.70).to_numpy()
    p30 = r.rolling(pct_win, min_periods=120).quantile(0.30).to_numpy()
    vol20 = pd.Series(v).rolling(vol_win, min_periods=10).mean().to_numpy()
    thin = np.isfinite(v) & np.isfinite(vol20) & (v <= 0.5 * vol20)
    sig = np.full(len(c), 0.0)
    sig[thin & (ret >= p70)] = -1.0
    sig[thin & (ret <= p30)] = 1.0
    sig[~(np.isfinite(ret) & np.isfinite(p70))] = np.nan
    return _sig_events(bars, sig, horizon=1, cooldown=1, asset=asset)


# ── 9-10. ROTATION: BTC-alt catch-up / weekly loser bounce ───────────────

def btc_alt_rotation_3d(btc_d: pd.DataFrame, alt_d: pd.DataFrame,
                        asset: str, pct_win: int = 252) -> pd.DataFrame:
    """spread = btc7d - alt7d; |spread| >= p90 -> dir=sign(spread) on alt."""
    m = alt_d[["t", "c"]].merge(btc_d[["t", "c"]], on="t",
                              suffixes=("_a", "_b")).sort_values("t")
    ra = m["c_a"].pct_change(7).to_numpy()
    rb = m["c_b"].pct_change(7).to_numpy()
    spread = rb - ra
    thr = (pd.Series(np.abs(spread)).rolling(pct_win, min_periods=120)
           .quantile(0.90).to_numpy())
    sig = np.where(spread >= thr, 1.0,
                   np.where(spread <= -thr, -1.0, 0.0)).astype(float)
    sig[~(np.isfinite(spread) & np.isfinite(thr))] = np.nan
    bars = m[["t", "c_a"]].rename(columns={"c_a": "c"}).reset_index(drop=True)
    return _sig_events(bars, sig, horizon=3, cooldown=3, asset=asset)


def weekly_loser_bounce_1d(d1: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Rank 7d rets across assets daily: worst -> LONG +7d, best -> SHORT
    +7d. Per-asset cooldown 7d. Single pooled leg."""
    closes = {a: b.set_index("t")["c"] for a, b in d1.items()}
    panel = pd.DataFrame(closes).sort_index()
    r7 = panel.pct_change(7)
    rows = []
    last = {a: -8 for a in d1}
    tvals = panel.index
    for i in range(7, len(panel)):
        rr = r7.iloc[i]
        if rr.isna().all():
            continue
        worst, best = rr.idxmin(), rr.idxmax()
        if not (np.isfinite(rr[worst]) and np.isfinite(rr[best])):
            continue
        for a, d in ((worst, 1.0), (best, -1.0)):
            if i - last[a] <= 7:
                continue
            c0 = panel[a].iloc[i]
            if not (np.isfinite(c0) and c0 > 0):
                continue
            if (i + 7 > len(panel) - 1
                    or not np.isfinite(panel[a].iloc[i + 7])
                    or panel[a].iloc[i + 7] <= 0):
                rows.append({"t": tvals[i], "asset": a.upper(), "dir": d,
                             "t_eval": tvals[i], "ret_bp": float("nan"),
                             "gross_bp": float("nan"),
                             "exit_reason": "uncovered"})
            else:
                g = d * (panel[a].iloc[i + 7] / c0 - 1.0) * 1e4
                rows.append({"t": tvals[i], "asset": a.upper(), "dir": d,
                             "t_eval": tvals[i + 7],
                             "ret_bp": g - FEE_RT_BP, "gross_bp": g,
                             "rank7d": float(rr[a])})
            last[a] = i
    df = _events_to_df(rows)
    if not df.empty and "gross_bp" in df.columns:
        df["hit"] = df["gross_bp"] > 1.0
    return df
