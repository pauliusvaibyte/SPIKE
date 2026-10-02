"""Phase -1 Round 6 — cross-sectional expansion + new-mechanism batch.

Eight families declared in manifest.yaml `round6_candidates` BEFORE
execution: cross-asset lead/lag, funding cross-sectional RV, HL premium
dislocation, funding-duration persistence, 15m microstructure bounce,
equity->BTC macro beta, OI-crowding fade, taker-flow toxicity.
Universe: BTC, SOL + ETH, XRP, DOGE, AVAX, LINK (backfilled 2026-09-23).
Same falsify stack; n_trials=26.

Run: .venv/Scripts/python.exe run_round6.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round6 as C6
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round6.md"
N_FAMILIES = 26
EXT = Path(__file__).resolve().parent / "data_extended"

ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def _has(*parts) -> bool:
    return (EXT.joinpath(*parts)).exists()


def _available() -> list[str]:
    return [a for a in ALL
            if _has("funding", f"{a}_funding_full.json")
            and all(_has("candles", f"{a}_{iv}_full.json")
                    for iv in ("4h", "1h", "15m"))]


def _basket_medians(funds: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Per coin: [t, med] frame — median rate of the OTHER coins at each t
    (>=4 contributors required)."""
    wide = None
    for a, f in funds.items():
        s = f[["t", "rate"]].rename(columns={"rate": a})
        wide = s if wide is None else wide.merge(s, on="t", how="outer")
    wide = wide.sort_values("t").set_index("t")
    out = {}
    for a in funds:
        others = [c for c in funds if c != a]
        med = wide[others].median(axis=1, skipna=True)
        med[wide[others].notna().sum(axis=1) < 4] = np.nan
        out[a] = med.rename("med").reset_index()
    return out


def main() -> int:
    assets = _available()
    print(f"assets with extended data: {assets}")
    U = {a: a.upper() for a in assets}
    fund = {a: D.funding_full(a) for a in assets}
    b4h = {a: D.candles_full(a, "4h") for a in assets}
    b1h = {a: D.candles_full(a, "1h") for a in assets}
    b15m = {a: D.candles_full(a, "15m") for a in assets}
    med = _basket_medians(fund)
    hd = D.harmony_daily()

    def L(asset, src, fn):
        return (U[asset], src, fn)

    def _clip(df, *auxs):
        """Aux frames truncated to the slice's own horizon. Leg lambdas
        close over aux frames (bars/funding/medians); boundary_invariance
        truncates only the PRIMARY frame, so without this clip a truncated
        run still reads future aux rows and the check can pass on a
        leaking signal."""
        lim = df["t"].max()
        return [a[a["t"] <= lim] for a in auxs]

    specs: dict[str, dict] = {
        "xasset_btc_leads_alts": {
            "legs": [L(a, b1h[a],
                       (lambda aa: (lambda df: C6.xasset_btc_leads_alts(
                           _clip(df, b1h["btc"])[0], df, U[aa])))(a))
                     for a in assets if a != "btc"],
            "trunc_src": lambda a: b1h[a],
            "price": b1h["btc"], "hbars": 1, "barmin": 60,
            # per-asset placebo frames — pooled candidates get their
            # placebo drawn on each event's own asset, not one proxy
            "plc_price": {U[a]: b1h[a] for a in assets if a != "btc"}},
        "funding_xasset_rv": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C6.funding_xasset_rv(
                           df, *_clip(df, med[aa], b4h[aa]), U[aa])))(a))
                     for a in assets],
            "trunc_src": lambda a: fund[a],
            "price": b4h["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: b4h[a] for a in assets}},
        "hl_premium_disloc": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C6.hl_premium_disloc(
                           df, *_clip(df, b4h[aa]), U[aa])))(a))
                     for a in assets],
            "trunc_src": lambda a: fund[a],
            "price": b4h["btc"], "hbars": 2, "barmin": 240,
            "plc_price": {U[a]: b4h[a] for a in assets}},
        "funding_run_persistence": {
            "legs": [L(a, fund[a],
                       (lambda aa: (lambda df: C6.funding_run_persistence(
                           df, *_clip(df, b4h[aa]), U[aa])))(a))
                     for a in assets],
            "trunc_src": lambda a: fund[a],
            "price": b4h["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: b4h[a] for a in assets}},
        "serialcorr_15m_bounce": {
            "legs": [L(a, b15m[a],
                       (lambda aa: (lambda df: C6.serialcorr_15m_bounce(
                           df, U[aa])))(a))
                     for a in assets],
            "trunc_src": lambda a: b15m[a],
            "price": b15m["btc"], "hbars": 1, "barmin": 15,
            "plc_price": {U[a]: b15m[a] for a in assets}},
        "equity_lead_btc_5d": {
            "legs": [("BTC", hd, C6.equity_lead_btc_5d)],
            "trunc_src": lambda a: hd,
            "price": hd, "hbars": 5, "barmin": 1440},
        "oi_crowding_fade": {
            "legs": [L(a, D.binance_oi(a),
                       (lambda aa: (lambda df: C6.oi_crowding_fade(
                           df, *_clip(df, D.binance_funding(aa), b4h[aa]),
                           U[aa])))(a))
                     for a in ("btc", "sol")
                     if a in assets and _has("binance", f"{a}usdt_oi_hist_1h.json")],
            "trunc_src": lambda a: D.binance_oi(a),
            "price": b4h["btc"], "hbars": 6, "barmin": 240,
            "plc_price": {U[a]: b4h[a] for a in ("btc", "sol")
                          if a in assets}},
        "taker_toxicity_1h": {
            "legs": [L(a, D.binance_taker_ls(a),
                       (lambda aa: (lambda df: C6.taker_toxicity_1h(
                           df, *_clip(df, b1h[aa]), U[aa])))(a))
                     for a in ("btc", "sol")
                     if a in assets and _has("binance", f"{a}usdt_taker_ls_1h.json")],
            "trunc_src": lambda a: D.binance_taker_ls(a),
            "price": b1h["btc"], "hbars": 1, "barmin": 60,
            "plc_price": {U[a]: b1h[a] for a in ("btc", "sol")
                          if a in assets}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 6 — cross-sectional expansion + new-mechanism batch")
    w("")
    w("Declared pre-execution in manifest `round6_candidates`. Universe:")
    w("BTC,SOL,ETH,XRP,DOGE,AVAX,LINK on data_extended/. Mechanisms:")
    w("xasset lead/lag, funding RV vs basket, HL premium dislocation,")
    w("funding duration, 15m bounce, equity beta, OI crowding, taker")
    w("toxicity. n_trials=26.")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round6"
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
