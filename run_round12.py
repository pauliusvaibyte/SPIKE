"""Phase -1 Round 12 — REMAINING-COLUMNS BATCH (10 hypotheses).

Declared pre-execution in manifest `round12_batch`. Last untested
harmony_extended columns: CME OI (institutional positioning), venue
premia (coinbase/bybit), dormancy/CDD, miner economics, cycle
valuation, STH capitulation, nrpl loss side, cross-venue funding
spread. n_trials=50 effective families. Drift-audit + n_eff + funding
carry all live.

Run: .venv/Scripts/python.exe run_round12.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round12 as C12
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict
from run_round11 import _he, _funding_daily

REPORT = Path(__file__).resolve().parent / "reports" / "report_round12.md"
N_FAMILIES = 50


def main() -> int:
    he = _he()
    price = he[["t", "c"]].copy()
    fund_btc = _funding_daily("btc")

    specs: dict[str, dict] = {
        cid: {"legs": [("BTC", he,
                        (lambda f: (lambda df: f(df, "BTC")))(fn))]}
        for cid, fn in {
            "cme_oi_confirm_3d": C12.cme_oi_confirm_3d,
            "coinbase_premium_drift_1d": C12.coinbase_premium_drift_1d,
            "bybit_premium_drift_1d": C12.bybit_premium_drift_1d,
            "dormancy_spike_fade_7d": C12.dormancy_spike_fade_7d,
            "puell_extreme_7d": C12.puell_extreme_7d,
            "reserve_risk_regime_7d": C12.reserve_risk_regime_7d,
            "lth_mvrv_extreme_7d": C12.lth_mvrv_extreme_7d,
            "sth_sopr_loss_bounce_3d": C12.sth_sopr_loss_bounce_3d,
            "nrpl_capitulation_3d": C12.nrpl_capitulation_3d,
            "xvenue_funding_spread_1d": C12.xvenue_funding_spread_1d,
        }.items()
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 12 — REMAINING-COLUMNS BATCH")
    w("")
    w("Last untested harmony_extended columns: CME OI, venue premia,")
    w("dormancy, miner economics, cycle valuation, STH capitulation,")
    w("nrpl loss side, cross-venue funding spread. Daily clock,")
    w("c=px_bitstamp; trailing-prior-day percentiles; drift-audit and")
    w("n_eff gates live; funding carry reported as diagnostic.")
    w("Universe: BTC harmony clock. n_trials=50.")
    w("")
    w("| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round12"
    ev_dir.mkdir(exist_ok=True)
    for cid, spec in specs.items():
        ev_all = _pool(*[l[2](l[1]) for l in spec["legs"]])
        v = F.validate_events(ev_all)
        F.write_event_csv(ev_all, ev_dir / f"{cid}.csv")
        ev = ev_all.dropna(subset=["ret_bp"]) if not ev_all.empty else ev_all
        wil = C.wilson_gate(ev)
        power = F.power_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        ss = F.sharpe_stats(ret, n_trials=N_FAMILIES)
        splits = F.split_consistency(ev)
        viol = list(v["violations"])
        for asset, src, fn in spec["legs"]:
            viol.extend(F.boundary_invariance(fn, src, fn(src))["violations"])
        prefix = {"passed": not viol}
        hb = (int(round((pd.to_datetime(ev["t_eval"], utc=True, format="mixed")
                         - pd.to_datetime(ev["t"], utc=True, format="mixed"))
                        .dt.total_seconds().median() / 86400))
              if not ev.empty else 1)
        placebo = (F.placebo_time_shift(ev, price, max(1, hb), 1440)
                   if not ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, spec.get("drift_price", price))
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        net = float(ev["ret_bp"].sum()) if "ret_bp" in ev.columns else 0.0
        w(f"| {cid} | {len(ev)} | "
          f"{wil['hit']:.3f} | {wil['wilson_lo']:.3f} | {wil['gate']} | "
          f"{net:.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | "
          f"{ss.get('dsr', float('nan')):.3f} | "
          f"{pl:.3f} | {'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | **{verd}** |")
        w(f"  (power: {power['reason']})")
        if drift["n"]:
            w(f"  drift-audit: skill={drift['mean_skill_bp']:+.1f}bp/ev "
              f"t={drift['t_skill']:.2f} long%={drift['frac_long']:.0%} "
              f"L={drift['long_skill_bp']:+.1f} "
              f"S={drift['short_skill_bp']:+.1f}")
        bb = F.block_bootstrap(ev)
        w(f"  bb_p={bb['bb_p']:.3f} (block={bb['block_len']})")
        eras = F.era_breakdown(ev)
        if eras:
            w("  eras: " + " | ".join(f"{e['era']} n={e['n']} net={e['net_bp']:+.0f}"
                                     for e in eras))
        uncov = int((ev_all["exit_reason"] == "uncovered").sum()) \
            if not ev_all.empty and "exit_reason" in ev_all.columns else 0
        if uncov:
            w(f"  uncovered tail: {uncov} events (NaN'd, excluded)")
        if not ev.empty:
            evf, fcov = F.apply_funding_cost(ev, fund_btc)
            w(f"  funding-carry adj: net={float(evf['ret_bp_carry'].sum()):+.0f}bp "
              f"(paid {fcov['total_funding_bp']:+.0f}bp; "
              f"{fcov['coverage']:.0%} covered)")
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
