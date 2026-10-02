"""Phase -1 Round 4 — daily-frequency macro/on-chain families.

Four families declared pre-execution in manifest `round4_candidates`, on
the Harmony warehouse daily export (2010-2026). Same falsify stack;
n_trials=17. Daily data caveat: fewer independent events by construction.

Run: .venv/Scripts/python.exe run_round4.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round4 as C4
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round4.md"
N_FAMILIES = 17


def main() -> int:
    hd = D.harmony_daily()
    price = hd[["t", "c"]].dropna().reset_index(drop=True)
    specs = {
        "onchain_mvrv_regime":  {"fn": C4.onchain_mvrv_regime,  "hbars": 30},
        "fng_extreme_sentiment": {"fn": C4.fng_extreme_sentiment, "hbars": 7},
        "etf_flow_5d":          {"fn": C4.etf_flow_5d,          "hbars": 5},
        "cal_weekend_drift":    {"fn": C4.cal_weekend_drift,    "hbars": 3},
        "oi_price_divergence":  {"fn": C4.oi_price_divergence,  "hbars": 5},
    }
    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 4 — daily macro/on-chain families (Harmony export)")
    w("")
    w("Data: `data_extended/harmony/macro_daily.parquet` — blockchain_api BTC")
    w("price (2010-2026), coinmetrics MVRV, alternative.me fng, Farside ETF")
    w("flows (2024+), Binance daily OI, coc funding, FRED. Verified: price")
    w("sanity at known dates, ETF pre-launch clean (NaN not 0), monotonic.")
    w("n_trials=17. Daily data => fewer independent events by construction.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round4"
    ev_dir.mkdir(exist_ok=True)
    for cid, spec in specs.items():
        ev_all = spec["fn"](hd)
        F.write_event_csv(ev_all, ev_dir / f"{cid}.csv")
        ev = ev_all.dropna(subset=["ret_bp"]) if not ev_all.empty else ev_all
        wil = C.wilson_gate(ev)
        power = F.power_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        ss = F.sharpe_stats(ret, n_trials=N_FAMILIES)
        splits = F.split_consistency(ev)
        bres = F.boundary_invariance(spec["fn"], hd, ev_all)
        prefix = {"passed": not bres["violations"]}
        placebo = (F.placebo_time_shift(ev, price, spec["hbars"], 1440)
                   if not ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, spec.get("plc_price", price))
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        n_uncov = int(ev_all["ret_bp"].isna().sum()) if "ret_bp" in ev_all.columns else 0
        w(f"| {cid} | {len(ev)} | {n_uncov} | "
          f"{wil['hit']:.3f} | {wil['wilson_lo']:.3f} | {wil['gate']} | "
          f"{ev['ret_bp'].sum():.0f} | {ss.get('sharpe', 0):.2f} | "
          f"{ss.get('psr', float('nan')):.3f} | {ss.get('dsr', float('nan')):.3f} | "
          f"{pl:.3f} | {'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | **{verd}** |")
        w(f"  (power: {power['reason']})")
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
