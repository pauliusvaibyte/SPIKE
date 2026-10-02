"""Round-7 — 40/125 DMA trend retest, declared in manifest.yaml
`round7_dmaretest` BEFORE execution. Billed to the TREND family
(retest at a longer timescale, not a new mechanism).

Event contract unchanged: t, asset, dir, t_eval, ret_bp (net), gross_bp;
uncovered tail events emit NaN ret fields.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates import FEE_RT_BP, _events_to_df
from harness.candidates_round3 import _row


def dma_cross(bars: pd.DataFrame, asset: str, fast: int = 40,
              slow: int = 125, horizon_bars: int = 30) -> pd.DataFrame:
    """Golden/death cross of SMA(fast) vs SMA(slow) on close.

    Event at each sign change of (sma_fast - sma_slow); dir = sign of the
    post-cross spread; eval close -> close + horizon_bars.
    """
    c = bars["c"].to_numpy(dtype=float)
    t = bars["t"]
    f = pd.Series(c).rolling(fast).mean().to_numpy()
    s = pd.Series(c).rolling(slow).mean().to_numpy()
    spr = f - s
    rows = []
    prev = 0.0
    for i in range(len(c)):
        if not np.isfinite(spr[i]) or spr[i] == 0:
            continue
        cur = float(np.sign(spr[i]))
        if prev != 0 and cur != prev:
            d = cur
            if i + horizon_bars > len(c) - 1:
                rows.append(_row(t.iloc[i], asset, d, t, -1, None,
                                 {"spread": float(spr[i])}))
            else:
                xi = i + horizon_bars
                fwd = (c[xi] / c[i] - 1.0
                       if c[i] > 0 and np.isfinite(c[xi]) and c[xi] > 0
                       else None)
                rows.append(_row(t.iloc[i], asset, d, t, i + horizon_bars,
                                 fwd, {"spread": float(spr[i])}))
        prev = cur
    return _events_to_df(rows)
