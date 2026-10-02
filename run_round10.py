"""Phase -1 Round 10 — FLAGSHIP PORT (5 hypotheses).

Declared pre-execution in manifest `round10_flagship_port`. Cross-validates
Sentinely's strongest retrospective composite (base+N+V ~Sharpe 1.45 on
BTC daily, 15bps, t+1) inside this falsification stack at 10bp RT, on a
different venue (HL perp) and different assets (6 alts).
n_trials=40 effective families.

Run: .venv/Scripts/python.exe run_round10.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round10 as C10
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import _pool, verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round10.md"
N_FAMILIES = 40
EXT = Path(__file__).resolve().parent / "data_extended"
ALL = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")
CM_FLOWS = Path(__import__("os").environ.get(
    "CM_FLOWS_CSV", "research/cm_exchange_flows_20260907.csv"))
CLOCK_START = pd.Timestamp("2013-01-01")


def _stress(hd: pd.DataFrame) -> pd.Series:
    """N-leg stress flag on BTC (network-level): 7d net CM exchange inflow
    normalized by mcap > trailing-365d-prior p90.
    Prefers the DAILY-REFRESHED coinmetrics pull (data_extended); the
    static 2026-09-07 CSV is a fallback only — reading it silently would
    freeze the N-leg at Sep 7 while the refresh job updates the live file."""
    try:
        cm = D.coinmetrics_daily().set_index("t")
        cm.index = pd.to_datetime(cm.index, utc=True,
                                  format="mixed").tz_convert(None).normalize()
        fin, fout = "flowinexusd", "flowoutexusd"
        if fin not in cm.columns:
            raise KeyError("flow columns missing")
    except Exception as e:
        print(f"  !! refreshed CM flows unusable ({e}); "
              "falling back to static 2026-09-07 CSV")
        cm = pd.read_csv(CM_FLOWS, parse_dates=["time"]).set_index("time")
        cm.index = pd.to_datetime(cm.index, utc=True,
                                  format="mixed").tz_convert(None).normalize()
        fin, fout = "FlowInExUSD", "FlowOutExUSD"
    net = (pd.to_numeric(cm[fin], errors="coerce")
           - pd.to_numeric(cm[fout], errors="coerce"))
    net = net.groupby(level=0).last()
    px = hd.set_index("t")["btc_price"].astype(float)
    return C10.stress_netflow(net, px)


def _merged(bars: pd.DataFrame, stress: pd.Series, mvrv: pd.Series
            ) -> pd.DataFrame:
    df = bars[["t", "c"]].copy()
    if getattr(df["t"].dt, "tz", None) is not None:
        df["t"] = df["t"].dt.tz_convert(None)
    df["stress"] = df["t"].map(stress).fillna(0.0)
    df["mvrv"] = df["t"].map(mvrv)
    return df


def main() -> int:
    assets = [a for a in ALL
              if (EXT / "candles" / f"{a}_1d_full.json").exists()]
    d1 = {a: D.candles_full(a, "1d") for a in assets}
    hd = D.harmony_daily()
    stress = _stress(hd)
    mvrv = hd.set_index("t")["mvrv"].astype(float)
    btc_h = hd[["t", "c"]].copy()                    # c = btc_price alias
    bn_btc = D.binance_klines("btc", "1d")[["t", "c"]].copy()
    bn_btc["t"] = bn_btc["t"].dt.tz_convert(None)
    d1 = {a: (lambda b: (b.assign(t=b["t"].dt.tz_convert(None)))
              if getattr(b["t"].dt, "tz", None) is not None else b)(b)
          for a, b in d1.items()}
    U = {a: a.upper() for a in assets}

    def L(asset, src, fn):
        return (U[asset], src, fn)

    specs = {
        "flagship_base_btc": {
            "legs": [L("btc", btc_h,
                       lambda df: C10.flagship_base(df, "BTC"))],
            "price": btc_h, "hbars": 1, "barmin": 1440,
            "clip": CLOCK_START},
        "flagship_composite_btc": {
            "legs": [L("btc", _merged(btc_h, stress, mvrv),
                       lambda df: C10.flagship_composite(df, "BTC"))],
            "price": btc_h, "hbars": 1, "barmin": 1440,
            "clip": CLOCK_START},
        "flagship_composite_hlbtc": {
            "legs": [L("btc", _merged(d1["btc"], stress, mvrv),
                       lambda df: C10.flagship_composite(df, "BTC"))],
            "price": d1["btc"], "hbars": 1, "barmin": 1440},
        "flagship_composite_bnbtc": {
            "legs": [L("btc", _merged(bn_btc, stress, mvrv),
                       lambda df: C10.flagship_composite(df, "BTC"))],
            "price": bn_btc, "hbars": 1, "barmin": 1440},
        "flagship_base_alts": {
            "legs": [L(a, d1[a],
                       (lambda aa: (lambda df: C10.flagship_base(
                           df, U[aa])))(a))
                     for a in assets if a != "btc"],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets if a != "btc"}},
        "flagship_composite_alts": {
            "legs": [L(a, _merged(d1[a], stress, mvrv),
                       (lambda aa: (lambda df: C10.flagship_composite(
                           df, U[aa])))(a))
                     for a in assets if a != "btc"],
            "price": d1["btc"], "hbars": 1, "barmin": 1440,
            "plc_price": {U[a]: d1[a] for a in assets if a != "btc"}},
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 10 — FLAGSHIP PORT (Sentinely base+N+V)")
    w("")
    w("Cross-validation of upstream mega_screen's strongest retrospective")
    w("system inside this stack. Spec ported verbatim; 10bp RT (5bp/unit);")
    w("t+1 execution; events = invested days with turnover allocated inside")
    w("episodes. N-leg uses CM exchange flows (flash/provisional status —")
    w("declared limitation); V-leg uses harmony mvrv.")
    w(f"Universe: BTC max-clock + Binance perp BTC (2019+) + "
      f"{','.join(U[a] for a in assets if a != 'btc')} HL daily. "
      "n_trials=40.")
    w("")
    w("| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | "
      "placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ev_dir = REPORT.parent / "events_round10"
    ev_dir.mkdir(exist_ok=True)
    for cid, spec in specs.items():
        ev_all = _pool(*[l[2](l[1]) for l in spec["legs"]])
        if "clip" in spec and not ev_all.empty:
            ev_all = ev_all[ev_all["t"] >= spec["clip"]].reset_index(drop=True)
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
        # dict prices cover every asset in the event frame; a bare frame
        # covers only its own asset, so restrict the placebo to BTC
        plc_ev = ev if isinstance(plc_px, dict) else \
            (ev[ev["asset"] == "BTC"] if "asset" in ev.columns else ev)
        placebo = (F.placebo_time_shift(plc_ev, plc_px,
                                        spec["hbars"], spec["barmin"])
                   if not plc_ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, plc_px)
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp,
                       {"pbo": float("nan")}, drift=drift)
        pl = placebo.get("p_value", float("nan"))
        net = float(ev["ret_bp"].sum()) if "ret_bp" in ev.columns else 0.0
        w(f"| {cid} | {len(ev)} | "
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
        # continuous-strategy stats block (Sentinely-comparable)
        stat_rows = []
        for asset, src, fn in spec["legs"]:
            a = asset.lower() if asset.lower() in d1 else "btc"
            frame = d1.get(a, btc_h)
            is_comp = "composite" in cid
            if is_comp:
                px = src.set_index("t")["c"].astype(float)
                # publish-lag (A31): diagnostics must match the candidate
                # impl — day-d-stamped dampers finalize ~03:20Z d+1, after
                # the modeled execution; shift(1) inside w_composite /
                # flagship_composite already, keep the same here.
                ww = (C10.w_base(px)
                      * (1 - 0.5 * src.set_index("t")["stress"]
                         .reindex(px.index).shift(1).fillna(0.0)))
                mv = (src.set_index("t")["mvrv"].reindex(px.index)
                      .ffill().shift(1))
                ww = ww * (1 - 0.25 * (mv > 2.5).astype(float))
            else:
                px = src.set_index("t")["c"].astype(float)
                ww = C10.w_base(px)
            s10 = C10.strategy_stats(src[["t", "c"]], ww)
            s15 = C10.strategy_stats(src[["t", "c"]], ww, cost_per_unit=0.0015)
            stat_rows.append(f"{asset}: SR(10bp)={s10['sharpe']:.2f} "
                             f"SR(15bp)={s15['sharpe']:.2f} "
                             f"CAGR={s10['cagr']:.2f} MaxDD={s10['maxdd']:.2f} "
                             f"turnover={s10['turnover']:.1f}")
        if stat_rows:
            w("  strategy-stats: " + " | ".join(stat_rows))
        # buyhold benchmark on the same clock — clip the PRICE frame at the
        # same CLOCK_START the events respect; btc_h runs back to 2010 with
        # early zero closes that used to blow the benchmark to inf/nan.
        bh_src = spec["price"]
        if "clip" in spec:
            bh_src = bh_src[bh_src["t"] >= spec["clip"]]
        bh = C10.strategy_stats(bh_src, pd.Series(1.0,
                                index=bh_src.set_index("t").index))
        w(f"  buyhold-benchmark: Sharpe={bh['sharpe']:.2f} "
          f"CAGR={bh['cagr']:.2f} MaxDD={bh['maxdd']:.2f}")
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
