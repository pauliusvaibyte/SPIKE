"""Phase -1 Round 19 — §87 exit-path faithfulness bounds.

Declared pre-execution in manifest `round19_exitpath_check` (BILLED to FRA).
The round-2 r3000 kill already used the exact spec payout via _exit_path
(4% SL / +8% TP+3% trail / 24h, SL-before-TP intrabar = conservative).
Residual ambiguity is only intra-bar ordering on 4h OHLC: run the SAME
trigger events under both orderings — SL-first (pessimistic, as round-2)
and TP-first (optimistic). If net <= 0 under BOTH, the kill transfers to
the spec's payout shape outright; only a straddle leaves the live stream
as the arbiter.

Run: .venv/Scripts/python.exe run_round19.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import data as D
from harness import falsify as F

REPORT = Path(__file__).resolve().parent / "reports" / "report_round19.md"
BAR_4H = 14_400_000


def _exit_path_opt(bars, entry_i, direction, sl, tp, trail, max_bars):
    """TP-first variant of C._exit_path — the optimistic intrabar bound."""
    entry = float(bars["c"].iloc[entry_i])
    if not np.isfinite(entry) or entry <= 0:
        return entry_i, float("nan"), "uncovered"
    peak, armed = entry, False
    end = min(entry_i + max_bars, len(bars) - 1)
    for j in range(entry_i + 1, end + 1):
        h, l, cl = (float(bars[k].iloc[j]) for k in ("h", "l", "c"))
        if direction > 0:
            adverse, favorable = l, h
        else:
            adverse, favorable = h, l
        best = (favorable / entry - 1.0) * direction
        worst = (adverse / entry - 1.0) * direction
        if best >= tp:
            armed = True
        peak = max(peak, favorable) if direction > 0 else min(peak, favorable)
        if armed:
            dd = (peak - cl) / peak * direction
            if dd >= trail:
                return j, (cl / entry - 1.0) * direction, "trail"
            if worst <= -sl:
                return j, -sl, "sl"
        elif worst <= -sl:
            return j, -sl, "sl"
    j = end
    cl = float(bars["c"].iloc[j])
    return j, (cl / entry - 1.0) * direction, "time"


def emit(fund, bars, exit_fn, pctile_win=3000, horizon_bars=6,
         bar_ms=BAR_4H):
    """Same trigger loop as C.fra_momentum_p90_long, pluggable exit fn."""
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
        ei = C._bar_index(bt, ts_ms)
        if ei >= len(bars):
            break
        if bt[ei] - ts_ms > bar_ms or ei + horizon_bars > len(bars) - 1:
            rows.append({"t": ts, "asset": "BTC", "dir": 1.0,
                         "t_eval": ts, "ret_bp": float("nan"),
                         "gross_bp": float("nan"), "exit_reason": "uncovered",
                         "pctile": float(pct.iloc[i])})
            continue
        xj, ret, reason = exit_fn(bars, ei, +1.0, 0.04, 0.08, 0.03,
                                  horizon_bars)
        rows.append({"t": ts, "asset": "BTC", "dir": 1.0,
                     "t_eval": bars["t"].iloc[xj],
                     "ret_bp": ret * 1e4 - C.FEE_RT_BP,
                     "gross_bp": ret * 1e4,
                     "exit_reason": reason, "pctile": float(pct.iloc[i])})
        cooldown_until = bars["t"].iloc[xj]
    return C._events_to_df(rows)


def _stats(ev: pd.DataFrame) -> dict:
    cov = ev.dropna(subset=["ret_bp"])
    reasons = cov["exit_reason"].value_counts().to_dict()
    wil = C.wilson_gate(cov)
    ret = F.events_to_daily_returns(cov)
    ss = F.sharpe_stats(ret, n_trials=53)
    return {"n": len(cov), "hit": wil["hit"], "net": float(cov["ret_bp"].sum()),
            "sharpe": ss.get("sharpe", float("nan")), "dsr": ss.get("dsr", float("nan")),
            "reasons": reasons}


def main() -> int:
    fund = D.funding_full("btc")
    d4h = D.candles_full("btc", "4h")
    fund_t = fund[fund["t"] <= d4h["t"].iloc[-1]].reset_index(drop=True)
    pes = emit(fund_t, d4h, C._exit_path)          # SL-first (round-2 convention)
    opt = emit(fund_t, d4h, _exit_path_opt)        # TP-first (optimistic bound)
    saved = pd.read_csv(REPORT.parent / "events_extended"
                        / "fra_momentum_p90_long_r3000.csv")
    recon = "MATCH" if (len(saved.dropna(subset=["ret_bp"])) ==
                        len(pes.dropna(subset=["ret_bp"]))) else "CHECK-N"

    lines = []
    w = lines.append
    w("# Phase -1 Round 19 — §87 exit-path faithfulness bounds")
    w("")
    w("Declared in manifest `round19_exitpath_check` (BILLED to FRA).")
    w("Round-2's r3000 kill already used the spec payout (4%/8%/3%/24h);")
    w("this bounds the residual 4h intra-bar ordering ambiguity.")
    w(f"reconcile vs saved r3000 events (covered n): {recon}")
    w("")
    for label, ev in (("SL-first (round-2 convention)", pes),
                      ("TP-first (optimistic bound)", opt)):
        s = _stats(ev)
        w(f"## {label}")
        w(f"n={s['n']}  hit={s['hit']:.3f}  net={s['net']:+.0f}bp  "
          f"Sharpe={s['sharpe']:+.2f}  DSR={s['dsr']:.3f}")
        w(f"exits: {s['reasons']}")
        w("")
    s_p, s_o = _stats(pes), _stats(opt)
    if s_p["net"] <= 0 and s_o["net"] <= 0:
        verd = ("TRANSFERS — net <= 0 under both intra-bar orderings; the "
                "§87 thesis is dead in its own payout shape, not just as a "
                "forward-return approximation. Live shadow remains "
                "prospective-confirmation only.")
    elif s_p["net"] <= 0 < s_o["net"]:
        verd = ("STRADDLE — pessimistic bound <= 0 < optimistic bound: the "
                "kill is confirmed but exact-path faithfulness is "
                "unresolved on 4h data; the live stream stays the arbiter "
                "(and needs its n>=20 gate more than ever).")
    else:
        verd = ("DOES NOT TRANSFER — the spec payout survives under "
                "ordering bounds; revisit the round-2 kill basis.")
    w(f"**VERDICT: {verd}**")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
