"""Phase -1 Round 7 — 40/125 DMA trend retest (TREND-family billing).

Two timescales declared in manifest `round7_dmaretest`: daily cross ->
+30d eval (canonical, low power), and the same 40/125 structure on 4h
bars -> +30 bars (5d) eval (powered variant). Universe: all 7 extended
assets. n_trials=26 effective families (retests billed to TREND).

Run: .venv/Scripts/python.exe run_round7.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round7 as C7
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round7.md"
N_FAMILIES = 26
EXT = Path(__file__).resolve().parent / "data_extended"
ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def main() -> int:
    assets = [a for a in ALL
              if (EXT / "candles" / f"{a}_1d_full.json").exists()
              and (EXT / "candles" / f"{a}_4h_full.json").exists()]
    d1 = {a: D.candles_full(a, "1d") for a in assets}
    d4 = {a: D.candles_full(a, "4h") for a in assets}
    U = {a: a.upper() for a in assets}

    specs = {
        "dma_40_125_cross_1d": {
            "legs": [(U[a], d1[a],
                      (lambda aa: (lambda df: C7.dma_cross(
                          df, U[aa], horizon_bars=30)))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 30, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "dma_40_125_cross_4h": {
            "legs": [(U[a], d4[a],
                      (lambda aa: (lambda df: C7.dma_cross(
                          df, U[aa], horizon_bars=30)))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 30, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 7 — 40/125 DMA cross (TREND-family retest)")
    w("")
    w("Declared pre-execution in manifest `round7_dmaretest`. Retest billed")
    w("to TREND: same mechanism (trend persistence) at materially longer")
    w("timescale than the killed TREND-1/TREND-2 variants. Golden cross ->")
    w("LONG, death cross -> SHORT; 1d eval +30d, 4h eval +30 bars (5d).")
    w(f"Universe: {','.join(U[a] for a in assets)}. n_trials=26.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round7"
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
            (ev[ev["asset"] == "BTC"] if "asset" in ev.columns else ev)
        placebo = (F.placebo_time_shift(plc_ev, plc_px, spec["hbars"],
                                        spec["barmin"])
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
