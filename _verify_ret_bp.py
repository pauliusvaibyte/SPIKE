"""Independent recomputation of event-level ret_bp/gross_bp/hit from raw
candle/journal sources. Read-only audit.

ALL timestamps int64 nanoseconds. bar_ns = bar duration in ns.

Entry-rule hypotheses:
  open_ge    : first bar OPEN >= t            (candidates.py _bar_index, rounds 1-2)
  close_ge   : containing bar (close >= t)    (round6+ _entry_close; first close >= t)
  prior      : bar ending at/before floor(t)  (old floor-minus-one A-bug form)
  settle     : close of bar ending at floor(t,1h) (round3 settle1)
Exit rules:
  open_ge    : close of bar whose open == t_eval (all _row/_emit users)
  close_ge   : close of bar whose close == t_eval (settle1)
  path       : SL/TP/trail path sim on OHLC (fra_*)
Fee: ret_bp = gross_bp - 10.0 flat; position frames use 5bp/unit turnover
allocated to entry/exit day. hit = gross_bp > 1.0 deadband.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
EXT = BASE / "data_extended"
SNAP = BASE / "data_snapshot"
REP = BASE / "reports"
FEE = 10.0
DEADBAND = 1.0

SYM = {"btc": "btcusdt", "sol": "solusdt", "eth": "ethusdt",
       "xrp": "xrpusdt", "doge": "dogeusdt", "avax": "avaxusdt",
       "link": "linkusdt"}


def _jdf(p: Path) -> pd.DataFrame:
    df = pd.DataFrame(json.loads(Path(p).read_text()))
    df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    for col in ("o", "h", "l", "c", "v"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("t").reset_index(drop=True)


_FRAME_CACHE = {}


def frame(kind, asset=None, iv=None, span=None):
    key = (kind, asset, iv, span)
    if key in _FRAME_CACHE:
        return _FRAME_CACHE[key]
    a = (asset or "").lower()
    if kind == "ext":
        df = _jdf(EXT / "candles" / f"{a}_{iv}_full.json")
    elif kind == "snap":
        df = _jdf(SNAP / "data_cache" / f"{a}_{iv}_{span}.json")
    elif kind == "snap15m":
        df = _jdf(SNAP / f".cache_{a}_candles.json")
    elif kind == "bn":
        df = _jdf(EXT / "binance" / f"{SYM[a]}_klines_{iv}.json")
    elif kind == "macro":
        df = pd.read_csv(EXT / "harmony" / "macro_daily.csv",
                         parse_dates=["date"])
        df = df.rename(columns={df.columns[0]: "t"})
        df["c"] = pd.to_numeric(df["btc_price"], errors="coerce")
        df["t"] = pd.to_datetime(df["t"])
        df = df.sort_values("t").reset_index(drop=True)
    elif kind == "hext":
        df = pd.read_csv(EXT / "harmony" / "harmony_extended.csv",
                         parse_dates=["t"])
        df["t"] = pd.to_datetime(df["t"])
        if getattr(df["t"].dt, "tz", None) is not None:
            df["t"] = df["t"].dt.tz_convert(None)
        df = df.sort_values("t").reset_index(drop=True)
        df["c"] = pd.to_numeric(df["px_bitstamp"], errors="coerce")
    elif kind == "prem":
        kl = _jdf(EXT / "binance" / f"{SYM[a]}_klines_1d.json")[["t", "c"]]
        pr = _jdf(EXT / "binance" / f"{SYM[a]}_premium_1d.json")[["t", "c"]]
        pr = pr.rename(columns={"c": "prem"})
        for d in (kl, pr):
            d["t"] = pd.to_datetime(d["t"])
            if getattr(d["t"].dt, "tz", None) is not None:
                d["t"] = d["t"].dt.tz_convert(None)
        df = kl.merge(pr, on="t").sort_values("t").reset_index(drop=True)
    elif kind == "l2":
        p = SNAP / "l2_journal" / f"{a.upper()}_l2_testnet.jsonl"
        rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        df = pd.DataFrame(rows)
        df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
        df = df.sort_values("t").reset_index(drop=True)
        df["c"] = pd.to_numeric(df["mid"], errors="coerce")
    else:
        raise ValueError(kind)
    _FRAME_CACHE[key] = df
    return df


def _ns(df):
    return df["t"].astype("int64").to_numpy()


def B(bar_ms):
    return int(bar_ms) * 1_000_000


def t_ns(x):
    return int(pd.Timestamp(x).value)


# ── index rules (ns) ─────────────────────────────────────────────────────

def idx_open_ge(bt, ts):
    return int(np.searchsorted(bt, ts, side="left"))


def idx_close_ge(bt, ts, bar_ns):
    ts_s = ts // 1_000_000_000 * 1_000_000_000
    ei = int(np.searchsorted(bt, ts_s - bar_ns, side="left"))
    if ei < len(bt) and bt[ei] <= ts_s:
        return ei
    return -1


def idx_prior(bt, ts, bar_ns):
    fl = ts - (ts % bar_ns)
    ei = int(np.searchsorted(bt, fl, side="left"))
    return ei - 1


def idx_settle(bt, ts, bar_ns):
    fl = ts - (ts % bar_ns)
    ei = int(np.searchsorted(bt, fl, side="left"))
    if ei < len(bt) and abs(int(bt[ei]) - fl) <= bar_ns:
        return ei - 1
    return -1


def idx_exit_open(bt, te):
    return int(np.searchsorted(bt, te, side="left"))


def idx_exit_close(bt, te, bar_ns):
    xi = int(np.searchsorted(bt, te, side="left"))
    if xi < len(bt) and int(bt[xi]) + bar_ns == te:
        return xi
    return xi - 1


def exit_path_sim(bars, entry_i, direction, sl, tp, trail, max_bars):
    c = bars["c"].to_numpy(dtype=float)
    h = bars["h"].to_numpy(dtype=float)
    l = bars["l"].to_numpy(dtype=float)
    entry = float(c[entry_i])
    peak = entry
    armed = False
    end = min(entry_i + max_bars, len(bars) - 1)
    for j in range(entry_i + 1, end + 1):
        if direction > 0:
            adverse, favorable = l[j], h[j]
        else:
            adverse, favorable = h[j], l[j]
        worst = (adverse / entry - 1.0) * direction
        best = (favorable / entry - 1.0) * direction
        if worst <= -sl:
            return j, -sl, "sl"
        if best >= tp:
            armed = True
        peak = max(peak, favorable) if direction > 0 else min(peak, favorable)
        if armed:
            dd = (peak - float(c[j])) / peak * direction
            if dd >= trail:
                return j, (float(c[j]) / entry - 1.0) * direction, "trail"
    j = end
    return j, (float(c[j]) / entry - 1.0) * direction, "time"


RESULTS = []


def _rec(file, i, r, verdict, rep=np.nan, rec=np.nan, **kw):
    rep_g = r.get("gross_bp", rep)
    d = dict(file=file, row=i, t=str(r["t"]),
             asset=str(r.get("asset", "")), dir=r.get("dir"),
             rep=rep_g, rec=rec,
             delta=(float(rep_g) - rec if np.isfinite(rep_g) and np.isfinite(rec)
                    else np.nan),
             verdict=verdict)
    d.update(kw)
    RESULTS.append(d)


def verify_row(file, i, r, bt, bc, entry_i, exit_i, note=""):
    rep_g = r.get("gross_bp", np.nan)
    if (entry_i is None or entry_i < 0 or entry_i >= len(bc)
            or exit_i is None or exit_i >= len(bc) or exit_i < 0):
        _rec(file, i, r, "NO-EVAL-IDX " + note, rec=np.nan,
             ei=entry_i, xi=exit_i)
        return
    e0, e1 = float(bc[entry_i]), float(bc[exit_i])
    if not (np.isfinite(e0) and e0 > 0 and np.isfinite(e1) and e1 > 0):
        _rec(file, i, r, "BADPX " + note, rec=np.nan)
        return
    g = float(r["dir"]) * (e1 / e0 - 1.0) * 1e4
    rep_r = r.get("ret_bp", np.nan)
    fee_ok = np.isfinite(rep_r) and abs((g - FEE) - float(rep_r)) < 0.5
    rep_h = r.get("hit", None)
    hit_ok = (bool(rep_h) == (rep_g > DEADBAND)) if rep_h is not None else None
    delta = float(rep_g) - g if np.isfinite(rep_g) else np.nan
    v = ("MATCH" if (np.isfinite(delta) and abs(delta) < 0.5)
         else "MISMATCH") + " " + note
    _rec(file, i, r, v, rec=g,
         ei=entry_i, xi=exit_i,
         entry_open=str(pd.Timestamp(int(bt[entry_i]))),
         exit_open=str(pd.Timestamp(int(bt[exit_i]))),
         fee=f"{float(rep_g) - float(rep_r):.2f}" if np.isfinite(rep_r) else "?",
         fee_ok=fee_ok, hit_ok=hit_ok)


def uncovered_check(file, i, r, ev):
    ok = (pd.isna(r["gross_bp"]) and str(r.get("hit")) != "True"
          and (str(r.get("exit_reason")) == "uncovered"
               if "exit_reason" in ev.columns else True)
          and (r["t_eval"] == r["t"]
               if "exit_reason" in ev.columns else True))
    _rec(file, i, r,
         ("UNCOVERED-OK" if ok else "UNCOVERED-BAD")
         + f" er={r.get('exit_reason')} hit={r.get('hit')} "
         + f"te==t:{r['t_eval'] == r['t']}")


def load_events(rel):
    return pd.read_csv(REP / rel)


def pick_rows(ev, n=2):
    idxs = []
    cov = ev[ev["ret_bp"].notna()] if "ret_bp" in ev else ev
    if len(cov):
        for f_ in np.linspace(0.05, 0.95, n):
            idxs.append(int(cov.index[min(len(cov) - 1, int(f_ * len(cov)))]))
    unc = ev[ev["ret_bp"].isna()] if "ret_bp" in ev else ev.iloc[:0]
    if len(unc):
        idxs.append(int(unc.index[len(unc) // 2]))
    return list(dict.fromkeys(idxs))


def std_close_eval(rel, frames, bar_ms, entry="open_ge", exit_="open_ge",
                   n=2, alt_entries=("prior",)):
    """Recompute via declared convention; also record alt-hypothesis deltas."""
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        if a not in frames:
            _rec(rel, i, r, "NO-FRAME")
            continue
        f = frames[a]
        bt, bc = _ns(f), f["c"].to_numpy(dtype=float)
        if pd.isna(r["ret_bp"]):
            uncovered_check(rel, i, r, ev)
            continue
        ts, te = t_ns(r["t"]), t_ns(r["t_eval"])
        rule = {"open_ge": idx_open_ge,
                "close_ge": lambda b, s: idx_close_ge(b, s, B(bar_ms)),
                "prior": lambda b, s: idx_prior(b, s, B(bar_ms)),
                "settle": lambda b, s: idx_settle(b, s, B(bar_ms))}[entry]
        ei = rule(bt, ts)
        xi = (idx_exit_open(bt, te) if exit_ == "open_ge"
              else idx_exit_close(bt, te, B(bar_ms)))
        verify_row(rel, i, r, bt, bc, ei, xi, f"{entry}/{exit_}")
        # alternate-entry deltas for the A-bug check
        for alt in (alt_entries or ()):
            if alt == entry:
                continue
            arule = {"open_ge": idx_open_ge,
                     "close_ge": lambda b, s: idx_close_ge(b, s, B(bar_ms)),
                     "prior": lambda b, s: idx_prior(b, s, B(bar_ms)),
                     "settle": lambda b, s: idx_settle(b, s, B(bar_ms))}[alt]
            ae = arule(bt, ts)
            if 0 <= ae < len(bc) and 0 <= xi < len(bc) \
                    and bc[ae] > 0 and bc[xi] > 0:
                g_alt = float(r["dir"]) * (float(bc[xi]) / float(bc[ae]) - 1.0) * 1e4
                RESULTS[-1][f"alt_{alt}_delta"] = round(float(r["gross_bp"]) - g_alt, 3)
    return ev


def path_eval(rel, frames, bar_ms, horizon_bars, entry="open_ge",
              sl=0.04, tp=0.08, trail=0.03, n=3):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        f = frames[a]
        bt, bc = _ns(f), f["c"].to_numpy(dtype=float)
        if pd.isna(r["ret_bp"]):
            uncovered_check(rel, i, r, ev)
            continue
        ts = t_ns(r["t"])
        ei = (idx_open_ge(bt, ts) if entry == "open_ge"
              else idx_close_ge(bt, ts, B(bar_ms)))
        if ei >= len(bc):
            _rec(rel, i, r, "ENTRY-OOB")
            continue
        xj, ret, reason = exit_path_sim(f, ei, float(r["dir"]), sl, tp, trail,
                                        horizon_bars)
        g = ret * 1e4
        delta = float(r["gross_bp"]) - g
        te_rep = t_ns(r["t_eval"])
        te_ok = int(bt[xj]) == int(te_rep)
        er_ok = str(r.get("exit_reason")) == reason
        ok = abs(delta) < 0.5
        # alt entry hypothesis for the A-bug check
        ei_prior = idx_prior(bt, ts, B(bar_ms))
        alt_d = np.nan
        if 0 <= ei_prior < len(bc):
            _, ret_p, _ = exit_path_sim(f, ei_prior, float(r["dir"]),
                                        sl, tp, trail, horizon_bars)
            alt_d = float(r["gross_bp"]) - ret_p * 1e4
        _rec(rel, i, r,
             ("MATCH" if ok else "MISMATCH")
             + (" te!" if not te_ok else "")
             + (" er!" if not er_ok else ""),
             rec=g, delta=delta, exit_reason=f"{r.get('exit_reason')}/{reason}",
             te_ok=te_ok, ei=ei, xj=xj, alt_prior_delta=round(alt_d, 3))


def settle_eval(rel, frames, bar_ms=3_600_000, n=3):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        f = frames[a]
        bt, bc = _ns(f), f["c"].to_numpy(dtype=float)
        if pd.isna(r["ret_bp"]):
            uncovered_check(rel, i, r, ev)
            continue
        ei = idx_settle(bt, t_ns(r["t"]), B(bar_ms))
        xi = idx_exit_close(bt, t_ns(r["t_eval"]), B(bar_ms))
        verify_row(rel, i, r, bt, bc, ei, xi, "settle")
        # alt: entry one bar later (next open) vs one earlier
        xi2 = xi
        for lbl, ae in (("alt_next", ei + 1), ("alt_prior", ei - 1)):
            if 0 <= ae < len(bc) and 0 <= xi2 < len(bc):
                g_alt = float(r["dir"]) * (float(bc[xi2]) / float(bc[ae]) - 1.0) * 1e4
                RESULTS[-1][lbl] = round(float(r["gross_bp"]) - g_alt, 3)


def disloc_eval(rel, frames, horizon_bars=2, n=3):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        f = frames[a]
        bt, bc = _ns(f), f["c"].to_numpy(dtype=float)
        if pd.isna(r["ret_bp"]):
            uncovered_check(rel, i, r, ev)
            continue
        xi = idx_exit_open(bt, t_ns(r["t_eval"]))
        ei = xi - horizon_bars
        verify_row(rel, i, r, bt, bc, ei, xi, "epoch")
        if 0 <= ei < len(bt):
            close_ns = int(bt[ei]) + B(14_400_000)
            dt_s = (close_ns - t_ns(r["t"])) / 1e9
            RESULTS[-1]["entryclose_minus_t_s"] = round(dt_s, 1)


def position_eval(rel, px_by_asset, n=4):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        px = px_by_asset[a]
        pt = _ns(px)
        c = px["c"].to_numpy(dtype=float)
        i0 = int(np.searchsorted(pt, t_ns(r["t"]), side="left"))
        if i0 >= len(c) or i0 == 0 or int(pt[i0]) != t_ns(r["t"]):
            _rec(rel, i, r, "NO-IDX")
            continue
        r1 = c[i0] / c[i0 - 1] - 1.0
        w = float(r["w"])
        g = w * r1 * 1e4
        delta = float(r["gross_bp"]) - g
        fee = float(r["gross_bp"]) - float(r["ret_bp"])
        _rec(rel, i, r,
             ("MATCH" if abs(delta) < 0.5 else "MISMATCH") + f" fee={fee:.2f}",
             rec=g, delta=delta, fee=round(fee, 3), w=w,
             r1_bp=round(r1 * 1e4, 3))


def carry_eval(rel, frames, n=3):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        f = frames[a]
        bt, bc = _ns(f), f["c"].to_numpy(dtype=float)
        if pd.isna(r["ret_bp"]):
            uncovered_check(rel, i, r, ev)
            continue
        ei = idx_close_ge(bt, t_ns(r["t"]), B(14_400_000))
        xi = idx_exit_open(bt, t_ns(r["t_eval"]))
        carry = float(r.get("carry_bp", 0.0) or 0.0)
        rep_px = float(r["gross_bp"]) - carry
        if ei < 0 or xi >= len(bc):
            _rec(rel, i, r, "NO-IDX", rep=rep_px)
            continue
        g = float(r["dir"]) * (float(bc[xi]) / float(bc[ei]) - 1.0) * 1e4
        delta = rep_px - g
        _rec(rel, i, r,
             ("MATCH" if abs(delta) < 0.5 else "MISMATCH")
             + f" (px-part; carry={carry:.1f})",
             rep=rep_px, rec=g, delta=delta, ei=ei, xi=xi)


def l2_eval(rel, frames, n=3):
    ev = load_events(rel)
    for i in pick_rows(ev, n):
        r = ev.loc[i]
        a = str(r["asset"])
        f = frames[a]
        jt = _ns(f)
        jc = pd.to_numeric(f["c"], errors="coerce").to_numpy(dtype=float)
        ts, te = t_ns(r["t"]), t_ns(r["t_eval"])
        i0 = int(np.searchsorted(jt, ts, side="left"))
        j1 = int(np.searchsorted(jt, te, side="left"))
        if i0 >= len(jc) or j1 >= len(jc):
            _rec(rel, i, r, "NO-IDX")
            continue
        g = float(r["dir"]) * (jc[j1] / jc[i0] - 1.0) * 1e4
        delta = float(r["gross_bp"]) - g
        _rec(rel, i, r,
             "MATCH" if abs(delta) < 0.5 else "MISMATCH",
             rec=g, delta=delta)


def main():
    A7 = ("btc", "sol", "eth", "xrp", "doge", "avax", "link")
    ext4 = {a.upper(): frame("ext", a, "4h") for a in A7}
    ext1 = {a.upper(): frame("ext", a, "1d") for a in A7}
    ext1h = {a.upper(): frame("ext", a, "1h") for a in A7}

    std_close_eval("events/tsmom_daily_14d.csv",
                   {"BTC": frame("snap", "btc", "1d", "365d"),
                    "SOL": frame("snap", "sol", "1d", "365d")},
                   86_400_000, n=2)
    std_close_eval("events/mrv_rsi_reversion_1h.csv",
                   {"BTC": frame("snap", "btc", "1h", "365d"),
                    "SOL": frame("snap", "sol", "1h", "180d")},
                   3_600_000, n=2)
    std_close_eval("events/trend1_donchian_4h.csv",
                   {"BTC": frame("snap", "btc", "4h", "180d"),
                    "SOL": frame("snap", "sol", "4h", "180d")},
                   14_400_000, n=2)
    std_close_eval("events/flush1_reversal_15m.csv",
                   {"BTC": frame("snap15m", "btc"),
                    "SOL": frame("snap15m", "sol")},
                   900_000, n=2)
    std_close_eval("events/basis1_premium_p10.csv",
                   {"BTC": frame("snap15m", "btc"),
                    "SOL": frame("snap15m", "sol")},
                   900_000, n=2, alt_entries=("close_ge", "prior"))
    path_eval("events/fra_momentum_p90_long.csv",
              {"BTC": frame("snap15m", "btc")}, 900_000, 96, n=3)
    path_eval("events/fra_fade_p90_short.csv",
              {"BTC": frame("snap15m", "btc"),
               "SOL": frame("snap15m", "sol")}, 900_000, 96, n=3)
    path_eval("events_extended/fra_momentum_p90_long.csv",
              {"BTC": frame("ext", "btc", "4h")}, 14_400_000, 6, n=3)
    path_eval("events_extended/fra_momentum_p90_long_r3000.csv",
              {"BTC": frame("ext", "btc", "4h")}, 14_400_000, 6, n=3)
    path_eval("events_extended/fra_fade_p90_short.csv",
              {"BTC": frame("ext", "btc", "4h"),
               "SOL": frame("ext", "sol", "4h")}, 14_400_000, 6, n=3)
    std_close_eval("events_extended/basis1_premium_p10.csv",
                   {"BTC": frame("ext", "btc", "4h"),
                    "SOL": frame("ext", "sol", "4h")},
                   14_400_000, n=2, alt_entries=("close_ge", "prior"))
    settle_eval("events_round3/settle1_funding_drift.csv",
                {"BTC": frame("ext", "btc", "1h"),
                 "SOL": frame("ext", "sol", "1h")}, n=3)
    disloc_eval("events_round3/xvenue_funding_disloc.csv",
                {"BTC": frame("ext", "btc", "4h"),
                 "SOL": frame("ext", "sol", "4h")}, n=3)
    std_close_eval("events_round3/xvenue_basis_converge.csv",
                   {"BTC": frame("ext", "btc", "1h"),
                    "SOL": frame("ext", "sol", "1h")},
                   3_600_000, n=2)
    std_close_eval("events_round3/xvenue_leadlag_1h.csv",
                   {"BTC": frame("ext", "btc", "1h"),
                    "SOL": frame("ext", "sol", "1h")},
                   3_600_000, n=2)
    std_close_eval("events_round4/fng_extreme_sentiment.csv",
                   {"BTC": frame("macro")}, 86_400_000, n=2)
    std_close_eval("events_round4/onchain_mvrv_regime.csv",
                   {"BTC": frame("macro")}, 86_400_000, n=2)
    std_close_eval("events_round6/hl_premium_disloc.csv",
                   ext4, 14_400_000, entry="close_ge",
                   alt_entries=("open_ge", "prior"), n=3)
    std_close_eval("events_round6/funding_xasset_rv.csv",
                   ext4, 14_400_000, entry="close_ge",
                   alt_entries=("open_ge", "prior"), n=3)
    std_close_eval("events_round6/xasset_btc_leads_alts.csv",
                   ext1h, 3_600_000, n=2)
    std_close_eval("events_round7/dma_40_125_cross_1d.csv",
                   ext1, 86_400_000, n=2)
    std_close_eval("events_round7/dma_40_125_cross_4h.csv",
                   ext4, 14_400_000, n=2)
    std_close_eval("events_round8/rsi2_connors_1d.csv",
                   ext1, 86_400_000, n=2)
    std_close_eval("events_round8/drawdown_bounce_1d.csv",
                   ext1, 86_400_000, n=2)
    std_close_eval("events_round8/funding_flip_momentum.csv",
                   ext4, 14_400_000, entry="close_ge",
                   alt_entries=("open_ge", "prior"), n=2)
    carry_eval("events_round9/funding_carry_24h.csv", ext4, n=3)
    std_close_eval("events_round9/us_session_drift.csv",
                   ext4, 14_400_000, n=2)
    std_close_eval("events_round9/weekly_loser_bounce_1d.csv",
                   ext1, 86_400_000, n=2)
    position_eval("events_round10/flagship_base_btc.csv",
                  {"BTC": frame("ext", "btc", "1d")})
    position_eval("events_round10/flagship_composite_bnbtc.csv",
                  {"BTC": frame("bn", "btc", "1d")})
    position_eval("events_round10/flagship_base_alts.csv",
                  {a.upper(): frame("ext", a, "1d") for a in A7})
    std_close_eval("events_round11/nrpl_spike_top_3d.csv",
                   {"BTC": frame("hext")}, 86_400_000, n=2)
    std_close_eval("events_round11/skew_extreme_reversal_3d.csv",
                   {"BTC": frame("hext")}, 86_400_000, n=2)
    std_close_eval("events_round12/puell_extreme_7d.csv",
                   {"BTC": frame("hext")}, 86_400_000, n=2)
    std_close_eval("events_round12/xvenue_funding_spread_1d.csv",
                   {"BTC": frame("hext")}, 86_400_000, n=2)
    std_close_eval("events_fwd_mom24h_cont.csv", ext4, 14_400_000, n=2)
    std_close_eval("events_fwd_funding_streak_fade.csv",
                   ext4, 14_400_000, entry="close_ge",
                   alt_entries=("open_ge", "prior"), n=3)
    std_close_eval("events_fwd_premium_cont.csv",
                   ext4, 14_400_000, entry="close_ge",
                   alt_entries=("open_ge", "prior"), n=2)
    std_close_eval("events_fwd_xvenue_disloc_cont.csv",
                   ext4, 14_400_000, entry="open_ge",
                   alt_entries=("close_ge", "prior"), n=2)
    std_close_eval("events_fwd_alt_resid_cont.csv", ext1, 86_400_000, n=2)
    std_close_eval("events_fwd_alt_reversal.csv", ext1h, 3_600_000, n=2)
    std_close_eval("events_fwd_nrpl_cont.csv", {"BTC": frame("hext")},
                   86_400_000, n=2)
    std_close_eval("events_fwd_puell_extreme_cont.csv", {"BTC": frame("hext")},
                   86_400_000, n=2)
    std_close_eval("events_fwd_premium_basis_converge.csv",
                   {a.upper(): frame("prem", a) for a in A7},
                   86_400_000, n=2)
    position_eval("events_fwd_flagship_hlbtc.csv",
                  {"BTC": frame("ext", "btc", "1d")})
    l2_eval("events/ofi_imbalance_l2.csv",
            {"BTC": frame("l2", "btc"), "SOL": frame("l2", "sol")})

    df = pd.DataFrame(RESULTS)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_rows", 400)
    pd.set_option("display.max_colwidth", 48)
    df.to_csv(BASE / "_verify_results.csv", index=False)
    print(df.to_string())
    m = df[df["delta"].notna()]
    print("\n=== summary ===")
    print("rows recomputed:", len(m),
          "| match(<0.5bp):", int((m["delta"].abs() < 0.5).sum()),
          "| mismatch:", int((m["delta"].abs() >= 0.5).sum()),
          "| max |delta|:", float(m["delta"].abs().max()))
    bad = m[m["delta"].abs() >= 0.5]
    if len(bad):
        print(bad[["file", "row", "t", "rep", "rec", "delta", "verdict"]]
              .to_string())


if __name__ == "__main__":
    main()
