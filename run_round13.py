"""Phase -1 Round 13 — WALK-FORWARD SELECTION REPLAY.

Declared in manifest `round13_walkforward` BEFORE execution.

Pseudo-OOS test of the flagship rule family: for each cutoff C, screen a
parameter grid on data <= C (only inputs with coverage at C are eligible —
a 2017 researcher had no CoinMetrics flows), then evaluate the selected
config on C -> end. If the mechanism is real, selection transfers; if the
flagship was selection luck, OOS legs die across truncations.

Run: .venv/Scripts/python.exe run_round13.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates_round10 as C10
from harness import candidates_round11 as C11
from harness import candidates_round4 as C4
from harness import candidates_round8 as C8
from harness import data as D
from run_round10 import _stress

REPORT = Path(__file__).resolve().parent / "reports" / "report_round13.md"
CUTOFFS = ["2017-01-01", "2019-01-01", "2021-01-01", "2023-01-01"]

F_GRID = (20, 30, 45, 60)
S_GRID = (90, 125, 200)
K_GRID = (5, 10)
A_GRID = (0.4, 0.5, 0.6)
DAMPERS = ("none", "N", "V", "NV")


def w_grid(px: pd.Series, f: int, s: int, k: int, a: float) -> pd.Series:
    t = (px > px.rolling(f).mean()).astype(float)
    sm = px.rolling(s).mean()
    slow = ((px > sm) & (sm > sm.shift(k))).astype(float)
    return a * t + (1 - a) * slow


def damp(w: pd.Series, damper: str, stress: pd.Series, mvrv: pd.Series
         ) -> pd.Series:
    # publish-lag (A31 audit): the weight executes t+1 but reads values
    # stamped day t-1 that finalize ~03:20Z day t — unlagged dampers
    # leak ~3.3h/day into both IS selection and OOS replay.
    if "N" in damper:
        w = w * (1 - 0.5 * stress.reindex(w.index)
                 .shift(1).fillna(0.0))
    if "V" in damper:
        mv = mvrv.reindex(w.index).ffill().shift(1)
        w = w * (1 - 0.25 * (mv > 2.5).astype(float))
    return w


def eligible(damper: str, cutoff: pd.Timestamp, stress: pd.Series,
             mvrv: pd.Series) -> bool:
    """A config is only selectable at C if its inputs existed at C.
    With the publish-lag shift the last publicly-visible stamp at C is
    C-1, so the existence check stops one stamp short of the cutoff."""
    boundary = cutoff - pd.Timedelta(days=1)
    if "N" in damper and stress.loc[:boundary].sum() == 0:
        return False
    if "V" in damper and mvrv.loc[:boundary].dropna().empty:
        return False
    return True


def main() -> int:
    he = D.harmony_extended()
    he["t"] = pd.to_datetime(he["t"], format="mixed")
    if getattr(he["t"].dt, "tz", None) is not None:
        he["t"] = he["t"].dt.tz_convert(None)
    he = he.sort_values("t").reset_index(drop=True)
    he["c"] = pd.to_numeric(he["px_bitstamp"], errors="coerce")
    bars = he[["t", "c"]].dropna().reset_index(drop=True)
    px = bars.set_index("t")["c"].astype(float)

    hd = D.harmony_daily()
    stress = _stress(hd)
    mvrv = hd.set_index("t")["mvrv"].astype(float)

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 13 — walk-forward selection replay")
    w("")
    w("Screen the flagship rule grid on data <= C only, then evaluate the")
    w("selected config on C -> end. Selection must transfer OOS or the")
    w("flagship's support is selection luck. Costs: strategy_stats @10bp")
    w("IS-select; OOS reported at 10/20/30bp. Clock: px_bitstamp.")
    w("")

    for cs in CUTOFFS:
        C = pd.Timestamp(cs)
        # strict < C: the C-1 -> C return is decided before C but REALIZED
        # at C — under the fully-realized-IS convention (events use
        # t_eval < C) it straddles the boundary and stays out of scoring.
        px_in = px.loc[px.index < C]
        px_out = px.loc[C:]
        if len(px_in) < 400 or len(px_out) < 100:
            w(f"## cutoff {cs}: skipped (insufficient data either side)")
            continue
        scored = []
        for f in F_GRID:
            for s in S_GRID:
                for k in K_GRID:
                    for a in A_GRID:
                        for d in DAMPERS:
                            if not eligible(d, C, stress, mvrv):
                                continue
                            wt = damp(w_grid(px_in, f, s, k, a), d,
                                      stress, mvrv)
                            st = C10.strategy_stats(
                                bars.loc[bars["t"] < C], wt)
                            scored.append(((f, s, k, a, d),
                                           st["sharpe"]))
        scored.sort(key=lambda x: -x[1])
        best = scored[0]
        f, s, k, a, d = best[0]
        wt_full = damp(w_grid(px, f, s, k, a), d, stress, mvrv)
        out_bars = bars.loc[bars["t"] > C].reset_index(drop=True)
        s10 = C10.strategy_stats(out_bars, wt_full.loc[out_bars["t"]])
        s20 = C10.strategy_stats(out_bars, wt_full.loc[out_bars["t"]],
                                 cost_per_unit=0.002)
        s30 = C10.strategy_stats(out_bars, wt_full.loc[out_bars["t"]],
                                 cost_per_unit=0.003)
        bh = C10.strategy_stats(out_bars,
                                pd.Series(1.0, index=out_bars["t"]))
        flagship_cfg = damp(w_grid(px, 45, 125, 5, 0.5), "NV", stress, mvrv)
        sf = C10.strategy_stats(out_bars, flagship_cfg.loc[out_bars["t"]])
        # DSR on the OOS leg: deflated against THIS screen's own Sharpe
        # dispersion. purgedcv divides var_sharpe by bars_per_year
        # itself — passing var/365 here double-deflated the benchmark by
        # 365x, printing ~1.000 DSRs that were effectively raw PSR.
        try:
            from purgedcv import deflated_sharpe_ratio
            tr_oos = C10.strategy_ret(out_bars, wt_full.loc[out_bars["t"]])
            var_d = float(np.var([sr for _, sr in scored]))
            dsr = float(deflated_sharpe_ratio(
                tr_oos.to_numpy(), n_trials=len(scored),
                var_sharpe=var_d, bars_per_year=365))
        except Exception:
            dsr = float("nan")
        w(f"## cutoff {cs}")
        w(f"- IS-selected: f={f} s={s} k={k} a={a} damper={d} "
          f"(in-sample Sharpe {best[1]:.2f}, {len(scored)} eligible configs)")
        w(f"- OOS {cs}->end: Sharpe@10bp={s10['sharpe']:.2f} "
          f"@20bp={s20['sharpe']:.2f} @30bp={s30['sharpe']:.2f} "
          f"DSR@10bp={dsr:.3f} "
          f"CAGR={s10['cagr']:.2f} MaxDD={s10['maxdd']:.2f}")
        w(f"- OOS buyhold: Sharpe={bh['sharpe']:.2f} CAGR={bh['cagr']:.2f} "
          f"MaxDD={bh['maxdd']:.2f}")
        w(f"- OOS actual-flagship (45/125/5/0.5+NV): Sharpe@10bp="
          f"{sf['sharpe']:.2f} CAGR={sf['cagr']:.2f}")
        w(f"- top-5 IS configs: " + "; ".join(
            f"{c}(SR {sr:.2f})" for c, sr in scored[:5]))
        w("")

    # ── LEADS REPLAY ────────────────────────────────────────────────────
    # Same discipline for the declared forward leads: at each cutoff,
    # re-derive direction AND threshold on events fully realized <= C,
    # evaluate on events starting >= C (straddlers excluded from both).
    # _prior_q is shift(1)-trailing so post-C events stay causal.
    w("# Leads replay — direction + threshold re-derived per cutoff")
    w("")

    def _ev(sig_df, col, p_lo, p_hi, d_lo, d_hi, horizon, asset="BTC"):
        # publish-lag: bgeo/CM stamps land ~12:00Z the FOLLOWING day —
        # the entry at day-i close can only know stamps <= i-1, so the
        # value is shift(1) exactly like the impls' _pcol reads
        v = pd.to_numeric(sig_df.set_index("t")[col],
                          errors="coerce")
        vv = v.shift(1).to_numpy()
        lo = C11._prior_q(pd.Series(v), p_lo)
        hi = C11._prior_q(pd.Series(v), p_hi)
        sig = np.where(vv >= hi, d_hi, np.where(vv <= lo, d_lo, 0.0))
        # degenerate quantiles (flat/rewritten input: lo==hi) must not
        # fire — same fail-closed class as the emitter guards
        sig[~(np.isfinite(vv) & np.isfinite(lo) & np.isfinite(hi)
              & (lo < hi))] = np.nan
        return C8._sig_events(sig_df, sig, horizon=horizon,
                              cooldown=horizon, asset=asset)

    PCTS = ((0.20, 0.80), (0.15, 0.85), (0.10, 0.90), (0.05, 0.95))
    LEAD_CUTOFFS = ["2019-01-01", "2021-01-01", "2023-01-01",
                    "2025-01-01"]

    # two-sided on-chain/options families: mode cont = fwd direction
    fams = [
        ("nrpl(one-sided hi)", "nrpl_usd", 3,
         {"short": (0.0, -1.0), "long": (0.0, 1.0)}),
        ("puell", "puell", 7,
         {"fade": (1.0, -1.0), "cont": (-1.0, 1.0)}),
        ("reserve_risk", "reserve_risk", 7,
         {"fade": (1.0, -1.0), "cont": (-1.0, 1.0)}),
        ("skew25_1m", "skew25_1m", 3,
         {"revert": (1.0, -1.0), "cont": (-1.0, 1.0)}),
    ]
    for fname, col, hz, modes in fams:
        if col not in he.columns:
            w(f"## {fname}: column missing")
            continue
        for cs in LEAD_CUTOFFS:
            C = pd.Timestamp(cs)
            scored = []
            for pname, (dl, dh) in modes.items():
                for plo, phi in PCTS:
                    ev = _ev(he, col, plo, phi, dl, dh, hz)
                    if ev.empty:
                        continue
                    tt = pd.to_datetime(ev["t"], format="mixed")
                    te = pd.to_datetime(ev["t_eval"], format="mixed")
                    is_ev = ev[te < C].dropna(subset=["ret_bp"])
                    oos_ev = ev[tt >= C].dropna(subset=["ret_bp"])
                    if len(is_ev) < 15:
                        continue
                    scored.append(((pname, plo, phi),
                                   float(is_ev["ret_bp"].sum()),
                                   is_ev, oos_ev))
            if not scored:
                w(f"## {fname} @{cs}: no config reached IS n>=15")
                continue
            scored.sort(key=lambda x: -x[1])
            (cfg, is_net, is_ev, oos_ev) = scored[0]
            o_hit = (float(oos_ev["hit"].mean()) if len(oos_ev)
                     else float("nan"))
            w(f"## {fname} @{cs}")
            w(f"- IS-selected: mode={cfg[0]} pct=({cfg[1]},{cfg[2]}) "
              f"IS n={len(is_ev)} net={is_net:+.0f}bp")
            w(f"- OOS: n={len(oos_ev)} hit={o_hit:.3f} "
              f"net={float(oos_ev['ret_bp'].sum()):+.0f}bp")
        w("")

    # premium_basis_converge: per-asset pooled, |prem|>=p -> dir
    ext = Path(__file__).resolve().parent / "data_extended"
    prem_frames = {}
    for a in ("btc", "sol", "eth", "xrp", "doge", "avax", "link"):
        pp = ext / "binance" / f"{a}usdt_premium_1d.json"
        if not pp.exists():
            continue
        kl = D.binance_klines(a, "1d")[["t", "c"]].copy()
        pr = D.binance_premium(a)[["t", "c"]].rename(columns={"c": "prem"})
        for d_ in (kl, pr):
            d_["t"] = pd.to_datetime(d_["t"], format="mixed")
            if getattr(d_["t"].dt, "tz", None) is not None:
                d_["t"] = d_["t"].dt.tz_convert(None)
        prem_frames[a.upper()] = kl.merge(pr, on="t").sort_values(
            "t").reset_index(drop=True)
    if prem_frames:
        for cs in LEAD_CUTOFFS:
            C = pd.Timestamp(cs)
            scored = []
            for mode in ("converge", "runaway"):
                sgn = -1.0 if mode == "converge" else 1.0
                for p in (0.80, 0.85, 0.90, 0.95):
                    evs = []
                    for asset, mdf in prem_frames.items():
                        pv = pd.to_numeric(mdf["prem"],
                                           errors="coerce").to_numpy()
                        thr = C11._prior_q(pd.Series(np.abs(pv)), p)
                        sig = np.where(np.abs(pv) >= thr,
                                       sgn * np.sign(pv), 0.0)
                        sig[~(np.isfinite(pv) & np.isfinite(thr))] = np.nan
                        evs.append(C8._sig_events(mdf, sig, horizon=1,
                                                  cooldown=1,
                                                  asset=asset))
                    ev = (pd.concat(evs).sort_values("t")
                          .reset_index(drop=True))
                    if ev.empty:
                        continue
                    tt = pd.to_datetime(ev["t"], format="mixed")
                    te = pd.to_datetime(ev["t_eval"], format="mixed")
                    is_ev = ev[te < C].dropna(subset=["ret_bp"])
                    oos_ev = ev[tt >= C].dropna(subset=["ret_bp"])
                    if len(is_ev) < 15:
                        continue
                    scored.append(((mode, p), float(is_ev["ret_bp"].sum()),
                                   is_ev, oos_ev))
            if scored:
                scored.sort(key=lambda x: -x[1])
                cfg, is_net, is_ev, oos_ev = scored[0]
                o_hit = (float(oos_ev["hit"].mean()) if len(oos_ev)
                         else float("nan"))
                w(f"## premium_basis @{cs}")
                w(f"- IS-selected: mode={cfg[0]} p={cfg[1]} "
                  f"IS n={len(is_ev)} net={is_net:+.0f}bp")
                w(f"- OOS: n={len(oos_ev)} hit={o_hit:.3f} "
                  f"net={float(oos_ev['ret_bp'].sum()):+.0f}bp")
        w("")

    # fng fear side: fear threshold x direction (declared: long)
    if "fng" in hd.columns:
        for cs in LEAD_CUTOFFS:
            C = pd.Timestamp(cs)
            scored = []
            for mode in ("long", "short"):
                d_ = 1.0 if mode == "long" else -1.0
                for fear in (5, 10, 15, 20):
                    # fng publishes ~00:0xZ on its stamp day — minutes
                    # after the 00:00Z entry; lag 1 (same as C4 impl)
                    v = (pd.to_numeric(hd.set_index("t")["fng"],
                                       errors="coerce")
                         .shift(1).to_numpy())
                    sig = np.where(v <= fear, d_, 0.0).astype(float)
                    sig[~np.isfinite(v)] = np.nan
                    ev = C4._daily_rows(hd, sig, 7, 7)
                    if ev.empty:
                        continue
                    tt = pd.to_datetime(ev["t"], format="mixed")
                    te = pd.to_datetime(ev["t_eval"], format="mixed")
                    is_ev = ev[te < C].dropna(subset=["ret_bp"])
                    oos_ev = ev[tt >= C].dropna(subset=["ret_bp"])
                    if len(is_ev) < 15:
                        continue
                    scored.append(((mode, fear),
                                   float(is_ev["ret_bp"].sum()),
                                   is_ev, oos_ev))
            if scored:
                scored.sort(key=lambda x: -x[1])
                cfg, is_net, is_ev, oos_ev = scored[0]
                o_hit = (float(oos_ev["hit"].mean()) if len(oos_ev)
                         else float("nan"))
                w(f"## fng_fear @{cs}")
                w(f"- IS-selected: mode={cfg[0]} fear={cfg[1]} "
                  f"IS n={len(is_ev)} net={is_net:+.0f}bp")
                w(f"- OOS: n={len(oos_ev)} hit={o_hit:.3f} "
                  f"net={float(oos_ev['ret_bp'].sum()):+.0f}bp")

    # mom24h on Binance BTC 4h (2019+) — approximates the HL pooled lead
    bn4 = D.binance_klines("btc", "4h")[["t", "c"]].copy()
    bn4["t"] = pd.to_datetime(bn4["t"], format="mixed")
    if getattr(bn4["t"].dt, "tz", None) is not None:
        bn4["t"] = bn4["t"].dt.tz_convert(None)
    bn4 = bn4.sort_values("t").reset_index(drop=True)
    for cs in LEAD_CUTOFFS:
        C = pd.Timestamp(cs)
        scored = []
        for mode in ("cont", "fade"):
            sgn = 1.0 if mode == "cont" else -1.0
            for hb in (4, 6, 8):
                c = bn4["c"].to_numpy(dtype=float)
                t = bn4["t"]
                rows, i = [], 6
                while i < len(c):
                    r24 = c[i] / c[i - 6] - 1.0
                    if np.isfinite(r24) and r24 != 0 and c[i] > 0:
                        d = sgn * (1.0 if r24 > 0 else -1.0)
                        if i + hb <= len(c) - 1:
                            g = d * (c[i + hb] / c[i] - 1.0) * 1e4
                            rows.append({"t": t.iloc[i], "dir": d,
                                         "t_eval": t.iloc[i + hb],
                                         "gross_bp": g,
                                         "ret_bp": g - 10.0})
                        i += hb
                    else:
                        i += 1
                ev = pd.DataFrame(rows)
                if ev.empty:
                    continue
                is_ev = ev[ev["t_eval"] < C]
                oos_ev = ev[ev["t"] >= C]
                if len(is_ev) < 15:
                    continue
                scored.append(((mode, hb), float(is_ev["ret_bp"].sum()),
                               is_ev, oos_ev))
        if scored:
            scored.sort(key=lambda x: -x[1])
            cfg, is_net, is_ev, oos_ev = scored[0]
            o_hit = (float((oos_ev["gross_bp"] > 1).mean())
                     if len(oos_ev) else float("nan"))
            w(f"## mom24h(binance BTC 4h) @{cs}")
            w(f"- IS-selected: mode={cfg[0]} horizon={cfg[1]} "
              f"IS n={len(is_ev)} net={is_net:+.0f}bp")
            w(f"- OOS: n={len(oos_ev)} hit={o_hit:.3f} "
              f"net={float(oos_ev['ret_bp'].sum()):+.0f}bp")
        w("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
