"""Phase -1 Round 16 — basis1 mechanism audit (declared pre-execution).

The one WATCH survivor of round2_extended_eval gets its declared follow-up:
sub-period robustness, cluster concentration, dose-response (premium depth
vs outcome), premium convergence during holds, placebo re-check. Events are
re-emitted with the IDENTICAL round-2 construction and reconciled against
events_extended/basis1_premium_p10.csv — a mismatch means the audit is
auditing a different stream and the run aborts.

Kill rule (manifest round16_basis1_audit): KILL if ANY of — >50% of
calendar quarters net <= 0; top-5 events contribute >60% of total net bp;
deeper-band mean <= shallow-band mean; median premium delta <= 0.
SURVIVE => stays WATCH; promotion requires untouched-forward evidence.

Run: .venv/Scripts/python.exe run_round16.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import data as D
from harness import falsify as F

REPORT = Path(__file__).resolve().parent / "reports" / "report_round16.md"
EV_DIR = REPORT.parent / "events_round16"
SAVED = REPORT.parent / "events_extended" / "basis1_premium_p10.csv"
BAR_4H = 14_400_000
FEE_RT_BP = 10.0  # convention fee_per_side_bp=5 -> 10bp round trip


def _emit():
    """Identical to run_extended_eval._legs_extended['basis1_premium_p10']
    (funds carry extra p05/p10/p50 columns — the emitter ignores them)."""
    d4h = {"BTC": D.candles_full("btc", "4h"), "SOL": D.candles_full("sol", "4h")}
    funds = {a: fb_p(D.funding_full(a)) for a in ("BTC", "SOL")}
    legs = [C.basis1_premium_p10(
                funds[a], *F.truncate_aux(funds[a], d4h[a]), a,
                horizon_bars=2, bar_ms=BAR_4H)
            for a in ("BTC", "SOL")]
    return pd.concat(legs, ignore_index=True), funds


def fb_p(fund: pd.DataFrame) -> pd.DataFrame:
    """Funding frame + trailing-720 premium p10 (same basis as emitter)."""
    fund = fund.copy()
    fund["p10"] = fund["premium"].rolling(720, min_periods=720).quantile(0.10)
    fund["p05"] = fund["premium"].rolling(720, min_periods=720).quantile(0.05)
    fund["p50"] = fund["premium"].rolling(720, min_periods=720).quantile(0.50)
    return fund


def _reconcile(ev: pd.DataFrame) -> str:
    saved = pd.read_csv(SAVED)
    s_cov = saved.dropna(subset=["ret_bp"])
    e_cov = ev.dropna(subset=["ret_bp"])
    ok_n = len(s_cov) == len(e_cov)
    ok_net = np.isclose(s_cov["ret_bp"].sum(), e_cov["ret_bp"].sum(), atol=1.0)
    ok_t = sorted(pd.to_datetime(s_cov["t"], utc=True, format="mixed").tolist()) == \
        sorted(pd.to_datetime(e_cov["t"], utc=True, format="mixed").tolist())
    status = "MATCH" if (ok_n and ok_net and ok_t) else "MISMATCH"
    msg = (f"reconcile vs events_extended: {status} "
           f"(rows {len(ev)} vs {len(saved)}, covered {len(e_cov)} vs "
           f"{len(s_cov)}, net {e_cov['ret_bp'].sum():.0f} vs "
           f"{s_cov['ret_bp'].sum():.0f})")
    return msg, status


def _enrich(ev: pd.DataFrame, funds: dict) -> pd.DataFrame:
    """Per-event premium depth at entry + premium at the 8h eval point."""
    prem_in, p05_in, p10_in, p50_in, prem_out = [], [], [], [], []
    for _, r in ev.iterrows():
        f = funds[r["asset"]]
        i = int(f["t"].searchsorted(r["t"]))
        if i >= len(f) or f["t"].iloc[i] != r["t"]:
            prem_in.append(np.nan); p05_in.append(np.nan)
            p10_in.append(np.nan); p50_in.append(np.nan)
            prem_out.append(np.nan); continue
        prem_in.append(float(f["premium"].iloc[i]))
        p05_in.append(float(f["p05"].iloc[i]))
        p10_in.append(float(f["p10"].iloc[i]))
        p50_in.append(float(f["p50"].iloc[i]))
        j = int(f["t"].searchsorted(r["t_eval"]))
        prem_out.append(float(f["premium"].iloc[j]) if j < len(f) else np.nan)
    ev = ev.copy()
    ev["prem_in"], ev["p05"], ev["p10"], ev["p50"], ev["prem_out"] = (
        prem_in, p05_in, p10_in, p50_in, prem_out)
    ev["prem_delta"] = ev["prem_out"] - ev["prem_in"]
    ev["deep"] = ev["prem_in"] <= ev["p05"]   # deeper than p5 within armed band
    return ev


def main() -> int:
    ev_all, funds = _emit()
    recon, status = _reconcile(ev_all)
    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 16 — basis1_premium_p10 mechanism audit")
    w("")
    w(recon)
    if status != "MATCH":
        w("")
        w("**AUDIT ABORTED — re-emitted stream diverges from the round-2 "
          "artifact; findings would not describe the declared spec.**")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 2

    ev = _enrich(ev_all.dropna(subset=["ret_bp"]).reset_index(drop=True), funds)
    EV_DIR.mkdir(exist_ok=True)
    ev.to_csv(EV_DIR / "basis1_premium_p10_enriched.csv", index=False)

    n = len(ev); net = float(ev["ret_bp"].sum())
    w("")
    w(f"covered events n={n}  net={net:+.0f}bp  "
      f"hit={float((ev['ret_bp'] > 0).mean()):.3f}")
    w("")

    # q_subperiod — quarterly table + leave-one-year-out
    eq = ev.set_index("t")["ret_bp"].groupby(pd.Grouper(freq="QE"))
    quarters = [(str(q.date()), int(g.notna().sum()), float(g.sum()))
                for q, g in eq if g.notna().sum() > 0]
    neg_q = sum(1 for _, _, s in quarters if s <= 0)
    w("## Sub-period robustness")
    w("")
    w("| quarter | n | net_bp |")
    w("|---|---|---|")
    for q, qn, s in quarters:
        w(f"| {q} | {qn} | {s:+.0f} |")
    w("")
    loyo = []
    for y in sorted(ev["t"].dt.year.unique()):
        sub = ev[ev["t"].dt.year != y]
        loyo.append(f"ex-{y}: net {sub['ret_bp'].sum():+.0f}bp "
                    f"(n={len(sub)})")
    w("leave-one-year-out: " + " | ".join(loyo))
    w("")

    # q_cluster — top-5 share of net
    top5 = float(ev["ret_bp"].nlargest(5).sum())
    top5_share = top5 / net if net > 0 else float("inf")
    n_eff = F._count_episodes(ev)
    w("## Cluster concentration")
    w("")
    w(f"top-5 events: {top5:+.0f}bp = {top5_share:.0%} of total net "
      f"(cap 60%) | effective episodes n_eff={n_eff:.0f}")
    w("")

    # q_dose — deeper than p5 vs shallow p5..p10 inside the armed band
    deep = ev[ev["deep"]]; shallow = ev[~ev["deep"]]
    d_mean = float(deep["ret_bp"].mean()) if len(deep) else float("nan")
    s_mean = float(shallow["ret_bp"].mean()) if len(shallow) else float("nan")
    w("## Dose-response (deeper dislocation should earn more)")
    w("")
    w(f"deep (prem<=p5): n={len(deep)} mean={d_mean:+.1f}bp "
      f"net={deep['ret_bp'].sum():+.0f}bp "
      f"hit={float((deep['ret_bp'] > 0).mean()):.3f}")
    w(f"shallow (p5<prem<=p10): n={len(shallow)} mean={s_mean:+.1f}bp "
      f"net={shallow['ret_bp'].sum():+.0f}bp "
      f"hit={float((shallow['ret_bp'] > 0).mean()):.3f}")
    w("")

    # q_converge — premium normalizes upward during holds
    med_delta = float(ev["prem_delta"].median())
    conv_share = float((ev["prem_delta"] > 0).mean())
    w("## Convergence (premium should normalize toward median during hold)")
    w("")
    w(f"median premium delta over hold: {med_delta:+.2e} | "
      f"share converged upward: {conv_share:.3f} | "
      f"median prem_in={ev['prem_in'].median():.2e} "
      f"p50={ev['p50'].median():.2e}")
    w("")

    # q_placebo — same call as extended eval
    plc = F.placebo_time_shift(ev, {"BTC": D.candles_full("btc", "4h"),
                                    "SOL": D.candles_full("sol", "4h")},
                               2, 240)
    w("## Placebo re-check")
    w("")
    w(f"time-shift p={plc.get('p_value', float('nan')):.3f} "
      f"real_mean={plc.get('real_mean_bp', float('nan')):+.1f}bp "
      f"n_perm={plc.get('n_perm')}")
    w("")

    # verdict per declared kill rule
    kills = []
    if quarters and neg_q > len(quarters) / 2:
        kills.append(f"{neg_q}/{len(quarters)} quarters net<=0")
    if net > 0 and top5_share > 0.60:
        kills.append(f"top-5 = {top5_share:.0%} of net (>60%)")
    if not (d_mean > s_mean):
        kills.append(f"no dose-response (deep {d_mean:+.1f} <= shallow "
                     f"{s_mean:+.1f})")
    if not (med_delta > 0):
        kills.append(f"no convergence (median delta {med_delta:+.2e})")
    verdict = "KILL" if kills else "SURVIVES (stays WATCH — forward decides)"
    w("## Verdict (declared kill rule)")
    w("")
    for k in kills:
        w(f"- trigger: {k}")
    w(f"**{verdict}**")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
