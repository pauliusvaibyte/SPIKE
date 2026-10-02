"""Phase -1 orchestrator — executes the frozen manifest against the frozen
snapshot. Order is fixed: fixtures (validator calibration) BEFORE real
candidates. Output: reports/report.md.

Run: .venv/Scripts/python.exe run_phase_minus_1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import data as D
from harness import falsify as F

N_FAMILIES = 9          # declared effective families (manifest trial_accounting)
REPORT = Path(__file__).resolve().parent / "reports" / "report.md"


# ── candidate runners: (fn, args) → events df; variants for PBO ──────────

def _pool(*dfs: pd.DataFrame) -> pd.DataFrame:
    nonempty = [d for d in dfs if not d.empty]
    if not nonempty:
        return pd.DataFrame()
    # stable sort: pooled assets share bar timestamps; quicksort reorders
    # ties nondeterministically across truncation lengths (false leak alarms)
    return pd.concat(nonempty).sort_values("t", kind="stable").reset_index(drop=True)


def load_all():
    return {
        "btc_1d": D.candles("btc", "1d", "365d"),
        "sol_1d": D.candles("sol", "1d", "365d"),
        "btc_1h": D.candles("btc", "1h", "365d"),
        "sol_1h": D.candles("sol", "1h", "180d"),
        "btc_4h": D.candles("btc", "4h", "180d"),
        "sol_4h": D.candles("sol", "4h", "180d"),
        "btc_15m": D.candles_15m("btc"),
        "sol_15m": D.candles_15m("sol"),
        "btc_fund": D.funding("btc", "90d"),
        "sol_fund": D.funding("sol", "90d"),
        "btc_l2": D.l2_journal("BTC"),
        "sol_l2": D.l2_journal("SOL"),
    }


def real_candidates(d: dict) -> dict[str, dict]:
    """manifest id -> {legs:[(asset, fn, src_df)], events_fn, variants_fn,
    price_for_placebo, horizon_bars}. Leak checks run per-leg on src_df."""
    def legs(pair):  # pair = [(asset, df, fn_factory), ...]
        return [(a, f, df) for a, df, f in pair]

    return {
        "tsmom_daily_14d": {
            "legs": [("BTC", d["btc_1d"], lambda df: C.tsmom_daily_14d(df, "BTC")),
                     ("SOL", d["sol_1d"], lambda df: C.tsmom_daily_14d(df, "SOL"))],
            "variants": lambda: {
                f"lb{lb}": F.events_to_daily_returns(_pool(
                    _tsmom_lb(d["btc_1d"], "BTC", lb), _tsmom_lb(d["sol_1d"], "SOL", lb)))
                for lb in (7, 10, 14, 20)},
            "price": d["btc_1d"], "hbars": 7, "barmin": 1440,
            "plc_price": {"BTC": d["btc_1d"], "SOL": d["sol_1d"]},
        },
        "fra_momentum_p90_long": {
            "legs": [("BTC", d["btc_fund"],
                      lambda df: C.fra_momentum_p90_long(
                          df, *F.truncate_aux(df, d["btc_15m"])))],
            "variants": lambda: {
                f"p{p}": F.events_to_daily_returns(_fra_var(d, p))
                for p in (85.0, 90.0, 95.0, 97.5)},
            "price": d["btc_15m"], "hbars": 96, "barmin": 15,
        },
        "fra_fade_p90_short": {
            "legs": [("BTC", d["btc_fund"],
                      lambda df: C.fra_fade_p90_short(
                          df, *F.truncate_aux(df, d["btc_15m"]), "BTC")),
                     ("SOL", d["sol_fund"],
                      lambda df: C.fra_fade_p90_short(
                          df, *F.truncate_aux(df, d["sol_15m"]), "SOL"))],
            "variants": lambda: {},
            "price": d["btc_15m"], "hbars": 96, "barmin": 15,
            "plc_price": {"BTC": d["btc_15m"], "SOL": d["sol_15m"]},
        },
        "trend1_donchian_4h": {
            "legs": [("BTC", d["btc_4h"], lambda df: C.trend1_donchian_4h(df, "BTC")),
                     ("SOL", d["sol_4h"], lambda df: C.trend1_donchian_4h(df, "SOL"))],
            "variants": lambda: {},
            "price": d["btc_4h"], "hbars": 1, "barmin": 240,
            "plc_price": {"BTC": d["btc_4h"], "SOL": d["sol_4h"]},
        },
        "flush1_reversal_15m": {
            "legs": [("BTC", d["btc_15m"], lambda df: C.flush1_reversal_15m(df, "BTC")),
                     ("SOL", d["sol_15m"], lambda df: C.flush1_reversal_15m(df, "SOL"))],
            "variants": lambda: {},
            "price": d["btc_15m"], "hbars": 16, "barmin": 15,
            "plc_price": {"BTC": d["btc_15m"], "SOL": d["sol_15m"]},
        },
        "basis1_premium_p10": {
            "legs": [("BTC", d["btc_fund"],
                      lambda df: C.basis1_premium_p10(
                          df, *F.truncate_aux(df, d["btc_15m"]), "BTC")),
                     ("SOL", d["sol_fund"],
                      lambda df: C.basis1_premium_p10(
                          df, *F.truncate_aux(df, d["sol_15m"]), "SOL"))],
            "variants": lambda: {},
            "price": d["btc_15m"], "hbars": 32, "barmin": 15,
            "plc_price": {"BTC": d["btc_15m"], "SOL": d["sol_15m"]},
        },
        "mrv_rsi_reversion_1h": {
            "legs": [("BTC", d["btc_1h"], lambda df: C.mrv_rsi_reversion_1h(df, "BTC")),
                     ("SOL", d["sol_1h"], lambda df: C.mrv_rsi_reversion_1h(df, "SOL"))],
            "variants": lambda: {},
            "price": d["btc_1h"], "hbars": 4, "barmin": 60,
            "plc_price": {"BTC": d["btc_1h"], "SOL": d["sol_1h"]},
        },
        "ofi_imbalance_l2": {
            "legs": [("BTC", d["btc_l2"], lambda df: C.ofi_imbalance_l2(df, "BTC")),
                     ("SOL", d["sol_l2"], lambda df: C.ofi_imbalance_l2(df, "SOL"))],
            "variants": lambda: {},
            "price": None, "hbars": 0, "barmin": 0,
        },
    }


def _tsmom_lb(df: pd.DataFrame, asset: str, lb: int) -> pd.DataFrame:
    c = df["c"].to_numpy(); t = df["t"]
    rows, last_i = [], -8
    for i in range(lb, len(c)):
        if i - last_i < 7 or c[i - lb] <= 0:
            continue
        ret = c[i] / c[i - lb] - 1.0
        if abs(ret) < 0.01:
            continue
        j = i + 7
        if j >= len(c):
            break
        fwd = c[j] / c[i] - 1.0
        d = 1.0 if ret > 0 else -1.0
        rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                     "t_eval": t.iloc[j], "ret_bp": d * fwd * 1e4 - 10.0,
                     "gross_bp": d * fwd * 1e4})
        last_i = i
    out = pd.DataFrame(rows)
    if not out.empty:
        out["hit"] = out["gross_bp"] > 1.0
    return out


def _fra_var(d: dict, pct: float) -> pd.DataFrame:
    fund = d["btc_fund"].copy()
    p = fund["rate"].rolling(2160, min_periods=720).rank(pct=True)
    sel = fund[p >= pct / 100.0]
    # inline variant (differs from fra_momentum only in threshold)
    bars = d["btc_15m"]; bt = bars["t"].astype("int64").to_numpy()
    rows, cool = [], pd.Timestamp("1970-01-01", tz="UTC")
    for i in sel.index:
        ts = fund["t"].iloc[i]
        if ts <= cool:
            continue
        ei = int(np.searchsorted(bt, int(ts.timestamp() * 1000), side="left"))
        if ei >= len(bars) - 96:
            break
        xj, ret, _r = C._exit_path(bars, ei, 1.0, 0.04, 0.08, 0.03, 96)
        rows.append({"t": ts, "asset": "BTC", "dir": 1.0,
                     "t_eval": bars["t"].iloc[xj],
                     "ret_bp": ret * 1e4 - 10.0, "gross_bp": ret * 1e4})
        cool = bars["t"].iloc[xj]
    out = pd.DataFrame(rows)
    if not out.empty:
        out["hit"] = out["gross_bp"] > 1.0
    return out


# ── verdict policy (deterministic, declared) ─────────────────────────────

def verdict(candidate_id: str, ev: pd.DataFrame, power: dict,
            wil: dict, ss: dict, placebo: dict, prefix: dict,
            implaus: dict, pbo: dict, drift: dict | None = None) -> str:
    if ev.empty:
        return "UNDERPOWERED"
    # contract FIRST — a malformed frame earns BLOCKED, never a
    # substantive verdict (forward_gate already checks first; the
    # in-sample path was handing contract violations real verdicts,
    # and a missing 'asset' column silently collapsed episodes)
    if not F.validate_events(ev)["passed"]:
        return "BLOCKED"
    if not prefix["passed"]:
        return "BLOCKED"
    if implaus["implausible"]:
        return "BLOCKED"
    if not power["sufficient"]:
        return "UNDERPOWERED"
    net_bp = float(pd.to_numeric(ev["ret_bp"], errors="coerce").sum())
    dsr = ss.get("dsr", float("nan"))
    # A31: the gate reads EPISODE-level hit stats — row-level wilson
    # inflates clustered streams the same way the raw-row t-stat did
    # (one shock = N rows = fake evidence). Report tables print the
    # episode stats beside row-level descriptives.
    eph = F.episode_hit_stats(ev)
    ep_gate = ("PASS" if (eph["n_ep"] >= 30 and eph["wilson_lo"] >= 0.50)
               else ("UNDERPOWERED" if eph["n_ep"] < 30 else "FAIL"))
    if ep_gate == "UNDERPOWERED":
        return "UNDERPOWERED"
    if net_bp <= 0 and ep_gate == "FAIL":
        return "KILL"
    positive = (net_bp > 0 and not np.isnan(dsr) and dsr > 0.95
                and not np.isnan(placebo.get("p_value", float("nan")))
                and placebo["p_value"] < 0.10)
    contradictions = (ss.get("sharpe", 0) > 1.0 and
                      not np.isnan(placebo.get("p_value", float("nan"))) and
                      placebo["p_value"] > 0.30)
    if contradictions:
        return "MODEL_RISK"
    # drift-audit gate (2026-09-23): a powered positive whose per-event
    # skill over unconditional same-window drift is <=0 is beta capture,
    # not timing. Demotes WATCH/positive paths to KILL.
    if (drift is not None and drift.get("n", 0) >= 30
            and net_bp > 0
            and not np.isnan(drift.get("mean_skill_bp", float("nan")))
            and drift["mean_skill_bp"] <= 0):
        return "KILL"
    if positive and ep_gate == "PASS":
        # RESEARCH_SUPPORTED additionally requires DEMONSTRATED skill —
        # resolved drift (n>=30 episodes) with t_skill > SKILL_T_MIN,
        # matching forward_gate's PROMOTED bar and the manifest spec
        # ("unresolved drift skill can never promote"). High measured
        # PBO (selection overfit > 0.5) also caps at WATCH.
        skill = (drift.get("t_skill", float("nan"))
                 if drift is not None else float("nan"))
        pbo_v = pbo.get("pbo", float("nan"))
        if (drift is not None and drift.get("n", 0) >= 30
                and np.isfinite(skill) and skill > F.SKILL_T_MIN
                and (not np.isfinite(pbo_v) or pbo_v <= 0.5)):
            return "RESEARCH_SUPPORTED"
        return "WATCH"
    if net_bp > 0:
        return "WATCH"
    return "KILL"


# ── main ─────────────────────────────────────────────────────────────────

def main() -> int:
    # ✓/✗ markers crash cp1252 consoles when stdout is piped (Windows)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = load_all()
    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Empirical Existence Test — report")
    w("")
    w(f"snapshot: `data_snapshot/` (50-file hash manifest); manifest: `manifest.yaml` frozen 2026-09-23")
    w(f"declared families for deflation: {N_FAMILIES}; costs: 5bp/side")
    w("")

    # ── STEP 2 (run first): validator calibration on fixtures ────────────
    w("## Step 1 — Validator calibration (fixtures)")
    w("")
    w("| fixture | n | hit | wilson_lo | net_bp | sharpe | prefix_inv | implausible | expected | result |")
    w("|---|---|---|---|---|---|---|---|---|---|")

    cal_ok = True
    fix_results = {}

    # leak fixture
    ev_leak = _pool(C.leak_tsmom_nextclose(d["btc_1d"], "BTC"),
                    C.leak_tsmom_nextclose(d["sol_1d"], "SOL"))
    def _tsmom_prefix(frac, fn):
        return _pool(fn(d["btc_1d"].iloc[: int(len(d["btc_1d"]) * frac)] if frac else d["btc_1d"], "BTC"),
                     fn(d["sol_1d"].iloc[: int(len(d["sol_1d"]) * frac)] if frac else d["sol_1d"], "SOL"))

    def _pre_leak(frac):
        return _tsmom_prefix(frac, C.leak_tsmom_nextclose)
    leak_full = _pre_leak(None); viol = []
    for frac in (0.5, 0.75):
        part = _pre_leak(frac)
        lim = part["t"].max()
        a = leak_full[leak_full["t"] <= lim].reset_index(drop=True)
        b = part.reset_index(drop=True)
        if len(a) != len(b) or not a[["t", "dir"]].equals(b[["t", "dir"]]):
            viol.append(frac)
    # boundary truncation: event must still fire when its bar is the last row
    ev_leak_btc = C.leak_tsmom_nextclose(d["btc_1d"], "BTC")
    bres = F.boundary_invariance(lambda df: C.leak_tsmom_nextclose(df, "BTC"),
                                 d["btc_1d"], ev_leak_btc)
    leak_caught = len(viol) > 0 or not bres["passed"]
    ret_leak = F.events_to_daily_returns(ev_leak)
    imp_leak = F.implausibility_check(ret_leak)
    wil_leak = C.wilson_gate(ev_leak)
    ok = leak_caught or imp_leak["implausible"]
    cal_ok &= ok
    fix_results["leak"] = ok
    w(f"| leak_tsmom | {len(ev_leak)} | {wil_leak['hit']:.3f} | {wil_leak['wilson_lo']:.3f} | "
      f"{ev_leak['ret_bp'].sum():.0f} | {imp_leak['sharpe']:.2f} | "
      f"{'FAIL' if leak_caught else 'pass'} | {imp_leak['implausible']} | caught | {'✓' if ok else '✗ MISSED'} |")

    # null fixtures
    for name, fn, args, label in [
        ("null_random", C.null_random_entries, (d["btc_1h"], "BTC"), "no edge"),
        ("null_shifted", C.null_shifted_tsmom, (d["btc_1d"], "BTC"), "no edge"),
    ]:
        ev = fn(*args)
        wil = C.wilson_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        dead = wil["gate"] != "PASS" or ev["ret_bp"].sum() <= 0
        cal_ok &= dead
        fix_results[name] = dead
        w(f"| {name} | {len(ev)} | {wil['hit']:.3f} | {wil['wilson_lo']:.3f} | "
          f"{ev['ret_bp'].sum():.0f} | {imp['sharpe']:.2f} | n/a | {imp['implausible']} | dies | {'✓' if dead else '✗ SURVIVED'} |")

    # planted weak edge
    ev_pl = _pool(C.planted_weak_edge(d["btc_1d"], "BTC"),
                  C.planted_weak_edge(d["sol_1d"], "SOL"))
    wil_pl = C.wilson_gate(ev_pl)
    ret_pl = F.events_to_daily_returns(ev_pl)
    imp_pl = F.implausibility_check(ret_pl)
    # calibrate against the REAL gate unit — episode-level hit stats,
    # not the row-level wilson the fixtures used to certify
    eph_pl = F.episode_hit_stats(ev_pl)
    survived = (ev_pl["ret_bp"].sum() > 0
                and eph_pl["n_ep"] >= 30 and eph_pl["hit"] > 0.5)
    cal_ok &= survived
    fix_results["planted"] = survived
    w(f"| planted_weak_edge | {len(ev_pl)} | {wil_pl['hit']:.3f} | {wil_pl['wilson_lo']:.3f} | "
      f"{ev_pl['ret_bp'].sum():.0f} | {imp_pl['sharpe']:.2f} | n/a | {imp_pl['implausible']} | survives | {'✓' if survived else '✗ KILLED'} |")

    w("")
    w(f"**Calibration: {'PASS' if cal_ok else 'FAIL — harness cannot discriminate; stop'}**")
    w("")

    if not cal_ok:
        w("Harness failed calibration; real-candidate evaluation skipped (would be meaningless).")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1

    # ── STEP 1+3: power gate then evaluation on real candidates ──────────
    w("## Step 2 — Real candidates")
    w("")
    w("| candidate | n | hit | wilson_lo | n_ep | ep_hit | ep_wlo | ep_gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | prefix | PBO | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    specs = real_candidates(d)
    summary = []
    for cid, spec in specs.items():
        ev_all = _pool(*[l[2](l[1]) for l in spec["legs"]])
        ev = ev_all.dropna(subset=["ret_bp"]) if not ev_all.empty else ev_all
        wil = C.wilson_gate(ev)
        power = F.power_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        ss = F.sharpe_stats(ret, n_trials=N_FAMILIES)
        splits = F.split_consistency(ev)
        # leak checks per leg: (a) append-side prefix invariance, (b) boundary
        # truncation — event must still fire when its signal bar is the last row
        viol_prefix, viol_bound = [], []
        for _asset, src, fn in spec["legs"]:
            full = fn(src)
            for frac in (0.5, 0.75):
                part = fn(src.iloc[: int(len(src) * frac)])
                if part.empty:
                    continue
                lim = part["t"].max()
                a = full[full["t"] <= lim].reset_index(drop=True)
                b = part.reset_index(drop=True)
                if len(a) != len(b) or not a[["t", "dir"]].equals(b[["t", "dir"]]):
                    viol_prefix.append({"asset": _asset, "prefix": frac})
            ev_leg = full  # boundary check needs ALL events incl. unevaluable tail
            bres = F.boundary_invariance(fn, src, ev_leg)
            viol_bound.extend(bres["violations"])
        prefix = {"passed": not viol_prefix and not viol_bound,
                  "violations": {"prefix": viol_prefix, "boundary": viol_bound}}
        # placebo (needs price frame with matching granularity); dict
        # prices draw each event's shifted return on its own asset
        plc_px = spec.get("plc_price", spec["price"])
        if plc_px is not None and not ev.empty:
            plc_ev = ev if isinstance(plc_px, dict) else \
                (ev[ev["asset"] == "BTC"] if "asset" in ev.columns else ev)
            placebo = F.placebo_time_shift(plc_ev, plc_px, spec["hbars"],
                                           spec["barmin"])
        else:
            placebo = {"p_value": float("nan")}
        pbo = F.pbo_over_variants(spec["variants"]()) if spec["variants"] else {"pbo": float("nan")}
        drift = F.drift_skill(ev, plc_px)
        verd = verdict(cid, ev, power, wil, ss, placebo, prefix, imp, pbo, drift=drift)
        eph = F.episode_hit_stats(ev)
        ep_g = ("PASS" if (eph["n_ep"] >= 30 and eph["wilson_lo"] >= 0.50)
                else ("UNDERPOWERED" if eph["n_ep"] < 30 else "FAIL"))
        ep_h = f"{eph['hit']:.3f}" if np.isfinite(eph["hit"]) else "nan"
        ep_w = f"{eph['wilson_lo']:.3f}" if np.isfinite(eph["wilson_lo"]) else "nan"
        pbo_s = f"{pbo['pbo']:.2f}" if np.isfinite(pbo.get("pbo", float("nan"))) else "n/a"
        pl_s = f"{placebo['p_value']:.3f}" if np.isfinite(placebo.get("p_value", float("nan"))) else "n/a"
        w(f"| {cid} | {len(ev)} | {wil['hit']:.3f} | {wil['wilson_lo']:.3f} | "
          f"{eph['n_ep']} | {ep_h} | {ep_w} | {ep_g} | "
          f"{ev['ret_bp'].sum():.0f} | {ss.get('sharpe', 0):.2f} | {ss.get('psr', float('nan')):.3f} | "
          f"{ss.get('dsr', float('nan')):.3f} | {pl_s} | "
          f"{'consistent' if splits.get('sign_consistent') else 'mixed'} | "
          f"{'pass' if prefix['passed'] else 'FAIL'} | {pbo_s} | **{verd}** |")
        summary.append({"id": cid, "n": len(ev), "verdict": verd,
                        "net_bp": float(ev["ret_bp"].sum()) if not ev.empty else 0.0,
                        "power": power["reason"]})

    w("")
    w("## Audit notes (reproducibility caveats)")
    w("")
    w("- Data eras are disjoint: 1d/1h/4h caches end ~2026-05-21 while 15m/funding/L2")
    w("  cover Mar-Sep 2026. Powered KILL verdicts bound the OLD regime set, not the")
    w("  recent Aug-Sep rally (manifest errata E3).")
    w("- fra_* evaluated on 15m bars, not the 1h named in the spec text — the 1h cache")
    w("  has zero overlap with the funding window (errata E1).")
    w("- Power gate enforces n>=30 AND event span>=30d; clustered events are not")
    w("  independent observations (errata E2).")
    w("- Event CSVs include unevaluable tail events (NaN ret_bp) — signal identity is")
    w("  preserved for leak checks; metrics drop them.")
    w("- planted_weak_edge trips the implausibility flag (Sharpe ~5) by construction;")
    w("  it still passes survival criteria — the flag working is itself evidence.")
    w("")
    w("## Verdicts")
    w("")
    surv = [s for s in summary if s["verdict"] in ("RESEARCH_SUPPORTED", "WATCH")]
    undp = [s for s in summary if s["verdict"] == "UNDERPOWERED"]
    kill = [s for s in summary if s["verdict"] == "KILL"]
    for s in summary:
        w(f"- `{s['id']}`: **{s['verdict']}** (n={s['n']}, net={s['net_bp']:.0f}bp) — {s['power']}")
    w("")
    w("## Branch decision")
    w("")
    if surv:
        w(f"**{len(surv)} credible survivor(s)** → Phase 0+ platform engineering is JUSTIFIED.")
    elif len(undp) == len(summary):
        w("**All UNDERPOWERED** → next investment is data accumulation, not architecture.")
    elif not surv:
        w("**Zero survivors on powered data** → next investment is better hypotheses / "
          "different information sources, not architecture. This bounds the tested "
          "hypothesis space only — it does not prove the venue has no alpha.")
    w("")
    # events BEFORE the report — freshness requires report >= events
    # mtime; a crash between them must look stale, not fresh-but-wrong
    (Path(REPORT.parent) / "events").mkdir(exist_ok=True)
    for cid, spec in specs.items():
        # write_event_csv emits a schema header even for a fully-empty
        # pool — raw to_csv leaves a zero-byte file pandas can't re-read
        F.write_event_csv(_pool(*[l[2](l[1]) for l in spec["legs"]]),
                          REPORT.parent / "events" / f"{cid}.csv")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
