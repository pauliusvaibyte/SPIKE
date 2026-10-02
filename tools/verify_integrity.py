"""Durable integrity verifier — the repo's persistent verification layer.

Behavioral invariants only (AGENTS.md Verification Doctrine): each check
rejects a class of *real* failure observed or plausible in this harness —
not implementation details. Exit 0 = all pass, 1 = any FAIL.

Checks:
  1. event contract — every reports/events*/ file satisfies F.validate_events
  2. open-bar hygiene — no persisted candle/klines row with t+iv > now
     (A17/A20 failure class: frozen partial bars)
  3. freshness — last bar within 2 intervals of now (stalled refresh)
  4. forward completeness — every events_fwd_*.csv partitions at its cutoff
  5. coverage — stored column spans vs reports/source_spans.json baseline
  6. power gate — the promotion gate's episode counting on synthetic frames
     (A27 failure class: a 1-day/6-shock pooled frame reached DEAD as
     n_eff=36 because a refused power check fell back to raw row count)

Usage: .venv/Scripts/python.exe tools/verify_integrity.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

IV_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000,
         "1d": 86_400_000, "1h_hist": 3_600_000}

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def check_event_contracts() -> None:
    """Contract + phantom-window check. Beyond F.validate_events, covered
    rows must sit near the file's own event horizon: the A24 defect bound
    pre-coverage signals to the first eval bar, producing covered rows
    with (t_eval - t) measured in MONTHS on files whose real horizon is
    hours/days. Use the min positive horizon (robust when >50% of a file
    is pinned — the median can be polluted too). Uncovered rows must be
    wellformed: t_eval == t, NaN ret_bp, exit_reason == 'uncovered'."""
    import pandas as pd
    from harness import falsify as F
    reports = ROOT / "reports"
    files = ([p for d in reports.glob("events*") if d.is_dir()
              for p in d.rglob("*.csv")]
             + list(reports.glob("events*.csv")))
    bad, n = [], 0
    for p in files:
        try:
            ev = pd.read_csv(p)
            if ev.empty:
                continue          # header-only = declared no-events file
            n += 1
            if "t" not in ev.columns:
                bad.append(f"{p.name}: non-empty file with no 't' "
                           "column (malformed, not skipped)")
                continue
            r = F.validate_events(ev)
            if not r["passed"]:
                bad.append(f"{p.name}: {'; '.join(r['violations'][:2])}")
                continue
            tt = pd.to_datetime(ev["t"], utc=True, format="mixed")
            te = pd.to_datetime(ev["t_eval"], utc=True, format="mixed")
            # fabricated timestamps: no event may be stamped in the
            # future, and no covered row may claim a future evaluation —
            # checked on EVERY file, not only the forward book
            now = pd.Timestamp.now(tz="UTC")
            if (tt > now).any():
                bad.append(f"{p.name}: {int((tt > now).sum())} events "
                           "stamped in the future")
                continue
            cov_mask = ev["ret_bp"].notna() if "ret_bp" in ev \
                else pd.Series(False, index=ev.index)
            if (te[cov_mask] > now).any():
                bad.append(f"{p.name}: covered rows with future t_eval")
                continue
            h = te - tt
            cov = ev["ret_bp"].notna() if "ret_bp" in ev else h > pd.Timedelta(0)
            hpos = h[cov & (h > pd.Timedelta(0))]
            if len(hpos) >= 10:
                # window blowout: covered window > 4x the file's median —
                # the A24 class (pre-coverage signals pinned to bar 0,
                # windows measured in months on hour-scale emitters).
                # Variable-window emitters (SL/TP _exit_path) only shorten
                # windows, never extend them.
                hmed = hpos.median()
                blown = int((hpos > max(4 * hmed,
                                       hmed + pd.Timedelta(days=2))).sum())
                if blown:
                    bad.append(f"{p.name}: {blown} covered rows with "
                               f"window >> median {hmed} (pinned?)")
                    continue
                # pin signature: several distinct signals on one asset
                # evaluated at the SAME instant — every emitter here uses
                # per-signal eval bars, so same-asset duplicate t_evals on
                # covered rows only happen when entries pin to bar 0.
                if "asset" in ev.columns:
                    dup = (ev.loc[cov].groupby(
                        [ev.loc[cov, "asset"], te[cov]]).size())
                    pins = dup[dup >= 5]
                    if len(pins):
                        bad.append(f"{p.name}: {int(pins.sum())} covered "
                                   f"rows share t_eval per asset "
                                   f"(max group {int(pins.max())})")
            # uncovered-row wellformedness: a finite ret must never wear
            # the 'uncovered' tag (it is how -10000bp phantoms hid).
            if "exit_reason" in ev.columns and "ret_bp" in ev.columns:
                bad_ret = int((ev["ret_bp"].notna()
                               & (ev["exit_reason"] == "uncovered")).sum())
                if bad_ret:
                    bad.append(f"{p.name}: {bad_ret} uncovered rows with "
                               f"finite ret_bp")
        except Exception as e:
            bad.append(f"{p.name}: read failed {type(e).__name__}")
    check("event contracts", not bad and n > 0,
          f"{n} files clean" if not bad else "; ".join(bad[:5]))


def check_open_bars() -> None:
    now = int(time.time() * 1000)
    bad = []
    n_files = 0
    for p in (ROOT / "data_extended" / "candles").glob("*_full.json"):
        iv = p.stem.rsplit("_", 2)[1]
        bar = IV_MS.get(iv)
        if not bar:
            continue
        n_files += 1
        rows = json.loads(p.read_text())
        open_rows = [r for r in rows if int(r["t"]) + bar > now]
        if open_rows:
            bad.append(f"{p.name}({len(open_rows)} open)")
    for p in (ROOT / "data_extended" / "binance").glob("*.json"):
        stem = p.stem
        iv = "1h" if ("1h" in stem) else stem.rsplit("_", 1)[-1]
        bar = IV_MS.get(iv)
        if not bar or "funding" in stem:
            continue
        n_files += 1
        rows = json.loads(p.read_text())
        key = "timestamp" if rows and "timestamp" in rows[0] else "t"
        open_rows = [r for r in rows if int(r[key]) + bar > now]
        if open_rows:
            bad.append(f"{p.name}({len(open_rows)} open)")
    check("open-bar hygiene", not bad and n_files > 0,
          f"{n_files} files clean" if not bad else "; ".join(bad[:5]))


def check_freshness() -> None:
    """Two honest invariants, using file mtime as the refresh instant:
    (a) completeness — the last stored bar is the most recent one that
        was CLOSED at write time (open-bar exclusion must not create gaps);
    (b) run recency — the file was written within ~36h (daily job ran).
    """
    now = int(time.time() * 1000)
    bar = IV_MS["1h"]
    stale = []
    for p in (ROOT / "data_extended" / "candles").glob("*_1h_full.json"):
        rows = json.loads(p.read_text())
        if not rows:
            continue
        mtime_ms = int(p.stat().st_mtime * 1000)
        last_t = int(rows[-1]["t"])
        expected_last = (mtime_ms // bar) * bar - bar   # last bar closed at write
        missing = last_t < expected_last
        old = now - mtime_ms > 36 * 3_600_000
        if missing or old:
            stale.append(f"{p.stem}(last={last_t} exp>={expected_last}"
                         f"{' OLD_FILE' if old else ''})")
    check("freshness (1h tails)", not stale,
          "all files complete-through-write + recently written"
          if not stale else "; ".join(stale))

    # Absolute-staleness WARN tier for every input the daily refresh
    # owns (A32 red-team: funding/klines/premium/15m-4h-1d candles could
    # die silently forever — only *_1h_full had a recency invariant).
    # WARN not FAIL: an upstream outage shouldn't hard-block, but the
    # morning note surfaces accumulating staleness daily. oi_hist/
    # taker_ls are refreshed for btcusdt+solusdt only.
    warn_stale = []
    refreshed = list(
        (ROOT / "data_extended" / "funding").glob("*.json"))
    for p in (ROOT / "data_extended" / "binance").glob("*.json"):
        if ("oi_hist" in p.name or "taker_ls" in p.name) and not \
                p.name.startswith(("btcusdt", "solusdt")):
            continue
        refreshed.append(p)
    refreshed += [p for p in
                  (ROOT / "data_extended" / "candles").glob("*_full.json")
                  if "_1h_full" not in p.name]
    for p in refreshed:
        try:
            age_h = (time.time() - p.stat().st_mtime) / 3600.0
        except OSError:
            continue
        if age_h > 48:
            warn_stale.append(f"{p.name}({age_h:.0f}h)")
    if warn_stale:
        print(f"WARN  {len(warn_stale)} refreshed inputs stale >48h: "
              f"{warn_stale[:8]} — feed death is invisible to verdicts")


def check_forward_completeness() -> None:
    """Set identity vs CF.LEAD_CUTOFFS (every declared lead has exactly
    one events file — a missing, extra, or mislabeled file FAILs); the
    report exists, is newer than its event files, and is absolutely
    recent (the morning chain runs daily — an old report means the chain
    stalled, not just relative staleness)."""
    import pandas as pd
    from harness import candidates_forward as CF
    reports = ROOT / "reports"
    fwd = list(reports.glob("events_fwd_*.csv"))
    rep = reports / "report_forward.md"
    probs = []
    if not rep.exists():
        probs.append("report_forward.md missing")
    else:
        rep_m = rep.stat().st_mtime
        newer = [p.name for p in fwd if p.stat().st_mtime > rep_m + 1]
        if newer:
            probs.append(f"report older than events: {newer[:3]}")
        age_h = (time.time() - rep_m) / 3600.0
        if age_h > 40:
            probs.append(f"report is {age_h:.0f}h old (>40h — chain stalled)")
    have = {p.stem.replace("events_", "") for p in fwd}
    want = set(CF.LEAD_CUTOFFS)
    if have != want:
        missing = sorted(want - have)
        extra = sorted(have - want)
        if missing:
            probs.append(f"missing lead files: {missing}")
        if extra:
            probs.append(f"undeclared lead files: {extra}")
    check("forward completeness", not probs,
          f"{len(fwd)}/{len(want)} lead files, report fresh"
          if not probs else "; ".join(probs))


STAT_RE = None


def check_report_reconcile() -> None:
    """Recompute every lead's post-cutoff gate from its event file and
    compare against report_forward.md line-for-line — a fabricated,
    stale, or hand-edited report FAILs even when mtimes are right
    (verifier independence: the report is text on disk; the oracle is
    the recomputation). INPUT_DEAD/RETIRED lines are reconciled against
    the shared input probes."""
    import re
    import pandas as pd
    from harness import candidates_forward as CF
    from harness import falsify as F
    from harness import data as D

    rep = ROOT / "reports" / "report_forward.md"
    if not rep.exists():
        check("forward report reconciliation", False, "report missing")
        return
    lines = rep.read_text(encoding="utf-8").splitlines()
    reported: dict[str, str] = {}
    cid = None
    for ln in lines:
        if ln.startswith("## "):
            cid = ln[3:].strip()
        elif cid and ln.startswith("post-cutoff:"):
            reported[cid] = ln
            cid = None
    probs = []
    try:
        probes = D.forward_input_probes()
    except Exception as e:
        probs.append(f"input probes failed: {type(e).__name__}")
        probes = {}
    try:
        drift_px = D.forward_drift_prices()
    except Exception as e:
        probs.append(f"drift prices failed: {type(e).__name__}")
        drift_px = {}
    retired = CF.retired_leads()

    def num(s: str) -> float:
        return float("nan") if s == "nan" else float(s)

    stat_re = re.compile(
        r"post-cutoff: n=(\d+) n_eff=([\d.]+) hit=([\d.-]+|nan) "
        r"wilson_lo=([\d.-]+|nan) net=([+-][\d.]+|nan)bp "
        r"drift_t=([\d.-]+|nan|-?inf) -> \*\*([A-Z_]+)\*\*")
    for lead, cutoff in CF.LEAD_CUTOFFS.items():
        ln = reported.get(lead)
        if ln is None:
            probs.append(f"{lead}: no post-cutoff line in report")
            continue
        label, last_ts = probes.get(lead, ("?", pd.NaT))
        dead = pd.isna(last_ts) or last_ts < cutoff
        m = stat_re.search(ln)
        if m:
            if dead:
                probs.append(f"{lead}: report shows stats but input is "
                             f"dead (last={last_ts})")
                continue
            fp = ROOT / "reports" / f"events_{lead}.csv"
            try:
                ev_all = pd.read_csv(fp)
            except Exception as e:
                probs.append(f"{lead}: events file unreadable "
                             f"({type(e).__name__})")
                continue
            tt = pd.to_datetime(ev_all["t"], utc=True, format="mixed")
            post = ev_all[tt >= cutoff].dropna(subset=["ret_bp"])
            st = F.forward_gate(post, drift_px.get(lead))
            got_n = int(m.group(1))
            if got_n != st["n"]:
                probs.append(f"{lead}: n {got_n} != recomputed {st['n']}")
                continue
            if abs(float(m.group(2)) - st["n_eff"]) > 0.6:
                probs.append(f"{lead}: n_eff {m.group(2)} != "
                             f"{st['n_eff']:.0f}")
                continue
            for grp, key, tol in ((3, "hit", 0.0016), (4, "wilson_lo", 0.0016),
                                  (5, "net", 0.6), (6, "drift", 0.006)):
                rv, cv = num(m.group(grp)), float(st.get(key, float("nan")))
                if pd.isna(rv) and pd.isna(cv):
                    continue
                if abs(rv - cv) > tol:
                    probs.append(f"{lead}: {key} {m.group(grp)} != "
                                 f"{cv:.4g}")
                    break
            else:
                if m.group(7) != st["verdict"]:
                    probs.append(f"{lead}: verdict {m.group(7)} != "
                                 f"recomputed {st['verdict']}")
                continue
            continue
        if "**INPUT_DEAD**" in ln:
            if not dead:
                probs.append(f"{lead}: report says INPUT_DEAD but input "
                             f"last={last_ts:%Y-%m-%d} >= cutoff")
            elif (pd.notna(last_ts) and
                  (pd.Timestamp.now(tz="UTC") - last_ts)
                  <= pd.Timedelta(days=7)):
                probs.append(f"{lead}: report says INPUT_DEAD but input "
                             f"last={last_ts:%Y-%m-%d} is fresh <=7d "
                             "(should be AWAITING)")
            continue
        if "**AWAITING**" in ln:
            if not dead:
                probs.append(f"{lead}: report says AWAITING but input "
                             f"last={last_ts:%Y-%m-%d} >= cutoff")
            elif (pd.isna(last_ts) or
                  (pd.Timestamp.now(tz="UTC") - last_ts)
                  > pd.Timedelta(days=7)):
                probs.append(f"{lead}: report says AWAITING but input "
                             f"is stale >7d or n/a (should be INPUT_DEAD)")
            continue
        if "**RETIRED**" in ln:
            if lead not in retired:
                probs.append(f"{lead}: report says RETIRED but no "
                             "manifest.forward_retired entry")
            elif not dead:
                probs.append(f"{lead}: report says RETIRED but input "
                             f"revived (last={last_ts:%Y-%m-%d})")
            continue
        probs.append(f"{lead}: unrecognized report line format")
    if set(reported) - set(CF.LEAD_CUTOFFS):
        probs.append(f"report covers undeclared leads: "
                     f"{sorted(set(reported) - set(CF.LEAD_CUTOFFS))}")
    check("forward report reconciliation", not probs,
          f"{len(reported)} leads recompute to reported values"
          if not probs else "; ".join(probs[:5]))


def check_insample_reconcile() -> None:
    """In-sample report <-> event-file reconciliation (A31 red-team: the
    corpus was only shape-checked — file swaps, deletions, truncations,
    and injected values all passed). For every events*/ dir: require
    the matching report, parse its candidate table header-aware, and
    recompute covered n / hit / net_bp per file within print tolerance.
    A report row without a file (deletion) or a file without a row
    (phantom/undeclared artifact) both FAIL."""
    import re
    import pandas as pd
    from harness import falsify as F

    reports = ROOT / "reports"
    probs = []
    for d in sorted(reports.glob("events*")):
        if not d.is_dir():
            continue
        rep = reports / ("report" + d.name[len("events"):] + ".md")
        if not rep.exists():
            probs.append(f"{d.name}: no report_*.md — undeclared event "
                         "dir")
            continue
        hdr = None
        rows: dict[str, dict[str, str]] = {}
        for ln in rep.read_text(encoding="utf-8").splitlines():
            if not ln.startswith("|"):
                continue
            cs = [c.strip() for c in ln.split("|")[1:-1]]
            if "candidate" in cs:
                hdr = cs
                continue
            if hdr and "---" not in ln and len(cs) == len(hdr) and cs[0]:
                rows[cs[0]] = dict(zip(hdr, cs))
        if not rows:
            probs.append(f"{rep.name}: no candidate table parsed")
            continue
        files = {p.stem: p for p in d.rglob("*.csv")}
        for cid, row in rows.items():
            fp = files.get(cid)
            if fp is None:
                probs.append(f"{d.name}/{cid}: report row but no "
                             "event file")
                continue
            try:
                ev = pd.read_csv(fp)
            except Exception as e:
                probs.append(f"{d.name}/{cid}: unreadable "
                             f"({type(e).__name__})")
                continue
            cov = (ev[ev["ret_bp"].notna()] if "ret_bp" in ev.columns
                   else ev)
            try:
                rn = int(float(row.get("n", "nan")))
            except ValueError:
                probs.append(f"{d.name}/{cid}: n cell unparseable "
                             f"{row.get('n')!r} — possible tampering")
                continue
            if rn != len(cov):
                probs.append(f"{d.name}/{cid}: n {rn} != "
                             f"{len(cov)} covered rows")
                continue
            try:
                rhit = float(row.get("hit", "nan"))
                if len(cov) and "hit" in cov.columns and \
                        abs(rhit - float(cov["hit"].mean())) > 0.0006:
                    probs.append(f"{d.name}/{cid}: hit {rhit} != "
                                 f"{float(cov['hit'].mean()):.4f}")
                    continue
                rnet = float(row.get("net_bp", "nan"))
                if len(cov) and abs(rnet - float(cov["ret_bp"].sum())) > 0.6:
                    probs.append(f"{d.name}/{cid}: net {rnet} != "
                                 f"{float(cov['ret_bp'].sum()):.1f}")
            except ValueError:
                probs.append(f"{d.name}/{cid}: hit/net cells "
                             "unparseable — possible tampering")
                continue
            # verdict-cell necessary conditions, recomputed from the
            # event file (A32 red-team: the printed verdict was never
            # reconciled — a KILL could be hand-edited to
            # RESEARCH_SUPPORTED with zero detection). Only cheap-to-
            # verify NECESSARY conditions are asserted: promotion needs
            # episode-gate+power+positive-net; WATCH needs net>0;
            # UNDERPOWERED needs insufficient power or an UNDERPOWERED
            # episode gate; MODEL_RISK needs Sharpe>1. KILL/BLOCKED have
            # many legal paths and are left to the drift journal.
            import numpy as np
            import re as _re
            mv = _re.search(r"[A-Z_]+", row.get("**verdict**",
                                                row.get("verdict", "")))
            verdict = mv.group(0) if mv else ""
            if verdict not in ("RESEARCH_SUPPORTED", "WATCH",
                               "UNDERPOWERED", "MODEL_RISK",
                               "KILL", "BLOCKED"):
                probs.append(f"{d.name}/{cid}: verdict cell "
                             f"{row.get('**verdict**', row.get('verdict'))!r} "
                             "unrecognized")
                continue
            if verdict in ("RESEARCH_SUPPORTED", "WATCH",
                           "UNDERPOWERED", "MODEL_RISK"):
                try:
                    ep = F.episode_hit_stats(ev)
                    pw = F.power_gate(ev)
                    net = float(pd.to_numeric(ev["ret_bp"],
                                              errors="coerce").sum())
                except Exception as e:
                    # a stats recompute that raises is itself a flag —
                    # defaulting silently turns code bugs into "net=0"
                    # false flags (bit us once already)
                    probs.append(f"{d.name}/{cid}: verdict recompute "
                                 f"raised {type(e).__name__}: {e}")
                    continue
                # episode gate classification mirrors verdict()'s
                ep_gate = ("PASS" if (ep["n_ep"] >= 30 and
                                      ep["wilson_lo"] >= 0.50)
                           else ("UNDERPOWERED" if ep["n_ep"] < 30
                                 else "FAIL"))
                if verdict == "RESEARCH_SUPPORTED" and not (
                        ep_gate == "PASS" and pw.get("sufficient")
                        and net > 0):
                    probs.append(f"{d.name}/{cid}: verdict "
                                 "RESEARCH_SUPPORTED but episode gate "
                                 f"{ep_gate}/power {pw.get('sufficient')}"
                                 f"/net {net:.0f} cannot support it")
                elif verdict == "WATCH" and not net > 0:
                    probs.append(f"{d.name}/{cid}: verdict WATCH but "
                                 f"net={net:.0f} <= 0")
                elif verdict == "UNDERPOWERED" and not ev.empty and \
                        pw.get("sufficient") and \
                        ep_gate != "UNDERPOWERED":
                    probs.append(f"{d.name}/{cid}: verdict "
                                 "UNDERPOWERED but recomputed power/"
                                 "episode gates are sufficient")
                elif verdict == "MODEL_RISK":
                    try:
                        sr = F.sharpe_ann(
                            F.events_to_daily_returns(ev))
                    except Exception:
                        sr = float("nan")
                    if not (np.isfinite(sr) and sr > 1.0):
                        probs.append(f"{d.name}/{cid}: verdict "
                                     f"MODEL_RISK but recomputed "
                                     f"Sharpe={sr:.2f} <= 1")
        extra = set(files) - set(rows)
        if extra:
            probs.append(f"{d.name}: event files with no report row: "
                         f"{sorted(extra)[:4]}")
    check("in-sample report reconciliation", not probs,
          "all reports recompute against their event files"
          if not probs else "; ".join(probs[:5]))


STALL_DAYS = 45


def check_column_stalls() -> None:
    """Two-tier warehouse freshness. WARN: any harmony/macro column whose
    last valid value is >45d old — upstream-stalled families aren't
    SPIKE-fixable but must stay visible (the coverage baseline only
    catches shrinkage, not stalls — the 2026-02-19 coc_* family death
    and reserve_risk's 2025-12-28 end were invisible to it). FAIL: a
    declared forward lead whose limiting input never reaches its cutoff
    can never accrue — a promotion-critical false-green. All 14 leads are
    probed via the shared D.forward_input_probes() (the same eval the
    runner prints), never a drifted second map."""
    import pandas as pd
    from harness import data as D
    now = pd.Timestamp.now(tz="UTC")
    frames = {}
    for name, fn in (("harmony_extended", D.harmony_extended),
                     ("harmony_daily", D.harmony_daily)):
        try:
            frames[name] = fn()
        except Exception as e:
            check("forward input freshness", False, f"{name} load: {e}")
            return
    warns = []
    for name, df in frames.items():
        t = pd.to_datetime(df["t"], utc=True)
        for c in df.columns:
            if c == "t":
                continue
            idx = df.index[df[c].notna()]
            if not len(idx):
                continue
            if now - t.loc[idx].max() > pd.Timedelta(days=STALL_DAYS):
                warns.append(f"{name}.{c} last={t.loc[idx].max():%Y-%m-%d}")
    if warns:
        print(f"WARN  column stalls ({len(warns)}): " + "; ".join(warns))
    # A dead input FAILs unless manifest.forward_retired ledgers the lead
    # as upstream-extinct (then WARN — visible, never silent). A retired
    # lead must name its ledger entry, and a retired input that revives
    # is surfaced for review. Retirements are diffed against the FULL
    # declared universe (LEAD_CUTOFFS), not a partial input map.
    from harness import candidates_forward as CF
    retired = CF.retired_leads()
    try:
        probes = D.forward_input_probes()
    except Exception as e:
        check("forward input freshness", False,
              f"probe eval: {type(e).__name__}: {e}")
        return
    dead, ret_dead, revived, awaiting = [], [], [], []
    for lead in CF.LEAD_CUTOFFS:
        cutoff = CF.LEAD_CUTOFFS[lead]
        label, last = probes.get(lead, ("?", pd.NaT))
        tag = f"{lead}: {label} last={last.date() if pd.notna(last) else 'n/a'}"
        # An input that is still publishing but hasn't crossed a freshly
        # declared cutoff is AWAITING its first crossing (publish lag —
        # a cutoff declared today cannot be crossed until the source's
        # next cycle), not dead. Death = stale vs NOW, not merely
        # behind cutoff. The 7d bound keeps a truly extinct input from
        # hiding behind a future cutoff.
        fresh_now = (pd.notna(last)
                     and (now - last) <= pd.Timedelta(days=7))
        is_dead = pd.isna(last) or (last < cutoff and not fresh_now)
        r = retired.get(lead)
        if r and not r.get("ledger"):
            dead.append(f"{lead}: retired without a ledger reference")
        elif is_dead and r:
            ret_dead.append(tag)
        elif is_dead:
            dead.append(tag)
        elif pd.notna(last) and last < cutoff:
            awaiting.append(tag)
        elif r:
            revived.append(tag)
    for lead in set(retired) - set(CF.LEAD_CUTOFFS):
        dead.append(f"{lead}: retired but not a known declared lead")
    if ret_dead:
        print(f"WARN  retired leads ({len(ret_dead)}, inputs extinct "
              f"upstream): " + "; ".join(ret_dead))
    if awaiting:
        print(f"WARN  leads awaiting first input crossing ({len(awaiting)} "
              f"— inputs alive, publish-lagged): " + "; ".join(awaiting))
    if revived:
        print(f"WARN  retired-lead input REVIVED — review: " + "; ".join(revived))
    check("forward input freshness", not dead,
          "all live declared-lead inputs reach their cutoffs"
          if not dead else "; ".join(dead))


def check_coverage() -> None:
    spans_p = reports_p = ROOT / "reports" / "source_spans.json"
    if not spans_p.exists():
        check("coverage baseline", False, "source_spans.json missing")
        return
    prev = json.loads(spans_p.read_text())
    from harness import data as D
    cur_n = {}
    for name, fn in (("harmony_extended", D.harmony_extended),
                     ("harmony_daily", D.harmony_daily),
                     ("coinmetrics", D.coinmetrics_daily)):
        try:
            df = fn()
            for c in df.columns:
                if c != "t":
                    cur_n[f"{name}.{c}"] = int(df[c].notna().sum())
        except Exception as e:
            check("coverage baseline", False, f"{name} load: {e}")
            return
    shrank = [f"{k}: {prev[k].get('n')} -> {v}"
              for k, v in cur_n.items()
              if k in prev and "n" in prev[k] and v < prev[k]["n"] - 5]
    # column identity + history-integrity: a dropped column or a
    # last-valid date moving BACKWARD are history rewrites, invisible to
    # a row-count-only baseline (renames trip here deliberately — they
    # are ledgered in manifest.yaml)
    dropped = sorted(k for k in prev
                     if k not in cur_n and "." in k)
    import hashlib
    import pandas as pd
    back = []
    rewrites = []
    for name, fn in (("harmony_extended", D.harmony_extended),
                     ("harmony_daily", D.harmony_daily),
                     ("coinmetrics", D.coinmetrics_daily)):
        try:
            df = fn()
        except Exception:
            continue
        t = pd.to_datetime(df["t"], utc=True)
        for c in df.columns:
            if c == "t":
                continue
            k = f"{name}.{c}"
            old = prev.get(k) or {}
            s = df.loc[df[c].notna(), "t"]
            cur_last = pd.to_datetime(s, utc=True).max() if len(s) else pd.NaT
            try:
                old_last = pd.to_datetime(old.get("last"), utc=True)
            except Exception:
                old_last = pd.NaT
            if pd.notna(old_last) and pd.notna(cur_last) \
                    and cur_last < old_last - pd.Timedelta(days=2):
                back.append(f"{k}: last {old_last.date()} -> "
                            f"{cur_last.date()}")
            # value-signature: hash values dated <= the baseline's last
            # stamp — catches in-place history rewrites that row-count
            # and last-date baselines cannot see (A32 red-team).
            if old.get("sig") and pd.notna(old_last):
                try:
                    ss = (df.loc[df[c].notna(), ["t", c]]
                          .sort_values("t"))
                    tt = pd.to_datetime(ss["t"], utc=True,
                                        format="mixed").dt.tz_convert(None)
                    pref = ss[tt <= old_last.tz_convert(None)]
                    psig = hashlib.sha1(pd.util.hash_pandas_object(
                        pref[c], index=False).values.tobytes()
                        ).hexdigest()[:16]
                    if psig != old["sig"]:
                        rewrites.append(
                            f"{k}: values rewritten inside baseline "
                            f"span (<={old['last']})")
                except Exception:
                    pass
    probs = (shrank + [f"dropped: {dropped}" if dropped else ""]
             + back + rewrites)
    probs = [p for p in probs if p]
    check("coverage baseline", not probs,
          f"{len(cur_n)} columns, 0 regressions"
          if not probs else "; ".join(probs[:5]))


def check_power_gate() -> None:
    """Episode-counting invariants on the REAL gate + verdict path
    (F.power_gate + F.forward_gate), using frames shaped like observed
    failures. Expected counts are hand-derived from the frame geometry,
    not read back from the implementation. A27 class: 36 pooled rows on 6
    shared triggers over a 1d span reached DEAD as 'n_eff=36' — the span
    refusal returned without n_eff and the verdict path substituted raw
    n. Also guards the inverse: the gate must still PROMOTE a genuinely
    powered winner and kill a powered loser (otherwise 'ACCRUING-for-
    everything' passes). Each probe is isolated: a crash is a FAIL line,
    never an aborted verifier."""
    import pandas as pd
    from harness import falsify as F

    H = pd.Timedelta(hours=1)
    D = pd.Timedelta(days=1)

    def frame(times_assets, h=D, win=True):
        rows = []
        for t, a in times_assets:
            g = 55.0 if win else -60.0
            rows.append({"t": t, "asset": a, "dir": 1.0, "t_eval": t + h,
                         "ret_bp": g - 10.0, "gross_bp": g,
                         "hit": bool(g > 1.0)})
        return pd.DataFrame(rows, columns=["t", "asset", "dir", "t_eval",
                                           "ret_bp", "gross_bp", "hit"])

    base = pd.Timestamp("2026-09-23", tz="UTC")
    probs = []

    def probe(name, ev, n_eff=None, sufficient=None, verdict=None,
              price=None):
        try:
            pw = F.power_gate(ev)
            got = pw.get("n_eff")
            if n_eff is not None and got != n_eff:
                probs.append(f"{name}: n_eff={got} expected {n_eff}")
            if sufficient is not None and bool(pw.get("sufficient")) != sufficient:
                probs.append(f"{name}: sufficient={pw.get('sufficient')}")
            if verdict is not None:
                st = F.forward_gate(ev, price)
                if st["verdict"] != verdict:
                    probs.append(f"{name}: verdict={st['verdict']} "
                                 f"expected {verdict}")
        except Exception as e:
            probs.append(f"{name}: raised {type(e).__name__}: {e}")

    # (a) the observed failure: 6 shocks 8h apart x 6 assets, 1h exits,
    #     all losers -> 6 episodes, 1d span, underpowered, NOT dead.
    shocks = [base + 8 * i * H for i in range(6)]
    probe("6x6 shared-shock losers",
          frame([(t, a) for t in shocks for a in "ABCDEF"], h=H, win=False),
          n_eff=6.0, sufficient=False, verdict="ACCRUING")
    # (b) cross-asset dedupe at powered scale: 10 shocks 10d apart x 4
    #     assets = 40 rows, 90d span. Per-asset counting says 40 episodes
    #     and PROMOTES; the honest count is 10 -> ACCRUING.
    shocks = [base + 10 * i * D for i in range(10)]
    probe("10x4 shared-shock winners",
          frame([(t, a) for t in shocks for a in "ABCD"], h=H),
          n_eff=10.0, sufficient=False, verdict="ACCRUING")
    # (c) extreme collapse: 35 assets on ONE trigger = 1 episode.
    probe("35-asset single trigger",
          frame([(base, f"A{i:02d}") for i in range(35)]),
          n_eff=1.0, sufficient=False)
    # (d) overlap chains merge: 40 hourly entries x 10d windows = 1.
    probe("40 chained 10d windows",
          frame([(base + i * H, "BTC") for i in range(40)], h=10 * D),
          n_eff=1.0, sufficient=False)
    # (e) tiled independent 10d trades over ~400d: powered both ways.
    # PROMOTED now additionally requires RESOLVED drift skill — without a
    # price frame the gate cannot verify skill, so the same winner is
    # ACCRUING until a price frame demonstrates skill. Flat price =>
    # wins are pure skill -> PROMOTED; price drifting ABOVE the wins =>
    # beta capture -> DEAD.
    tiled = [(base + 10 * i * D, "BTC") for i in range(40)]
    probe("tiled 40x10d winners (no price)",
          frame(tiled, h=10 * D),
          n_eff=40.0, sufficient=True, verdict="ACCRUING")
    px_flat = pd.DataFrame({"t": [base + i * D for i in range(-5, 500)],
                            "c": [100.0] * 505})
    probe("tiled 40x10d winners + flat price",
          frame(tiled, h=10 * D),
          n_eff=40.0, sufficient=True, verdict="PROMOTED",
          price=px_flat)
    px_drift = pd.DataFrame(
        {"t": [base + i * D for i in range(-5, 500)],
         "c": [100.0 * (1.005 ** (i + 5)) for i in range(-5, 500)]})
    probe("tiled 40x10d winners + outpacing price (beta)",
          frame(tiled, h=10 * D),
          n_eff=40.0, sufficient=True, verdict="DEAD",
          price=px_drift)
    probe("tiled 40x10d losers", frame(tiled, h=10 * D, win=False),
          n_eff=40.0, sufficient=True, verdict="DEAD")
    # (f) same-day continuous position (t_eval == t): 40 consecutive
    #     hourly invested bars on one asset = 1 decision.
    run = [base + i * H for i in range(40)]
    probe("same-day continuous run", frame([(t, "BTC") for t in run],
                                          h=pd.Timedelta(0)),
          n_eff=1.0, sufficient=False)
    # (g) same-day pooled: 5 assets on the SAME two runs (5d apart) =
    #     2 episodes, not 10.
    runs = run + [base + 5 * D + i * H for i in range(40)]
    probe("same-day pooled 2 runs x 5 assets",
          frame([(t, a) for t in runs for a in "ABCDE"], h=pd.Timedelta(0)),
          n_eff=2.0, sufficient=False)
    # (h) degenerate inputs: empty and all-NaT -> honest zero, no crash.
    probe("empty frame", frame([]), n_eff=0.0, sufficient=False,
          verdict="ACCRUING")
    nat = frame([(base + i * D, "BTC") for i in range(30)])
    nat["t"] = pd.NaT
    nat["t_eval"] = pd.NaT
    probe("all-NaT frame", nat, n_eff=0.0, sufficient=False)
    # (i) uncovered rows carry no evidence. Tagged-uncovered (zero-width
    #     window, NaN returns) is contract-valid but counts nothing;
    #     windowed-uncovered (t_eval>t, NaN ret) violates the contract ->
    #     BLOCKED, never a powered DEAD on zero realized outcomes.
    unc_tagged = frame([(base + i * D, "BTC") for i in range(40)])
    unc_tagged["t_eval"] = unc_tagged["t"]
    unc_tagged["ret_bp"] = float("nan")
    unc_tagged["gross_bp"] = float("nan")
    unc_tagged["hit"] = False
    unc_tagged["exit_reason"] = "uncovered"
    probe("40 tagged-uncovered", unc_tagged,
          n_eff=0.0, sufficient=False, verdict="ACCRUING")
    unc_win = unc_tagged.copy()
    unc_win["t_eval"] = unc_win["t"] + 10 * D
    probe("40 windowed-uncovered", unc_win,
          n_eff=0.0, sufficient=False, verdict="BLOCKED")
    # (j) 1-second cross-asset jitter must not defeat dedupe: the same
    #     shock stamped +0s/+1s on BTC/ETH = one episode per shock.
    jit = []
    for i in range(15):
        jit += [(base + 10 * i * D, "BTC"),
                (base + 10 * i * D + pd.Timedelta(seconds=1), "ETH")]
    probe("15 shocks x2 assets +1s jitter", frame(jit, h=H),
          n_eff=15.0, sufficient=False, verdict="ACCRUING")
    # (k) staggered overlapping windows across assets = one shock:
    #     BTC [0,10d] + ETH [5,15d] merge, not 2.
    st = frame([(base, "BTC"), (base + 5 * D, "ETH")], h=10 * D)
    probe("staggered overlap 2 assets", st, n_eff=1.0, sufficient=False)
    # (l) no-asset frames count the same way (power path doesn't need
    #     the column; verdict path requires it -> BLOCKED).
    noa = frame([(base + 10 * i * D, "") for i in range(40)], h=10 * D)
    noa = noa.drop(columns=["asset"])
    probe("no-asset tiled 40", noa, n_eff=40.0, sufficient=True,
          verdict="BLOCKED")
    # (m) contract violations BLOCK before stats — a frame with bad dir
    #     must never reach verdict math or crash the gate.
    badc = frame([(base + 10 * i * D, "BTC") for i in range(40)], h=10 * D)
    badc.loc[0, "dir"] = 0.0
    probe("bad-dir frame", badc, verdict="BLOCKED")
    # (n) window-touching-window boundary rule (A32 red-team gap): two
    #     windows exactly abutting are DISJOINT exposure = 2 episodes,
    #     while a point sitting ON a window boundary is the same instant
    #     and merges. A regression merging tiled windows back to 1 is
    #     the over-merge bug this rule was carved out to fix.
    touch = frame([(base, "BTC"), (base + 10 * D, "BTC")], h=10 * D)
    probe("abutting 10d windows", touch, n_eff=2.0, sufficient=False)
    pt_on = pd.concat([frame([(base, "BTC")], h=10 * D),
                       frame([(base + 10 * D, "BTC")],
                             h=pd.Timedelta(0))])
    probe("point on window edge", pt_on, n_eff=1.0, sufficient=False)
    # (o) unsorted input must not change the count — the merge sorts by
    #     t internally; a frame arriving shuffled must produce the same
    #     episode count as the sorted twin.
    uns = frame([(base + 10 * i * D, "BTC") for i in range(40)], h=10 * D)
    uns = uns.sample(frac=1.0, random_state=7).reset_index(drop=True)
    probe("shuffled tiled 40", uns, n_eff=40.0, sufficient=True)
    # (p) equal-timestamp order stability (A32 fix): a point row and a
    #     window row sharing t must produce the same episode regardless
    #     of row order inside the file.
    w = frame([(base, "BTC")], h=10 * D)
    p = frame([(base, "BTC")], h=pd.Timedelta(0))
    ord_a = pd.concat([p, w]); ord_b = pd.concat([w, p])
    probe("equal-t point+window order A", ord_a, n_eff=1.0,
          sufficient=False)
    probe("equal-t point+window order B", ord_b, n_eff=1.0,
          sufficient=False)

    check("power gate invariants", not probs,
          "episodes counted, shared triggers collapse, refusals carry "
          "n_eff, underpowered cannot die" if not probs else "; ".join(probs))


def check_publish_lag() -> None:
    """Truncation invariance for CF.LAGGED_INPUTS: mask the lagged
    column's last `lag` valid values, re-emit, and the event stream must
    be IDENTICAL — if the signal read unpublished rows, tail events
    would change or vanish. Live proof that publish-lag shifts exist in
    the impls, not just in comments."""
    import numpy as np
    import pandas as pd
    from harness import candidates_forward as CF
    from harness import data as D

    probs = []
    hd, he = D.harmony_daily(), D.he_price_frame()

    def emit_for(lead: str, masked: dict):
        """masked: {column: masked_series} applied to the lead's own
        input frame; returns the re-emitted event frame."""
        if lead == "fwd_fng_fear_long":
            return CF.fwd_fng_fear_long(hd.assign(**masked))
        if lead == "fwd_momentum_extremes":
            return CF.fwd_momentum_extremes(hd.assign(**masked))
        if lead == "fwd_oi_divergence_short":
            return CF.fwd_oi_divergence_short(hd.assign(**masked))
        if lead == "fwd_equity_lead_short":
            return CF.fwd_equity_lead_short(hd.assign(**masked))
        if lead == "fwd_riskoff_cluster":
            return CF.fwd_riskoff_cluster(hd.assign(**masked))
        if lead == "fwd_flagship_hlbtc":
            s = masked.get("mvrv")
            return CF.fwd_flagship_hlbtc(
                D.candles_full("btc", "1d"),
                s if s is not None
                else hd.set_index("t")["mvrv"].astype(float))
        fn = {"fwd_nrpl_cont": CF.fwd_nrpl_cont,
              "fwd_puell_extreme_cont": CF.fwd_puell_extreme_cont,
              "fwd_reserve_risk_cont": CF.fwd_reserve_risk_cont,
              "fwd_skew_reversal": CF.fwd_skew_reversal,
              "fwd_dormancy_spike_long": CF.fwd_dormancy_spike_long}[lead]
        return fn(he.assign(**masked))

    for lead, cols in CF.LAGGED_INPUTS.items():
        try:
            base_ev = emit_for(lead, {})
            if base_ev.empty:
                probs.append(f"{lead}: base emit produced no events")
                continue
            for col, lag in cols.items():
                # mask boundary: masked stamps legitimately feed later
                # events' rolling-quantile windows (and are read by
                # events INSIDE the mask for extinct inputs) — compare
                # only events at t <= earliest masked stamp, where a
                # lagged impl can never see the masked values.
                if lead == "fwd_flagship_hlbtc":
                    s = hd.set_index("t")["mvrv"].astype(float)
                    mask_idx = s.dropna().index[-lag:]
                    mask_lo = pd.Timestamp(mask_idx.min())
                    if mask_lo.tz is not None:
                        mask_lo = mask_lo.tz_convert(None)
                    s.loc[mask_idx] = float("nan")
                    masked = {"mvrv": s}
                else:
                    src = hd if col in hd.columns else he
                    m = src[col].copy()
                    mask_idx = m.dropna().index[-lag:]
                    mask_lo = pd.to_datetime(
                        src.loc[mask_idx, "t"], utc=True,
                        format="mixed").min().tz_convert(None)
                    m.loc[mask_idx] = float("nan")
                    masked = {col: m}
                b = base_ev.reset_index(drop=True)
                pm = emit_for(lead, masked).reset_index(drop=True)
                tb = pd.to_datetime(b["t"], utc=True,
                                    format="mixed").dt.tz_convert(None)
                tp = pd.to_datetime(pm["t"], utc=True,
                                    format="mixed").dt.tz_convert(None)
                same = (b[tb <= mask_lo].reset_index(drop=True)
                        .equals(pm[tp <= mask_lo].reset_index(drop=True)))
                if not same:
                    probs.append(f"{lead}: events at t<={mask_lo.date()} "
                                 f"changed when {col} tail masked — "
                                 "signal reads unpublished rows")
                    continue
                # Perturbation probe (A31 red-team): NaN-masking alone
                # passes vacuously when no event samples the tail, and
                # a NaN can be silently ffill'd past. Instead overwrite
                # the stamps in the lag window of the LAST covered
                # event t* — stamps dated in (t* - lag, t*]: an unlagged
                # impl reads them at t* (events change -> FAIL); a
                # lagged impl reads only stamps <= t*-lag (identical).
                # Comparison restricted to t <= t* — later events may
                # legitimately see the perturbed stamps.
                src = (hd if (lead == "fwd_flagship_hlbtc"
                              or col in hd.columns) else he)
                ser = (hd.set_index("t")[col] if lead ==
                       "fwd_flagship_hlbtc" else src[col]).astype(float)
                stamps = pd.to_datetime(
                    ser.dropna().index if lead == "fwd_flagship_hlbtc"
                    else src["t"], utc=True, format="mixed")
                if getattr(stamps, "tz", getattr(stamps.dt, "tz", None)
                           if isinstance(stamps, pd.Series) else None):
                    stamps = (stamps.dt.tz_convert(None)
                              if isinstance(stamps, pd.Series)
                              else stamps.tz_convert(None))
                tt = pd.to_datetime(base_ev["t"], utc=True,
                                    format="mixed").dt.tz_convert(None)
                cov = base_ev["ret_bp"].notna() & tt.notna()
                if not cov.any():
                    print(f"WARN  {lead}: no covered events — "
                          "perturbation probe vacuous")
                    continue
                t_star = tt[cov].max()
                win_lo = t_star - pd.Timedelta(days=lag)
                in_win = (stamps > win_lo) & (stamps <= t_star)
                if not in_win.any():
                    print(f"WARN  {lead}.{col}: no stamps inside lag "
                          "window — probe vacuous")
                    continue
                extreme = ser.abs().max() * 100.0
                if not np.isfinite(extreme) or extreme == 0:
                    extreme = 1e6
                m = ser.copy()
                if lead == "fwd_flagship_hlbtc":
                    sidx = ser.dropna().index
                    sidx = sidx[(sidx > win_lo) & (sidx <= t_star)]
                    m.loc[sidx] = extreme
                    masked = {"mvrv": m}
                else:
                    m.loc[(stamps > win_lo) & (stamps <= t_star)] = \
                        extreme
                    masked = {col: m}
                pert = emit_for(lead, masked).reset_index(drop=True)
                b = base_ev.reset_index(drop=True)
                tb = pd.to_datetime(b["t"], utc=True,
                                    format="mixed").dt.tz_convert(None)
                tp = pd.to_datetime(pert["t"], utc=True,
                                    format="mixed").dt.tz_convert(None)
                same = (b[tb <= t_star].equals(pert[tp <= t_star]))
                if not same:
                    probs.append(f"{lead}: events at t<={t_star.date()} "
                                 f"changed when {col} stamps in "
                                 f"({win_lo.date()},{t_star.date()}] "
                                 "were perturbed — signal reads "
                                 "not-yet-published values")
        except Exception as e:
            probs.append(f"{lead}: probe raised {type(e).__name__}: {e}")
    check("publish-lag truncation invariance", not probs,
          "masked tails + perturbed lag windows leave every lagged "
          "lead's events identical"
          if not probs else "; ".join(probs[:4]))


def check_artifact_anchoring() -> None:
    """Tamper-evidence snapshot (A31 red-team: a consistent events+report
    rollback passed because nothing anchored post-verification state).
    After a fully-passing run the verifier writes sha256 of every event
    file, report, manifest, and code file (harness/, run_*, tools/) to
    reports/artifact_hashes.json; later runs FAIL on any changed or
    deleted artifact and re-anchor only on PASS. New artifacts WARN —
    appearing where nothing existed is visible, not silent, but isn't
    tampering with verified state. Hashing the code makes edits that
    SHOULD have regenerated artifacts but didn't loud once (the FAIL
    lists the changed files; a coherent regen re-seals)."""
    import hashlib
    snap_p = ROOT / "reports" / "artifact_hashes.json"
    targets = sorted(
        [p for d in (ROOT / "reports").glob("events*") if d.is_dir()
         for p in d.rglob("*") if p.is_file()]
        + [p for p in (ROOT / "reports").glob("events*.csv")
           if p.is_file()]
        + list((ROOT / "reports").glob("report*.md"))
        + [ROOT / "manifest.yaml",
           # the coverage baseline is itself a trust root — rewriting it
           # to match degraded data would absorb a collapse silently
           ROOT / "reports" / "source_spans.json"]
        + list((ROOT / "harness").glob("*.py"))
        + list(ROOT.glob("run_*.py"))
        + list((ROOT / "tools").glob("*.py")))
    cur = {}
    for p in targets:
        try:
            cur[str(p.relative_to(ROOT))] = hashlib.sha256(
                p.read_bytes()).hexdigest()
        except Exception:
            continue
    global _PENDING_ANCHOR
    _PENDING_ANCHOR = cur
    prev = {}
    if snap_p.exists():
        try:
            prev = json.loads(snap_p.read_text()).get("sha256", {})
        except Exception:
            check("artifact anchoring", False,
                  "snapshot unreadable — possible tampering")
            return
    if not prev:
        # missing OR empty snapshot is an anchoring FAILURE, not a WARN:
        # a deleted/emptied artifact_hashes.json previously re-seeded the
        # tampered corpus as baseline with zero FAILs ever (A32 red-team
        # critical). Failing keeps the deletion loud; the sole-failure
        # re-anchor in main() re-seals on the next run, same semantics
        # as changed artifacts.
        check("artifact anchoring", False,
              "artifact snapshot missing or empty — possible tampering; "
              "re-run to seal a fresh baseline")
        return
    probs = []
    changed = [k for k in prev if k in cur and cur[k] != prev[k]]
    missing = [k for k in prev if k not in cur]
    new = sorted(k for k in cur if k not in prev)
    if changed:
        probs.append(f"{len(changed)} artifacts changed since last "
                     f"verified state: {changed[:20]}"
                     + (" ..." if len(changed) > 20 else ""))
    if missing:
        probs.append(f"{len(missing)} artifacts deleted since last "
                     f"verified state: {missing[:20]}"
                     + (" ..." if len(missing) > 20 else ""))
    if new:
        print(f"WARN  {len(new)} new artifacts unanchored: {new[:8]}")
    check("artifact anchoring", not probs,
          f"{len(cur)} artifacts match verified snapshot"
          if not probs else "; ".join(probs[:2]))


# module-level stash: main() re-anchors ONLY when every check passed —
# writing mid-run could seal a state that a later check rejects
_PENDING_ANCHOR: dict | None = None


def _write_snapshot(snap_p, cur: dict) -> bool:
    import time as _t
    prev = {}
    if snap_p.exists():
        try:
            prev = json.loads(
                snap_p.read_text(encoding="utf-8")).get("sha256", {})
        except Exception:
            prev = {}
    changed = sorted(k for k in prev if k in cur and cur[k] != prev[k])
    removed = sorted(k for k in prev if k not in cur)
    added = sorted(k for k in cur if k not in prev)
    if cur == prev:
        return False  # identical seal — no file churn, no journal noise
    stamp = _t.strftime("%Y-%m-%d %H:%M UTC", _t.gmtime())
    payload = {"anchored_at": stamp, "sha256": cur}
    tmp = snap_p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    tmp.replace(snap_p)
    # durable seal journal: a silent re-anchor is indistinguishable from
    # tampering-absorption after the fact — record every diff that gets
    # blessed (the journal itself is intentionally NOT hashed).
    line = f"- {stamp} — sealed {len(cur)} artifacts"
    if not prev:
        line += " [fresh baseline]"
    for tag, lst in (("changed", changed), ("removed", removed),
                     ("added", added)):
        if lst:
            line += f" | {tag}={len(lst)}: {', '.join(lst[:10])}" + (
                " …" if len(lst) > 10 else "")
    j = snap_p.parent / "anchor_journal.md"
    with j.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return True


def check_insample_freshness() -> None:
    """Every in-sample report must be at least as fresh as its event
    dir — a report older than the events it summarizes is stale (the
    runner regenerated events but died before the report)."""
    probs = []
    reps = ROOT / "reports"
    for d in reps.glob("events*"):
        if not d.is_dir():
            continue
        rep = reps / ("report" + d.name[len("events"):] + ".md")
        if not rep.exists():
            continue          # covered by contract/completeness checks
        ev_m = max((f.stat().st_mtime for f in d.rglob("*.csv")),
                   default=0.0)
        if ev_m > rep.stat().st_mtime + 60:
            probs.append(f"{rep.name} older than {d.name}/ events "
                         f"({(ev_m - rep.stat().st_mtime) / 3600:.1f}h)")
    check("in-sample report freshness", not probs,
          "all reports at least as fresh as their event files"
          if not probs else "; ".join(probs[:4]))


def check_manifest() -> None:
    """manifest.yaml is the ledger — it must parse, declare the forward
    gate honestly, and keep ledgered retirements inside the declared
    universe."""
    import yaml
    from harness import candidates_forward as CF
    probs = []
    try:
        man = yaml.safe_load(
            (ROOT / "manifest.yaml").read_text(encoding="utf-8")) or {}
    except Exception as e:
        check("manifest integrity", False, f"yaml: {e}")
        return
    if "forward_declared" not in man:
        probs.append("forward_declared section missing")
    for r in (man.get("forward_retired") or []):
        if r.get("lead") not in CF.LEAD_CUTOFFS:
            probs.append(f"forward_retired names undeclared lead "
                         f"{r.get('lead')}")
        if not r.get("ledger"):
            probs.append(f"forward_retired {r.get('lead')} lacks ledger ref")
    gate = str(man.get("forward_promotion_gate") or "")
    if gate and "drift" not in gate.lower() and "skill" not in gate.lower():
        probs.append("forward_promotion_gate text omits the drift-skill "
                     "clause the code enforces")

    # Bidirectional declared-universe <-> artifact set (A31 red-team:
    # deleting a manifest candidate or dropping an event file both
    # passed silently). Declared ids = items under any 'candidates' /
    # 'hypotheses' key; fixture_* statuses are harness self-tests that
    # never emit files. Forward leads -> events_fwd_<id>.csv; in-sample
    # ids -> some events*/<id>.csv.
    declared: set[str] = set()

    def _collect(o, key=None):
        if isinstance(o, dict):
            if key in ("candidates", "hypotheses") and "id" in o:
                st = str(o.get("status", ""))
                if not st.startswith("fixture_"):
                    declared.add(str(o["id"]))
            for k, v in o.items():
                _collect(v, k)
        elif isinstance(o, list):
            for v in o:
                _collect(v, key)
    _collect(man)

    reps = ROOT / "reports"
    files = set()
    for d in reps.glob("events*"):
        if d.is_dir():
            files |= {p.stem for p in d.rglob("*.csv")}
    files |= {p.name[len("events_"):-4]
              for p in reps.glob("events_fwd_*.csv")}
    undeclared = sorted(files - declared)
    missing = sorted(declared - files)
    if undeclared:
        probs.append(f"event files with no manifest declaration: "
                     f"{undeclared[:5]}")
    if missing:
        probs.append(f"declared ids with no event file: {missing[:5]}")
    check("manifest integrity", not probs,
          "ledger parses, declared universe consistent, artifact set "
          "matches declarations"
          if not probs else "; ".join(probs[:4]))


def main() -> int:
    print(f"verify_integrity — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    for fn in (check_event_contracts, check_open_bars, check_freshness,
               check_forward_completeness, check_report_reconcile,
               check_column_stalls, check_publish_lag, check_coverage,
               check_insample_reconcile, check_insample_freshness,
               check_manifest, check_power_gate,
               check_artifact_anchoring):
        try:
            fn()
        except Exception:
            import traceback
            tb = traceback.format_exc().strip().splitlines()[-1]
            check(f"{fn.__name__} (crashed)", False, tb)
    # Re-anchor when every substantive check is green — including when
    # anchoring itself is the only failure (a coherent regeneration
    # passes reconcile/contract/manifest, so the diff is blessed state).
    # Incoherent tampering (swap/inject/truncate) trips reconcile too —
    # the snapshot then persists unreplaced until the corpus is restored.
    if _PENDING_ANCHOR is not None and \
            (not FAILURES or FAILURES == ["artifact anchoring"]):
        if _write_snapshot(ROOT / "reports" / "artifact_hashes.json",
                           _PENDING_ANCHOR):
            print("anchored artifact snapshot")
    print(f"\n{'ALL PASS' if not FAILURES else f'{len(FAILURES)} FAILED: {FAILURES}'}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
