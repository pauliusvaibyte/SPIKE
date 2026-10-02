"""Phase -1 Round 2 — extended-data evaluation.

Evaluates the collect-only funding candidates on data_extended/ (funding
history backfilled to launch, ~3.3y; eval frame = 4h bars, ~833d coverage,
6-bar hold = 24h). Specs unchanged — parameters frozen; only data depth
changed. This is the declared collect_only re-test, delivered early via
backfill instead of journal accretion.

Round-2 verdicts are recorded in reports/report_extended.md. The original
frozen-snapshot report remains the primary declared experiment record.

Run: .venv/Scripts/python.exe run_extended_eval.py
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
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_extended.md"
BAR_4H = 14_400_000
N_FAMILIES = 9


def _legs_extended(d4h_btc, d4h_sol):
    fb, fs = D.funding_full("btc"), D.funding_full("sol")
    return {
        "fra_momentum_p90_long": {
            "legs": [("BTC", fb, lambda df: C.fra_momentum_p90_long(
                df, *F.truncate_aux(df, d4h_btc),
                horizon_bars=6, bar_ms=BAR_4H))],
            "price": d4h_btc, "hbars": 6, "barmin": 240},
        "fra_momentum_p90_long_r3000": {   # production rolling-3000 basis
            "legs": [("BTC", fb, lambda df: C.fra_momentum_p90_long(
                df, *F.truncate_aux(df, d4h_btc),
                pctile_win=3000, horizon_bars=6, bar_ms=BAR_4H))],
            "price": d4h_btc, "hbars": 6, "barmin": 240},
        "fra_fade_p90_short": {
            "legs": [("BTC", fb, lambda df: C.fra_fade_p90_short(
                df, *F.truncate_aux(df, d4h_btc), "BTC",
                horizon_bars=6, bar_ms=BAR_4H)),
                     ("SOL", fs, lambda df: C.fra_fade_p90_short(
                df, *F.truncate_aux(df, d4h_sol), "SOL",
                horizon_bars=6, bar_ms=BAR_4H))],
            "price": d4h_btc, "hbars": 6, "barmin": 240,
            "plc_price": {"BTC": d4h_btc, "SOL": d4h_sol}},
        "basis1_premium_p10": {
            "legs": [("BTC", fb, lambda df: C.basis1_premium_p10(
                df, *F.truncate_aux(df, d4h_btc), "BTC",
                horizon_bars=2, bar_ms=BAR_4H)),
                     ("SOL", fs, lambda df: C.basis1_premium_p10(
                df, *F.truncate_aux(df, d4h_sol), "SOL",
                horizon_bars=2, bar_ms=BAR_4H))],
            "price": d4h_btc, "hbars": 2, "barmin": 240,
            "plc_price": {"BTC": d4h_btc, "SOL": d4h_sol}},
    }


def main() -> int:
    d4h_btc, d4h_sol = D.candles_full("btc", "4h"), D.candles_full("sol", "4h")
    specs = _legs_extended(d4h_btc, d4h_sol)
    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 2 — extended-data evaluation")
    w("")
    w("data: `data_extended/` — fundingHistory backfilled to launch (28,894 rows,")
    w("Jun 2023 -> Sep 2026) x 4h eval bars (833d, Jun 2024 -> Sep 2026).")
    w("Specs frozen; only data depth changed (declared collect_only re-test).")
    w("Eval granularity note: 4h-bar exit paths are coarser than live 5-min")
    w("mids — conservative bias on SL/TP resolution (errata E5).")
    w("")
    w("| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_extended"
    ev_dir.mkdir(exist_ok=True)
    for cid, spec in specs.items():
        ev_all = _pool(*[l[2](l[1]) for l in spec["legs"]])
        F.write_event_csv(ev_all, ev_dir / f"{cid}.csv")
        ev = ev_all.dropna(subset=["ret_bp"]) if not ev_all.empty else ev_all
        wil = C.wilson_gate(ev)
        power = F.power_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        ss = F.sharpe_stats(ret, n_trials=N_FAMILIES)
        splits = F.split_consistency(ev)
        viol = []
        for _asset, src, fn in spec["legs"]:
            full = fn(src)
            bres = F.boundary_invariance(fn, src, full)
            viol.extend(bres["violations"])
        prefix = {"passed": not viol}
        plc_px = spec.get("plc_price", spec["price"])
        plc_ev = ev if isinstance(plc_px, dict) else \
            (ev[ev["asset"] == "BTC"] if "asset" in ev.columns else ev)
        placebo = (F.placebo_time_shift(plc_ev, plc_px, spec["hbars"],
                                        spec["barmin"])
                   if not plc_ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, plc_px)
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        w(f"| {cid} | {len(ev)} | {wil['hit']:.3f} | {wil['wilson_lo']:.3f} | "
          f"{wil['gate']} | {ev['ret_bp'].sum():.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | {ss.get('dsr', float('nan')):.3f} | "
          f"{pl:.3f} | {'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | **{verd}** |")
        w(f"  (n_uncovered={int(ev_all['ret_bp'].isna().sum())}, "
          f"power: {power['reason']})")
        bb = F.block_bootstrap(ev)
        w(f"  bb_p={bb['bb_p']:.3f} (block={bb['block_len']})")
        eras = F.era_breakdown(ev)
        if eras:
            w("  eras: " + " | ".join(f"{e['era']} n={e['n']} net={e['net_bp']:+.0f}"
                                     for e in eras))
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
