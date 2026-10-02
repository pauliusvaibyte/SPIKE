"""WATCH audit: is each WATCH beating the market's own drift, or just
capturing it? For every event we decompose

    gross_bp = dir * mkt_ret * 1e4
             = dir * mu_span * 1e4        (drift component: unconditional
                                           mean window return, same asset,
                                           same span the events cover)
             + skill_bp                    (excess over unconditional)

Report per candidate: mean gross, mean drift component, mean skill,
t-stat of skill, and long/short asymmetry. A signal that only works
long-side in a bull window is beta, not timing.

Run: .venv/Scripts/python.exe tools/analyze_watch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import data as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _naive(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["t"] = pd.to_datetime(df["t"])
    if getattr(df["t"].dt, "tz", None) is not None:
        df["t"] = df["t"].dt.tz_convert(None)
    return df.sort_values("t").reset_index(drop=True)


def price_map() -> dict[str, pd.Series]:
    """asset -> close series (daily). HL for perp assets, Bitstamp lineage
    for BTC macro-clock events, Binance perp for basis events."""
    m: dict[str, pd.Series] = {}
    for a in ("btc", "sol", "eth", "xrp", "doge", "avax", "link"):
        try:
            m[a.upper()] = _naive(D.candles_full(a, "1d")).set_index("t")["c"]
        except Exception:
            pass
        # intraday-horizon candidates need their own bar grid — a 1d frame
        # cannot attribute a sub-day holding window (funding_carry_24h
        # resolved "no evaluable events" on daily bars alone).
        try:
            m[a.upper() + "_4H"] = _naive(
                D.candles_full(a, "4h")).set_index("t")["c"]
        except Exception:
            pass
        try:
            m["BN_" + a.upper()] = _naive(
                D.binance_klines(a, "1d")).set_index("t")["c"]
        except Exception:
            pass
    he = _naive(D.harmony_extended())
    m["BTC_H"] = pd.to_numeric(
        he.set_index("t")["px_bitstamp"], errors="coerce")
    hd = D.harmony_daily()
    hd["t"] = pd.to_datetime(hd["t"])
    m["BTC_MACRO"] = pd.to_numeric(hd.set_index("t")["c"], errors="coerce")
    return m


# candidate -> (events_csv, price_key_fn)
WATCHES = {
    "xvenue_funding_disloc":   ("events_round3/xvenue_funding_disloc.csv",
                                lambda a: a),
    "fng_extreme_sentiment":   ("events_round4/fng_extreme_sentiment.csv",
                                lambda a: "BTC_MACRO"),
    "equity_lead_btc_5d":      ("events_round6/equity_lead_btc_5d.csv",
                                lambda a: "BTC_MACRO"),
    "dma_40_125_cross_1d":     ("events_round7/dma_40_125_cross_1d.csv",
                                lambda a: a),
    "drawdown_bounce_1d":      ("events_round8/drawdown_bounce_1d.csv",
                                lambda a: a),
    "month_end_drift_1d":      ("events_round8/month_end_drift_1d.csv",
                                lambda a: a),
    "vix_spike_btc_long":      ("events_round8/vix_spike_btc_long.csv",
                                lambda a: "BTC_MACRO"),
    "breadth_thrust_1d":       ("events_round9/breadth_thrust_1d.csv",
                                lambda a: a),
    "flagship_composite_bnbtc": ("events_round10/flagship_composite_bnbtc.csv",
                                 lambda a: "BN_" + a),
    "skew_extreme_reversal_3d": ("events_round11/skew_extreme_reversal_3d.csv",
                                 lambda a: "BTC_H"),
    "iv_term_inversion_3d":    ("events_round11/iv_term_inversion_3d.csv",
                                lambda a: "BTC_H"),
    "liq_flush_bounce_1d":     ("events_round11/liq_flush_bounce_1d.csv",
                                lambda a: "BTC_H"),
    "premium_basis_converge_1d": ("events_round11/premium_basis_converge_1d.csv",
                                  lambda a: "BN_" + a),
    "funding_carry_24h":        ("events_round9/funding_carry_24h.csv",
                                 lambda a: a + "_4H"),
}


REPORT_TO_EVENTS = {
    "report.md": "events", "report_extended.md": "events_extended",
}
for _n in (3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14):
    REPORT_TO_EVENTS[f"report_round{_n}.md"] = f"events_round{_n}"


def discover_watches() -> dict[str, tuple[str, object]]:
    """Current WATCHes from the reports, not a frozen list — the 13-name
    hardcoded map went stale the moment a re-run moved a verdict (audit
    2026-09-25: 5 live WATCHes were unexamined). Manifest
    verdict_overrides supersede the printed cell — an overridden
    candidate must not be analyzed under its stale label."""
    try:
        import yaml
        ov = (yaml.safe_load((ROOT / "manifest.yaml")
                             .read_text(encoding="utf-8")) or {}
              ).get("verdict_overrides") or {}
    except Exception:
        ov = {}
    found: dict[str, tuple[str, object]] = {}
    for rpt, edir in REPORT_TO_EVENTS.items():
        p = ROOT / "reports" / rpt
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not (line.startswith("| ") and "**WATCH**" in line):
                continue
            cid = line.strip("|").split("|")[0].strip()
            if ov.get(cid, "WATCH") != "WATCH":
                continue
            csv = ROOT / "reports" / edir / f"{cid}.csv"
            if csv.exists():
                _, keyf = WATCHES.get(cid, ("", lambda a: a))
                found[cid] = (f"{edir}/{cid}.csv", keyf)
    return found


def main() -> int:
    from harness import falsify as F
    pm = price_map()
    print(f"{'candidate':<28} {'n':>5} {'gross':>7} {'drift':>7} "
          f"{'skill':>7} {'t(skill)':>8} {'long%':>6} "
          f"{'L-skill':>8} {'S-skill':>8}")
    for cid, (csv, keyf) in discover_watches().items():
        p = ROOT / "reports" / csv
        if not p.exists():
            print(f"{cid:<28}  MISSING {csv}")
            continue
        ev = pd.read_csv(p)
        ev = ev.dropna(subset=["gross_bp"])
        if ev.empty:
            print(f"{cid:<28}  empty")
            continue
        # per-asset price frames keyed by the event's own asset labels
        frames = {}
        for a in ev["asset"].unique():
            px = pm.get(keyf(str(a)))
            if px is not None:
                frames[str(a)] = pd.DataFrame(
                    {"t": px.index, "c": px.to_numpy()})
        if not frames:
            print(f"{cid:<28}  no evaluable events")
            continue
        drift = F.drift_skill(ev, frames)
        if not drift["n"]:
            print(f"{cid:<28}  no evaluable events")
            continue
        print(f"{cid:<28} {drift['n']:>5} "
              f"{ev['gross_bp'].mean():>7.1f} "
              f"{drift['mean_drift_bp']:>7.1f} {drift['mean_skill_bp']:>7.1f} "
              f"{drift['t_skill']:>8.2f} {drift['frac_long']:>5.0%} "
              f"{drift['long_skill_bp']:>8.1f} "
              f"{drift['short_skill_bp']:>8.1f}")
    print()
    print("gross/drift/skill = mean bp per event. drift = dir*mu(window,")
    print("same-asset, event-span). skill = gross - drift. t>~2 = timing")
    print("adds over unconditional drift. long% = share of long events;")
    print("L/S-skill = skill on long vs short events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
