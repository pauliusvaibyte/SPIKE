"""Phase -1 Round 15 — LIVE-UNUSED-COLUMNS batch.

Five hypotheses declared pre-execution in manifest `round15_batch`:
the last economically distinct LIVE inputs never consumed by any
emitter (2026-09-28 coverage audit). Trial ledger: +5 signal
evaluations, +2 new families (hashrate mining-economics, us10y
rates-shock); dormancy/pl_ratio/sth_mvrv billed to existing families.
effective_families 51 -> 53, total_signal_evaluations 78 -> 83.

Run: .venv/Scripts/python.exe run_round15.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round15 as C15
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict
from run_round11 import _he

REPORT = Path(__file__).resolve().parent / "reports" / "report_round15.md"
N_FAMILIES = 53


def main() -> int:
    he = _he()                          # c = px_bitstamp, naive t
    hd = D.harmony_daily()
    hd["t"] = __import__("pandas").to_datetime(hd["t"])
    if getattr(hd["t"].dt, "tz", None) is not None:
        hd["t"] = hd["t"].dt.tz_convert(None)
    hd = hd.sort_values("t").reset_index(drop=True)
    price_he = he[["t", "c"]].copy()
    price_hd = hd[["t", "c"]].dropna().reset_index(drop=True)

    B = lambda f: (lambda df: f(df, "BTC"))
    specs = {
        "dormancy_spike_short_7d": {
            "legs": [("BTC", he, B(C15.dormancy_spike_short_7d))],
            "price": price_he, "hbars": 7, "barmin": 1440},
        "hashrate_drawdown_long_14d": {
            "legs": [("BTC", he, B(C15.hashrate_drawdown_long_14d))],
            "price": price_he, "hbars": 14, "barmin": 1440},
        "us10y_shock_short_5d": {
            "legs": [("BTC", hd, B(C15.us10y_shock_short_5d))],
            "price": price_hd, "hbars": 5, "barmin": 1440},
        "realized_pl_ratio_capitulation_5d": {
            "legs": [("BTC", he, B(C15.realized_pl_ratio_capitulation_5d))],
            "price": price_he, "hbars": 5, "barmin": 1440},
        "sth_mvrv_capitulation_7d": {
            "legs": [("BTC", he, B(C15.sth_mvrv_capitulation_7d))],
            "price": price_he, "hbars": 7, "barmin": 1440},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 15 — LIVE-UNUSED-COLUMNS batch (5 hypotheses)")
    w("")
    w("Declared pre-execution in manifest `round15_batch`. Coverage")
    w("audit 2026-09-28: these are the last economically distinct LIVE")
    w("inputs never consumed by any emitter. Daily clock; he-frame")
    w("c=px_bitstamp, us10y leg on harmony_daily c; publish-lagged")
    w("inputs; trailing-prior-day percentiles; drift-audit + n_eff live.")
    w("n_trials=53 effective families.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round15"
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
        plc_ev = ev[ev["asset"] == "BTC"] if "asset" in ev.columns else ev
        placebo = (F.placebo_time_shift(plc_ev, spec["price"],
                                        spec["hbars"], spec["barmin"])
                   if not plc_ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, spec["price"])
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        n_uncov = int(ev_all["ret_bp"].isna().sum()) if "ret_bp" in ev_all.columns else 0
        net = float(ev["ret_bp"].sum()) if "ret_bp" in ev.columns else 0.0
        w(f"| {cid} | {len(ev)} | {n_uncov} | "
          f"{wil['hit']:.3f} | {wil['wilson_lo']:.3f} | {wil['gate']} | "
          f"{net:.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | "
          f"{ss.get('dsr', float('nan')):.3f} | "
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
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
