"""Round-3 clean-room candidates — new-mechanism families declared in
manifest.yaml `round3_candidates` BEFORE execution.

Same event contract as harness/candidates.py: rows carry t, asset, dir,
t_eval, ret_bp (net), gross_bp; unevaluable events (signal exists but no
eval bar within coverage) emit NaN ret fields with exit_reason="uncovered"
so event identity is preserved and metrics drop them downstream.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _bar_index, _events_to_df

H1_MS = 3_600_000
H4_MS = 14_400_000
H8_MS = 28_800_000


def _row(ts, asset, d, bars_t, exit_i, fwd, extra=None):
    if exit_i < 0 or fwd is None:
        r = {"t": ts, "asset": asset, "dir": d, "t_eval": ts,
             "ret_bp": float("nan"), "gross_bp": float("nan"),
             "exit_reason": "uncovered"}
    else:
        g = d * fwd * 1e4
        r = {"t": ts, "asset": asset, "dir": d,
             "t_eval": bars_t.iloc[exit_i] if hasattr(bars_t, "iloc") else ts,
             "ret_bp": g - FEE_RT_BP, "gross_bp": g}
    if extra:
        r.update(extra)
    return r


def settle1_funding_drift(fund: pd.DataFrame, bars1h: pd.DataFrame,
                          asset: str, mag_win: int = 2160,
                          horizon_bars: int = 1,
                          bar_ms: int = H1_MS) -> pd.DataFrame:
    """SETTLE-1: |rate| >= rolling-median(|rate|) -> -sign(rate) over the
    settlement hour (entry = close of the bar ending at the settle ts)."""
    mag = fund["rate"].abs()
    thr = mag.rolling(mag_win, min_periods=720).median()
    bt = bars1h["t"].astype("int64").to_numpy(); bc = bars1h["c"].to_numpy()
    rows = []
    for i in range(len(fund)):
        # NaN rate/mag must not fall through to the else-long branch:
        # mag NaN < thr -> False would emit a LONG on a missing print.
        if (not np.isfinite(thr.iloc[i]) or not np.isfinite(mag.iloc[i])
                or not np.isfinite(fund["rate"].iloc[i])
                or mag.iloc[i] < thr.iloc[i]):
            continue
        ts = fund["t"].iloc[i]
        ts_ms = int(ts.timestamp() * 1000)
        # funding stamps carry sub-second write latency (T+~73ms); the settle
        # instant is the hour floor. entry = close of bar ending at T.
        # t_eval is the eval bar's CLOSE (start + bar_ms): with event t =
        # print time (mid-bucket), bucket-start would record t_eval < t.
        ts_h = ts_ms - (ts_ms % H1_MS)
        ei = _bar_index(bt, ts_h)
        entry_i = ei - 1 if ei < len(bt) and abs(bt[ei] - ts_h) <= bar_ms else -1
        if not np.isfinite(fund["rate"].iloc[i]):
            continue          # NaN rate is no signal — emit nothing
        d = -1.0 if fund["rate"].iloc[i] > 0 else 1.0
        if entry_i < 0 or entry_i + horizon_bars > len(bc) - 1:
            rows.append(_row(ts, asset, d, bars1h["t"], -1, None))
            continue
        xi = entry_i + horizon_bars
        fwd = (bc[xi] / bc[entry_i] - 1.0
               if bc[entry_i] > 0 and np.isfinite(bc[xi]) and bc[xi] > 0
               else None)
        te = bars1h["t"].iloc[xi] + pd.Timedelta(
            milliseconds=bar_ms)
        if fwd is None:
            rows.append(_row(ts, asset, d, bars1h["t"], -1, None))
            continue
        g = d * fwd * 1e4
        rows.append({"t": ts, "asset": asset, "dir": d, "t_eval": te,
                     "ret_bp": g - FEE_RT_BP, "gross_bp": g})
    return _events_to_df(rows)


def xvenue_funding_disloc(hl_fund: pd.DataFrame, bn_fund: pd.DataFrame,
                          bars4h: pd.DataFrame, asset: str,
                          pctile_win: int = 540, horizon_bars: int = 2,
                          bar_ms: int = H4_MS) -> pd.DataFrame:
    """XV-DISLOC: at each Binance 8h epoch T, hl8h = sum HL rates in
    (T-8h, T]; fire |hl8h - bn| >= rolling p90 -> dir = -sign(spread)."""
    ft = hl_fund["t"].astype("int64").to_numpy()
    fr = hl_fund["rate"].to_numpy()
    ep_t, ep_last, spread = [], [], []
    for _, r in bn_fund.iterrows():
        t_ms = int(r["t"].timestamp() * 1000)
        lo, hi = np.searchsorted(ft, t_ms - H8_MS, side="right"), np.searchsorted(ft, t_ms, side="right")
        if hi - lo < 8:                      # incomplete HL window -> skip
            continue
        ep_t.append(t_ms)
        ep_last.append(int(ft[hi - 1]))
        spread.append(float(fr[lo:hi].sum()) - float(r["rate"]))
    if not ep_t:
        return _events_to_df([])
    ep_t = np.array(ep_t); ep_last = np.array(ep_last); spread = np.array(spread)
    thr = pd.Series(np.abs(spread)).rolling(pctile_win, min_periods=180).quantile(0.90).to_numpy()
    bt = bars4h["t"].astype("int64").to_numpy(); bc = bars4h["c"].to_numpy()
    rows = []
    for k in range(len(ep_t)):
        if (not np.isfinite(thr[k]) or thr[k] <= 0
                or not np.isfinite(spread[k])
                or abs(spread[k]) < thr[k]):
            continue
        # BN fundingTime carries +ms jitter; floor the epoch to the bar
        # grid or _bar_index slips one bar forward and entry lands a full
        # 4h late (A23).
        ts_ms = ep_t[k] - (ep_t[k] % bar_ms)
        # event t = last HL funding print inside the window (the causal
        # decision instant — and a real src row so boundary_invariance can
        # truncate on it); eval stays anchored at the epoch boundary.
        ts = pd.Timestamp(int(ep_last[k]), unit="ms", tz="UTC")
        ei = _bar_index(bt, ts_ms)
        entry_i = ei - 1 if (ei < len(bt) and ei > 0
                             and abs(bt[ei] - ts_ms) <= bar_ms) else -1
        d = -1.0 if spread[k] > 0 else 1.0
        if entry_i < 0 or entry_i + horizon_bars > len(bc) - 1:
            rows.append(_row(ts, asset, d, bars4h["t"], -1, None))
            continue
        xi = entry_i + horizon_bars
        fwd = (bc[xi] / bc[entry_i] - 1.0
               if bc[entry_i] > 0 and np.isfinite(bc[xi]) and bc[xi] > 0
               else None)
        rows.append(_row(ts, asset, d, bars4h["t"], xi, fwd,
                         {"spread": float(spread[k])}))
    return _events_to_df(rows)


def _aligned(hl_bars: pd.DataFrame, bn_bars: pd.DataFrame):
    """Inner-join two bar frames on timestamp; returns (t, hl_c, bn_c)."""
    m = hl_bars[["t", "c"]].merge(bn_bars[["t", "c"]], on="t", suffixes=("_hl", "_bn"))
    return (m["t"], m["c_hl"].to_numpy(), m["c_bn"].to_numpy())


def xvenue_leadlag_1h(bn_bars: pd.DataFrame, hl_bars: pd.DataFrame,
                      asset: str, pctile_win: int = 2160,
                      horizon_bars: int = 1) -> pd.DataFrame:
    """XV-LEADLAG: large Binance 1h move -> same-direction HL next-1h move."""
    t, hc, bc = _aligned(hl_bars, bn_bars)
    rows = []
    bn_ret = bc[1:] / bc[:-1] - 1.0
    thr = pd.Series(np.abs(bn_ret)).rolling(pctile_win, min_periods=720).quantile(0.90).to_numpy()
    for i in range(1, len(hc)):
        k = i - 1                          # bn_ret index
        if (not np.isfinite(thr[k]) or thr[k] <= 0
                or not np.isfinite(bn_ret[k])
                or abs(bn_ret[k]) < thr[k]):
            continue
        if i + horizon_bars > len(hc) - 1:
            rows.append(_row(t.iloc[i], asset, np.sign(bn_ret[k]), t, -1, None))
            continue
        xi = i + horizon_bars
        fwd = (hc[xi] / hc[i] - 1.0
               if hc[i] > 0 and np.isfinite(hc[xi]) and hc[xi] > 0 else None)
        d = 1.0 if bn_ret[k] > 0 else -1.0
        rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars, fwd,
                         {"bn_ret_bp": float(bn_ret[k]) * 1e4}))
    return _events_to_df(rows)


def xvenue_basis_converge(bn_bars: pd.DataFrame, hl_bars: pd.DataFrame,
                          asset: str, pctile_win: int = 2160,
                          horizon_bars: int = 4) -> pd.DataFrame:
    """XV-BASIS: |HL-BN price basis| >= rolling p99 -> convergence trade."""
    t, hc, bc = _aligned(hl_bars, bn_bars)
    rows = []
    basis = (hc / bc - 1.0) * 1e4
    thr = pd.Series(np.abs(basis)).rolling(pctile_win, min_periods=720).quantile(0.99).to_numpy()
    for i in range(len(hc)):
        if (not np.isfinite(thr[i]) or thr[i] <= 0
                or not np.isfinite(basis[i])
                or abs(basis[i]) < thr[i]):
            continue
        if i + horizon_bars > len(hc) - 1:
            rows.append(_row(t.iloc[i], asset, -np.sign(basis[i]), t, -1, None))
            continue
        xi = i + horizon_bars
        fwd = (hc[xi] / hc[i] - 1.0
               if hc[i] > 0 and np.isfinite(hc[xi]) and hc[xi] > 0 else None)
        d = -1.0 if basis[i] > 0 else 1.0
        rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars, fwd,
                         {"basis_bp": float(basis[i])}))
    return _events_to_df(rows)
