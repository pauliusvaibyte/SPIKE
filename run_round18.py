"""Phase -1 Round 18 — DVOL retest on provider-native Deribit feed.

Declared pre-execution in manifest `round18_dvol`. BILLED to OPTIONS-VOL:
horizon/param retests of killed dvol_spike_bounce_1d (round11, +1d on
harmony dvol_close, stale 2026-02-19). Honest prior: KILL. Value: native
feed extends +7mo past the stale harmony cutoff and tests whether the
+5d window resurrects what +1d killed. BTC-only, daily bars.
n_trials=53 effective families.

Run: .venv/Scripts/python.exe run_round18.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import candidates as C
from harness import candidates_round18 as C18
from harness import data as D
from harness import falsify as F
from run_phase_minus_1 import verdict

REPORT = Path(__file__).resolve().parent / "reports" / "report_round18.md"
EXT = Path(__file__).resolve().parent / "data_extended"
N_FAMILIES = 53


def _load_dvol() -> pd.DataFrame:
    rows = json.loads((EXT / "deribit" / "btc_dvol_1d.json").read_text())
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    return df.sort_values("t").reset_index(drop=True)


def main() -> int:
    dvol = _load_dvol()
    btc = D.candles_full("btc", "1d")
    merged = C18.merged_dvol_btc(dvol, btc)
    n_dvol, n_join = len(dvol), len(merged)

    specs = {
        "dvol_spike_btc_long": C18.dvol_spike_btc_long,
        "dvol_level_long": C18.dvol_level_long,
    }

    lines: list[str] = []
    w = lines.append
    w("# Phase -1 Round 18 — DVOL retest (provider-native Deribit feed)")
    w("")
    w("Declared pre-execution in manifest `round18_dvol`. BILLED to")
    w("OPTIONS-VOL — horizon/param retests of killed dvol_spike_bounce_1d")
    w("(round11: +1d on harmony dvol_close, n=138 hit .471 KILL). Prior:")
    w("KILL expected; value is native-feed freshness (+7mo past harmony's")
    w("2026-02-19 cutoff) and +5d horizon coverage.")
    w("")
    w(f"join coverage: {n_join}/{n_dvol} DVOL days matched to BTC closes")
    w("")
    w("| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | "
      "PSR | DSR | placebo_p | splits | leak | **verdict** |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    ev_dir = REPORT.parent / "events_round18"
    ev_dir.mkdir(exist_ok=True)
    for cid, fn in specs.items():
        ev_all = fn(merged)
        F.write_event_csv(ev_all, ev_dir / f"{cid}.csv")
        ev = ev_all.dropna(subset=["ret_bp"]) if not ev_all.empty else ev_all
        wil = C.wilson_gate(ev)
        power = F.power_gate(ev)
        ret = F.events_to_daily_returns(ev)
        imp = F.implausibility_check(ret)
        ss = F.sharpe_stats(ret, n_trials=N_FAMILIES)
        splits = F.split_consistency(ev)
        bound = F.boundary_invariance(fn, merged, ev_all)
        prefix = {"passed": bound["passed"]}
        placebo = (F.placebo_time_shift(ev, {"BTC": btc}, 5, 1440)
                   if not ev.empty else {"p_value": float("nan")})
        drift = F.drift_skill(ev, {"BTC": btc})
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
    w("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
