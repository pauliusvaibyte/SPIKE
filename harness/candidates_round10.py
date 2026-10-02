"""Round-10 FLAGSHIP PORT — declared in manifest.yaml `round10_flagship_port`
BEFORE execution. Cross-validation of Sentinely's strongest retrospective
system (mega_screen 2026-09-07: base+N+V ~Sharpe 1.45, BTC daily, 15bps,
t+1) inside this falsification stack at our 10bp RT convention.

Specs ported verbatim from upstream/research/mega_screen_20260907.py —
no re-optimization:
  base  = 0.5*(px>SMA45) + 0.5*((px>SMA125)&(SMA125>SMA125.shift(5)))
  N     = 7d-sum(CM net flow USD)/(px*supply) > trailing-365d-prior p90
          -> position *= 0.5
  V     = mvrv > 2.5 -> position *= 0.75
  v60   = base * clip(0.60/RV30ann, 0, 1)   (diagnostic variant)

Event-frame bridge: one event per invested day, dir=sign(position),
gross=position*day_ret. Turnover charged 5bp per unit |dw| and allocated
inside episodes (entry leg to the entry day, exit leg to the last invested
day) so flat days carry no phantom events.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _events_to_df

FEE_PER_UNIT_BP = FEE_RT_BP / 2.0      # 5bp per side per unit of weight

HALVINGS = [("2009-01-03", 50.0), ("2012-11-28", 25.0), ("2016-07-09", 12.5),
            ("2020-05-11", 6.25), ("2024-04-20", 3.125)]


def supply_schedule(idx: pd.DatetimeIndex) -> pd.Series:
    """Verbatim port — fixed historical halving subsidy schedule."""
    bounds = np.array([pd.Timestamp(d) for d, _ in HALVINGS] + [idx.max() + pd.Timedelta(days=1)],
                      dtype="datetime64[ns]")
    days = np.maximum(0, (np.minimum(idx.values[:, None], bounds[None, 1:])
                          - bounds[None, :-1]).astype("timedelta64[D]").astype(int))
    subs = np.array([sub for _, sub in HALVINGS], dtype=float)
    return pd.Series((days * 144 * subs).sum(axis=1), index=idx)


# ── position constructors ────────────────────────────────────────────────

def w_base(px: pd.Series) -> pd.Series:
    t45 = (px > px.rolling(45).mean()).astype(float)
    s125 = px.rolling(125).mean()
    s = ((px > s125) & (s125 > s125.shift(5))).astype(float)
    return 0.5 * t45 + 0.5 * s


def w_v60(px: pd.Series) -> pd.Series:
    rv = px.pct_change().rolling(30).std() * np.sqrt(365)
    return w_base(px) * (0.60 / rv).clip(upper=1)


def stress_netflow(flow_net_usd: pd.Series, px: pd.Series) -> pd.Series:
    """N-leg stress flag: 7d net inflow / mcap > trailing-365d-prior p90."""
    sup = supply_schedule(px.index)
    mcap = px * sup.reindex(px.index).ffill()
    ncm = (flow_net_usd.rolling(7).sum()
           / mcap.reindex(flow_net_usd.index).ffill()).dropna()
    q = ncm.shift(1).rolling(365, min_periods=300).quantile(0.90)
    return (ncm > q).astype(float)


def w_composite(px: pd.Series, stress: pd.Series, mvrv: pd.Series) -> pd.Series:
    w = w_base(px)
    # publish-lag (A31 audit): w[i-1] executes at the ~00:00Z day-i close
    # but day-(i-1)-stamped mvrv/stress finalize ~03:20Z day i — the
    # unlagged damper leaks ~3.3h/day. The forward twin already shifts;
    # in-sample now matches it.
    st = stress.reindex(w.index).shift(1).fillna(0.0)
    mv = mvrv.reindex(w.index).ffill().shift(1)
    return (w * (1 - 0.5 * st) * (1 - 0.25 * (mv > 2.5).astype(float)))


# ── position series -> event frame ───────────────────────────────────────

def position_events(bars: pd.DataFrame, w: pd.Series, asset: str
                    ) -> pd.DataFrame:
    """bars: t/c daily. w: target weight indexed like bars. t+1 execution.
    Emits one event per invested day; turnover fees allocated inside
    episodes; hit = day gross > deadband."""
    px = bars.set_index("t")["c"].astype(float)
    px = px.where(px > 0)                          # zero/neg closes are
    # data holes, not prices — masking keeps the uncovered branch below
    # reachable instead of fabricating flat days via fillna(0).
    w = w.reindex(px.index)
    e = w.shift(1).fillna(0.0)                     # executed position
    ret = px.pct_change()
    d_e = e.diff().fillna(0.0)

    # allocate each transition's 5bp/unit cost to an invested day:
    # if the new position is nonzero charge that day, else charge the
    # previous (exit) day.
    fee = pd.Series(0.0, index=px.index)
    prev_i = None
    idx = list(px.index)
    for i, t in enumerate(idx):
        if d_e.iloc[i] == 0:
            continue
        if e.iloc[i] != 0:
            fee.iloc[i] += FEE_PER_UNIT_BP * abs(d_e.iloc[i])
        elif prev_i is not None:
            fee.iloc[prev_i] += FEE_PER_UNIT_BP * abs(d_e.iloc[i])
        if e.iloc[i] != 0:
            prev_i = i

    rows = []
    n = len(px)
    for i, t in enumerate(idx):
        ei = e.iloc[i]
        if not np.isfinite(ei) or ei == 0:
            continue
        r = ret.iloc[i]
        d = 1.0 if ei > 0 else -1.0
        if not np.isfinite(r):
            rows.append({"t": t, "asset": asset, "dir": d, "t_eval": t,
                         "ret_bp": float("nan"), "gross_bp": float("nan"),
                         "exit_reason": "uncovered"})
            continue
        g = ei * r * 1e4
        rows.append({"t": t, "asset": asset, "dir": d, "t_eval": t,
                     "ret_bp": g - float(fee.iloc[i]), "gross_bp": g,
                     "w": float(ei)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["hit"] = df["gross_bp"] > 1.0
    return df


# ── candidate entry points (boundary-invariance compatible: fn(df)) ──────

def flagship_base(bars: pd.DataFrame, asset: str) -> pd.DataFrame:
    px = bars.set_index("t")["c"].astype(float)
    return position_events(bars, w_base(px), asset)


def flagship_composite(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """df columns: t, c, mvrv, stress (precomputed exogenous flags merged
    onto the asset's daily price frame)."""
    px = df.set_index("t")["c"].astype(float)
    w = w_base(px) * (1 - 0.5 * df.set_index("t")["stress"]
                        .reindex(px.index).shift(1).fillna(0.0))
    mv = df.set_index("t")["mvrv"].reindex(px.index).ffill().shift(1)
    w = w * (1 - 0.25 * (mv > 2.5).astype(float))
    return position_events(df[["t", "c"]], w, asset)


def strategy_ret(bars: pd.DataFrame, w: pd.Series,
                 cost_per_unit: float = 0.0005) -> pd.Series:
    """Daily net return series — shared by strategy_stats and the DSR
    report path (which needs observations, not just summary stats)."""
    px = bars.set_index("t")["c"].astype(float)
    px = px.where(px > 0)                    # early zero-price rows would
    w = w.reindex(px.index)                  # otherwise give -inf returns
    e = w.shift(1).fillna(0.0)
    ret = px.pct_change()
    return (e * ret - e.diff().abs().fillna(0.0) * cost_per_unit).dropna()


def strategy_stats(bars: pd.DataFrame, w: pd.Series,
                   cost_per_unit: float = 0.0005) -> dict:
    """Continuous-series stats for the flagship comparison (Sentinely
    stats() equivalent at our cost convention)."""
    tr = strategy_ret(bars, w, cost_per_unit)
    if tr.empty or tr.std() == 0:
        return {"sharpe": 0.0, "cagr": 0.0, "maxdd": 0.0, "turnover": 0.0}
    eq = (1 + tr).cumprod()
    n = len(tr)
    px = bars.set_index("t")["c"].astype(float)
    e = w.reindex(px.index).shift(1).fillna(0.0)
    return {"sharpe": float(tr.mean() / tr.std() * np.sqrt(365)),
            "cagr": float(eq.iloc[-1] ** (365 / n) - 1),
            "maxdd": float((eq / eq.cummax() - 1).min()),
            "turnover": float(e.diff().abs().sum())}
