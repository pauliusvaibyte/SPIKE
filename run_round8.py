"""Phase -1 Round 8 — throughput batch (10 hypotheses).

Declared pre-execution in manifest `round8_batch`. Mechanisms: vol-shock
fade, volume climax, funding sign-flip drift, trapped-positioning squeeze,
alt residual reversal, drawdown capitulation, month-end rebalancing, taker
share toxicity (TOXIC-FLOW retest on 2y klines), VIX-spike macro bounce,
Connors RSI-2 (MRV retest). Universe: 7 assets on data_extended/.
n_trials=34.

Run: .venv/Scripts/python.exe run_round8.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round8 as C8
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round8.md"
N_FAMILIES = 34
EXT = Path(__file__).resolve().parent / "data_extended"
ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def main() -> int:
    assets = [a for a in ALL
              if (EXT / "candles" / f"{a}_1d_full.json").exists()
              and (EXT / "candles" / f"{a}_4h_full.json").exists()
              and (EXT / "candles" / f"{a}_1h_full.json").exists()
              and (EXT / "funding" / f"{a}_funding_full.json").exists()]
    d1 = {a: D.candles_full(a, "1d") for a in assets}
    d4 = {a: D.candles_full(a, "4h") for a in assets}
    d1h = {a: D.candles_full(a, "1h") for a in assets}
    fund = {a: D.funding_full(a) for a in assets}
    bnk = {a: D.binance_klines(a, "1h") for a in assets
           if (EXT / "binance" / f"{a}usdt_klines_1h.json").exists()}
    hd = D.harmony_daily()
    U = {a: a.upper() for a in assets}

    def L(asset, src, fn):
        return (U[asset], src, fn)

    specs = {
        "rv_spike_fade_4h": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C8.rv_spike_fade_4h(df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 1, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "volume_climax_fade": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C8.volume_climax_fade(df, U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 1, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "funding_flip_momentum": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C8.funding_flip_momentum(
                           df, *F.truncate_aux(df, d4[aa]), U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "trapped_positioning_squeeze": {
            "legs": [L(a, d4[a],
                       (lambda aa: (lambda df: C8.trapped_positioning_squeeze(
                           df, *F.truncate_aux(df, fund[aa]), U[aa])))(a))
                     for a in assets],
            "price": d4["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: d4[a] for a in assets}},
        "alt_resid_reversal_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C8.alt_resid_reversal_1d(
                           *F.truncate_aux(df, d1["btc"]), df, U[aa])))(a))
                     for a in assets if a != "btc"],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets if a != "btc"}},
        "drawdown_bounce_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C8.drawdown_bounce_1d(df, U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 7, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "month_end_drift_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C8.month_end_drift_1d(df, U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 2, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
        "taker_share_fade_1h": {
            "legs": [L(a, bnk[a],
                       (lambda aa: (lambda df: C8.taker_share_fade_1h(
                           df, *F.truncate_aux(df, d1h[aa]), U[aa])))(a))
                     for a in bnk],
            "price": d1h["btc"], "hbars": 1, "barmin": 60,
            "plc_price": {U[a]: d1h[a] for a in bnk}},
        "vix_spike_btc_long": {
            "legs": [("BTC", hd, C8.vix_spike_btc_long)],
            "price": hd, "hbars": 5, "barmin": 1440},
        "rsi2_connors_1d": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C8.rsi2_connors_1d(df, U[aa])))(a))
                     for a in assets],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 8 — throughput batch (10 hypotheses)")
    w("")
    w("Declared pre-execution in manifest `round8_batch`. Mechanisms:")
    w("vol shock, volume climax, funding flip, trapped squeeze, alt")
    w("residual reversal, drawdown capitulation, month-end rebalancing,")
    w("taker share (2y retest), VIX spike, RSI-2 (MRV retest).")
    w(f"Universe: {','.join(U[a] for a in assets)}. n_trials=34.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round8"
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
