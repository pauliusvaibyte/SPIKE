"""Clean-room candidate reconstructions — implemented from the FROZEN specs in
manifest.yaml / bias_audit_2026-09-04.md, NOT imported from production code.
Production-code parity is checked separately (spec-vs-impl divergence is itself
a finding).

Each returns an events DataFrame:
    t (signal ts), asset, dir (+1/-1), t_eval (end of horizon), ret_bp (net),
    plus spec metadata.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEE_RT_BP = 10.0      # 5bp per side, round trip (registered convention)
DEADBAND_BP = 1.0     # par.61: |fwd| < 1bp counts as miss


# ── helpers ──────────────────────────────────────────────────────────────

def _fwd_ret(close: np.ndarray, i: int, bars: int) -> float | None:
    """Forward close-to-close return over `bars` bars from index i."""
    j = i + bars
    if (j >= len(close) or not np.isfinite(close[i]) or close[i] <= 0
            or not np.isfinite(close[j]) or close[j] <= 0):
        return None      # a nonpositive/NaN leg is a data hole -> uncovered
    return close[j] / close[i] - 1.0


def _wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - half, center + half)


def _events_to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["hit"] = df["gross_bp"] > DEADBAND_BP
    return df


def wilson_gate(events: pd.DataFrame) -> dict:
    """C179 gate: pooled N>=30 AND Wilson lower > 0.50 on directional hits.
    Only rows with a RESOLVED hit count — an uncovered/NaN-hit row counted
    as a miss dilutes the rate downward and can kill a stream on
    un-evaluated rows (2026-09-25 audit)."""
    if events.empty:
        return {"n": 0, "hit": float("nan"), "wilson_lo": float("nan"), "gate": "UNDERPOWERED"}
    # Emitters always write a bool hit, so hit.notna() never excludes
    # anything — exclude on the evaluable signal instead: ret_bp is NaN
    # exactly when a row is unresolved (and exit_reason='uncovered' when
    # the tag exists). Fail-closed either way.
    if "ret_bp" in events.columns:
        res = events[events["ret_bp"].notna()]
    elif "exit_reason" in events.columns:
        res = events[events["exit_reason"] != "uncovered"]
    else:
        res = events
    n = len(res)
    wins = int(res["hit"].sum())
    lo, hi = _wilson(wins, n)
    gate = "PASS" if (n >= 30 and lo > 0.50) else ("UNDERPOWERED" if n < 30 else "FAIL")
    return {"n": n, "hit": wins / n if n else float("nan"),
            "wilson_lo": lo, "wilson_hi": hi, "gate": gate}


# ── REAL candidates ──────────────────────────────────────────────────────

def tsmom_daily_14d(df_daily: pd.DataFrame, asset: str) -> pd.DataFrame:
    """TREND-2: sign(14d ret) with >=1% deadband predicts 7d fwd sign.
    Events spaced >=7d (first event after a gap)."""
    c = df_daily["c"].to_numpy(dtype=float)
    t = df_daily["t"]
    rows, last_i = [], -8
    for i in range(14, len(c)):
        # NaN comparisons are False in numpy — an all-NaN price column
        # would otherwise emit phantom uncovered rows for every bar
        if i - last_i < 7 or not np.isfinite(c[i - 14]) or c[i - 14] <= 0 \
                or not np.isfinite(c[i]) or c[i] <= 0:
            continue
        ret = c[i] / c[i - 14] - 1.0
        if abs(ret) < 0.01:
            continue
        fwd = _fwd_ret(c, i, 7)
        d = 1.0 if ret > 0 else -1.0
        g = d * fwd * 1e4 if fwd is not None else float("nan")
        # uncovered rows keep the t_eval==t convention — clamping to the
        # last bar stamped a fabricated holding window on tail rows
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": (t.iloc[i + 7] if fwd is not None
                                else t.iloc[i]),
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g,
                     "exit_reason": None if fwd is not None else "uncovered"})
        last_i = i
    return _events_to_df(rows)


def _exit_path(bars: pd.DataFrame, entry_i: int, direction: float,
               sl: float, tp: float, trail: float, max_bars: int) -> tuple[int, float, str]:
    """Shared SL/TP/trail/time-stop exit on OHLC bars. Returns (exit_i, gross_ret, reason).
    Conservative intrabar order: SL checked before TP within a bar."""
    entry = float(bars["c"].iloc[entry_i])
    # invalid entry (NaN/inf/<=0 close) must not fabricate exits —
    # return an uncovered marker: callers stamp t_eval=t.iloc[entry_i]
    if not np.isfinite(entry) or entry <= 0:
        return entry_i, float("nan"), "uncovered"
    peak = entry
    armed = False
    end = min(entry_i + max_bars, len(bars) - 1)
    for j in range(entry_i + 1, end + 1):
        h, l, cl = float(bars["h"].iloc[j]), float(bars["l"].iloc[j]), float(bars["c"].iloc[j])
        if direction > 0:
            adverse, favorable = l, h
        else:
            adverse, favorable = h, l
        worst = (adverse / entry - 1.0) * direction
        best = (favorable / entry - 1.0) * direction
        if worst <= -sl:
            return j, -sl, "sl"
        if best >= tp:
            armed = True
        peak = max(peak, favorable) if direction > 0 else min(peak, favorable)
        if armed:
            dd = (peak - cl) / peak * direction
            if dd >= trail:
                return j, (cl / entry - 1.0) * direction, "trail"
    j = end
    cl = float(bars["c"].iloc[j])
    return j, (cl / entry - 1.0) * direction, "time"


def _bar_index(bt: np.ndarray, ts_ms: int) -> int:
    return int(np.searchsorted(bt, ts_ms, side="left"))

def fra_momentum_p90_long(fund: pd.DataFrame, bars: pd.DataFrame,
                          pctile_win: int = 2160, horizon_bars: int = 96,
                          bar_ms: int = 900_000) -> pd.DataFrame:
    """FRA-CHALLENGER: funding pctile>=90 -> LONG; 4% SL / 8% TP+3% trail / 24h.
    `bars` is the eval frame (15m -> horizon_bars=96 covers 24h)."""
    pct = fund["rate"].rolling(pctile_win, min_periods=720).rank(pct=True)
    bt = bars["t"].astype("int64").to_numpy()
    rows, cooldown_until = [], pd.Timestamp("1970-01-01", tz="UTC")
    for i in range(len(fund)):
        if not np.isfinite(pct.iloc[i]) or pct.iloc[i] < 0.90:
            continue
        ts = fund["t"].iloc[i]
        if ts <= cooldown_until:
            continue
        ts_ms = int(ts.timestamp() * 1000)
        ei = _bar_index(bt, ts_ms)
        if ei >= len(bars):
            break
        if bt[ei] - ts_ms > bar_ms or ei + horizon_bars > len(bars) - 1:
            rows.append({"t": ts, "asset": "BTC", "dir": 1.0,
                         "t_eval": ts, "ret_bp": float("nan"),
                         "gross_bp": float("nan"), "exit_reason": "uncovered",
                         "pctile": float(pct.iloc[i])})
            continue
        xj, ret, reason = _exit_path(bars, ei, +1.0, 0.04, 0.08, 0.03,
                                     horizon_bars)
        rows.append({"t": ts, "asset": "BTC", "dir": 1.0,
                     "t_eval": bars["t"].iloc[xj],
                     "ret_bp": ret * 1e4 - FEE_RT_BP, "gross_bp": ret * 1e4,
                     "exit_reason": reason, "pctile": float(pct.iloc[i])})
        cooldown_until = bars["t"].iloc[xj]
    return _events_to_df(rows)


def fra_fade_p90_short(fund: pd.DataFrame, bars: pd.DataFrame, asset: str,
                     pctile_win: int = 2160, horizon_bars: int = 96,
                     bar_ms: int = 900_000) -> pd.DataFrame:
    """FRA condemned direction: pctile>=90 -> SHORT, same exit structure."""
    pct = fund["rate"].rolling(pctile_win, min_periods=720).rank(pct=True)
    bt = bars["t"].astype("int64").to_numpy()
    rows, cooldown_until = [], pd.Timestamp("1970-01-01", tz="UTC")
    for i in range(len(fund)):
        if not np.isfinite(pct.iloc[i]) or pct.iloc[i] < 0.90:
            continue
        ts = fund["t"].iloc[i]
        if ts <= cooldown_until:
            continue
        ts_ms = int(ts.timestamp() * 1000)
        ei = _bar_index(bt, ts_ms)
        if ei >= len(bars):
            break
        if bt[ei] - ts_ms > bar_ms or ei + horizon_bars > len(bars) - 1:
            rows.append({"t": ts, "asset": asset, "dir": -1.0,
                         "t_eval": ts, "ret_bp": float("nan"),
                         "gross_bp": float("nan"), "exit_reason": "uncovered",
                         "pctile": float(pct.iloc[i])})
            continue
        xj, ret, reason = _exit_path(bars, ei, -1.0, 0.04, 0.08, 0.03,
                                     horizon_bars)
        rows.append({"t": ts, "asset": asset, "dir": -1.0,
                     "t_eval": bars["t"].iloc[xj],
                     "ret_bp": ret * 1e4 - FEE_RT_BP, "gross_bp": ret * 1e4,
                     "exit_reason": reason, "pctile": float(pct.iloc[i])})
        cooldown_until = bars["t"].iloc[xj]
    return _events_to_df(rows)


def trend1_donchian_4h(df4h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """TREND-1: first cross of prior-24-bar Donchian predicts fwd-4h (1 bar) sign."""
    h = df4h["h"].to_numpy(); l = df4h["l"].to_numpy(); c = df4h["c"].to_numpy()
    t = df4h["t"]
    rows, prev_pos = [], 0
    for i in range(24, len(c)):
        ch_hi, ch_lo = h[i - 24:i].max(), l[i - 24:i].min()
        pos = 1 if c[i] > ch_hi else (-1 if c[i] < ch_lo else 0)
        if pos != 0 and prev_pos == 0:
            fwd = _fwd_ret(c, i, 1)
            g = pos * fwd * 1e4 if fwd is not None else float("nan")
            rows.append({"t": t.iloc[i], "asset": asset, "dir": float(pos),
                         "t_eval": (t.iloc[i + 1] if fwd is not None
                                    else t.iloc[i]),
                         "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                         "gross_bp": g,
                         "exit_reason": None if fwd is not None
                         else "uncovered"})
        prev_pos = pos
    return _events_to_df(rows)


def flush1_reversal_15m(df15m: pd.DataFrame, asset: str) -> pd.DataFrame:
    """FLUSH-1: wick/range>=0.60 & vol>=2x med20 -> predict reversal fwd-4h (16 bars)."""
    o = df15m["o"].to_numpy(); h = df15m["h"].to_numpy()
    l = df15m["l"].to_numpy(); c = df15m["c"].to_numpy(); v = df15m["v"].to_numpy()
    t = df15m["t"]
    rows, last_ev = [], -5
    for i in range(20, len(c)):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        lo_wick = min(o[i], c[i]) - l[i]
        hi_wick = h[i] - max(o[i], c[i])
        vmed = np.median(v[i - 20:i])
        spike = vmed > 0 and v[i] >= 2 * vmed
        if not spike:
            continue
        d = 0
        if lo_wick / rng >= 0.60:
            d = 1       # down-flush -> predict up
        elif hi_wick / rng >= 0.60:
            d = -1      # up-flush -> predict down
        if d == 0 or i - last_ev <= 4:
            continue
        fwd = _fwd_ret(c, i, 16)
        g = d * fwd * 1e4 if fwd is not None else float("nan")
        rows.append({"t": t.iloc[i], "asset": asset, "dir": float(d),
                     "t_eval": (t.iloc[i + 16] if fwd is not None
                                else t.iloc[i]),
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g,
                     "exit_reason": None if fwd is not None
                     else "uncovered"})
        last_ev = i
    return _events_to_df(rows)


def basis1_premium_p10(fund: pd.DataFrame, bars15m: pd.DataFrame,
                       asset: str, horizon_bars: int = 32,
                       bar_ms: int = 900_000) -> pd.DataFrame:
    """BASIS-1: premium<=trailing-720 p10 -> predict UP fwd-8h; anchors every 8th row."""
    if "premium" not in fund.columns:
        return _events_to_df([])
    p10 = fund["premium"].rolling(720, min_periods=720).quantile(0.10)
    bt = bars15m["t"].astype("int64").to_numpy(); bc = bars15m["c"].to_numpy()
    rows = []
    for i in range(720, len(fund), 8):          # non-overlapping anchors
        if not np.isfinite(p10.iloc[i]) \
                or not np.isfinite(fund["premium"].iloc[i]) \
                or fund["premium"].iloc[i] > p10.iloc[i]:
            continue
        ts = fund["t"].iloc[i]
        ts_ms = int(ts.timestamp() * 1000)
        ei = _bar_index(bt, ts_ms)
        if ei >= len(bc):
            break
        ok = (bt[ei] - ts_ms <= bar_ms
              and ei + horizon_bars <= len(bc) - 1 and bc[ei] > 0
              and np.isfinite(bc[ei + horizon_bars]))
        fwd = bc[ei + horizon_bars] / bc[ei] - 1.0 if ok else None
        g = fwd * 1e4 if fwd is not None else float("nan")
        rows.append({"t": ts, "asset": asset, "dir": 1.0,
                     "t_eval": bars15m["t"].iloc[min(ei + horizon_bars, len(bc) - 1)],
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g})
    return _events_to_df(rows)


def mrv_rsi_reversion_1h(df1h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """MRV approximate clean-room: RSI14(1h)<30 long / >70 short, fwd-4h."""
    c = df1h["c"].to_numpy(); t = df1h["t"]
    if len(c) < 16:                # prepend=c[0] IndexErrors on empty input
        return _events_to_df([])
    delta = np.diff(c, prepend=c[0])
    # inf/NaN deltas must not enter the EWM — a single bad tick would
    # poison al to +inf and pin rsi at 0 (phantom LONG) for every bar
    # after it
    delta = np.where(np.isfinite(delta), delta, 0.0)
    gain = np.where(delta > 0, delta, 0.0); loss = np.where(delta < 0, -delta, 0.0)
    ag = pd.Series(gain).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    al = pd.Series(loss).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    # al==0 (zero losses in window) means a monotone up-run -> RSI=100,
    # not 50; matches rsi2_connors_1d's convention in round8.
    rsi = np.where(al > 0, 100 - 100 / (1 + ag / al),
                   np.where(ag > 0, 100.0, 50.0))
    rows = []
    for i in range(15, len(c)):
        d = 1.0 if rsi[i] < 30 else (-1.0 if rsi[i] > 70 else 0.0)
        if d == 0:
            continue
        fwd = _fwd_ret(c, i, 4)
        g = d * fwd * 1e4 if fwd is not None else float("nan")
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": (t.iloc[i + 4] if fwd is not None
                                else t.iloc[i]),
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g,
                     "exit_reason": None if fwd is not None
                     else "uncovered"})
    return _events_to_df(rows)


def ofi_imbalance_l2(l2: pd.DataFrame, asset: str,
                     horizon_ms: int = 8 * 3_600_000) -> pd.DataFrame:
    """OFI on journal mids: |imb|>=0.05 -> predict direction fwd-8h.
    Horizon is TIME-based (first journal row >= t+8h) — row-count offsets
    silently change meaning when the journal cadence changes."""
    imb = l2["imbalance"].to_numpy(); mid = l2["mid"].to_numpy(); t = l2["t"]
    horizon = pd.Timedelta(milliseconds=horizon_ms)
    t_vals = t.to_numpy()
    rows = []
    last_ev_t = None
    for i in range(len(mid)):
        if not np.isfinite(imb[i]) or abs(imb[i]) < 0.05:
            continue
        if last_ev_t is not None and t.iloc[i] - last_ev_t <= horizon:
            continue
        j = int(t.searchsorted(t.iloc[i] + horizon, side="left"))
        ok = (j < len(mid) and mid[i] > 0
              and np.isfinite(mid[i]) and np.isfinite(mid[j]))
        fwd = mid[j] / mid[i] - 1.0 if ok else None
        d = 1.0 if imb[i] > 0 else -1.0
        g = d * fwd * 1e4 if fwd is not None else float("nan")
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": t.iloc[min(j, len(mid) - 1)],
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g})
        last_ev_t = t.iloc[i]
    return _events_to_df(rows)


# ── FIXTURES (validator calibration — labeled expectations) ──────────────

def null_random_entries(bars1h: pd.DataFrame, asset: str, n: int = 30,
                        seed: int = 7) -> pd.DataFrame:
    """Random-entry null with challenger exit structure."""
    rng = np.random.default_rng(seed)
    pool = np.arange(720, len(bars1h) - 24)
    if len(pool) == 0:
        return _events_to_df([])
    idx = rng.choice(pool, size=min(n, 30, len(pool)), replace=False)
    rows = []
    for ei in sorted(idx):
        xj, ret, reason = _exit_path(bars1h, int(ei), 1.0, 0.04, 0.08, 0.03, 24)
        rows.append({"t": bars1h["t"].iloc[int(ei)], "asset": asset, "dir": 1.0,
                     "t_eval": bars1h["t"].iloc[xj],
                     "ret_bp": ret * 1e4 - FEE_RT_BP, "gross_bp": ret * 1e4,
                     "exit_reason": reason})
    return _events_to_df(rows)


def null_shifted_tsmom(df_daily: pd.DataFrame, asset: str, shift: int = 14) -> pd.DataFrame:
    """TSMOM signal shifted forward `shift` days — decorrelated control."""
    ev = tsmom_daily_14d(df_daily, asset)
    if ev.empty:
        return ev
    c = df_daily["c"].to_numpy(); t = df_daily["t"]
    rows = []
    for _, r in ev.iterrows():
        i = int(df_daily["t"].searchsorted(r["t"])) + shift
        if i >= len(c) - 7:
            continue
        fwd = _fwd_ret(c, i, 7)
        if fwd is None:
            continue
        rows.append({"t": t.iloc[i], "asset": asset, "dir": r["dir"],
                     "t_eval": t.iloc[i + 7],
                     "ret_bp": r["dir"] * fwd * 1e4 - FEE_RT_BP,
                     "gross_bp": r["dir"] * fwd * 1e4})
    return _events_to_df(rows)


def leak_tsmom_nextclose(df_daily: pd.DataFrame, asset: str) -> pd.DataFrame:
    """DELIBERATE LEAK: 14d lookback includes close[t+1] — tomorrow's data in
    today's decision. Must be caught by prefix-invariance + implausibility."""
    c = df_daily["c"].to_numpy(); t = df_daily["t"]
    rows, last_i = [], -8
    for i in range(14, len(c) - 1):
        if i - last_i < 7:
            continue
        ret = c[i + 1] / c[i - 13] - 1.0   # LEAK: uses t+1 close
        if abs(ret) < 0.01:
            continue
        fwd = _fwd_ret(c, i, 7)
        d = 1.0 if ret > 0 else -1.0
        g = d * fwd * 1e4 if fwd is not None else float("nan")
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": t.iloc[min(i + 7, len(c) - 1)],
                     "ret_bp": g - FEE_RT_BP if fwd is not None else float("nan"),
                     "gross_bp": g})
        last_i = i
    return _events_to_df(rows)


def planted_weak_edge(df_daily: pd.DataFrame, asset: str,
                      p_correct: float = 0.58, seed: int = 11) -> pd.DataFrame:
    """PLANTED: signal = true 7d-fwd sign with prob p_correct, else random.
    A weak-but-real edge the validator must retain (not kill)."""
    c = df_daily["c"].to_numpy(); t = df_daily["t"]
    rng = np.random.default_rng(seed)
    rows, last_i = [], -8
    for i in range(14, len(c) - 7):
        if i - last_i < 7:
            continue
        fwd = _fwd_ret(c, i, 7)
        if fwd is None:
            break
        true_sign = 1.0 if fwd > 0 else -1.0
        d = true_sign if rng.random() < p_correct else -true_sign
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": t.iloc[i + 7],
                     "ret_bp": d * fwd * 1e4 - FEE_RT_BP,
                     "gross_bp": d * fwd * 1e4})
        last_i = i
    return _events_to_df(rows)
