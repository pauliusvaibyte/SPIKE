"""Phase -1 Round 3 — new-mechanism families on extended data.

Four families declared in manifest.yaml `round3_candidates` BEFORE execution:
settle1_funding_drift, xvenue_funding_disloc, xvenue_leadlag_1h,
xvenue_basis_converge. Same falsify stack as rounds 1-2; n_trials=13.

Run: .venv/Scripts/python.exe run_round3.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round3 as C3
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round3.md"
N_FAMILIES = 13


def _legs():
    hl1h = {a: D.candles_full(a, "1h") for a in ("btc", "sol")}
    hl4h = {a: D.candles_full(a, "4h") for a in ("btc", "sol")}
    hlf = {a: D.funding_full(a) for a in ("btc", "sol")}
    bnf = {a: D.binance_funding(a) for a in ("btc", "sol")}
    bnk = {a: D.binance_klines(a, "1h") for a in ("btc", "sol")}
    A = {"btc": "BTC", "sol": "SOL"}
    return {
        "settle1_funding_drift": {
            "legs": [(A[a], hlf[a],
                      (lambda aa: (lambda df: C3.settle1_funding_drift(
                          df, *F.truncate_aux(df, hl1h[aa]), A[aa])))(a))
                     for a in ("btc", "sol")],
            "trunc_src": lambda a: hlf[a],
            "price": hl1h["btc"], "hbars": 1, "barmin": 60,
            "plc_price": {"BTC": hl1h["btc"], "SOL": hl1h["sol"]}},
        "xvenue_funding_disloc": {
            "legs": [(A[a], hlf[a],
                      (lambda aa: (lambda df: C3.xvenue_funding_disloc(
                          df, *F.truncate_aux(df, bnf[aa], hl4h[aa]),
                          A[aa])))(a))
                     for a in ("btc", "sol")],
            "trunc_src": lambda a: hlf[a],
            "price": hl4h["btc"], "hbars": 2, "barmin": 240,
            "plc_price": {"BTC": hl4h["btc"], "SOL": hl4h["sol"]}},
        "xvenue_leadlag_1h": {
            "legs": [(A[a], hl1h[a],
                      (lambda aa: (lambda df: C3.xvenue_leadlag_1h(
                          *F.truncate_aux(df, bnk[aa]), df, A[aa])))(a))
                     for a in ("btc", "sol")],
            "trunc_src": lambda a: hl1h[a],
            "price": hl1h["btc"], "hbars": 1, "barmin": 60,
            "plc_price": {"BTC": hl1h["btc"], "SOL": hl1h["sol"]}},
        "xvenue_basis_converge": {
            "legs": [(A[a], hl1h[a],
                      (lambda aa: (lambda df: C3.xvenue_basis_converge(
                          *F.truncate_aux(df, bnk[aa]), df, A[aa])))(a))
                     for a in ("btc", "sol")],
            "trunc_src": lambda a: hl1h[a],
            "price": hl1h["btc"], "hbars": 4, "barmin": 60,
            "plc_price": {"BTC": hl1h["btc"], "SOL": hl1h["sol"]}},
    }


def main() -> int:
    specs = _legs()
    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 3 — new-mechanism families (extended data)")
    w("")
    w("Declared pre-execution in manifest `round3_candidates`. Mechanisms:")
    w("settlement cash-flow drift, cross-venue funding dislocation,")
    w("cross-venue lead/lag, cross-venue price-basis convergence.")
    w("Data: HL funding to launch, HL 1h (208d) / 4h (833d) bars,")
    w("Binance funding (2019+) + 1h klines (~2y). n_trials=13.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round3"
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
        for a in ("btc", "sol"):
            src = spec["trunc_src"](a)
            fn = [l[2] for l in spec["legs"] if l[0] == a.upper()][0]
            full = fn(src)
            viol.extend(F.boundary_invariance(fn, src, full)["violations"])
        prefix = {"passed": not viol}
        placebo = (F.placebo_time_shift(
            ev, spec.get("plc_price", spec["price"]),
            spec["hbars"], spec["barmin"])
            if not ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, spec.get("plc_price", spec["price"]))
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        w(f"| {cid} | {len(ev)} | {int(ev_all['ret_bp'].isna().sum())} | "
          f"{wil['hit']:.3f} | {wil['wilson_lo']:.3f} | {wil['gate']} | "
          f"{ev['ret_bp'].sum():.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | {ss.get('dsr', float('nan')):.3f} | "
          f"{pl:.3f} | {'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | **{verd}** |")
        w(f"  (power: {power['reason']})")
        if drift["n"]:
            w(f"  drift-audit: skill={drift['mean_skill_bp']:+.1f}bp/ev "
              f"t={drift['t_skill']:.2f}")
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
