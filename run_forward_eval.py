"""Forward evaluation of declared leads — post-cutoff events only.

Manifest `forward_declared.cutoff_utc` = 2026-09-23T00:00Z. Candidates
emit their full event stream; this runner evaluates ONLY t >= cutoff
rows so nothing observed in-sample contaminates the verdict. UNDERPOWERED
until n >= 30 post-cutoff events. Also appends a diagnostic battery:
post-2026-09-24 stats on every other regenerated events_*.csv — null
battery + era-shift detection, NOT promotion-eligible (a revival is a
new hypothesis needing fresh declaration). Run daily via
tools/morning_research.py or standalone:
.venv/Scripts/python.exe run_forward_eval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_forward as CF
from harness import data as D
from harness import falsify as F

REPORT = Path(__file__).resolve().parent / "reports" / "report_forward.md"


ASSETS = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")


def main() -> int:
    import pandas as pd
    hd = D.harmony_daily()
    ext = Path(__file__).resolve().parent / "data_extended"
    assets = [a for a in ASSETS
              if (ext / "funding" / f"{a}_funding_full.json").exists()
              and (ext / "candles" / f"{a}_4h_full.json").exists()
              and (ext / "candles" / f"{a}_1h_full.json").exists()]
    disloc, prem, streak, altrev, mom24, residc, carry = (
        [], [], [], [], [], [], [])
    for a in assets:
        disloc.append(CF.fwd_xvenue_disloc_cont(
            D.funding_full(a), D.binance_funding(a),
            D.candles_full(a, "4h"), a.upper()))
        prem.append(CF.fwd_premium_cont(
            D.funding_full(a), D.candles_full(a, "4h"), a.upper()))
        streak.append(CF.fwd_funding_streak_fade(
            D.funding_full(a), D.candles_full(a, "4h"), a.upper()))
        carry.append(CF.fwd_carry_p90_p10(
            D.funding_full(a), D.candles_full(a, "4h"), a.upper()))
        mom24.append(CF.fwd_mom24h_cont(
            D.candles_full(a, "4h"), a.upper()))
        if a != "btc" and (ext / "candles" / "btc_1h_full.json").exists():
            altrev.append(CF.fwd_alt_reversal(
                D.candles_full("btc", "1h"), D.candles_full(a, "1h"),
                a.upper()))
            residc.append(CF.fwd_alt_resid_cont(
                D.candles_full("btc", "1d"), D.candles_full(a, "1d"),
                a.upper()))
    C0, C6_, C8_, C10_, C11_ = (CF.CUTOFF, CF.CUTOFF_R6, CF.CUTOFF_R8,
                              CF.CUTOFF_R10, CF.CUTOFF_R11)
    mvrv_s = hd.set_index("t")["mvrv"].astype(float)
    flagship = CF.fwd_flagship_hlbtc(D.candles_full("btc", "1d"), mvrv_s)
    he = D.harmony_extended()
    he["t"] = pd.to_datetime(he["t"])
    if getattr(he["t"].dt, "tz", None) is not None:
        he["t"] = he["t"].dt.tz_convert(None)
    he = he.sort_values("t").reset_index(drop=True)
    he["c"] = pd.to_numeric(he["px_bitstamp"], errors="coerce")
    nrpl = CF.fwd_nrpl_cont(he)
    skew = CF.fwd_skew_reversal(he)
    puell = CF.fwd_puell_extreme_cont(he)
    rrisk = CF.fwd_reserve_risk_cont(he)
    oi_short = CF.fwd_oi_divergence_short(hd)
    eq_short = CF.fwd_equity_lead_short(hd)
    cluster = CF.fwd_riskoff_cluster(hd)
    dorm_long = CF.fwd_dormancy_spike_long(he)

    def _prem(a: str) -> pd.DataFrame:
        return D.prem_merged(a)

    basis_assets = [a for a in ASSETS
                    if (ext / "binance" / f"{a}usdt_premium_1d.json").exists()]
    basis = [CF.fwd_premium_basis_converge(_prem(a), a.upper())
             for a in basis_assets]

    # Input-freshness probes — a lead whose limiting input never reaches
    # its cutoff can never produce a post-cutoff event. Report INPUT_DEAD
    # (with the input's last valid date) instead of eternal ACCRUING;
    # auto-recovers when the source refreshes past the cutoff. Evaluated
    # from the shared CF.LEAD_INPUT_SPECS / LEAD_DRIFT_SPECS maps so the
    # verifier's freshness gate and report reconciliation see identical
    # numbers — never a second, drifting implementation.
    LEAD_INPUTS = D.forward_input_probes()
    DRIFT_PRICE = D.forward_drift_prices()
    LC = CF.LEAD_CUTOFFS
    frames = {
        "fwd_fng_fear_long":      CF.fwd_fng_fear_long(hd),
        "fwd_momentum_extremes":  CF.fwd_momentum_extremes(hd),
        "fwd_xvenue_disloc_cont": pd.concat(disloc),
        "fwd_premium_cont":       pd.concat(prem),
        "fwd_funding_streak_fade": pd.concat(streak),
        "fwd_alt_reversal":       pd.concat(altrev),
        "fwd_mom24h_cont":        pd.concat(mom24),
        "fwd_alt_resid_cont":     pd.concat(residc),
        "fwd_flagship_hlbtc":     flagship,
        "fwd_nrpl_cont":          nrpl,
        "fwd_premium_basis_converge": (pd.concat(basis) if basis
                                       else pd.DataFrame()),
        "fwd_skew_reversal":      skew,
        "fwd_puell_extreme_cont": puell,
        "fwd_reserve_risk_cont":  rrisk,
        "fwd_oi_divergence_short": oi_short,
        "fwd_equity_lead_short":  eq_short,
        "fwd_riskoff_cluster":    cluster,
        "fwd_dormancy_spike_long": dorm_long,
        "fwd_carry_p90_p10":      (pd.concat(carry) if carry
                                 else pd.DataFrame()),
    }
    specs = {cid: ((f.sort_values("t").reset_index(drop=True)
                    if not f.empty else f), LC[cid])
             for cid, f in frames.items()}
    retired = CF.retired_leads()
    # Premise health — whether the in-sample basis for each declaration
    # still stands after the A23/A24 decontamination. Most leads are
    # inverse declarations on anti-predictive KILLs, so "premise" = the
    # in-sample side's current verdict/strength. An ACCRUING lead on a
    # dead premise is a false-green; a PROMOTED on one is a contradiction
    # that demands investigation, not celebration.
    LEAD_PREMISE = {
        "fwd_fng_fear_long": "MIXED — IS fear side +14k/.615 but replay "
            "direction flips across cutoffs (unstable)",
        "fwd_xvenue_disloc_cont": "SUSPECT — in-sample disloc now BLOCKED "
            "(boundary-invariance fails once aux frames truncate, A24); "
            "implied cont ~.467 post-fix, was .623",
        "fwd_momentum_extremes": "INTACT — inverse of killed mvrv_regime",
        "fwd_premium_cont": "WEAK — hl_premium_disloc fully clean: .495, "
            "-135.6k; implied continuation ~coin flip (was .558)",
        "fwd_funding_streak_fade": "VOID — funding_run_persistence clean "
            "is .498; nothing to fade",
        "fwd_alt_reversal": "INTACT — xasset_btc_leads_alts still "
            "anti-predictive (.447 KILL) post-fix",
        "fwd_mom24h_cont": "NEGATIVE — round13 replay: OOS negative at "
            "all 3 Binance cutoffs (HL pool still accrues; venue caveat)",
        "fwd_alt_resid_cont": "INTACT — alt_resid_reversal still "
            "anti-predictive (.463 KILL) post-fix",
        "fwd_flagship_hlbtc": "STRONG — walk-forward transfer at all 4 "
            "cutoffs, DSR >= .995",
        "fwd_nrpl_cont": "STRONG — replay: direction re-derives at all 4 "
            "cutoffs, OOS positive every time",
        "fwd_premium_basis_converge": "INTACT — same-direction WATCH; "
            "mature-selection transfer in replay",
        "fwd_skew_reversal": "INTACT-THIN — revert re-derives at viable "
            "cutoffs; input dead upstream",
        "fwd_puell_extreme_cont": "STRONG — replay: cont re-derives at "
            "all 4 cutoffs",
        "fwd_reserve_risk_cont": "DECAYING — replay OOS positive but "
            "thinning; input dead upstream",
        "fwd_oi_divergence_short": "WATCH-BASIS — round-14 short variant: "
            "+243bp/ep t=0.97, ep-gate fail on n=40",
        "fwd_equity_lead_short": "STRONG-SKILL — round-14: +240bp/ep "
            "t=3.04; magnitude edge, hit-rate gate can't bless IS",
        "fwd_riskoff_cluster": "DILUTED — round-14: +276bp/ep t=3.09 "
            "but net < equity-lead single (shared risk-off state)",
        "fwd_dormancy_spike_long": "STRONG-INVERSE — round-15 declared "
            "side lost -87133bp (bb_p=0.001, era-consistent); "
            "anti-predictive like nrpl/puell inverses",
        "fwd_carry_p90_p10": "WATCH-BASIS — A29 override-restored carry "
            "WATCH: +13.7bp/ev drift skill (t=1.93), income mechanism "
            "not beta; forward accrual decides if the WATCH earns a "
            "forward gate",
    }
    lines = ["# Forward evaluation — declared 2026-09-23, cutoff-frozen", "",
             "data-as-of: " + "; ".join(
                 f"{LEAD_INPUTS[cid][0]}={LEAD_INPUTS[cid][1]:%Y-%m-%d}"
                 if pd.notna(LEAD_INPUTS[cid][1]) else
                 f"{LEAD_INPUTS[cid][0]}=n/a" for cid in
                 ("fwd_momentum_extremes", "fwd_flagship_hlbtc",
                  "fwd_nrpl_cont")), "",
             f"Cutoffs: {C0} (round-1) / {C6_} (round-6 inverses) / "
             f"{C8_} (round-8 decomposition leads) / "
             f"{C10_} (round-10 flagship shadow) / "
             f"{C11_} (round-11 nrpl inverse). "
             "Only post-cutoff events enter stats.", ""]
    for cid, (ev_all, cutoff) in specs.items():
        F.write_event_csv(ev_all, REPORT.parent / f"events_{cid}.csv")
        label, last_ts = LEAD_INPUTS.get(cid, ("?", pd.NaT))
        lines.append(f"## {cid}")
        prem = LEAD_PREMISE.get(cid)
        if prem:
            lines.append(f"premise: {prem}")
        ret = retired.get(cid)
        if pd.isna(last_ts) or last_ts < cutoff:
            lv = (last_ts.strftime("%Y-%m-%d %H:%MZ") if pd.notna(last_ts)
                  else "n/a")
            # distinguish a truly dead input (stale vs now — the
            # verifier's 7d bound) from an alive-but-publish-lagged
            # input that simply hasn't crossed a fresh cutoff yet
            alive = (pd.notna(last_ts)
                     and (pd.Timestamp.now(tz="UTC") - last_ts)
                     <= pd.Timedelta(days=7))
            if ret:
                lines.append(
                    f"post-cutoff: **RETIRED** — input '{label}' extinct "
                    f"upstream (last valid {lv}; ledger {ret.get('ledger')}); "
                    f"substitution forbidden, declaration kept frozen and "
                    f"re-evaluated daily — flags if the source revives")
            elif alive:
                lines.append(
                    f"post-cutoff: **AWAITING** — input '{label}' last "
                    f"valid {lv} < cutoff "
                    f"{cutoff.strftime('%Y-%m-%d %H:%MZ')} but still "
                    f"publishing; first crossing on the next input "
                    f"cycle (auto-resumes; nothing is lost)")
            else:
                lines.append(
                    f"post-cutoff: **INPUT_DEAD** — input '{label}' last "
                    f"valid {lv} < cutoff "
                    f"{cutoff.strftime('%Y-%m-%d %H:%MZ')} and stale "
                    f">7d — accrual impossible until the source "
                    f"refreshes (auto-resumes; nothing is lost)")
            lines.append("")
            continue
        if ret:
            lines.append(f"**RETIRED-INPUT REVIVED** — '{label}' reaches the "
                         f"cutoff again; review un-retirement "
                         f"(ledger {ret.get('ledger')})")
        # datetime-domain comparison — .astype("int64") preserves the
        # stored unit (ms/us/ns differ across sources) while cutoff.value
        # is always ns; an int compare silently zeroes the post window.
        tt = (pd.to_datetime(ev_all["t"], utc=True, format="mixed")
              if not ev_all.empty else ev_all)
        post = (ev_all[tt >= cutoff] if not ev_all.empty else ev_all)
        post = post.dropna(subset=["ret_bp"]) if not post.empty else post
        st = F.forward_gate(post, DRIFT_PRICE.get(cid))
        lines.append(f"post-cutoff: n={st['n']} n_eff={st['n_eff']:.0f} "
                     f"hit={st.get('hit', float('nan')):.3f} "
                     f"wilson_lo={st.get('wilson_lo', float('nan')):.3f} "
                     f"net={st['net']:+.0f}bp "
                     f"drift_t={st.get('drift', float('nan')):.2f} "
                     f"-> **{st['verdict']}**")
        if not ev_all.empty:
            n_pre = int((tt < cutoff).sum())
            lines.append(f"(pre-cutoff context events: {n_pre} — excluded by design)")
        eras = F.era_breakdown(post) if len(post) else []
        if eras:
            lines.append("  eras: " + " | ".join(
                f"{e['era']} n={e['n']} net={e['net_bp']:+.0f}" for e in eras))
        lines.append("")

    # ── Diagnostic battery: post-cutoff stats on EVERY event stream ─────
    # All candidate implementations were frozen post-audit, so a single
    # boundary partitions every regenerated events_*.csv into context vs
    # accrual. DIAGNOSTIC ONLY — not promotion-eligible: a killed
    # candidate reviving post-boundary is a new hypothesis needing its
    # own fresh declaration window. Value = null battery (pipeline
    # regression check) + era-shift detection.
    DIAG = pd.Timestamp("2026-09-24T00:00:00Z")
    fwd_ids = {f"events_{cid}.csv" for cid in specs}
    lines += ["", f"# Diagnostic battery — all event streams, post {DIAG.date()}",
              "(diagnostic only — revival here is a NEW hypothesis, not a promotion)", ""]
    n_tracked = n_live = 0
    event_files = sorted(REPORT.parent.glob("events*/*.csv"))
    for f in event_files:
        if f.parent == REPORT.parent or f.name in fwd_ids:
            continue
        try:
            ev = pd.read_csv(f)
            if (ev.empty or "t" not in ev.columns or "ret_bp" not in ev.columns
                    or "hit" not in ev.columns):
                continue
            n_tracked += 1
            tt = pd.to_datetime(ev["t"], utc=True, format="mixed")
            post = ev[tt >= DIAG].dropna(subset=["ret_bp"])
            if post.empty:
                continue
            n_live += 1
            cid = f.stem.replace("events_", "")
            wil = C.wilson_gate(post) if len(post) >= 2 else {}
            hit = wil.get("hit", float("nan"))
            net = float(post["ret_bp"].sum())
            flag = " **WATCHING**" if len(post) >= 30 and net > 0 else ""
            lines.append(f"- {cid}: n={len(post)} hit={hit:.3f} net={net:+.0f}bp{flag}")
        except Exception as e:
            lines.append(f"- {f.name}: battery read failed ({type(e).__name__}: {e})")
    lines.append(f"(tracking {n_tracked} streams; {n_live} with post-boundary events)")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
