"""Round-8 throughput batch — declared in manifest.yaml `round8_batch`
BEFORE execution. Ten hypotheses; mechanisms ex-ante reasoned, none mutate
killed families. taker_share_fade_1h bills to TOXIC-FLOW and
rsi2_connors_1d bills to MRV as family retests on deeper/different data.

Event contract unchanged. Entry convention: close of the eval bar ending
at/before the signal instant (causal); Binance-bucketed series are treated
as known at bucket end (+1h).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _events_to_df
from harness.candidates_round3 import _row
from harness.candidates_round6 import _emit
from harness.candidates_round6 import _entry_close  # noqa: F401  (re-export)

H1_MS = 3_600_000
H4_MS = 14_400_000


def _sig_events(bars: pd.DataFrame, sig: np.ndarray, horizon: int,
                cooldown: int, asset: str) -> pd.DataFrame:
    """sig aligned to bars rows; fire nonzero, eval close[i]->close[i+h]."""
    c = bars["c"].to_numpy(dtype=float)
    t = bars["t"]
    rows, last_i = [], -cooldown - 1
    for i in range(len(c)):
        d = sig[i]
        if not np.isfinite(d) or d == 0 or i - last_i <= cooldown:
            continue
        if not np.isfinite(c[i]) or c[i] <= 0:
            continue
        if (i + horizon > len(c) - 1 or not np.isfinite(c[i + horizon])
                or c[i + horizon] <= 0):
            rows.append(_row(t.iloc[i], asset, float(d), t, -1, None))
        else:
            fwd = c[i + horizon] / c[i] - 1.0
            rows.append(_row(t.iloc[i], asset, float(d), t, i + horizon, fwd))
        last_i = i
    return _events_to_df(rows)


# ── 1. VOL-SHOCK: outsized 4h move fades next bar ────────────────────────

def rv_spike_fade_4h(bars: pd.DataFrame, asset: str, vol_win: int = 42,
                   k: float = 2.5) -> pd.DataFrame:
    """|ret| >= k * RV(vol_win) measured on PRIOR bars -> fade next 4h."""
    c = bars["c"].to_numpy(dtype=float)
    t = bars["t"]
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    rv = pd.Series(ret).rolling(vol_win).std().shift(1).to_numpy()
    rows = []
    for i in range(2, len(c)):
        if not np.isfinite(rv[i]) or rv[i] <= 0:
            continue
        if not np.isfinite(ret[i]) or abs(ret[i]) < k * rv[i]:
            continue
        d = -1.0 if ret[i] > 0 else 1.0
        if i + 1 > len(c) - 1:
            rows.append(_row(t.iloc[i], asset, d, t, -1, None))
            continue
        fwd = (c[i + 1] / c[i] - 1.0
               if c[i] > 0 and np.isfinite(c[i + 1]) and c[i + 1] > 0
               else None)
        rows.append(_row(t.iloc[i], asset, d, t, i + 1, fwd,
                         {"shock_k": float(abs(ret[i]) / rv[i])}))
    return _events_to_df(rows)


# ── 2. VOLUME-CLIMAX: extreme volume + move -> fade ──────────────────────

def volume_climax_fade(bars: pd.DataFrame, asset: str, win: int = 2160,
                       horizon_bars: int = 1) -> pd.DataFrame:
    """v >= p99(v) AND |ret| >= p90(|ret|) jointly -> fade next 4h."""
    c = bars["c"].to_numpy(dtype=float)
    v = bars["v"].to_numpy(dtype=float)
    t = bars["t"]
    ret = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    p99v = pd.Series(v).rolling(win, min_periods=720).quantile(0.99).to_numpy()
    p90r = pd.Series(np.abs(ret)).rolling(win, min_periods=720).quantile(0.90).to_numpy()
    rows = []
    for i in range(1, len(c)):
        if not (np.isfinite(p99v[i]) and np.isfinite(p90r[i])):
            continue
        if not (v[i] >= p99v[i] and abs(ret[i]) >= p90r[i]):
            continue
        d = -1.0 if ret[i] > 0 else 1.0
        if i + horizon_bars > len(c) - 1:
            rows.append(_row(t.iloc[i], asset, d, t, -1, None))
            continue
        fwd = (c[i + horizon_bars] / c[i] - 1.0
               if c[i] > 0 and np.isfinite(c[i + horizon_bars])
               and c[i + horizon_bars] > 0 else None)
        rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars, fwd,
                         {"v_ratio": float(v[i] / p99v[i])}))
    return _events_to_df(rows)


# ── 3. FUNDING-FLIP: sign change drift ───────────────────────────────────

def funding_flip_momentum(fund: pd.DataFrame, bars4h: pd.DataFrame,
                          asset: str, horizon_bars: int = 6) -> pd.DataFrame:
    """rate sign change (both nonzero) -> drift with the NEW sign, +24h."""
    rate = fund["rate"].to_numpy(dtype=float)
    rows = []
    for i in range(1, len(fund)):
        a, b = rate[i - 1], rate[i]
        if not (np.isfinite(a) and np.isfinite(b)) or a == 0 or b == 0:
            continue
        if np.sign(a) == np.sign(b):
            continue
        ts = fund["t"].iloc[i]
        entry_i = _entry_close(bars4h, int(ts.timestamp() * 1000), H4_MS)
        _emit(rows, ts, asset, float(np.sign(b)), bars4h, entry_i,
              horizon_bars, {"rate": float(b)})
    return _events_to_df(rows)


# ── 4. SQUEEZE: trapped positioning unwind ───────────────────────────────

def trapped_positioning_squeeze(bars4h: pd.DataFrame, fund: pd.DataFrame,
                                asset: str, move: float = 0.03,
                                horizon_bars: int = 6,
                                cooldown: int = 6) -> pd.DataFrame:
    """price -3%/24h while funding>0 -> trapped longs -> SHORT; symmetric."""
    c = bars4h["c"].to_numpy(dtype=float)
    t = bars4h["t"]
    ret24 = np.concatenate([[np.nan] * 6, c[6:] / c[:-6] - 1.0])
    fr = fund[["t", "rate"]]
    # backward join with a cadence bound — without tolerance a funding
    # print stays "current" forever and stale rates leak into the signal.
    m = pd.merge_asof(bars4h[["t"]], fr, on="t", direction="backward",
                      tolerance=pd.Timedelta(hours=8))
    rate = m["rate"].to_numpy()
    rows, last_i = [], -cooldown - 1
    for i in range(6, len(c)):
        if i - last_i <= cooldown:
            continue
        if not (np.isfinite(ret24[i]) and np.isfinite(rate[i])) or rate[i] == 0:
            continue
        if ret24[i] <= -move and rate[i] > 0:
            d = -1.0          # trapped longs paying into a drop -> unwind
        elif ret24[i] >= move and rate[i] < 0:
            d = 1.0           # trapped shorts
        else:
            continue
        if i + horizon_bars > len(c) - 1:
            rows.append(_row(t.iloc[i], asset, d, t, -1, None))
        else:
            xi = i + horizon_bars
            fwd = (c[xi] / c[i] - 1.0
                   if c[i] > 0 and np.isfinite(c[xi]) and c[xi] > 0
                   else None)
            rows.append(_row(t.iloc[i], asset, d, t, xi, fwd,
                             {"ret24": float(ret24[i]), "rate": float(rate[i])}))
        last_i = i
    return _events_to_df(rows)


# ── 5. RESID-REV: idiosyncratic alt move reverts (daily) ─────────────────

def alt_resid_reversal_1d(btc_d: pd.DataFrame, alt_d: pd.DataFrame,
                        asset: str, beta_win: int = 90, pctile_win: int = 252,
                        horizon: int = 1, cooldown: int = 1) -> pd.DataFrame:
    """resid = alt_ret - beta*btc_ret; |resid| >= rolling p90 -> fade +1d."""
    m = alt_d[["t", "c"]].merge(btc_d[["t", "c"]], on="t",
                              suffixes=("_a", "_b")).sort_values("t")
    ra = m["c_a"].pct_change().to_numpy()
    rb = m["c_b"].pct_change().to_numpy()
    cov = pd.Series(ra).rolling(beta_win).cov(pd.Series(rb))
    var = pd.Series(rb).rolling(beta_win).var()
    beta = (cov / var).to_numpy()
    resid = ra - beta * rb
    thr = (pd.Series(np.abs(resid)).rolling(pctile_win, min_periods=120)
           .quantile(0.90).to_numpy())
    sig = np.where(resid >= thr, -1.0, np.where(resid <= -thr, 1.0, 0.0))
    sig = sig.astype(float)
    sig[~(np.isfinite(resid) & np.isfinite(thr))] = np.nan
    bars = m[["t", "c_a"]].rename(columns={"c_a": "c"}).reset_index(drop=True)
    return _sig_events(bars, sig, horizon, cooldown, asset)


# ── 6. CAPITULATION: deep drawdown bounce (daily) ────────────────────────

def drawdown_bounce_1d(bars: pd.DataFrame, asset: str, hi_win: int = 90,
                     dd: float = -0.15, horizon: int = 7,
                     cooldown: int = 7) -> pd.DataFrame:
    """close <= rolling-90d high * (1+dd) -> LONG, +7d."""
    c = bars["c"].to_numpy(dtype=float)
    hi = pd.Series(c).rolling(hi_win, min_periods=30).max().to_numpy()
    cond = (c / hi - 1.0) <= dd
    sig = np.where(cond, 1.0, 0.0)
    sig[~(np.isfinite(c) & np.isfinite(hi))] = np.nan
    return _sig_events(bars, sig.astype(float), horizon, cooldown, asset)


# ── 7. CAL-REBAL: month-end drift (daily) ────────────────────────────────

def month_end_drift_1d(bars: pd.DataFrame, asset: str, horizon: int = 2,
                       cooldown: int = 0) -> pd.DataFrame:
    """Last 2 calendar days of month -> LONG, +2d close-close."""
    t = bars["t"]
    days_to_eom = (t.dt.daysinmonth - t.dt.day).to_numpy()
    sig = np.where(days_to_eom <= 1, 1.0, 0.0)
    sig[~np.isfinite(bars["c"].to_numpy(dtype=float))] = np.nan
    return _sig_events(bars, sig.astype(float), horizon, cooldown, asset)


# ── 8. TOXIC-FLOW retest: taker share on 2y klines ───────────────────────

def taker_share_fade_1h(bn_klines: pd.DataFrame, hl_bars: pd.DataFrame,
                        asset: str, win: int = 2160, min_periods: int = 720,
                        horizon_bars: int = 1) -> pd.DataFrame:
    """share = taker_buy_vol/v; >=p95 -> SHORT next-1h, <=p5 -> LONG.
    Binance kline t is bucket START -> conservative entry at bucket end."""
    v = bn_klines["v"].to_numpy(dtype=float)
    tb = bn_klines["taker_buy_vol"].to_numpy(dtype=float)
    share = np.where(v > 0, tb / v, np.nan)
    s = pd.Series(share)
    hi = s.rolling(win, min_periods=min_periods).quantile(0.95).to_numpy()
    lo = s.rolling(win, min_periods=min_periods).quantile(0.05).to_numpy()
    rows = []
    for i in range(len(bn_klines)):
        if not np.isfinite(hi[i]) or not np.isfinite(share[i]):
            continue
        if share[i] >= hi[i]:
            d = -1.0
        elif share[i] <= lo[i]:
            d = 1.0
        else:
            continue
        ts = bn_klines["t"].iloc[i]
        ts_ms = int(ts.timestamp() * 1000) + H1_MS      # bucket end
        entry_i = _entry_close(hl_bars, ts_ms, H1_MS)
        _emit(rows, ts, asset, d, hl_bars, entry_i, horizon_bars,
              {"share": float(share[i])})
    return _events_to_df(rows)


# ── 9. MACRO-VOL: VIX spike -> BTC bounce (daily, harmony) ───────────────

def vix_spike_btc_long(df: pd.DataFrame, pctile_win: int = 252,
                       horizon: int = 5, cooldown: int = 5) -> pd.DataFrame:
    """fred_vix 5d change >= rolling p90 -> BTC LONG +5d."""
    # publish-lag: FRED's day-D VIX close prints ~21:00Z on day D, after
    # the modeled ~00:00Z entry — shift(1) reads the provably-published
    # D-1 value (A31 audit; same fix class as round-4 metric lags).
    vix = df["fred_vix"].astype(float).ffill(limit=4).shift(1)
    chg5 = (vix - vix.shift(5)).to_numpy()
    thr = (pd.Series(chg5).rolling(pctile_win, min_periods=120)
           .quantile(0.90).to_numpy())
    sig = np.where(chg5 >= thr, 1.0, 0.0).astype(float)
    sig[~(np.isfinite(chg5) & np.isfinite(thr))] = np.nan
    bars = pd.DataFrame({"t": df["t"], "c": df["btc_price"]})
    return _sig_events(bars, sig, horizon, cooldown, "BTC")


# ── 10. MRV retest: Connors RSI-2 (daily) ────────────────────────────────

def rsi2_connors_1d(bars: pd.DataFrame, asset: str, horizon: int = 1,
                  cooldown: int = 1) -> pd.DataFrame:
    """RSI(2) <=5 -> LONG / >=95 -> SHORT; eval +1d. Wilder-free 2-period
    mean of gains/losses."""
    c = bars["c"].to_numpy(dtype=float)
    d = np.diff(c)
    # inf/NaN deltas poison the 2-bar means (al=inf -> rsi=0 -> phantom
    # LONG); neutralize the corrupt bar rather than let it signal
    d = np.where(np.isfinite(d), d, 0.0)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    rsi = np.full(len(c), np.nan)
    for i in range(3, len(c)):
        ag = up[i - 2:i].mean()      # 2-period avg gain (bars i-1, i)
        al = dn[i - 2:i].mean()
        if al == 0:
            rsi[i] = 100.0 if ag > 0 else 50.0
        else:
            rsi[i] = 100.0 - 100.0 / (1.0 + ag / al)
    sig = np.where(rsi <= 5, 1.0, np.where(rsi >= 95, -1.0, 0.0))
    sig = sig.astype(float)
    sig[~np.isfinite(rsi)] = np.nan
    return _sig_events(bars, sig, horizon, cooldown, asset)
