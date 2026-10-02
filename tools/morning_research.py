"""Morning research job — scheduled 07:00 daily.

Read-only w.r.t. the bot and the frozen snapshot. Each run:
  1. incrementally refreshes data_extended/ (HL funding, candles, Binance)
  2. checks collect-only gate maturity (ofi span, shadow/funding journal n)
  3. re-runs round 2/3/4 evaluations on updated data
  4. writes reports/morning/YYYY-MM-DD.md with verdicts + gate status

Designed to be safe under Task Scheduler: every stage isolated, failures
recorded in the note rather than crashing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # run as tools/ script: harness not on path
EXT = ROOT / "data_extended"
OUT = ROOT / "reports" / "morning"
OUT.mkdir(parents=True, exist_ok=True)
BOT = Path(os.environ.get("SPIKE_BOT_DIR", "."))

HL_INFO = "https://api.hyperliquid.xyz/info"
BN_FAPI = "https://fapi.binance.com"
COINS = ("BTC", "SOL", "ETH", "XRP", "DOGE", "AVAX", "LINK")
BN_SYMS = tuple(f"{c}USDT" for c in COINS)


def _atomic_write_text(p: Path, text: str) -> None:
    tmp = p.with_name(p.name + ".tmp")
    # utf-8 explicitly — cp1252 default (Py<3.15 on Windows) dies on the
    # ✓/—/→ chars subprocess output embeds, losing the note itself
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)


def _open(req_or_url, tries: int = 4):
    for i in range(tries):
        try:
            return urllib.request.urlopen(req_or_url, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code in (418, 429) and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            raise


def _post(url: str, payload: dict) -> list | dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with _open(req) as r:
        return json.loads(r.read())


def _get(url: str) -> list | dict:
    with _open(url) as r:
        return json.loads(r.read())


def refresh_funding(log: list[str]) -> None:
    for coin in COINS:
        try:
            _refresh_funding_one(coin, log)
        except Exception as e:
            log.append(f"funding {coin}: FAILED {type(e).__name__}: {e}")


def _refresh_funding_one(coin: str, log: list[str]) -> None:
    p = EXT / "funding" / f"{coin.lower()}_funding_full.json"
    rows = json.loads(p.read_text())
    last = max(int(r["time"]) for r in rows)
    added = 0
    start = last + 1
    while True:
        batch = _post(HL_INFO, {"type": "fundingHistory", "coin": coin,
                                "startTime": start})
        if not batch:
            break
        rows.extend(batch)
        added += len(batch)
        start = int(batch[-1]["time"]) + 1
        if len(batch) < 500:
            break
        time.sleep(0.15)
    # dedupe by time
    seen, dedup = set(), []
    for r in sorted(rows, key=lambda r: int(r["time"])):
        t = int(r["time"])
        if t not in seen:
            seen.add(t); dedup.append(r)
    _atomic_write_text(p, json.dumps(dedup))
    log.append(f"funding {coin}: +{added} rows (total {len(dedup)})")


def refresh_candles(log: list[str]) -> None:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    for coin in COINS:
        for iv in ("15m", "1h", "4h", "1d"):
            try:
                _refresh_candle_file(coin, iv, now_ms, log)
            except Exception as e:
                log.append(f"candles {coin} {iv}: FAILED "
                           f"{type(e).__name__}: {e}")


def _refresh_candle_file(coin: str, iv: str, now_ms: int,
                         log: list[str]) -> None:
    p = EXT / "candles" / f"{coin.lower()}_{iv}_full.json"
    rows = json.loads(p.read_text())
    last_t = max(int(r["t"]) for r in rows)
    merged = {int(r["t"]): r for r in rows}
    start = last_t + 1
    # paginate forward — a single request capped at ~5000 bars
    # would leave a permanent hole if the file ever goes stale by
    # more than that (job downtime). Bounded at 8 pulls (~40k bars).
    pulls = 0
    while start < now_ms and pulls < 8:
        batch = _post(HL_INFO, {"type": "candleSnapshot",
                                "req": {"coin": coin, "interval": iv,
                                        "startTime": start,
                                        "endTime": now_ms}})
        if not batch:
            break
        n_before = len(merged)
        for r in batch:
            merged[int(r["t"])] = r
        # advance from the NEWEST bar regardless of batch order — and
        # bail when nothing advances: the tail is the still-open bar
        # (API snaps startTime to the bar boundary and re-returns it)
        new_start = max(int(r["t"]) for r in batch) + 1
        pulls += 1
        if new_start <= start and len(merged) == n_before:
            break
        start = new_start
        time.sleep(0.15)
    if pulls == 8 and start < now_ms:
        log.append(f"  !! candles {coin} {iv}: gap beyond 8 pulls "
                   f"(still missing {start}->{now_ms})")
    # never persist a still-open bar — its partial OHLC would be
    # frozen forever since next run resumes at last_t+1
    dropped = sum(1 for k in merged if k + _iv_ms(iv) > now_ms)
    out = [merged[k] for k in sorted(merged)
           if k + _iv_ms(iv) <= now_ms]
    _atomic_write_text(p, json.dumps(out))
    note = f" (-{dropped} open)" if dropped else ""
    log.append(f"candles {coin} {iv}: +{len(out)-len(rows)} "
               f"(total {len(out)}){note}")


_IV_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
def _iv_ms(iv: str) -> int:
    return _IV_MS[iv]


def refresh_binance(log: list[str]) -> None:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    for sym in BN_SYMS:
        try:
            p = EXT / "binance" / f"{sym.lower()}_funding.json"
            rows = json.loads(p.read_text())
            last = max(int(r["fundingTime"]) for r in rows)
            batch = _get(f"{BN_FAPI}/fapi/v1/fundingRate?symbol={sym}"
                         f"&startTime={last + 1}&limit=1000")
            rows.extend(batch)
            seen, dedup = set(), []
            for r in sorted(rows, key=lambda r: int(r["fundingTime"])):
                t = int(r["fundingTime"])
                if t not in seen:
                    seen.add(t); dedup.append(r)
            _atomic_write_text(p, json.dumps(dedup))
            log.append(f"binance funding {sym}: +{len(batch)} "
                       f"(total {len(dedup)})")
        except Exception as e:
            log.append(f"binance funding {sym}: FAILED "
                       f"{type(e).__name__}: {e}")
        time.sleep(0.15)
    # 30d-lookback datasets decay without refresh — append incrementally
    for sym in ("BTCUSDT", "SOLUSDT"):
        for name, tkey in (("oi_hist_1h", "timestamp"),
                           ("taker_ls_1h", "timestamp")):
            try:
                p = EXT / "binance" / f"{sym.lower()}_{name}.json"
                if not p.exists():
                    continue
                rows = json.loads(p.read_text())
                last = max(int(r[tkey]) for r in rows)
                batch = _get(f"{BN_FAPI}/futures/data/"
                             f"{'openInterestHist' if name.startswith('oi') else 'takerlongshortRatio'}"
                             f"?symbol={sym}&period=1h&startTime={last + 1}&limit=500")
                rows.extend(batch)
                seen, dedup = set(), []
                for r in sorted(rows, key=lambda r: int(r[tkey])):
                    t = int(r[tkey])
                    if t not in seen:
                        seen.add(t); dedup.append(r)
                # drop the still-open hourly period — same frozen-
                # partial-bar failure as HL candles
                dedup = [r for r in dedup if int(r[tkey]) + 3_600_000 <= now_ms]
                _atomic_write_text(p, json.dumps(dedup))
                log.append(f"binance {name} {sym}: +{len(batch)} "
                           f"(total {len(dedup)})")
            except Exception as e:
                log.append(f"binance {name} {sym}: FAILED "
                           f"{type(e).__name__}: {e}")
            time.sleep(0.15)
    # deep klines + premium index: incremental append for all 7 assets
    for sym in BN_SYMS:
        for name, path in (("klines_1h", "klines"), ("klines_1d", "klines"),
                           ("klines_4h", "klines"),
                           ("premium_1d", "premiumIndexKlines")):
            try:
                p = EXT / "binance" / f"{sym.lower()}_{name}.json"
                if not p.exists():
                    continue
                rows = json.loads(p.read_text())
                last = max(int(r["t"]) for r in rows)
                interval = name.split("_")[1]
                batch = _get(f"{BN_FAPI}/fapi/v1/{path}?symbol={sym}"
                             f"&interval={interval}&startTime={last + 1}&limit=1500")
                if not batch:
                    continue
                seen = {int(r["t"]): r for r in rows}
                for k in batch:
                    if path == "klines":
                        seen[int(k[0])] = {"t": k[0], "o": float(k[1]),
                                           "h": float(k[2]), "l": float(k[3]),
                                           "c": float(k[4]), "v": float(k[5]),
                                           "taker_buy_vol": float(k[9]),
                                           "n_trades": int(k[8])}
                    else:
                        seen[int(k[0])] = {"t": k[0], "o": float(k[1]),
                                           "h": float(k[2]), "l": float(k[3]),
                                           "c": float(k[4])}
                # drop still-open bar before persisting
                out = [seen[k] for k in sorted(seen)
                       if k + _iv_ms(interval) <= now_ms]
                _atomic_write_text(p, json.dumps(out))
                log.append(f"binance {name} {sym}: +{len(out)-len(rows)}")
            except Exception as e:
                log.append(f"binance {name} {sym}: FAILED "
                           f"{type(e).__name__}: {e}")
            time.sleep(0.15)


def refresh_aux_sources(log: list[str]) -> None:
    """CoinMetrics community refresh + harmony warehouse re-export.
    Both self-incrementing; harmony export follows the upstream weekly
    harvest cadence (its freshness is bounded by the upstream repo)."""
    py = ROOT / ".venv" / "Scripts" / "python.exe"
    for tool in ("tools/backfill_coinmetrics.py",
                 "tools/export_harmony_extended.py",
                 "tools/export_macro_daily.py"):
        try:
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            r = subprocess.run([str(py), tool], cwd=ROOT, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=900, env=env)
            tail = (r.stdout or "").strip().splitlines()
            log.append(f"{tool}: {'ok' if r.returncode == 0 else 'FAILED'} "
                       f"({tail[-1][:110] if tail else 'no output'})")
        except Exception as e:
            # "CRASHED" — the exit-code scanner matches that token; a bare
            # "CRASH" was invisible and the run exited 0 on tool death
            log.append(f"{tool}: CRASHED: {type(e).__name__}: {e}")


_PENDING_SPANS: dict = {}
_PENDING_ALERTS: list[str] = []


def coverage_sentinel(log: list[str]) -> None:
    """Per-source (column -> n, first, last) spans diffed vs the previous
    baseline; the write is DEFERRED to commit_coverage_baseline (runs
    after run_evals) so verify_integrity compares today's data against
    the PRE-refresh baseline — a same-day regression fails loudly once
    instead of being absorbed into a baseline written minutes earlier.
    A column that shrinks, truncates, or dies is loud — btc_price
    silently ending 2023-12-13 is the failure this exists to catch."""
    import hashlib
    import pandas as pd
    from harness import data as D
    spans: dict[str, dict] = {}
    frames = {
        "harmony_extended": lambda: D.harmony_extended(),
        "harmony_daily": lambda: D.harmony_daily(),
        "coinmetrics": lambda: D.coinmetrics_daily(),
    }
    for name, fn in frames.items():
        try:
            df = fn()
            for c in df.columns:
                if c == "t":
                    continue
                s = df[["t", c]].dropna().sort_values("t")
                if s.empty:
                    spans[f"{name}.{c}"] = {"n": 0}
                else:
                    sig = hashlib.sha1(pd.util.hash_pandas_object(
                        s[c], index=False).values.tobytes()
                        ).hexdigest()[:16]
                    spans[f"{name}.{c}"] = {
                        "n": int(s[c].notna().sum()),
                        "first": str(s["t"].min())[:10],
                        "last": str(s["t"].max())[:10],
                        "sig": sig}
        except Exception as e:
            # preserve the old baseline entry instead of wiping it — an
            # error entry must not silently re-seed coverage on recovery
            spans[name] = {"error": str(e)[:120]}
    global _PENDING_SPANS, _PENDING_ALERTS
    prev_p = OUT.parent / "source_spans.json"
    prev = json.loads(prev_p.read_text(encoding="utf-8")) \
        if prev_p.exists() else {}
    alerts = []
    for k in set(prev) - set(spans):
        alerts.append(f"{k}: column vanished entirely "
                      f"(baseline n={prev[k].get('n')} last={prev[k].get('last')})")
    for k, cur in spans.items():
        if "error" in cur:
            alerts.append(f"{k}: frame unreadable — {cur['error']}")
            if k in prev:
                spans[k] = prev[k]      # keep last-good baseline entry
            continue
        old = prev.get(k)
        if old is None or "error" in old:
            continue
        if cur.get("n", 0) < old.get("n", 0) - 5:
            alerts.append(f"{k}: n shrank {old.get('n')} -> {cur.get('n')}")
        if cur.get("last", "9") < old.get("last", "0"):
            alerts.append(f"{k}: last ts moved BACK {old.get('last')} "
                          f"-> {cur.get('last')}")
        # value-signature check (A32 red-team: n/first/last is shape-only
        # — an in-place rewrite of history passed silently). Re-hash the
        # baseline-dated prefix: appended days can't false-alarm, an
        # edited or dropped historical value trips here.
        if old.get("sig") and old.get("last"):
            name = k.split(".", 1)[0]
            try:
                df = frames[name]()
                c = k.split(".", 1)[1]
                s = df[["t", c]].dropna().sort_values("t")
                cutoff = pd.Timestamp(old["last"])
                if getattr(s["t"].dt, "tz", None) is not None:
                    cutoff = cutoff.tz_localize("UTC")
                pref = s[s["t"] <= cutoff]
                psig = hashlib.sha1(pd.util.hash_pandas_object(
                    pref[c], index=False).values.tobytes()
                    ).hexdigest()[:16]
                if psig != old["sig"]:
                    alerts.append(f"{k}: VALUES REWRITTEN inside "
                                  f"baseline span (<={old['last']})")
            except Exception:
                pass
    _PENDING_SPANS = spans
    _PENDING_ALERTS = alerts
    log.append(f"coverage: {len(spans)} columns tracked, "
               f"{len(alerts)} regressions (baseline deferred until "
               f"verify runs)")
    log.extend(f"  !! {a}" for a in alerts)


def commit_coverage_baseline(log: list[str]) -> None:
    """Write the pending coverage spans AFTER run_evals — verify_integrity
    must see the pre-refresh baseline for its coverage check to be real.
    Alerts are journaled append-only to reports/coverage_journal.md so a
    collapse stays durable evidence even though the baseline self-heals
    (A32: the unconditional commit meant loud-once-then-absorbed; the
    journal keeps the once visible in the record)."""
    if not _PENDING_SPANS:
        log.append("coverage baseline: nothing pending")
        return
    prev_p = OUT.parent / "source_spans.json"
    _atomic_write_text(prev_p, json.dumps(_PENDING_SPANS, indent=1))
    log.append(f"coverage baseline committed ({len(_PENDING_SPANS)} "
               f"columns)")
    if _PENDING_ALERTS:
        jpath = OUT.parent / "coverage_journal.md"
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = (f"\n## {stamp} coverage alerts "
                 f"({len(_PENDING_ALERTS)})\n\n"
                 + "\n".join(f"- {a}" for a in _PENDING_ALERTS) + "\n")
        try:
            with open(jpath, "a", encoding="utf-8") as fh:
                fh.write(entry)
            log.append(f"coverage journal: {len(_PENDING_ALERTS)} "
                       "alerts recorded")
        except OSError as e:
            log.append(f"  !! coverage journal write failed: {e}")


def validate_event_files(log: list[str]) -> None:
    """Contract-assert every reports/events_*.csv via F.validate_events."""
    import pandas as pd
    from harness import falsify as F
    reports = ROOT / "reports"
    files = sorted(p for d in reports.glob("events*")
                   if d.is_dir()
                   for p in d.rglob("*.csv")) + \
        sorted(reports.glob("events*.csv"))
    bad = 0
    for p in files:
        try:
            ev = pd.read_csv(p)
            r = F.validate_events(ev)
        except Exception as e:
            r = {"passed": False, "violations": [f"read/cast: {e}"]}
        if not r["passed"]:
            bad += 1
            log.append(f"  !! {p.name}: {'; '.join(r['violations'])}")
    log.append(f"event contracts: {len(files)} files checked, {bad} bad")


def gate_status(log: list[str]) -> None:
    # OFI journal span (bot data is read-only here)
    for asset in ("BTC", "SOL"):
        p = BOT / "data" / "l2_journal" / f"{asset}_l2_testnet.jsonl"
        if not p.exists():
            log.append(f"ofi journal {asset}: missing")
            continue
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        ts = [r["t"] for r in rows]
        span = (max(ts) - min(ts)) / 86_400_000
        gate = "READY" if span >= 30 else f"{span:.1f}d / 30d"
        log.append(f"ofi journal {asset}: n={len(rows)} span={gate}")
    sh = BOT / "data" / "shadow_fra_momentum.jsonl"
    if sh.exists():
        n = sum(1 for l in sh.read_text().splitlines() if l.strip())
        log.append(f"shadow fra_momentum journal: n={n}")


def run_evals(log: list[str]) -> None:
    py = ROOT / ".venv" / "Scripts" / "python.exe"
    for script in ("run_phase_minus_1.py", "run_extended_eval.py",
                   "run_round3.py", "run_round4.py",
                   "run_round6.py", "run_round7.py", "run_round8.py",
                   "run_round9.py", "run_round10.py", "run_round11.py",
                   "run_round12.py", "run_round13.py", "run_round14.py",
                   "run_round15.py",
                   "run_forward_eval.py",
                   "tools/verify_integrity.py"):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            r = subprocess.run([str(py), script], cwd=ROOT,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=1800, env=env)
        except Exception as e:
            # a hung/timed-out script must not starve the remaining evals
            # (verify_integrity runs LAST — its loss is the worst outcome)
            log.append(f"{script}: FAILED {type(e).__name__}: {e}")
            continue
        status = "ok" if r.returncode == 0 else "FAILED"
        log.append(f"{script}: {status}")
        # surface degradation markers from otherwise-"ok" scripts — a
        # frozen-CSV fallback must be visible in the note (prefixed
        # 'warn' so it doesn't masquerade as a stage failure)
        for wl in (r.stdout or "").splitlines():
            ls = wl.lstrip()
            if ls.startswith(("!!", "WARN")):
                log.append(f"  warn[{script}]: {wl.strip()[:110]}")
        if r.returncode != 0:
            tail = (r.stderr.strip().splitlines()
                    or r.stdout.strip().splitlines())[-3:]
            log.append(f"  tail: {tail}")


def collect_verdicts(man_warn: list[str] | None = None) -> list[str]:
    try:
        import yaml
        man = yaml.safe_load((ROOT / "manifest.yaml").read_text(
            encoding="utf-8")) or {}
        overrides = man.get("verdict_overrides") or {}
    except Exception as e:
        overrides = {}
        # manifest unreadable means verdict_overrides silently skipped —
        # surface it in the note rather than printing raw verdicts
        if man_warn is not None:
            man_warn.append(f"  !! manifest verdict_overrides "
                            f"unreadable: {type(e).__name__}: {e}")
    # one verdict per candidate — later reports in the list supersede
    # earlier ones (round12 re-evals of round11 candidates must not print
    # twice), manifest overrides applied last. Source tagged per verdict.
    seen: dict[str, str] = {}
    src_of: dict[str, str] = {}
    for name in ("report.md", "report_extended.md", "report_round3.md",
                 "report_round4.md",
                 "report_round6.md", "report_round7.md", "report_round8.md",
                 "report_round9.md", "report_round10.md",
                 "report_round11.md", "report_round12.md"):
        p = ROOT / "reports" / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and "**" in line and "candidate" not in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2:
                    seen[cells[0]] = cells[-1]
                    src_of[cells[0]] = name
    out = [f"{cid}: {overrides.get(cid, v)}  [{src_of[cid]}]"
           for cid, v in seen.items()]
    fp = ROOT / "reports" / "report_forward.md"
    if fp.exists():
        cid = None
        for line in fp.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                cid = line[3:].strip()
            elif cid and "post-cutoff:" in line and "**" in line:
                out.append(f"{cid} [fwd]: {line.split('**')[-2]}")
                cid = None
    return out


def _verdict_map() -> dict:
    return {v.split(":", 1)[0].strip(): v.split(":", 1)[1].strip()
            for v in collect_verdicts()}


def verdict_drift_journal(log: list[str], pre: dict, post: dict,
                          stamp: str) -> None:
    """In-sample reports re-execute daily on refreshed data — a verdict
    that moves is post-hoc unless journaled. Append-only ledger: any
    candidate whose printed verdict changed vs the pre-run snapshot, or
    that appeared/vanished, is recorded with both sides so the manifest
    can be reconciled (the funding_carry_24h and cal_weekend_drift
    ledger contradictions were exactly this silent-drift class)."""
    diffs = []
    for cid, v in post.items():
        old = pre.get(cid)
        if old is None:
            diffs.append(f"+ {cid}: NEW -> {v}")
        elif old != v:
            diffs.append(f"~ {cid}: {old} -> {v}")
    for cid in set(pre) - set(post):
        diffs.append(f"- {cid}: vanished (was {pre[cid]})")
    journal = ROOT / "reports" / "verdict_drift.md"
    if diffs or not journal.exists():
        entry = f"\n## {stamp}\n\n" + "".join(f"{d}\n" for d in diffs)
        if not diffs:
            entry += "(baseline snapshot — no prior state)\n"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else ""
        _atomic_write_text(journal, prior + entry)
    log.append(f"verdict drift: {len(diffs)} changes journaled"
               + (f" — {diffs[0]}" if diffs else ""))


def main() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    log: list[str] = []
    log.append(f"# Morning research note — {today}")
    log.append("")
    try:
        pre_verdicts = _verdict_map()
    except Exception:
        # a corrupt manifest/report mid-parse must not kill the whole
        # note — record it and continue with an empty pre-state
        pre_verdicts = {}
        log.append("  !! pre_verdicts snapshot failed: "
                   + traceback.format_exc().splitlines()[-1])
    for stage in (refresh_funding, refresh_candles, refresh_binance,
                  refresh_aux_sources, coverage_sentinel, gate_status,
                  run_evals, commit_coverage_baseline,
                  validate_event_files):
        try:
            stage(log)
        except Exception:
            log.append(f"{stage.__name__} CRASHED:")
            log.append("```\n" + traceback.format_exc()[-1500:] + "\n```")
    try:
        verdict_drift_journal(log, pre_verdicts, _verdict_map(), stamp)
    except Exception:
        log.append("verdict_drift_journal CRASHED:")
        log.append("```\n" + traceback.format_exc()[-800:] + "\n```")
    log.append("")
    log.append("## Current verdicts")
    try:
        log.extend(f"- {v}" for v in collect_verdicts(log))
    except Exception:
        log.append("  !! collect_verdicts failed: "
                   + traceback.format_exc().splitlines()[-1])
    note = OUT / f"{today}.md"
    _atomic_write_text(note, "\n".join(log))
    print("\n".join(log))
    # Honest exit code: a stage failure recorded in the note must show
    # as a nonzero task result — exit-0-on-failure hid verify_integrity
    # FAILs inside the scheduled job (2026-09-25 audit).
    bad = [l for l in log if "FAILED" in l or "CRASHED" in l
           or l.lstrip().startswith("!!")]
    if bad:
        print(f"\n{len(bad)} stage failures — see note")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
