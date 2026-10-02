"""Falsification stack — power gate, prefix-invariance, placebos, PSR/DSR,
CSCV/PBO over parameter neighborhoods, split consistency.

Layered per the Phase -1 manifest: power first, calibration second, then
evaluation. Verdicts are semantic, never a single scalar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from purgedcv import (
    deflated_sharpe_ratio,
    min_track_record_length,
    minimum_backtest_length,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

DAYS_PER_YEAR = 365.0
IMPLAUSIBLE_SHARPE = 4.0   # Penrose-analog gate: Sharpe ~18 corpus lesson


def _to_ns(s) -> np.ndarray:
    """Timestamps -> int64 nanoseconds, robust to string input and to
    mixed storage units. Bare .astype('int64') preserves the stored unit
    (ms/us/ns differ) — a datetime64[ms] frame vs a datetime64[ns] frame
    silently misaligns searchsorted by 10^6; strings crash outright."""
    return (pd.to_datetime(s, utc=True, format="mixed")
            .dt.as_unit("ns").astype("int64").to_numpy())


# ── return-series plumbing ───────────────────────────────────────────────

def events_to_daily_returns(events: pd.DataFrame, freq: str = "1D") -> pd.Series:
    """Attribute each event's net return uniformly across its holding window.

    Overlapping holds sum. Produces the per-period return stream the
    Sharpe-family statistics consume.
    """
    if events.empty:
        return pd.Series(dtype=float)
    ev = events.dropna(subset=["ret_bp"])
    # drop unresolvable/invalid windows BEFORE the ceil() below — a NaT
    # bound crashes int() and a negative window silently attributes the
    # return to the signal day
    tt = pd.to_datetime(ev["t"], utc=True, format="mixed",
                        errors="coerce")
    te = pd.to_datetime(ev["t_eval"], utc=True, format="mixed",
                        errors="coerce")
    keep = (tt.notna() & te.notna() & (te >= tt)).to_numpy()
    ev = ev[keep]
    if ev.empty:
        return pd.Series(dtype=float)
    # use the normalized UTC stamps — re-parsing raw row values crashes
    # on naive/aware mixes that the coercion above already resolved
    tts = tt[keep].reset_index(drop=True)
    tes = te[keep].reset_index(drop=True)
    pieces = []
    for i, (_, r) in enumerate(ev.iterrows()):
        t0, t1 = tts.iloc[i], tes.iloc[i]
        n = max(1, int(np.ceil((t1 - t0) / pd.Timedelta(freq))))
        per = r["ret_bp"] / n / 1e4
        # return accrues over (t0, t1]: first allocated day is the first
        # full bucket AFTER the signal, not the signal day itself — unless
        # the event is same-day (position frames), which earns day t0.
        start = (t0.floor(freq) + pd.Timedelta(freq)
                 if t1 > t0 else t0.floor(freq))
        idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
        pieces.append(pd.Series(per, index=idx))
    s = pd.concat(pieces).groupby(level=0).sum().sort_index()
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freq, tz="UTC")
    return s.reindex(full_idx, fill_value=0.0)


def sharpe_ann(ret: pd.Series) -> float:
    sd = ret.std()
    if not (sd > 0):
        # zero-variance stream: Sharpe is undefined, not 0 — a constant
        # +8bp/day series is the degenerate artifact implausibility_check
        # exists to catch, so report +-inf rather than "no edge"
        m = float(ret.mean())
        return float(np.sign(m) * np.inf) if m != 0 else 0.0
    return float(ret.mean() / sd * np.sqrt(DAYS_PER_YEAR))


def profit_factor(ret_bp: np.ndarray) -> float:
    w = ret_bp[ret_bp > 0].sum(); l = -ret_bp[ret_bp < 0].sum()
    return float(w / l) if l > 0 else (float("inf") if w > 0 else 0.0)


# ── Layer O: power gate (runs FIRST, before compute) ─────────────────────

# one-sided 95% t-threshold for demonstrated drift skill — the old bare
# `> 0` sign check promoted ~24% of pure-beta streams on an uptrend
SKILL_T_MIN = 1.645


_POINT_RUN_CAP_NS = int(2 * 86_400e9)   # consecutive-position cap: 2d


def _episode_intervals(t: np.ndarray, e: np.ndarray
                       ) -> tuple[list, np.ndarray]:
    """Union-merge episode intervals for ONE asset (sorted int64 ns).

    Asymmetric boundary rule: WINDOW-WINDOW boundary touching is disjoint
    (one exposure exits where the next enters — separate bets); any POINT
    row touching a boundary is the same instant and merges (fails closed:
    under-counts on ambiguous attribution, never over-counts).

    Point rows (t_eval <= t — position markers) merge into an open window
    (t <= win_end), or into a point run when the gap matches the LOCAL
    cadence: gap <= min(2x min(neighbor gaps), 2d absolute cap). A global
    median gets polluted by mixed cadences (47 hourly + 40 daily rows
    minted 41 fake episodes) and self-scales to absurdity (10y-spaced
    points merged into 1) — the local test merges only genuinely
    consecutive position bars."""
    pt_pos = np.flatnonzero((e - t) <= 0)
    pt = t[pt_pos]
    # mergeable[k] = gap between pt[k] and pt[k+1] continues a run
    if len(pt) > 1:
        g = np.diff(pt)
        left = np.concatenate(([g[0]], g[:-1]))
        right = np.concatenate((g[1:], [g[-1]]))
        mergeable = g <= np.minimum(2 * np.minimum(left, right),
                                    _POINT_RUN_CAP_NS)
    else:
        mergeable = np.zeros(0, dtype=bool)
    run_end_of = {}   # pt index -> does gap AFTER it merge (helper map)
    for k in range(len(mergeable)):
        run_end_of[int(pt_pos[k])] = bool(mergeable[k])
    eps = []
    labels = np.empty(len(t), dtype=int)   # episode id per row
    win_end = None          # running end of the current windowed episode
    last_pi = -1            # index (into t) of last point row in the run
    cur = 0
    for i, (ti, ei) in enumerate(zip(t, e)):
        if ei > ti:                       # windowed row
            # window touching window is DISJOINT exposure ([0,10] exits
            # where [10,20] enters) — half-open boundary; a point row
            # touching is the same instant and merges below.
            if win_end is None or ti >= win_end:
                eps.append([ti, ei]); cur = len(eps) - 1
            elif ei > eps[cur][1]:
                eps[cur][1] = ei
            win_end = eps[cur][1]
            last_pi = -1
        else:                             # point row (same-day marker)
            in_window = win_end is not None and ti <= win_end
            in_run = last_pi >= 0 and run_end_of.get(last_pi, False)
            if in_run:
                # a run continuing INSIDE an open window must never shrink
                # the window's end — eps[cur] may be that window's episode
                eps[cur][1] = max(eps[cur][1], ti)
            elif not in_window:
                eps.append([ti, ti]); cur = len(eps) - 1
            last_pi = i
            # in_window: absorbed by the open window — nothing to extend
        labels[i] = cur
    return eps, labels


def _merged_episode_ids(t: np.ndarray, e: np.ndarray,
                        asset: np.ndarray) -> np.ndarray:
    """Per-ROW global episode ids: per-asset union-merge via
    _episode_intervals, then cross-asset union of the resulting
    intervals (same asymmetric boundary rule as _count_episodes) —
    one economic shock spanning assets is one episode, and every member
    row shares its id. Caller passes only evaluable rows."""
    ids = np.empty(len(t), dtype=int)
    if len(t) == 0:
        return ids
    g_eps: list = []
    g_rows: list = []      # per-eps: list of row indices
    for name in dict.fromkeys(asset.tolist()):
        m = np.flatnonzero(asset == name)
        # same windows-first tie-break as _count_episodes — point at a
        # window's boundary merges into it regardless of input order
        order = np.lexsort(((e[m] <= t[m]).astype(np.int8), t[m]))
        rows = m[order]
        eps, labels = _episode_intervals(t[rows], e[rows])
        for k in range(len(eps)):
            g_eps.append(eps[k])
            g_rows.append(rows[labels == k].tolist())
    order = sorted(range(len(g_eps)),
                   key=lambda k: (g_eps[k][0], -g_eps[k][1]))
    end, end_wide, mid = None, False, -1
    for k in order:
        s, en = g_eps[k]
        wide = en > s
        if end is None or s > end or (s == end and wide and end_wide):
            mid += 1
            end, end_wide = en, wide
        elif en > end:
            end, end_wide = en, wide
        for ri in g_rows[k]:
            ids[ri] = mid
    return ids


def episode_hit_stats(events: pd.DataFrame) -> dict:
    """Episode-level hit rate + Wilson bounds — the independence-honest
    version of the row-level wilson_gate. A merged episode's outcome is
    its summed net bp; win iff > 0. Clustered streams (one shock =
    many rows) can no longer inflate hit-rate evidence."""
    out = {"n_ep": 0, "wins": 0, "hit": float("nan"),
           "wilson_lo": float("nan"), "wilson_hi": float("nan")}
    if events.empty or not {"t", "t_eval", "ret_bp"} <= set(events.columns):
        return out
    tt = pd.to_datetime(events["t"], utc=True, format="mixed",
                        errors="coerce")
    te = pd.to_datetime(events["t_eval"], utc=True, format="mixed",
                        errors="coerce")
    ret = pd.to_numeric(events["ret_bp"], errors="coerce")
    # te>=tt matches the contract/returns-layer drop — reversed-interval
    # rows must not mint episodes in direct callers that skip validation
    ok = (ret.notna() & np.isfinite(ret.astype(float))
          & tt.notna() & te.notna() & (te >= tt)).to_numpy()
    if not ok.any():
        return out
    t = tt.dt.as_unit("ns").astype("int64").to_numpy()[ok]
    e = te.dt.as_unit("ns").astype("int64").to_numpy()[ok]
    a = (events.loc[ok, "asset"].astype(str).to_numpy()
         if "asset" in events.columns else np.full(int(ok.sum()), ""))
    rv = ret.to_numpy()[ok].astype(float)
    gid = _merged_episode_ids(t, e, a)
    n_ep = int(gid.max()) + 1
    ep_net = np.bincount(gid, weights=rv, minlength=n_ep)
    wins = int((ep_net > 0).sum())
    out["n_ep"], out["wins"] = n_ep, wins
    if n_ep:
        # Wilson score interval (z=1.96) — local copy keeps falsify
        # independent of candidates.py import direction
        z = 1.959963984540054          # norm.ppf(0.975)
        z2 = z * z                     # center/denominator use z^2
        p = wins / n_ep
        den = 1 + z2 / n_ep
        ctr = (p + z2 / (2 * n_ep)) / den
        # half-width scales by z, not z^2 — the z2 multiplier here made
        # every interval ~1.96x too wide (30/40 wins: lo 0.473 vs true
        # 0.598), biasing the promotion gate against live edges
        half = (z * np.sqrt(p * (1 - p) / n_ep + z2 / (4 * n_ep ** 2))
                / den)
        out["hit"] = p
        out["wilson_lo"] = float(max(0.0, ctr - half))
        out["wilson_hi"] = float(min(1.0, ctr + half))
    return out


def _count_episodes(events: pd.DataFrame) -> float:
    """Effective independent-episode count for any event frame.

    Only EVALUABLE rows count — covered rows (finite ret_bp) with valid
    time bounds. Uncovered/unresolved rows carry no realized outcome, so
    a stream of them cannot fake power (2026-09-25: an all-uncovered
    windowed frame reached DEAD on zero evidence). Per-asset episodes
    union-merge, then episode INTERVALS cluster across assets by
    overlap — one economic shock spanning assets/windows is one
    observation (exact-timestamp dedupe was evadable by 1s jitter and
    never merged staggered windows)."""
    if events.empty or not {"t", "t_eval", "ret_bp"} <= set(events.columns):
        return 0.0
    tt = pd.to_datetime(events["t"], utc=True, format="mixed",
                        errors="coerce")
    te = pd.to_datetime(events["t_eval"], utc=True, format="mixed",
                        errors="coerce")
    ret = pd.to_numeric(events["ret_bp"], errors="coerce")
    ok = (ret.notna() & np.isfinite(ret.astype(float))
          & tt.notna() & te.notna() & (te >= tt)).to_numpy()
    if not ok.any():
        return 0.0
    a = (events.loc[ok, "asset"].astype(str).to_numpy()
         if "asset" in events.columns else np.full(int(ok.sum()), ""))
    # as_unit("ns") BEFORE int64 — bare astype preserves the stored unit
    # and a us/ns mix (CSV-inferred dtypes can differ per column) makes
    # every row look like one giant window
    t = tt.dt.as_unit("ns").astype("int64").to_numpy()[ok]
    e = te.dt.as_unit("ns").astype("int64").to_numpy()[ok]
    eps = []
    for name in pd.unique(a):
        m = a == name
        # ties break WINDOWS-first so a point at a window's boundary
        # merges into it deterministically — input order among same-t
        # rows must not change episode membership
        order = np.lexsort(((e[m] <= t[m]).astype(np.int8), t[m]))
        eps.extend(_episode_intervals(t[m][order], e[m][order])[0])
    if not eps:
        return 0.0
    # Asymmetric closed merge: a WINDOWED interval starting exactly where
    # the running episode's window ended is disjoint exposure (separate);
    # any point interval touching the boundary is the same instant (merge).
    # Deterministic via (start, -end) sort — the old strict '>' both
    # under-merged same-instant shocks and was row-order dependent.
    eps.sort(key=lambda iv: (iv[0], -iv[1]))
    n_ep, end, end_wide = 0, None, False
    for s, en in eps:
        wide = en > s
        if end is None or s > end or (s == end and wide and end_wide):
            n_ep += 1
            end, end_wide = en, wide
        elif en > end:
            end, end_wide = en, wide
    return float(n_ep)


def power_gate(events: pd.DataFrame, target_sharpe: float = 0.5,
               min_span_days: int = 30, n_trials: int = 50) -> dict:
    """Can this candidate's data resolve a claimed edge at all?
    Two axes: effective episode count AND temporal span — clustered
    events are not n independent observations (autocorrelation).

    n_eff counts union-merged episodes over EVALUABLE rows only and is
    computed BEFORE every early return — a refused power check still
    reports the honest count and downstream gates never fall back to raw
    n (the 2026-09-25 A27 failure mode). Span likewise covers evaluable
    evidence only."""
    n = len(events)
    out = {"n_events": n, "sufficient": False, "reason": ""}
    n_eff = _count_episodes(events)
    tt = (pd.to_datetime(events["t"], utc=True, format="mixed",
                         errors="coerce")
          if "t" in events else pd.Series(dtype="datetime64[ns, UTC]"))
    te = (pd.to_datetime(events["t_eval"], utc=True, format="mixed",
                         errors="coerce")
          if "t_eval" in events else pd.Series(dtype="datetime64[ns, UTC]"))
    ok = ((pd.to_numeric(events["ret_bp"], errors="coerce").notna()
           & np.isfinite(pd.to_numeric(events["ret_bp"], errors="coerce")
                         .astype(float))
           & tt.notna() & te.notna() & (te >= tt))
          if {"t", "t_eval", "ret_bp"} <= set(events.columns)
          else pd.Series(False, index=events.index))
    horizons = ((te[ok] - tt[ok]).dt.total_seconds() / 86400.0
                if ok.any() else pd.Series(dtype=float))
    med_h = (float(horizons[horizons > 0].median())
             if (horizons > 0).any() else 1.0)
    span = int((te[ok].max() - tt[ok].min()).days) if ok.any() else 0
    out["n_eff"] = n_eff
    out["n_episodes"] = int(n_eff)
    if n < 30:
        out["reason"] = f"n={n} < 30 minimum for directional resolution"
        return out
    if span < min_span_days:
        out["reason"] = (f"span={span}d < {min_span_days}d minimum — clustered "
                         "events are not independent observations")
        return out
    if n_eff < 30:
        out["reason"] = (f"n_eff={n_eff:.0f} < 30 (span {span}d / median "
                         f"horizon {med_h:.0f}d) — overlapping windows "
                         "are not independent")
        return out
    ret = events_to_daily_returns(events)
    s = sharpe_ann(ret)
    # purgedcv wants per-observation Sharpe + NON-excess kurtosis and
    # returns a count of observations; ret is a DAILY series, so the
    # (annualized) target must be divided by sqrt(365) to match.
    s_d = float(ret.mean() / ret.std()) if len(ret) and ret.std() > 0 else 0.0
    tgt_d = target_sharpe / np.sqrt(DAYS_PER_YEAR)
    skew = float(ret.skew()); kurt = float(ret.kurtosis() + 3.0)
    try:
        mintrl = float(min_track_record_length(
            s_d if abs(s_d) > 0.001 else 0.001, tgt_d, 0.05, skew, kurt))
    except (ValueError, ZeroDivisionError):
        # degenerate/constant streams give extreme moments the Gaussian
        # approximation can't digest — MinTRL is advisory, not a gate
        mintrl = float("nan")
    minbtl = minimum_backtest_length(n_trials=n_trials,
                                     target_sharpe=target_sharpe)
    out.update({"sharpe_obs": s, "mintrl_days": mintrl,
                "minbtl_years": float(minbtl),
                "sufficient": True,
                "reason": f"n={n} (n_eff={n_eff:.0f}), Sharpe={s:.2f}, "
                          f"MinTRL={mintrl:.0f}d, MinBTL={minbtl:.1f}y@SR{target_sharpe}"})
    return out


def forward_gate(ev: pd.DataFrame, price=None) -> dict:
    """Frozen promotion gate (manifest.forward_promotion_gate): PROMOTED
    requires n_eff >= 30 EPISODES of evaluable evidence (not raw rows — a
    continuous-position frame emits one event per invested day and
    uncovered windows carry no realized outcome), a sufficient
    power_gate (span >= 30d), EPISODE-level wilson_lo >= 0.5 (the
    same merge as power_gate — clustered rows cannot inflate hit
    evidence), net > 0 @10bp, and
    DEMONSTRATED drift skill: t_skill > SKILL_T_MIN (one-sided 95%) on
    >= 30 resolved episodes — the old bare `> 0`/NaN-allowed rule promoted
    ~24% of pure-beta streams. Contract violations report BLOCKED and
    are checked FIRST (a malformed frame must never crash a gate).
    Unresolvable skill (no/insufficient price) => ACCRUING, never
    PROMOTED. Every return carries the same keys."""
    out = {"n": len(ev), "n_eff": 0.0, "hit": float("nan"),
           "wilson_lo": float("nan"), "net": 0.0,
           "drift": float("nan"), "verdict": "ACCRUING"}
    contract = validate_events(ev)
    if not contract["passed"]:
        out["verdict"] = "BLOCKED"
        return out
    # Episode-level hit stats — the same merge as power_gate and
    # drift_skill. Row-level Wilson on a clustered frame is cluster-
    # inflated (a 10-day shared shock counted as 10 wins); the forward
    # gate that decides production promotion must count independent
    # episodes like the in-sample verdict path does.
    eph = episode_hit_stats(ev)
    out["hit"] = eph.get("hit", float("nan"))
    out["wilson_lo"] = eph.get("wilson_lo", float("nan"))
    ret = pd.to_numeric(ev["ret_bp"], errors="coerce")
    out["net"] = float(ret.sum()) if ret.notna().any() else 0.0
    power = power_gate(ev)
    # A refused power check is UNDERPOWERED, not raw-n-powered — never
    # default n_eff to len(ev). (2026-09-25: alt_reversal reached DEAD on
    # 36 same-shock rows over a 1d span only because an early power_gate
    # return left n_eff unset and the caller silently substituted 36.)
    out["n_eff"] = float(power.get("n_eff", 0.0) or 0.0)
    drift = drift_skill(ev, price) if price is not None else None
    skill = drift.get("t_skill", float("nan")) if drift else float("nan")
    out["drift"] = skill
    if not power.get("sufficient"):
        verdict = "ACCRUING"
    elif out["wilson_lo"] >= 0.5 and out["net"] > 0:
        # clears the economic bars; promotion still requires resolved,
        # statistically positive skill — unresolved => keep accruing
        if drift is not None and drift["n"] >= 30 and not np.isnan(skill):
            verdict = "PROMOTED" if skill > SKILL_T_MIN else "DEAD"
        else:
            verdict = "ACCRUING"
    else:
        verdict = "DEAD"
    out["verdict"] = verdict
    return out


# ── Layer B: prefix invariance (leak detector) ───────────────────────────

def prefix_invariance(signal_fn, data_args_fn, prefixes=(0.5, 0.75)) -> dict:
    """Recompute the signal on truncated prefixes of the data; any event at
    t <= prefix_end that differs from the full-data run proves the decision
    depended on future rows. data_args_fn(df) -> tuple of args after the df."""
    full = signal_fn(*data_args_fn(None))
    violations = []
    for frac in prefixes:
        cut = data_args_fn(frac)      # returns args with truncated frames
        part = signal_fn(*cut)
        if part.empty:
            continue
        limit = part["t"].max()
        a = full[full["t"] <= limit].reset_index(drop=True)
        b = part.reset_index(drop=True)
        if len(a) != len(b) or not a[["t", "dir"]].equals(b[["t", "dir"]]):
            violations.append({"prefix": frac, "full_n": len(a),
                               "part_n": len(b)})
            continue
        # magnitude leaks: a window fully evaluable inside the prefix
        # must earn the same return under truncation — ret/t_eval beyond
        # the limit can legitimately differ (the truncated run simply
        # lacks the future bars to evaluate), but ret_bp on windows that
        # DO fit may not (2026-09-25: t/dir-only compare let a
        # global-mean leak pass clean)
        if {"ret_bp", "t_eval"} <= set(a.columns) and \
                {"ret_bp", "t_eval"} <= set(b.columns):
            a_te = pd.to_datetime(a["t_eval"], utc=True, format="mixed")
            b_te = pd.to_datetime(b["t_eval"], utc=True, format="mixed")
            in_pre = (a_te <= limit) & (b_te <= limit)
            ra = a["ret_bp"][in_pre].to_numpy(dtype=float)
            rb = b["ret_bp"][in_pre].to_numpy(dtype=float)
            if not np.allclose(ra, rb, equal_nan=True, atol=1e-9):
                violations.append({"prefix": frac, "type": "ret_mismatch"})
    return {"passed": not violations, "violations": violations}


def truncate_aux(df: pd.DataFrame, *auxs: pd.DataFrame) -> list:
    """Aux frames truncated to df's own last timestamp. Leg lambdas close
    over aux frames (bars/funding/medians); boundary_invariance truncates
    only the PRIMARY frame, so without this a truncated run still reads
    future aux rows and the check can pass on a leaking signal."""
    lim = df["t"].max()
    return [a.loc[a.index <= lim] if isinstance(a, pd.Series)
            else a[a["t"] <= lim] for a in auxs]


def boundary_invariance(run_on_df, src_df: pd.DataFrame,
                        events: pd.DataFrame, max_checks: int = 40) -> dict:
    """Truncate the signal source so its last row IS the event's signal bar;
    if the event then fails to fire (or flips), the decision used future data.
    This catches +k-bar lookahead that append-side prefix checks cannot —
    the leaked value lives inside every truncated prefix.

    run_on_df(df_slice) -> events df for ONE asset's source frame.
    Samples up to max_checks events evenly across the run.
    """
    if events.empty:
        return {"passed": True, "violations": []}
    src_t = _to_ns(src_df["t"])
    ev_t = _to_ns(events["t"])
    violations, checked = [], 0
    order = np.arange(len(ev_t))
    step = max(1, len(order) // max_checks)
    for j in order[::step]:
        # truncate at the LAST source bar at/before the event's own
        # signal time — an event stamped off the bar grid (e.g. a funding
        # print between hourly bars) must find its own emitting bar, not
        # be pinned to the next bar that didn't exist at signal time
        i = int(np.searchsorted(src_t, ev_t[j], side="right")) - 1
        if i < 0:
            continue
        checked += 1
        sub = run_on_df(src_df.iloc[: i + 1])
        # does an event still fire at this signal time?
        fired = sub[_to_ns(sub["t"]) == ev_t[j]] if not sub.empty else sub
        orig = events[ev_t == ev_t[j]]
        if fired.empty:
            violations.append({"i": int(i), "type": "event_vanishes"})
        elif not orig.empty and (sorted(fired["dir"].astype(float).tolist())
                                 != sorted(orig["dir"].astype(float).tolist())):
            violations.append({"i": int(i), "type": "direction_flip"})
    return {"passed": not violations, "violations": violations, "checked": checked}


# ── Layer H: placebo / permutation ───────────────────────────────────────

def placebo_time_shift(events: pd.DataFrame, price,
                       horizon_bars: int, bar_minutes: int,
                       n_perm: int = 1000, seed: int = 3) -> dict:
    """Shift each event to a random valid index and recompute the directional
    forward return. Real mean vs the shifted distribution -> empirical p.

    `price` may be a single t/c frame OR a dict {asset: t/c frame} — for
    pooled multi-asset event files each event's shifted forward return is
    computed on ITS OWN asset's price series, not a shared proxy."""
    if events.empty or len(events) < 5:
        return {"p_value": float("nan"), "real_mean_bp": float("nan"), "n_perm": 0}
    ev = events.dropna(subset=["gross_bp"])
    if ev.empty:
        return {"p_value": float("nan"), "real_mean_bp": float("nan"), "n_perm": 0}
    rng = np.random.default_rng(seed)
    real_mean = float(ev["gross_bp"].mean())

    # per-asset price caches (single frame broadcasts to all assets)
    frames: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    ev_assets = ev["asset"].astype(str) if "asset" in ev.columns \
        else pd.Series("", index=ev.index)
    for a in ev_assets.unique():
        frame = price.get(a) if isinstance(price, dict) else price
        if frame is None or frame.empty:
            continue
        f = frame.sort_values("t").reset_index(drop=True)
        frames[a] = (_to_ns(f["t"]), f["c"].to_numpy(dtype=float))

    # per-event (asset, signal index) resolved against its own price frame
    ev = ev.reset_index(drop=True)
    t_ns = _to_ns(ev["t"])
    assets = ev_assets.reset_index(drop=True).to_numpy()
    dirs = ev["dir"].to_numpy(dtype=float)
    # preserve position sizing in the null: position-frame events carry w
    # (gross = w*dir*ret); without it the shifted distribution is ~1/w
    # oversized and p is biased high for scaled-position candidates.
    weights = (ev["w"].abs().to_numpy(dtype=float)
               if "w" in ev.columns else np.ones(len(ev)))
    keep = np.array([a in frames for a in assets])
    if not keep.any():
        return {"p_value": float("nan"), "real_mean_bp": real_mean, "n_perm": 0}
    # the "real" mean must cover the same rows the placebos can evaluate —
    # events on assets with no price frame are invisible to the null and
    # would skew the comparison (2026-09-25 audit)
    real_mean = float(ev["gross_bp"].to_numpy(dtype=float)[keep].mean())
    shifted = []
    base_ok = np.isfinite(weights) & np.isfinite(dirs)
    for _ in range(n_perm):
        fwd_all = np.full(len(ev), np.nan)
        for a, (ti, c) in frames.items():
            m = keep & (assets == a)
            if not m.any() or len(c) <= horizon_bars + 2:
                continue
            sig_idx = np.clip(np.searchsorted(ti, t_ns[m]),
                              0, len(c) - horizon_bars - 2)
            # sample WITHIN the event-covered index range (circular shift):
            # draws outside the evaluable window mix in regimes where the
            # candidate could never fire — and, on dirty frames, hit
            # zero/invalid prices that poisoned the old NaN->p=0 artifact.
            lo, hi = int(sig_idx.min()), int(sig_idx.max())
            span_i = max(1, hi - lo + 1)
            offs = rng.integers(0, span_i, size=int(m.sum()))
            idx = lo + (sig_idx + offs - lo) % span_i
            idx = np.clip(idx, 0, len(c) - horizon_bars - 2)
            denom = c[idx]
            fwd = np.where(np.isfinite(denom) & (denom > 0),
                           c[idx + horizon_bars] / np.where(denom > 0, denom, 1.0)
                           - 1.0,
                           np.nan)
            fwd_all[np.where(m)[0]] = fwd
        ok = np.isfinite(fwd_all) & base_ok
        if ok.sum() < 5:
            continue
        shifted.append(float((dirs[ok] * weights[ok]
                              * fwd_all[ok] * 1e4).mean()))
    shifted = np.asarray(shifted)
    if len(shifted) < 20:
        return {"p_value": float("nan"), "real_mean_bp": real_mean,
                "placebo_mean": float("nan"), "n_perm": len(shifted)}
    p = float((np.abs(shifted) >= abs(real_mean)).mean())
    return {"p_value": p, "real_mean_bp": real_mean,
            "placebo_mean": float(shifted.mean()), "n_perm": len(shifted)}


def _autocorr_block_len(r: np.ndarray, cap: int = 200) -> int:
    """Smallest block >=5 where |lag-1 autocorr| of the resampled units is
    below ~2/sqrt(n); bounded so it never exceeds n//4."""
    n = len(r)
    if n < 40:
        return max(5, min(n // 4, 10))
    ac = 1.0
    lag = 1
    while lag < min(cap, n // 4):
        a, b = r[:-lag], r[lag:]
        if a.std() == 0 or b.std() == 0:
            break
        ac = float(np.corrcoef(a, b)[0, 1])
        if abs(ac) < 2.0 / np.sqrt(n):
            break
        lag += 1
    return max(5, min(lag, n // 4))


def block_bootstrap(events: pd.DataFrame, n_boot: int = 2000,
                    seed: int = 11) -> dict:
    """Moving-block bootstrap over event net returns ordered by t.

    IID permutation placebos assume independence; event streams like
    pooled hourly funding events are serially dependent (adjacent events
    share the market path). Resampling contiguous blocks of events
    preserves that dependence, giving an honest p for "mean <= 0".
    Block length estimated from autocorrelation decay. Diagnostic layer —
    does not gate; reported alongside the iid placebo.
    """
    if len(events) < 30:
        return {"bb_p": float("nan"), "bb_lo": float("nan"),
                "bb_hi": float("nan"), "block_len": 0, "n_boot": 0}
    ev = events.sort_values("t").reset_index(drop=True)
    r = ev["ret_bp"].to_numpy(dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 30:
        return {"bb_p": float("nan"), "bb_lo": float("nan"),
                "bb_hi": float("nan"), "block_len": 0, "n_boot": 0}
    L = _autocorr_block_len(r)
    n_blocks = -(-n // L)
    starts = np.arange(0, n - L + 1)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([np.arange(s, s + L)
                              for s in rng.choice(starts, size=n_blocks)])[:n]
        means[b] = r[idx].mean()
    real = float(r.mean())
    return {"bb_p": float((means <= 0).mean()) if real > 0
                     else float((means >= 0).mean()),
            "bb_lo": float(np.quantile(means, 0.025)),
            "bb_hi": float(np.quantile(means, 0.975)),
            "block_len": int(L), "n_boot": n_boot}


# ── Layer F: PSR / DSR ───────────────────────────────────────────────────

# Empirical cross-trial Sharpe dispersion for DSR deflation, measured
# 2026-09-26 over the 77 evaluated report candidates: raw var 9.65 is
# degenerate-tail inflated; the MAD-robust estimate (1.4826*MAD)^2=1.372
# is the honest prior. The previous hardcoded 0.25 understated trial
# variance ~5.5x — DSRs printed ANTI-conservative (easier to pass).
EMPIRICAL_VAR_SHARPE = 1.372


def sharpe_stats(ret: pd.Series, n_trials: int = 9,
                 var_sharpe: float | None = None) -> dict:
    """PSR vs 0 and DSR deflated by the declared family count."""
    r = ret.to_numpy()
    if len(r) < 10 or r.std() == 0:
        return {"psr": float("nan"), "dsr": float("nan"), "sharpe": 0.0}
    s = sharpe_ann(ret)
    vs = var_sharpe if var_sharpe is not None else EMPIRICAL_VAR_SHARPE
    try:
        psr = float(probabilistic_sharpe_ratio(r, 0.0))
        dsr = float(deflated_sharpe_ratio(r, n_trials=n_trials,
                                          var_sharpe=vs,
                                          bars_per_year=int(DAYS_PER_YEAR)))
    except (ValueError, ZeroDivisionError):
        # extreme moments (near-degenerate streams) break the Gaussian
        # approximation — report NaN rather than crash the round
        psr = dsr = float("nan")
    return {"sharpe": s, "psr": psr, "dsr": dsr}


# ── Layer E: PBO over the candidate's own parameter neighborhood ─────────

def pbo_over_variants(variant_returns: dict[str, pd.Series]) -> dict:
    """CSCV/PBO across parameter variants of one candidate. returns matrix:
    rows=time, cols=variant. PBO = P(IS-best ranks below median OOS)."""
    if len(variant_returns) < 4:
        return {"pbo": float("nan"), "reason": "fewer than 4 variants"}
    mat = pd.DataFrame(variant_returns).fillna(0.0)
    if mat.shape[0] < 60 or (mat.abs().sum(axis=0) == 0).any():
        return {"pbo": float("nan"),
                "reason": f"sparse obs axis ({mat.shape[0]}d) — CSCV degenerate for event-driven candidates"}
    res = probability_of_backtest_overfitting(
        mat.to_numpy().T, n_splits=8)
    return {"pbo": float(res.pbo) if hasattr(res, "pbo") else float(res),
            "n_variants": mat.shape[1]}


# ── consistency: contiguous splits ───────────────────────────────────────

def split_consistency(events: pd.DataFrame, n_splits: int = 3) -> dict:
    """Contiguous event-count splits (not random): is the sign stable?"""
    if len(events) < n_splits * 5:
        return {"ok": False, "splits": []}
    ev = events.sort_values("t").reset_index(drop=True)
    bounds = [round(k * len(ev) / n_splits) for k in range(n_splits + 1)]
    chunks = [ev.iloc[bounds[k]:bounds[k + 1]] for k in range(n_splits)]
    out = []
    for ch in chunks:
        out.append({"n": len(ch), "hit": float(ch["hit"].mean()),
                    "mean_bp": float(ch["ret_bp"].mean()),
                    "pf": profit_factor(ch["ret_bp"].to_numpy())})
    return {"ok": True, "splits": out,
            "sign_consistent": all(s["mean_bp"] > 0 for s in out) or
                               all(s["mean_bp"] < 0 for s in out)}


def era_breakdown(events: pd.DataFrame, by: str = "year") -> list[dict]:
    """Regime decomposition — added 2026-09-23 after it caught basis1's
    single-era edge and fng's direction asymmetry in follow-up audits.
    Calendar-era hit/net per era; a 'survivor' concentrated in one era is
    regime luck, not a mechanism. Diagnostic layer — does not gate."""
    if events.empty:
        return []
    ev = events.copy()
    tt = pd.to_datetime(ev["t"], format="mixed", utc=True)
    key = tt.dt.year if by == "year" else tt.dt.to_period("Q").astype(str)
    out = []
    for era, g in ev.groupby(key):
        out.append({"era": str(era), "n": len(g),
                    "hit": float(g["hit"].mean()),
                    "net_bp": float(g["ret_bp"].sum()),
                    "mean_bp": float(g["ret_bp"].mean())})
    return out


# ── drift-skill decomposition (added 2026-09-23 after the WATCH audit
#    showed net-positive verdicts can be pure beta capture) ─────────────

def drift_skill(events: pd.DataFrame, price) -> dict:
    """Per-event split: gross_bp = dir*mu_unconditional*1e4 + skill_bp.

    mu_unconditional = mean window return on the event's own asset over
    the candidate's event span. The horizon is measured in the price
    frame's own bars (searchsorted on t/t_eval) — bar-native, so intraday
    events get intraday drift instead of a 1-day clamp. skill = gross
    minus that drift expectation. A positive-net signal with skill<=0
    is drift capture (beta), not timing.

    price: DataFrame(t,c) applied to all assets, OR dict {ASSET: df}.
    Returns mean/t-stat of skill plus long/short asymmetry. Diagnostic
    layer feeding verdict() — see watch_audit in manifest."""
    out = {"n": 0, "mean_skill_bp": float("nan"), "t_skill": float("nan"),
           "mean_drift_bp": float("nan"), "frac_long": float("nan"),
           "long_skill_bp": float("nan"), "short_skill_bp": float("nan")}
    if events.empty or "gross_bp" not in events.columns:
        return out
    ev = events.dropna(subset=["gross_bp"])
    if ev.empty:
        return out
    ev = ev.copy()
    for col in ("t", "t_eval"):
        ev[col] = pd.to_datetime(ev[col], utc=True, format="mixed",
                                 errors="coerce").dt.tz_convert(None)
    ev = ev.dropna(subset=["t", "t_eval"])
    if ev.empty:
        return out
    # resolved-event records; episode ids assigned per asset afterwards
    recs: list[tuple] = []   # (asset, t_ns, te_ns, skill, drift, dir)
    cache: dict[str, pd.Series] = {}
    gb = ev.groupby("asset") if "asset" in ev.columns \
        else [("", ev)]
    for asset, g in gb:
        frame = price.get(str(asset)) if isinstance(price, dict) else price
        if frame is None or getattr(frame, "empty", False):
            continue
        px = frame.copy()
        px["t"] = pd.to_datetime(px["t"], utc=True,
                                 format="mixed").dt.tz_convert(None)
        px = (px.sort_values("t").set_index("t")["c"].astype(float))
        if len(px) < 10:
            continue
        cache[str(asset)] = px
        pt = px.index.to_numpy()
        lo_d, hi_d = g["t"].min(), g["t_eval"].max()
        span_px = px.loc[(pt >= np.datetime64(lo_d))
                         & (pt <= np.datetime64(hi_d))]
        if len(span_px) < 10:
            span_px = px
        c = span_px.to_numpy()
        for _, r in g.iterrows():
            # t_eval < t is a contract violation — never attribute.
            # t_eval == t is a single-period event (continuous-position
            # frames emit one invested day per row): its holding period
            # is one bar of this frame, benchmark = mean 1-bar return.
            if r["t_eval"] < r["t"]:
                continue
            i0 = int(np.searchsorted(pt, np.datetime64(r["t"]),
                                     side="left"))
            i1 = int(np.searchsorted(pt, np.datetime64(r["t_eval"]),
                                     side="right")) - 1
            horizon = max(1, i1 - i0)
            if horizon < 1 or len(c) <= horizon:
                continue
            mu = float(pd.Series(c).pct_change(horizon).mean())
            if not np.isfinite(mu):
                continue
            drift = float(r["dir"]) * mu * 1e4
            recs.append((str(asset), r["t"].value, r["t_eval"].value,
                         float(r["gross_bp"]) - drift, drift,
                         float(r["dir"])))
    if not recs:
        return out
    # Episode-level aggregation: member events of one episode share the
    # same market path, so their skills are serially correlated — an iid
    # t-stat over raw events rejects a zero-skill null far above nominal
    # (rho~0.5 -> ~18% at the 1.645 cut). Episodes are disjoint by
    # construction; the honest unit is mean-skill PER EPISODE.
    ep_skill, ep_drift, ep_dir = [], [], []
    # global episode ids per resolved row — same union-merge semantics
    # as _count_episodes so the drift unit matches the power unit
    gid = _merged_episode_ids(
        np.array([r[1] for r in recs], dtype=np.int64),
        np.array([r[2] for r in recs], dtype=np.int64),
        np.array([r[0] for r in recs], dtype=object))
    by_mid: dict[int, list] = {}
    for i, mid in enumerate(gid):
        sk, dr, di = recs[i][3], recs[i][4], recs[i][5]
        by_mid.setdefault(int(mid), []).append((sk, dr, di))
    ep_skill = [float(np.mean([x[0] for x in v])) for v in by_mid.values()]
    ep_drift = [float(np.mean([x[1] for x in v])) for v in by_mid.values()]
    ep_dir = [float(np.sign(np.mean([x[2] for x in v])))
              for v in by_mid.values()]
    s = np.asarray(ep_skill)
    d = np.asarray(ep_dir)
    lo = s[d > 0]
    hi = s[d < 0]
    sd = float(s.std(ddof=1)) if len(s) > 1 else 0.0
    # sd==0 is NOT 0/0 here: episode skills are sign-consistent (a flat
    # price frame or a perfect beta capture produces identical per-
    # episode residuals). The honest fallback is the sign test — all
    # positive -> decisive skill (+inf), all negative -> decisively
    # dead (-inf); only a zero-valued or empty set is uninformative.
    if sd > 0:
        t_skill = float(s.mean() / (sd / np.sqrt(len(s))))
    elif len(s) and (s > 0).all():
        t_skill = float("inf")
    elif len(s) and (s < 0).all():
        t_skill = float("-inf")
    else:
        t_skill = float("nan")
    out.update({
        "n": len(s),                 # EPISODES (the power unit), not rows
        "n_events": len(recs),
        "mean_skill_bp": float(s.mean()),
        "t_skill": t_skill,
        "mean_drift_bp": float(np.mean(ep_drift)),
        "frac_long": float((d > 0).mean()),
        "long_skill_bp": float(lo.mean()) if len(lo) else float("nan"),
        "short_skill_bp": float(hi.mean()) if len(hi) else float("nan"),
    })
    return out


# ── event-frame contract assertions (added 2026-09-23; tz mix, funding
#    shape, and boundary-tail bugs were all caught by eye — automate) ────

EVENT_COLS = ["t", "asset", "dir", "t_eval", "ret_bp", "gross_bp", "hit"]


def write_event_csv(ev: pd.DataFrame, path) -> None:
    """Write an event frame so it can always be re-read: a fully-empty
    candidate emission (e.g. quarantined input -> zero signals) otherwise
    lands as a zero-byte file pandas can't parse (EmptyDataError) —
    which is exactly what an event-contract sweep must not choke on."""
    if ev.empty:
        ev = pd.DataFrame(columns=EVENT_COLS)
    # atomic: a kill mid-write must not leave a torn CSV that still
    # parses (anchoring catches it next run — but torn state shouldn't
    # sit on disk meanwhile)
    tmp = path.with_name(path.name + ".tmp")
    ev.to_csv(tmp, index=False)
    tmp.replace(path)


def validate_events(ev: pd.DataFrame) -> dict:
    """Invariant checks every event frame must satisfy. Violations are
    harness bugs or silent data rot — surface loudly, never auto-fix."""
    viol: list[str] = []
    if ev.empty:
        return {"passed": True, "violations": [], "n": 0}
    need = {"t", "asset", "dir", "t_eval", "ret_bp", "gross_bp", "hit"}
    missing = need - set(ev.columns)
    if missing:
        viol.append(f"missing columns {sorted(missing)}")
        return {"passed": False, "violations": viol, "n": len(ev)}
    # errors="coerce" — unparseable stamps become NaT and fall into the
    # NaT check instead of crashing the sweep (DateParseError class)
    tt = pd.to_datetime(ev["t"], utc=True, format="mixed",
                        errors="coerce")
    te = pd.to_datetime(ev["t_eval"], utc=True, format="mixed",
                        errors="coerce")
    if tt.isna().any() or te.isna().any():
        viol.append(f"{int(tt.isna().sum() + te.isna().sum())} NaT "
                    "t/t_eval rows")
    if ev["asset"].isna().any():
        viol.append(f"{int(ev['asset'].isna().sum())} events with "
                    "NaN asset")
    # ret/gross must be numeric and finite when present — inf is notna()
    # (counted as covered) but is not a realizable return; a Sharpe=inf
    # frame could otherwise reach PROMOTED
    for col in ("ret_bp", "gross_bp"):
        vals = pd.to_numeric(ev[col], errors="coerce")
        nonnum = ev[col].notna() & vals.isna()
        if nonnum.any():
            viol.append(f"{int(nonnum.sum())} non-numeric {col} rows")
        nonfin = vals.notna() & ~np.isfinite(vals.astype(float))
        if nonfin.any():
            viol.append(f"{int(nonfin.sum())} non-finite {col} rows")
    if ev["t"].dtype == object:
        tzs = ev["t"].dropna().map(
            lambda x: getattr(x, "tzinfo", None) is not None)
        if len(tzs) and tzs.nunique() > 1:
            viol.append("mixed tz-aware/naive t")
    if (te < tt).any():
        viol.append(f"{int((te < tt).sum())} events with t_eval < t")
    bad_dir = ~ev["dir"].isin([-1.0, 1.0])
    if bad_dir.any():
        viol.append(f"{int(bad_dir.sum())} events with dir not in +-1")
    evl = ev.dropna(subset=["gross_bp"])
    if "hit" in ev.columns and len(evl):
        bad_hit = (evl["hit"] != (evl["gross_bp"] > 1.0))
        if bad_hit.any():
            viol.append(f"{int(bad_hit.sum())} events where hit != "
                        "gross_bp > deadband")
    dup = ev.duplicated(subset=["asset", "t"])
    if dup.any():
        viol.append(f"{int(dup.sum())} duplicate (asset,t) events")
    # uncovered rows carry no outcome. Two conventions are valid: tagged
    # (exit_reason='uncovered' + zero-width t_eval — forward files) and
    # legacy (no tag column, t_eval = intended horizon). Both must have
    # NaN gross and a non-True hit — a row claiming an outcome with no
    # net is inconsistent, and power now counts covered rows only so a
    # windowed uncovered row can no longer mint phantom episodes.
    unc = ev["ret_bp"].isna()
    if unc.any():
        u = ev.loc[unc]
        bad = ~u["gross_bp"].isna()
        if "hit" in u.columns:
            bad = bad | u["hit"].fillna(False).astype(bool)
        if "exit_reason" in u.columns:
            bad = bad | (u["exit_reason"].astype(str) != "uncovered") \
                        | (te.loc[unc] != tt.loc[unc])
        if bad.any():
            viol.append(f"{int(bad.sum())} uncovered rows malformed "
                        "(NaN ret requires NaN gross, non-True hit, and "
                        "exit_reason='uncovered' + t_eval==t when tagged)")
    return {"passed": not viol, "violations": viol, "n": len(ev)}


# ── holding-cost adjustment (added 2026-09-23): perp positions pay/
#    receive funding while held — flat 10bp RT understates multi-day holds

def apply_funding_cost(events: pd.DataFrame, funding,
                       ) -> tuple[pd.DataFrame, dict]:
    """Subtract per-event funding carry over (t, t_eval].

    funding: pd.Series of daily-summed rates indexed by day, OR dict
    {ASSET: series}. Positive rate => LONG pays, SHORT receives.
    Produces funding_bp (signed cost to the position, bp) and
    ret_bp_carry = ret_bp - funding_bp. Returns (events, coverage stats).
    Diagnostic layer — verdicts stay on the declared 10bp RT spec."""
    ev = events.copy()
    if ev.empty:
        return ev, {"coverage": 0.0, "total_funding_bp": 0.0}
    ev["_t"] = pd.to_datetime(ev["t"], utc=True,
                              format="mixed").dt.tz_convert(None)
    ev["_te"] = pd.to_datetime(ev["t_eval"], utc=True,
                               format="mixed").dt.tz_convert(None)
    cache: dict[str, pd.Series] = {}
    carry, covered = [], 0
    for _, r in ev.iterrows():
        a = str(r["asset"])
        if a not in cache:
            src = funding[a] if isinstance(funding, dict) else funding
            if src is None:
                cache[a] = pd.Series(dtype=float)
            else:
                s = src.copy()
                s.index = pd.DatetimeIndex(
                    pd.to_datetime(s.index, utc=True, format="mixed")
                ).tz_convert(None)
                cache[a] = s.sort_index()
        s = cache[a]
        mask = (s.index > r["_t"]) & (s.index <= r["_te"])
        seg = s.loc[mask].dropna()
        if len(seg):
            covered += 1
        carry.append(float(r["dir"]) * float(seg.sum()) * 1e4)
    ev["funding_bp"] = carry
    ev["ret_bp_carry"] = ev["ret_bp"] - ev["funding_bp"]
    ev = ev.drop(columns=["_t", "_te"])
    return ev, {"coverage": covered / len(ev),
                "total_funding_bp": float(ev["funding_bp"].sum())}


# ── implausibility (Penrose-analog) ──────────────────────────────────────

def implausibility_check(ret: pd.Series) -> dict:
    """One-sided gate: only implausibly GOOD Sharpe indicates a broken harness.
    A very negative Sharpe on a thin sample is just a bad strategy, not a bug."""
    s = sharpe_ann(ret)
    nz = int((ret != 0).sum())
    bad = s > IMPLAUSIBLE_SHARPE and nz >= 30
    return {"sharpe": s, "implausible": bad,
            "reason": (f"Sharpe {s:.1f} > {IMPLAUSIBLE_SHARPE} on {nz} nonzero days "
                       "-> harness artifact, not edge") if bad else "plausible range"}
