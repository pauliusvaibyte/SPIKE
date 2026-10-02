"""Phase -1 Round 11 — NEW-DATA-DOMAIN BATCH (10 hypotheses).

Declared pre-execution in manifest `round11_batch`. Mechanisms only
testable after the 2026-09-23 data expansion: options vol surface
(DVOL/IV/skew 2021+), liquidation cascades (2022-12+), mark-index basis
(Binance premiumIndexKlines 2019+), cross-venue funding aggregates,
on-chain stress/flow. n_trials=46 effective families.

Run: .venv/Scripts/python.exe run_round11.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round11 as C11
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round11.md"
N_FAMILIES = 46
ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def _he() -> pd.DataFrame:
    """Harmony extended frame sorted by t with c = btc_price (naive ts)."""
    df = D.harmony_extended()
    df["t"] = pd.to_datetime(df["t"])
    if getattr(df["t"].dt, "tz", None) is not None:
        df["t"] = df["t"].dt.tz_convert(None)
    df = df.sort_values("t").reset_index(drop=True)
    # btc_price truncates 2023-12-13 upstream; px_bitstamp (2011+ ->
    # 2026-09-20) is the same instrument from the venue-named lineage —
    # declared substitution recorded in manifest errata.
    df["c"] = pd.to_numeric(df["px_bitstamp"], errors="coerce")
    return df


def _premium_merged(asset: str) -> pd.DataFrame:
    """Binance perp 1d close + premiumIndex 1d close on shared days."""
    kl = D.binance_klines(asset, "1d")[["t", "c"]].copy()
    pr = D.binance_premium(asset)[["t", "c"]].rename(
        columns={"c": "prem"})
    for d in (kl, pr):
        d["t"] = pd.to_datetime(d["t"])
        if getattr(d["t"].dt, "tz", None) is not None:
            d["t"] = d["t"].dt.tz_convert(None)
    m = kl.merge(pr, on="t").sort_values("t").reset_index(drop=True)
    return m


def _funding_daily(asset: str) -> pd.Series:
    """Binance perp funding summed per day (8h prints -> daily rate)."""
    f = D.binance_funding(asset)
    f = f.copy()
    f["t"] = pd.to_datetime(f["t"], utc=True,
                            format="mixed").dt.tz_convert(None)
    return f.set_index("t")["rate"].astype(float).groupby(
        lambda x: x.normalize()).sum()


def main() -> int:
    he = _he()
    price = he[["t", "c"]].copy()
    fund_btc = _funding_daily("btc")
    assets = [a for a in ALL
              if (Path(__file__).resolve().parent / "data_extended"
                  / "binance" / f"{a}usdt_klines_1d.json").exists()]
    U = {a: a.upper() for a in assets}

    prem_px = {U[a]: _premium_merged(a)[["t", "c"]].copy()
               for a in assets}
    specs: dict[str, dict] = {
        "dvol_spike_bounce_1d": {
            "legs": [("BTC", he,
                      lambda df: C11.dvol_spike_bounce_1d(df, "BTC"))]},
        "skew_extreme_reversal_3d": {
            "legs": [("BTC", he,
                      lambda df: C11.skew_extreme_reversal_3d(df, "BTC"))]},
        "iv_term_inversion_3d": {
            "legs": [("BTC", he,
                      lambda df: C11.iv_term_inversion_3d(df, "BTC"))]},
        "liq_cascade_cont_1d": {
            "legs": [("BTC", he,
                      lambda df: C11.liq_cascade_cont_1d(df, "BTC"))]},
        "liq_flush_bounce_1d": {
            "legs": [("BTC", he,
                      lambda df: C11.liq_flush_bounce_1d(df, "BTC"))]},
        "premium_basis_converge_1d": {
            "legs": [(U[a], _premium_merged(a),
                      (lambda aa: (lambda df:
                       C11.premium_basis_converge_1d(df, U[aa])))(a))
                     for a in assets],
            "drift_price": prem_px,
            "plc_price": prem_px,
            "funding": {U[a]: _funding_daily(a) for a in assets}},
        "funding_consensus_drift_1d": {
            "legs": [("BTC", he,
                      lambda df: C11.funding_consensus_drift_1d(
                          df, "BTC"))]},
        "lth_sopr_capitulation_7d": {
            "legs": [("BTC", he,
                      lambda df: C11.lth_sopr_capitulation_7d(
                          df, "BTC"))]},
        "nrpl_spike_top_3d": {
            "legs": [("BTC", he,
                      lambda df: C11.nrpl_spike_top_3d(df, "BTC"))]},
        "exchange_balance_drift_7d": {
            "legs": [("BTC", he,
                      lambda df: C11.exchange_balance_drift_7d(
                          df, "BTC"))]},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 11 — NEW-DATA-DOMAIN BATCH")
    w("")
    w("Mechanisms only testable after the data expansion: options vol")
    w("surface, liquidation cascades, mark-index basis, cross-venue")
    w("funding aggregates, on-chain stress/flow. Daily clock; signal day")
    w("d -> entry close d -> eval +k d; trailing-prior-day percentiles.")
    w("Column coverage differs per source (options 2021+, liq 2022-12+,")
    w("basis 2019+, funding agg, on-chain 2010+) — powered windows differ.")
    w(f"Universe: BTC harmony clock + {len(assets)} Binance perps. "
      "n_trials=46.")
    w("")
    w("| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round11"
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
        hb = (int(round((pd.to_datetime(ev["t_eval"], utc=True, format="mixed")
                         - pd.to_datetime(ev["t"], utc=True, format="mixed"))
                        .dt.total_seconds().median() / 86400))
              if not ev.empty else 1)
        placebo = (F.placebo_time_shift(ev, spec.get("plc_price", price),
                                        max(1, hb), 1440)
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
        per_asset = (ev.groupby("asset")["ret_bp"].sum()
                     if not ev.empty and "asset" in ev.columns else None)
        if per_asset is not None and len(per_asset) > 1:
            w("  per-asset net: " + " | ".join(f"{a} {v:+.0f}"
                                              for a, v in per_asset.items()))
        uncov = int((ev_all["exit_reason"] == "uncovered").sum()) \
            if not ev_all.empty and "exit_reason" in ev_all.columns else 0
        if uncov:
            w(f"  uncovered tail: {uncov} events (NaN'd, excluded)")
        if not ev.empty:
            evf, fcov = F.apply_funding_cost(
                ev_all.dropna(subset=["ret_bp"]),
                spec.get("funding", fund_btc))
            carry_net = float(evf["ret_bp_carry"].sum())
            w(f"  funding-carry adj: net={carry_net:+.0f}bp "
              f"(paid {fcov['total_funding_bp']:+.0f}bp carry; "
              f"{fcov['coverage']:.0%} of events have funding coverage)")
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
