"""Phase -1 Round 9 — mechanism-diverse batch (10 hypotheses).

Declared pre-execution in manifest `round9_batch`. Families: VOL-REGIME,
CARRY, SESSION, BREADTH, VOLUME-CLIMAX (billed retest), ROTATION.
Universe: 7 assets on data_extended/. n_trials=39 effective families.

Run: .venv/Scripts/python.exe run_round9.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round9 as C9
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round9.md"
N_FAMILIES = 39
EXT = Path(__file__).resolve().parent / "data_extended"
ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def _dict_boundary(fn, d1: dict, events, max_checks: int = 40) -> list:
    """boundary_invariance equivalent for a pooled multi-asset leg: truncate
    every asset's frame at the event timestamp and confirm the event still
    fires with the same direction."""
    import numpy as np
    if events.empty:
        return []
    viol = []
    evs = events.iloc[::max(1, len(events) // max_checks)]
    for _, e in evs.iterrows():
        sub = fn({k: v[v["t"] <= e["t"]] for k, v in d1.items()})
        hit = sub[(sub["t"] == e["t"]) & (sub["asset"] == e["asset"])]
        if hit.empty:
            viol.append({"t": str(e["t"]), "type": "event_vanishes"})
        elif float(hit["dir"].iloc[0]) != float(e["dir"]):
            viol.append({"t": str(e["t"]), "type": "direction_flip"})
    return viol


def main() -> int:
    assets = [a for a in ALL
              if (EXT / "candles" / f"{a}_1d_full.json").exists()
              and (EXT / "candles" / f"{a}_4h_full.json").exists()
              and (EXT / "funding" / f"{a}_funding_full.json").exists()]
    d1 = {a: D.candles_full(a, "1d") for a in assets}
    d4 = {a: D.candles_full(a, "4h") for a in assets}
    fund = {a: D.funding_full(a) for a in assets}
    breadth = C9.breadth_panel(d1)
    U = {a: a.upper() for a in assets}

    def L(asset, src, fn):
        return (U[asset], src, fn)

    specs = {
        "compression_breakout_4h": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C9.compression_breakout_4h(
                           df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "funding_carry_24h": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C9.funding_carry_24h(
                           df, *F.truncate_aux(df, d4[aa]), U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "us_session_drift": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C9.us_session_drift(
                           df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 3, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "asia_session_drift": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C9.asia_session_drift(
                           df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 2, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "us_session_momentum": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C9.us_session_momentum(
                           df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "breadth_thrust_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C9.breadth_thrust_1d(
                           df, *F.truncate_aux(df, breadth), U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "breadth_washout_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C9.breadth_washout_1d(
                           df, *F.truncate_aux(df, breadth), U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "volume_divergence_fade_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C9.volume_divergence_fade_1d(
                           df, U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "btc_alt_rotation_3d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C9.btc_alt_rotation_3d(
                           *F.truncate_aux(df, d1["btc"]), df, U[aa])))(a))
                     for a in assets if a != "btc"],
            "price": d1["btc"], "hbars": 3, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets if a != "btc"}},
        "weekly_loser_bounce_1d": {
            "legs": [("POOL", d1, C9.weekly_loser_bounce_1d)],
            "price": d1["btc"], "hbars": 7, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 9 — mechanism-diverse batch (10 hypotheses)")
    w("")
    w("Declared pre-execution in manifest `round9_batch`. Families:")
    w("VOL-REGIME, CARRY, SESSION, BREADTH, VOLUME-CLIMAX (retest),")
    w("ROTATION. Deliberately non-momentum-themed.")
    w(f"Universe: {','.join(U[a] for a in assets)}. n_trials=39.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round9"
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
            if isinstance(src, dict):
                viol.extend(_dict_boundary(fn, src, ev_all))
            else:
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
