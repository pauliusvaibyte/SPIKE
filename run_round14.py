"""Phase -1 Round 14 — WATCH-autopsy derivatives.

Four hypotheses declared pre-execution in manifest `round14_batch`:
the two short-leg-only risk-off singles, their union cluster, and the
concentrated carry variant. Trial ledger: +4 signal evaluations,
+1 new family (RISK-OFF composite); effective_families 39 -> 40,
total_signal_evaluations 74 -> 78.

Run: .venv/Scripts/python.exe run_round14.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round14 as C14
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round14.md"
N_FAMILIES = 51
ALL = ["btc", "eth", "sol", "xrp", "doge", "avax", "link"]
EXT = Path(__file__).resolve().parent / "data_extended"


def main() -> int:
    hd = D.harmony_daily()
    price = hd[["t", "c"]].dropna().reset_index(drop=True)
    assets = [a for a in ALL
              if (EXT / "candles" / f"{a}_4h_full.json").exists()
              and (EXT / "funding" / f"{a}_funding_full.json").exists()]
    d4 = {a: D.candles_full(a, "4h") for a in assets}
    fund = {a: D.funding_full(a) for a in assets}
    U = {a: a.upper() for a in assets}

    def L(asset, src, fn):
        return (U[asset], src, fn)

    specs = {
        "oi_price_divergence_short": {
            "legs": [("BTC", hd, C14.oi_price_divergence_short)],
            "price": hd, "hbars": 5, "barmin": 1440},
        "equity_lead_btc_5d_short": {
            "legs": [("BTC", hd, C14.equity_lead_btc_5d_short)],
            "price": hd, "hbars": 5, "barmin": 1440},
        "riskoff_cluster_5d": {
            "legs": [("BTC", hd, C14.riskoff_cluster_5d)],
            "price": hd, "hbars": 5, "barmin": 1440},
        "funding_carry_extreme": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C14.funding_carry_extreme(
                           df, *F.truncate_aux(df, d4[aa]), U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 14 — WATCH-autopsy derivatives (4 hypotheses)")
    w("")
    w("Declared pre-execution in manifest `round14_batch`. Derived from")
    w("the episode-gate autopsy: short-leg singles of the two candidates")
    w("whose only failing gate was ep-wilson, their union cluster, and")
    w("the carry edge concentrated to outer-5% funding (DSR-blocked parent).")
    w(f"Universe: BTC daily + {','.join(U[a] for a in assets)} carry.")
    w("n_trials=51 effective families. Each variant is a new trial —")
    w("derivation is billed.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round14"
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
        for asset, src, fn in spec["legs"]:
            viol.extend(F.boundary_invariance(fn, src, fn(src))["violations"])
        prefix = {"passed": not viol}
        plc_px = spec.get("plc_price", spec["price"])
        plc_ev = ev if isinstance(plc_px, dict) else \
            (ev[ev["asset"] == spec.get("plc_asset", "BTC")]
             if "asset" in ev.columns else ev)
        placebo = (F.placebo_time_shift(plc_ev, plc_px,
                                        spec["hbars"], spec["barmin"])
                   if not plc_ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, plc_px)
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        n_uncov = int(ev_all["ret_bp"].isna().sum()) if "ret_bp" in ev_all.columns else 0
        net = float(ev["ret_bp"].sum()) if "ret_bp" in ev.columns else 0.0
        w(f"| {cid} | {len(ev)} | {n_uncov} | "
          f"{wil['hit']:.3f} | {wil['wilson_lo']:.3f} | {wil['gate']} | "
          f"{net:.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | {ss.get('dsr', float('nan')):.3f} | "
          f"{pl:.3f} | {'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | **{verd}** |")
        w(f"  (power: {power['reason']})")
        if drift is not None:
            w(f"  drift-audit: skill={drift.get('mean_skill_bp', float('nan')):+.1f}bp/ev "
              f"t={drift.get('t_skill', float('nan')):.2f} "
              f"long%={100 * drift.get('frac_long', 0):.0f}% "
              f"L={drift.get('long_skill_bp', float('nan')):+.1f} "
              f"S={drift.get('short_skill_bp', float('nan')):+.1f}")
        bb = F.block_bootstrap(ev)
        w(f"  bb_p={bb['bb_p']:.3f} (block={bb['block_len']})")
        eras = F.era_breakdown(ev)
        if eras:
            w("  eras: " + " | ".join(f"{e['era']} n={e['n']} net={e['net_bp']:+.0f}"
                                     for e in eras))
        per_asset = (ev.groupby("asset")["ret_bp"].sum()
                     if not ev.empty and "asset" in ev.columns else None)
        if per_asset is not None and len(per_asset) > 1:
            w("  per-asset net: " + " | ".join(f"{a} {v:+.0f}"
                                              for a, v in per_asset.items()))
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
