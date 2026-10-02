# QuantLab OS — Master Engineering Build Specification

**Status:** Architecture Design Freeze / Engineering Handoff  
**Version:** 1.1  
**Date:** 2026-09-23  
**Revision:** 1.1 — 2026-09-24 — post-review reordering: Phase -1 empirical existence test inserted before Phase 0; MVP scope reduced; see §111 for the full errata  
**Audience:** Solo engineer + AI coding agents  
**Primary use case:** Crypto / prediction-market quantitative research, systematic alpha discovery, realistic execution validation, and controlled production deployment  
**Core principle:** *AI may generate unlimited ideas; it may not cheat the experiment, bypass risk, or directly promote itself to capital.*

---

# CURRENT PROJECT STATE

```text
QuantLab Phase -1: COMPLETE  (executed 2026-09-23 in SPIKE/, fka quantlab-spike/)

Result (cumulative, rounds 1-10 on frozen + extended + macro data):
 45 POWERED KILL   (incl. basis1 follow-up; TOXIC-FLOW powered-dead;
                    CARRY dead at n=24323; SESSION/VOL-REGIME/ROTATION
                    dead; r11: dvol_bounce, liq_cascade, funding_consensus,
                    lth_sopr, nrpl_spike_top [ANTI -> fwd_nrpl_cont],
                    exchange_balance; r12: bybit_premium, puell [ANTI ->
                    fwd_puell_cont], reserve_risk [ANTI -> fwd_rr_cont],
                    lth_mvrv, sth_sopr, nrpl_capitulation [nrpl dead
                    BOTH tails])
 15 WATCH          (drift-audit reclassified 4 as beta artifacts:
                    vix_spike, drawdown_bounce, month_end, breadth_thrust
                    are KILL-equivalent in promotion math. Remaining
                    genuine-skill WATCHes: premium_basis_converge,
                    skew_extreme_reversal [both symmetric two-sided],
                    flagship_composite_bnbtc [cross-venue trend],
                    xvenue_funding_spread, cme_oi_confirm + earlier weak
                    positives)
  1 BLOCKED        (coinbase_premium_drift: hit 1.000/Sharpe 7.68 ->
                    implausibility gate; confirmed corr(col, next-day
                    ret)=0.97 look-ahead in warehouse column.
                    QUARANTINED.)
  2 RESEARCH_SUPPORTED (round-10 flagship port: s45125 base AND base+N+V
                    composite on BTC 2013+ clock — Sharpe 1.65-1.76, placebo
                    <.001, era-consistent incl. bear years. FIRST full-stack
                    pass. Venue shift CONFIRMED on Binance perp 2019-2026
                    (era-diverse, 2022 bear contained). Caveats: modern-era
                    thin (2025-26 ~+900bp/yr); HL-venue span-starved and
                    alt-asset variants MODEL_RISK (degenerate to beta,
                    placebo .49-.91). Forward shadow declared:
                    fwd_flagship_hlbtc.)
  5 MODEL_RISK     (etf_flow_5d; funding_flip_momentum — strong stats but
                    decomposition showed pure momentum confound;
                    flagship_composite_hlbtc / flagship_base_alts /
                    flagship_composite_alts — modern-window beta)
  5 UNDERPOWERED   (ofi_imbalance_l2 journal span; oi_price_divergence thin
                    daily OI; oi_crowding_fade + taker_toxicity_1h on the
                    ~30d Binance window; dormancy_spike_fade n=22)
  HARNESS HARDENING (2026-09-23): drift-skill gate in verdict()
    (positive-net with skill<=0 -> KILL); n_eff in power_gate (span/
    median horizon >= 30); validate_events contract assertions +
    coverage-regression sentinel + funding-carry diagnostic — all in
    the daily job. Forward book: 14 leads accruing.
  1 SURVIVOR-STAT  (cal_weekend_drift: passed all declared gates —
                    n=839, Sharpe 1.33, placebo<.001 — but era-split
                    audit shows the edge is early-era drift; modern-era
                    edge ~= fee line. Does NOT clear the economic bar;
                    platform remains locked.)
  Rounds 6-8 (2026-09-23): universe expanded to 7 assets; systematic
    anti-predictivity in funding/premium/microstructure signals —
    inverse/continuation leads forward-declared, accrual daily.
  Round 10 + data expansion: harmony extended export (59 cols, venue
    clocks to 2011), Binance perp 1d/4h full-history + premium index,
    CoinMetrics community refresh (N-leg unfrozen). Structural finding
    now refined: microstructure positives remain era-beta/momentum
    proxies, BUT long-horizon BTC trend timing is the exception —
    replicates cross-venue through the 2022 bear.

Platform build status:
  LOCKED — all Phases 0+ of this document are dormant architecture,
  not the current backlog.

Unlock condition:
  >=1 candidate survives the declared Phase -1 falsification protocol
  with sufficient statistical power and economically realistic costs.

Current priorities:
  1. Generate materially new hypothesis families (different economic
     mechanisms, not parameter mutations of killed families).
  2. Continue forward/shadow evidence collection.
  3. Accumulate funding/L2/venue history.
  4. Re-test UNDERPOWERED families when preregistered sample
     requirements are reached (specs frozen; COLLECT ONLY until then).
  5. Do NOT implement QuantLab Phases 0+ until the unlock fires.

Killed families are permanently invalidated — parameter tuning of a
powered failure (threshold 0.90 -> 0.87, lookback 20 -> 23) is exactly
the behavior this framework exists to prevent.
```

---

# 0. Executive Summary

QuantLab OS is not “an AI trading bot” and not “another backtester.”

It is a **falsification-first autonomous quantitative research laboratory** whose job is to:

1. ingest and version point-in-time financial data correctly;
2. generate financially grounded hypotheses at high throughput;
3. compile those hypotheses into constrained, auditable factor/strategy representations;
4. account for *all* experiments, including failed and discarded ones;
5. aggressively attack apparent edge using leakage tests, purged validation, multiple-testing corrections, placebos, null worlds, parameter perturbations, regime tests, and independent referees;
6. use a truly sealed, single-use confirmation dataset before promotion;
7. convert validated forecasts into portfolio targets;
8. validate execution realism with NautilusTrader and, for market making/HFT, an independent HftBacktest replay;
9. deploy only cryptographically frozen strategy artifacts through independent deterministic risk controls;
10. learn from real execution telemetry without allowing live adaptation to bypass the validation pipeline.

The system is intentionally designed around a separation of powers:

```text
DISCOVERER
    │ proposes
    ▼
BUILDER
    │ implements
    ▼
EVALUATOR
    │ measures
    ▼
REFEREE
    │ attacks
    ▼
EXECUTOR
    │ trades
    ▼
RISK SUPERVISOR
```

No single component has permission to perform all roles.

The architecture deliberately reuses strong open-source components instead of rebuilding commodity infrastructure:

- **NautilusTrader** — canonical execution/runtime engine.
- **HftBacktest** — independent HFT/MM execution oracle.
- **Polars + Arrow + Parquet + DuckDB** — data/compute foundation.
- **Optuna** — search scheduling, but not experiment truth.
- **purgedcv + arch** — statistical validation building blocks.
- **skfolio** — portfolio construction and portfolio CV.
- **Penrose + Nullius** — independent falsification/referee implementations.
- **RD-Agent / AlphaAgent / QuantaAlpha / AlphaEvo / alpha-factor-agents** — architectural inspiration for agentic research and constrained factor generation.
- **Pandera** — schema contracts.
- **Prometheus/Grafana/OpenTelemetry** — optional operational observability.
- **MLflow** — optional UI/mirror only, never the canonical record.

The components we own—and where the actual differentiation lives—are:

- the **bitemporal financial data model**;
- the **typed factor/strategy DSL**;
- the **immutable Trial Ledger** and family lineage;
- the **sealed holdout service**;
- the **falsification/promotion policy engine**;
- the **AI capability boundary**;
- the **execution-model calibration loop**;
- the **signed deployment artifact model**;
- the **independent live Risk Supervisor**;
- the **research-process benchmark** that evaluates which idea-generation method produces credible OOS edge per unit of search/cost.

The first objective is not to build the complete platform. The first objective is to prove that a minimal version of this system can improve the quality of research on an existing BTC/crypto dataset. If that fails, the project stops before the production stack is built.

---

# 1. Problem Statement

Most quantitative research systems are optimized for:

```text
strategy → backtest → Sharpe
```

That is insufficient because a high backtest statistic can be manufactured by:

- lookahead leakage;
- revised data;
- universe survivorship;
- data timestamp errors;
- repeated parameter search;
- repeated model search;
- repeated LLM-generated hypothesis search;
- cherry-picked windows;
- cherry-picked assets;
- strategy-family mutation;
- biased feature engineering;
- optimistic fill assumptions;
- missing fees/funding;
- ignored latency;
- impossible queue priority;
- insufficient sample size;
- regime concentration;
- hidden correlation to existing factors;
- overestimated capacity;
- stale market rules;
- repeated peeking at the test set;
- arbitrary researcher discretion after seeing results.

An autonomous AI makes this problem worse because it can search thousands of hypotheses faster than a human can recognize the associated selection bias.

Therefore the target system optimizes for a different question:

> **How difficult can we make it for a false edge to reach real capital?**

The research target is not “the highest historical Sharpe.”

It is:

```text
maximize expected real-world,
cost-adjusted,
capacity-adjusted,
selection-bias-adjusted,
out-of-sample economic value

subject to:
    point-in-time data integrity
    reproducibility
    statistical credibility
    execution credibility
    portfolio/risk constraints
    sealed confirmation
    independent live controls
```

---

# 2. Success Criteria

QuantLab OS is successful only if it improves the *research process*, not merely if it has many features.

## 2.1 Research success

The system must demonstrate all of the following:

- Reproduce known baseline strategies exactly from frozen data/config.
- Reject planted lookahead strategies.
- Reject strategies built from pure noise often enough that false discovery is controlled.
- Detect a deliberately planted weak signal often enough that the validator is not simply “kill everything.”
- Correctly report **UNDERPOWERED** when the data cannot distinguish signal from noise.
- Account for all search trials, including pruned and failed trials.
- Produce identical results from identical immutable manifests and seeds.
- Prevent the research agent from reading sealed confirmation data.
- Produce an auditable causal chain from hypothesis → code → trial → validation → promotion decision.

## 2.2 Economic success

Before live execution is built, the research MVP must show that it can outperform the current manual workflow on a defined benchmark, for example:

- more credible OOS survivors per 100 hypotheses;
- lower OOS decay;
- fewer false positives on null tests;
- equivalent or better useful discovery rate at lower researcher time;
- candidate strategies that survive realistic costs and delay assumptions;
- candidates whose edge remains after ablation and parameter perturbation.

## 2.3 Production success

A production candidate must:

- correspond exactly to the signed artifact that passed validation;
- run through the same core strategy/execution architecture used in simulation;
- never expose exchange credentials to research/LLM workers;
- be blocked by risk controls outside strategy code;
- be fully replayable from an append-only event journal;
- support emergency kill independent of the strategy process;
- prove live behavior in shadow/paper/canary stages before full allocation.

---

# 3. Non-Goals

Do **not** turn this project into an infrastructure museum.

The initial project is explicitly *not*:

- a Bloomberg replacement;
- a general-purpose hedge-fund operating system;
- a data vendor;
- a full OMS for every asset class;
- a Kubernetes-first platform;
- a Kafka-first platform;
- a Spark cluster;
- a universal brokerage abstraction;
- a UI-first product;
- a black-box “AI decides what to trade” system;
- an automatic real-money agent;
- a guarantee of profitability.

Do not implement components merely because they appear in the long-term architecture.

Every new service/dependency must answer:

1. Which concrete failure mode does this remove?
2. Why can the current stack not solve it?
3. What new operational failure modes does it introduce?
4. Can it remain optional?

---

# 4. Non-Negotiable Design Invariants

These invariants override convenience.

## 4.1 Data invariants

1. All timestamps stored in UTC internally.
2. No feature is usable before its `available_time`.
3. Revised observations never overwrite history.
4. Universe membership is point-in-time.
5. Every dataset used by an experiment is content-addressable or manifest-addressed.
6. Raw source data is append-only.
7. Every transformation is reproducible from code + config + source manifest.
8. Missing data is explicit, never silently forward-filled unless an operator declares that rule.
9. Venue rules are versioned by effective date.
10. Order-book sequence gaps are detectable.

## 4.2 Research invariants

1. Every evaluated candidate creates a Trial Ledger record.
2. Failed/pruned/error trials count as search attempts where statistically relevant.
3. Strategy families cannot reset search history by renaming the strategy.
4. Research code cannot access sealed OOS data.
5. The same process that proposes a candidate cannot unilaterally certify it.
6. Final confirmation is single-use for a frozen artifact.
7. A failed sealed holdout contaminates that holdout for descendants of the candidate family.
8. Any post-result change creates a new candidate/version.
9. Promotion gates are deterministic code, not LLM judgment.
10. Statistical tests are diagnostics, not magical proof of profit.

## 4.3 Execution invariants

1. NautilusTrader is the canonical execution/runtime engine.
2. For execution-sensitive MM/HFT candidates, a second simulator is required.
3. Bar-level results cannot certify a queue-sensitive strategy.
4. Historical replay cannot claim to solve market impact; capacity is modeled conservatively.
5. Venue fee/tick/lot/funding/rule changes are effective-dated.
6. Shadow/paper/canary are separate promotion stages.
7. Live runtime executes only signed approved artifacts.

## 4.4 AI invariants

AI may:

- propose hypotheses;
- read allowed research data;
- create factor DSL expressions;
- write sandboxed candidate code;
- request experiments;
- inspect permitted research diagnostics;
- summarize evidence.

AI may **not**:

- access live secrets;
- access sealed OOS;
- override risk;
- edit history;
- modify promotion policy;
- sign deployment artifacts;
- directly route live orders;
- raise leverage/limits;
- change a failed verdict;
- reinterpret a failed gate as a pass.

---

# 5. Architectural Overview

```text
Human / API
    │
    ▼
Knowledge & Hypothesis Plane
    │
    ▼
Alpha Generation Firewall
    │
    ▼
Research Kernel + Trial Ledger
    │
    ▼
Point-in-Time Data Truth
    │
    ├───────────────┐
    ▼               ▼
Model Lab       FastScreen
    └──────┬────────┘
           ▼
Internal Falsification Stack
           ▼
Independent Referees
           ▼
Sealed Confirmation
           ▼
Portfolio Construction
           ▼
Execution Planner
           ▼
NautilusTrader
           │
           ├──── HftBacktest oracle for MM/HFT
           ▼
Shadow → Paper → Canary → Live
           ▼
Independent Risk Supervisor
           ▼
Live Event Journal
           ▼
Calibration / Challenger research
```

---

# 6. Technology Decisions

## 6.1 Mandatory core

| Responsibility | Technology | Decision |
|---|---|---|
| Language | Python 3.12 | Main orchestration/research language |
| Package/env | `uv` | Fast reproducible dependency management |
| Type/data contracts | Pydantic v2 | External/internal domain models |
| Static quality | Ruff + Pyright | Formatting/lint/types |
| Tests | Pytest + Hypothesis | Unit/property/metamorphic tests |
| Frames | Polars | Default high-performance dataframe engine |
| Interchange | Apache Arrow | Zero/low-copy boundaries |
| Historical files | Parquet | Primary immutable analytical format |
| Analytical SQL | DuckDB | Local SQL, ASOF joins, research queries |
| Metadata/ledger | PostgreSQL in production; SQLite in local tests | Transactional metadata |
| Migrations | Alembic | Schema evolution |
| API | FastAPI | Service boundaries |
| CLI | Typer | Research/operator commands |
| Optimizer | Optuna | Search scheduling only |
| Statistical CV | purgedcv | Purged CV/CPCV/PBO/DSR primitives |
| Multiple comparison | `arch` | SPA/Reality Check/StepM/MCS/bootstrap |
| Portfolio | skfolio | Portfolio construction and portfolio CV |
| Canonical runtime | NautilusTrader | Backtest/live execution engine |
| MM/HFT oracle | HftBacktest | Independent execution validation |
| Schema validation | Pandera | Polars/Arrow boundary checks |
| Container | Docker/Compose | Initial deployment |
| Logs | structured JSON | Machine-replayable observability |

## 6.2 Optional/later

- MLflow — run comparison UI/model registry mirror.
- Feast — optional online feature serving; never canonical PIT history.
- lakeFS — optional object-store dataset versioning once local manifests stop scaling.
- NannyML — optional model-monitoring diagnostics.
- Prometheus/Grafana — production monitoring.
- OpenTelemetry — traces across services.
- MinIO/S3 — artifact/object storage when local FS is insufficient.
- Dagster — workflow orchestration only after simple worker scheduling becomes limiting.
- QuestDB — optional high-rate live tick database if Parquet/Postgres pipeline becomes insufficient.

## 6.3 Explicit exclusions from the core

- VectorBT — not required; licensing and dependency are avoidable.
- Freqtrade runtime — ideas only.
- Hummingbot runtime — ideas only.
- LEAN — duplicates Nautilus.
- Jesse runtime — ideas only.
- Qlib monolith — adapters/ideas only.
- mlfinlab — not open source.
- ArcticDB — not required; licensing/runtime complexity unnecessary.
- Kafka/Spark/Kubernetes — no initial requirement.

---

# 7. Repository Layout

```text
quantlab/
├── pyproject.toml
├── uv.lock
├── README.md
├── SECURITY.md
├── LICENSES.md
├── docker-compose.yml
├── configs/
│   ├── research/
│   ├── validation/
│   ├── venues/
│   ├── risk/
│   └── deployment/
│
├── src/quantlab/
│   ├── contracts/
│   │   ├── ids.py
│   │   ├── temporal.py
│   │   ├── market.py
│   │   ├── feature.py
│   │   ├── hypothesis.py
│   │   ├── forecast.py
│   │   ├── portfolio.py
│   │   ├── order.py
│   │   ├── evidence.py
│   │   └── deployment.py
│   │
│   ├── data/
│   │   ├── ingest/
│   │   ├── raw/
│   │   ├── catalog/
│   │   ├── pit/
│   │   ├── revisions/
│   │   ├── universe/
│   │   ├── orderbook/
│   │   ├── quality/
│   │   └── manifests/
│   │
│   ├── features/
│   │   ├── registry/
│   │   ├── graph/
│   │   ├── technical/
│   │   ├── microstructure/
│   │   ├── semantic/
│   │   ├── onchain/
│   │   ├── macro/
│   │   └── transforms/
│   │
│   ├── knowledge/
│   │   ├── papers/
│   │   ├── mechanisms/
│   │   ├── retrieval/
│   │   └── graph/
│   │
│   ├── dsl/
│   │   ├── ast.py
│   │   ├── types.py
│   │   ├── operators.py
│   │   ├── parser.py
│   │   ├── compiler.py
│   │   ├── complexity.py
│   │   ├── novelty.py
│   │   └── safety.py
│   │
│   ├── research/
│   │   ├── hypotheses/
│   │   ├── families/
│   │   ├── trials/
│   │   ├── ledger/
│   │   ├── fastscreen/
│   │   ├── optimizer/
│   │   ├── lineage/
│   │   ├── preregistration/
│   │   └── holdout/
│   │
│   ├── models/
│   │   ├── base.py
│   │   ├── sklearn/
│   │   ├── lightgbm/
│   │   ├── pytorch/
│   │   ├── qlib/
│   │   ├── calibration/
│   │   └── uncertainty/
│   │
│   ├── validation/
│   │   ├── splitters/
│   │   ├── leakage/
│   │   ├── multiplicity/
│   │   ├── bootstrap/
│   │   ├── placebo/
│   │   ├── null_worlds/
│   │   ├── power/
│   │   ├── fragility/
│   │   ├── regimes/
│   │   ├── ablation/
│   │   ├── capacity/
│   │   └── verdicts/
│   │
│   ├── referees/
│   │   ├── penrose.py
│   │   ├── nullius.py
│   │   └── reference_math.py
│   │
│   ├── portfolio/
│   │   ├── skfolio_adapter/
│   │   ├── constraints/
│   │   └── risk_budget/
│   │
│   ├── execution/
│   │   ├── nautilus/
│   │   ├── hftbacktest/
│   │   ├── planners/
│   │   ├── controllers/
│   │   ├── cost_models/
│   │   ├── latency/
│   │   ├── capacity/
│   │   └── calibration/
│   │
│   ├── venues/
│   │   ├── specs/
│   │   ├── polymarket/
│   │   ├── hyperliquid/
│   │   └── cex/
│   │
│   ├── risk/
│   │   ├── policy.py
│   │   ├── pretrade.py
│   │   ├── exposure.py
│   │   ├── pnl.py
│   │   ├── data_health.py
│   │   ├── reconciliation.py
│   │   └── killswitch.py
│   │
│   ├── agents/
│   │   ├── capabilities.py
│   │   ├── researcher/
│   │   ├── builder/
│   │   ├── data_auditor/
│   │   ├── statistician/
│   │   ├── execution_critic/
│   │   └── allocator/
│   │
│   ├── promotion/
│   │   ├── gates.py
│   │   ├── policy.py
│   │   ├── manifest.py
│   │   └── signer.py
│   │
│   ├── live/
│   │   ├── runtime/
│   │   ├── supervisor/
│   │   ├── journal/
│   │   ├── shadow/
│   │   └── champion_challenger/
│   │
│   ├── monitoring/
│   │   ├── metrics.py
│   │   ├── traces.py
│   │   ├── drift.py
│   │   └── alerts.py
│   │
│   └── cli/
│
├── tests/
│   ├── unit/
│   ├── property/
│   ├── metamorphic/
│   ├── integration/
│   ├── statistical_calibration/
│   ├── null_worlds/
│   ├── execution_parity/
│   ├── replay/
│   ├── security/
│   └── performance/
│
├── schemas/
├── migrations/
├── notebooks/
├── scripts/
└── docs/
```

---

# 8. Identifier and Hashing Conventions

## 8.1 IDs

Use UUIDv7 where possible for database entities:

- `hypothesis_id`
- `family_id`
- `candidate_id`
- `trial_id`
- `study_id`
- `dataset_manifest_id`
- `feature_manifest_id`
- `model_artifact_id`
- `evidence_bundle_id`
- `deployment_id`
- `live_session_id`

Never use filenames or strategy names as identity.

## 8.2 Hashes

Use SHA-256 for durable cross-language identifiers.

Every immutable artifact should expose:

```text
sha256:<hex>
```

Canonical JSON must:

- sort keys;
- use explicit UTC timestamp formatting;
- forbid NaN/Infinity;
- normalize numeric serialization;
- include schema version.

Objects to hash:

- candidate source;
- DSL AST;
- data manifest;
- feature manifest;
- model bytes;
- config;
- dependency lock;
- container digest;
- validation policy;
- venue spec;
- risk policy;
- final deployment manifest.

---

# 9. Core Domain Contracts

These types are more important than framework-specific classes. Keep the contracts independent from Nautilus, Optuna, skfolio, and model libraries.

## 9.1 TemporalObservation

```python
class TemporalObservation(BaseModel):
    observation_id: UUID
    source: str
    entity_id: str
    field: str

    event_time: datetime
    source_publish_time: datetime | None
    available_time: datetime
    ingest_time: datetime
    revision_time: datetime | None

    revision_id: str
    source_sequence: int | None

    value: Any
    unit: str | None
    quality_flags: set[str] = set()

    source_record_hash: str
```

Semantics:

- `event_time`: when the underlying real-world event occurred.
- `source_publish_time`: when the original source publicly published it.
- `available_time`: earliest time QuantLab could legitimately have used it.
- `ingest_time`: when QuantLab received/stored it.
- `revision_time`: when this version superseded an earlier version.
- `revision_id`: stable lineage for revised values.

**Backtest eligibility rule:**

```text
available_time <= simulation_clock
```

not merely `event_time <= simulation_clock`.

## 9.2 LabelWindow

Required for correct purging.

```python
class LabelWindow(BaseModel):
    sample_id: UUID
    prediction_time: datetime
    evaluation_start: datetime
    evaluation_end: datetime
```

Purging must operate on actual overlapping label intervals, not a guessed integer gap.

## 9.3 Hypothesis

```python
class Hypothesis(BaseModel):
    hypothesis_id: UUID
    family_id: UUID

    title: str
    mechanism: str
    expected_sign: Literal["positive", "negative", "conditional", "nonlinear"]
    target: str
    horizon: str

    applicable_universe: str
    expected_regimes: list[str]
    confounders: list[str]
    falsification_conditions: list[str]

    required_fields: list[str]
    source_references: list[str]

    generator_type: str
    generator_model: str | None
    generator_prompt_hash: str | None

    created_at: datetime
```

A hypothesis without a falsification condition is incomplete.

## 9.4 Candidate

```python
class Candidate(BaseModel):
    candidate_id: UUID
    hypothesis_id: UUID
    family_id: UUID

    representation: Literal["dsl", "python_model", "mm_controller"]
    source_hash: str
    ast_hash: str | None

    parent_ids: list[UUID]
    mutation_operation: str | None

    complexity_score: float
    novelty_scores: dict[str, float]

    declared_search_space: dict
    declared_primary_metric: str
    declared_cost_model_id: str

    frozen_at: datetime
```

## 9.5 Forecast

```python
class Forecast(BaseModel):
    timestamp: datetime
    instrument_id: str
    horizon: timedelta

    expected_return: float
    uncertainty: float | None
    confidence: float | None

    model_id: str
    candidate_id: UUID
```

Allow alternative forecast targets:

- probability of up move;
- return quantile;
- expected return;
- volatility;
- probability of event outcome;
- fair probability for prediction market.

## 9.6 TargetPortfolio

```python
class TargetPortfolio(BaseModel):
    timestamp: datetime
    weights: dict[str, float]
    cash_weight: float
    optimizer_id: str
    constraints_hash: str
```

## 9.7 OrderIntent

```python
class OrderIntent(BaseModel):
    intent_id: UUID
    strategy_id: str
    candidate_hash: str

    instrument_id: str
    venue: str

    side: Literal["BUY", "SELL"]
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None

    post_only: bool = False
    reduce_only: bool = False
    ttl_ms: int | None = None

    created_at: datetime
    risk_context_hash: str
```

## 9.8 EvidenceBundle

```python
class EvidenceBundle(BaseModel):
    candidate_id: UUID
    candidate_hash: str
    dataset_manifest_hash: str

    sample_size: int
    trade_count: int

    in_sample_metrics: dict
    validation_metrics: dict
    cpcv_metrics: dict
    oos_metrics: dict | None

    psr: float | None
    dsr: float | None
    pbo: float | None
    spa_pvalue: float | None

    parameter_stability: dict
    regime_stability: dict
    cost_sensitivity: dict
    delay_sensitivity: dict
    capacity_sensitivity: dict

    referee_results: dict

    verdict: str
    verdict_reasons: list[str]

    policy_hash: str
```

---

# 10. Data Truth Plane

This is the highest-risk part of the system. A statistically perfect validator built on incorrect data is worthless.

## 10.1 Raw data policy

Raw data is immutable.

Storage layout:

```text
data/raw/
  source=<source>/
    data_type=<type>/
      date=YYYY-MM-DD/
        part-*.parquet
```

For order books:

```text
data/raw/
  source=binance/
    data_type=book_delta/
      symbol=BTCUSDT/
        date=...
```

Never “clean” the raw layer in place.

## 10.2 Derived layers

```text
RAW
 ↓
NORMALIZED
 ↓
PIT
 ↓
FEATURES
 ↓
TRAINING DATASET
```

Each layer has a manifest referencing its parents.

## 10.3 DatasetManifest

Must contain:

```text
manifest_version
dataset_id
created_at
parent_manifests[]
source_files[]
source_file_hashes[]
row_counts
min/max event_time
min/max available_time
schema_hash
transformation_git_sha
transformation_config_hash
quality_report_hash
partition_spec
```

## 10.4 Point-in-time query semantics

A PIT query requires:

```text
entity
feature
query_time
knowledge_cutoff
```

Selection:

1. `event_time` appropriate to feature definition.
2. `available_time <= query_time`.
3. if revisions exist, choose latest revision with `available_time <= query_time`.
4. never use revisions published after query time.
5. enforce maximum staleness if defined.
6. record the source observation IDs used.

DuckDB ASOF joins can implement parts of this efficiently, but a finance-specific wrapper must enforce `available_time` and revision semantics explicitly.

## 10.5 Point-in-time universe

For each tradable universe:

```text
instrument_id
valid_from
valid_to
tradable_from
tradable_to
source
reason
```

Examples:

- exchange listing/delisting;
- index constituent membership;
- contract creation/expiration;
- Polymarket market open/close/resolution;
- trading suspension.

A backtest universe at `t` is generated from membership known at `t`, not a current instrument list projected backward.

## 10.6 VenueSpec

```python
class VenueSpec(BaseModel):
    venue: str
    effective_from: datetime
    effective_until: datetime | None

    maker_fee_bps: float
    taker_fee_bps: float
    rebate_rules: dict

    tick_rules: dict
    lot_rules: dict
    min_notional_rules: dict

    margin_rules: dict
    funding_rules: dict
    position_mode_rules: dict

    supported_order_types: set[str]
    rate_limits: dict
    special_market_rules: dict

    source_refs: list[str]
    spec_hash: str
```

A 2023 backtest must not silently use a 2026 fee schedule.

## 10.7 Order-book data quality

For each L2/L3 stream:

- detect sequence gaps;
- detect duplicate sequence numbers;
- detect out-of-order deltas;
- checksum where venue provides one;
- rebuild snapshots periodically;
- mark unverifiable intervals invalid;
- log snapshot-to-delta discontinuities;
- flag crossed/negative/impossible books;
- preserve source timestamps and local receipt timestamps separately.

A market-making experiment cannot use an interval with unrepairable book gaps unless explicitly downgraded and marked.

---

# 11. Data Validation and Schema Gates

Every data boundary gets a Pandera contract.

Examples:

## 11.1 OHLCV

- UTC timezone.
- high ≥ max(open, close, low).
- low ≤ min(open, close, high).
- volume ≥ 0.
- price > 0.
- timestamp monotonic within instrument.
- no duplicate `(venue, instrument, timestamp)`.
- interval consistency.
- no future `available_time`.

## 11.2 Trades

- price > 0.
- quantity > 0.
- valid aggressor side enum or explicit unknown.
- monotonically increasing sequence where applicable.
- duplicate trade IDs flagged.

## 11.3 Semantic/social observations

- source identifier mandatory;
- original published timestamp mandatory if available;
- collection timestamp mandatory;
- model completion timestamp mandatory;
- output cannot be backdated before model completion;
- deleted/edited content revision lineage preserved.

## 11.4 Macro/fundamental

- observation period separate from publication date;
- original vintage preserved;
- revisions preserved;
- publication lag explicit;
- source timezone explicit.

---

# 12. Feature Registry and Lineage

A feature is not merely a dataframe column.

```python
class FeatureDefinition(BaseModel):
    name: str
    version: str
    description: str

    inputs: list[str]
    operator_graph_hash: str

    minimum_history: timedelta
    availability_lag: timedelta
    max_staleness: timedelta | None

    output_type: str
    unit: str | None

    code_hash: str
```

Every computed feature value stores or can derive:

- feature version;
- source manifest;
- input observation IDs or partition hashes;
- computation code hash;
- config hash;
- computation time;
- `available_time`.

## 12.1 Feature graph

Store a DAG:

```text
raw trade
  ↓
midprice
  ↓
microprice
  ↓
imbalance
  ↓
forecast input
```

When a raw series changes or a feature definition changes, descendants are invalidated/versioned.

---

# 13. Knowledge / Literature Grounding

The AI research system should search *mechanisms*, not merely formula space.

## 13.1 Knowledge graph entities

- Paper
- Mechanism
- Market phenomenon
- Data field
- Factor
- Strategy family
- Asset class
- Regime
- Failure mode
- Invalidation
- Successful conditional effect

Relationships:

```text
Paper → proposes → Mechanism
Mechanism → motivates → Factor
Factor → uses → Field
Factor → tested_on → Universe
Factor → fails_in → Regime
Factor → correlated_with → Factor
Hypothesis → derived_from → Mechanism
Experiment → invalidates → Hypothesis
```

## 13.2 Research query types

Examples:

- Which documented mechanisms have not been tested on crypto?
- Which mechanisms require data already available in our store?
- Which existing factor families show residual IC after controlling for trend?
- Which failed hypotheses fail only in high funding regimes?
- Which papers use mechanisms orthogonal to the current live portfolio?

## 13.3 Source reliability tiers

Do not treat every retrieved page equally.

Suggested tiers:

1. peer-reviewed paper / official exchange rule;
2. preprint with code/reproducibility;
3. reputable technical blog;
4. developer documentation;
5. community claim;
6. social post/speculation.

Hypothesis records preserve source tier.

---

# 14. Alpha Generation Firewall

The LLM must not receive arbitrary permission to invent Python and search unconstrained code space.

Default factor generation should use a safe typed DSL.

## 14.1 DSL types

Example value types:

```text
Price
Return
Volume
Probability
Count
Duration
Scalar
Boolean
CrossSectionalRank
OrderBookDepth
FundingRate
OpenInterest
SemanticScore
```

Type system prevents nonsense such as:

```text
price + probability
```

unless explicitly transformed.

## 14.2 Operator metadata

Each operator defines:

```text
name
input_types
output_type
minimum_history
causal/past-only semantics
complexity_cost
parameters
parameter_ranges
frequency_constraints
```

Example:

```text
rolling_mean(Return, window=20)
```

## 14.3 Initial operator classes

- arithmetic;
- lag/difference;
- rolling statistics;
- exponential filters;
- ranks/z-scores;
- robust scaling;
- volatility;
- trend;
- volume/liquidity;
- funding/open-interest;
- order-book imbalance;
- spread/depth;
- semantic/sentiment aggregations;
- regime interaction;
- cross-sectional transforms;
- logical conditions;
- clipping/winsorization.

## 14.4 Explicitly forbidden DSL operations

- future shift;
- centered rolling windows;
- global full-sample quantiles;
- fitting scalers on full dataset;
- direct access to target;
- arbitrary file/network access;
- unrestricted Python eval;
- non-versioned external calls.

## 14.5 Complexity score

Compute from canonical AST:

```text
complexity =
    node_count
  + weighted_parameter_count
  + nesting_penalty
  + nonlinear_operator_penalty
  + branch_penalty
```

Complexity is used for:

- admission limits;
- regularization;
- novelty comparisons;
- fragility reporting.

Do not use one universal complexity cutoff. Make limits strategy-class specific.

## 14.6 Structural novelty

Calculate:

- canonical AST edit distance;
- operator multiset similarity;
- parameterized-tree similarity;
- feature-output correlation;
- realized-return correlation;
- semantic embedding similarity;
- economic-mechanism similarity.

A renamed SMA45 variant does not become a new hypothesis family.

## 14.7 Hypothesis ↔ factor alignment

The proposed mechanism must be consistent with the factor.

Example:

Hypothesis:
> attention shock causes short-lived positive pressure.

Factor that only uses 200-day moving average:
> fails alignment.

LLM-based alignment can be used as a diagnostic, but deterministic checks should cover fields, horizon, sign, and stated interactions.

---

# 15. Research Kernel

The Research Kernel owns identity, lineage, experiment state, and reproducibility.

It must not depend conceptually on Optuna.

## 15.1 Entities

- Study
- HypothesisFamily
- Hypothesis
- Candidate
- Trial
- DatasetManifest
- FeatureManifest
- ModelArtifact
- EvidenceBundle
- HoldoutLease
- CandidateManifest
- DeploymentManifest

## 15.2 Study

Study declares the research question *before* results:

```text
study_id
research_question
target
horizon
universe
dataset partitions
primary metric
secondary metrics
cost model
candidate budget
search method
validation protocol
sealed holdout policy
```

## 15.3 Preregistration

Before a generated batch is evaluated, freeze:

- number of candidates requested;
- generator;
- search family;
- search budget;
- target;
- metric;
- filter rules;
- validation policy.

Discarded candidates still count where selection-bias accounting requires it.

---

# 16. Immutable Trial Ledger

The Trial Ledger is the heart of the research integrity system.

## 16.1 Append-only rule

No UPDATE/DELETE of historical trial records through normal application code.

Corrections are appended as new records referencing the old record.

## 16.2 Hash chain

Each ledger event:

```text
event_id
timestamp
event_type
payload
previous_hash
hash
```

`hash = SHA256(canonical_payload + previous_hash)`

Periodically produce a checkpoint/root hash and optionally sign it.

## 16.3 Trial record fields

At minimum:

```text
trial_id
study_id
family_id
hypothesis_id
candidate_id
candidate_hash

parent_candidate_ids

generator_type
generator_model
prompt_hash

data_manifest_hash
feature_manifest_hash

code_hash
config_hash
dependency_lock_hash
container_digest

search_space
trial_parameters
trial_number
random_seed

train_range
validation_range
test_range

execution_assumptions_hash
venue_spec_hash

metrics
warnings
failure_reason

status:
  CREATED
  RUNNING
  PRUNED
  FAILED
  COMPLETE
  REJECTED
  PROMOTED_FOR_VALIDATION
```

## 16.4 Optuna integration

Optuna is a worker/sampler, not the source of truth.

Before an Optuna trial starts:

1. allocate Trial Ledger record;
2. persist suggested parameters;
3. run trial;
4. persist completion/failure;
5. update search-family summary.

If process crashes, trial remains visible as incomplete/error.

---

# 17. Strategy Family / Search Accounting

A major statistical problem is that 1,000 tiny mutations are not 1,000 independent discoveries.

Represent candidate lineage as a DAG.

Family assignment considers:

- declared economic mechanism;
- parent lineage;
- AST similarity;
- feature overlap;
- return correlation;
- semantic similarity.

Never permit a generator to start a fresh family simply because it changed a name.

Track:

```text
raw_trial_count
effective_trial_count
candidate_count
surviving_count
sealed_holdouts_consumed
```

Use `effective_n_trials` only as an estimate, not as a magic exact count.

---

# 18. FastScreen Engine

FastScreen exists only to cheaply eliminate obviously bad candidates.

It must never pretend to be an order-book simulator.

## 18.1 Inputs

Canonical arrays:

```text
timestamp
instrument_id
features...
signal / forecast / target exposure
reference price
fees
```

## 18.2 Supported first-version strategy mode

Directional exposure:

```text
target_exposure[t] ∈ [-1, 1]
```

Optional portfolio weights later.

## 18.3 Execution approximation

Configurable:

- execute next bar open;
- execute next bar VWAP approximation;
- fixed/sliding fee;
- spread estimate;
- simple turnover slippage;
- configurable delay.

Never execute at the same timestamp used to compute an end-of-bar signal unless explicitly justified.

## 18.4 Output

- raw returns;
- turnover;
- gross exposure;
- net exposure;
- drawdown;
- trades;
- cost attribution;
- basic Sharpe/Sortino;
- per-regime summary;
- data/leak warnings.

## 18.5 FastScreen acceptance tests

- deterministic given identical seed/input;
- long-only buy-and-hold matches analytical return;
- zero signal = zero PnL except explicit costs;
- next-bar semantics proven by unit tests;
- one-bar future leak planted in test is caught by external leak detector;
- transaction-cost monotonicity: increasing cost cannot improve deterministic PnL absent rebates;
- result matches a simple independent reference implementation on golden cases.

---

# 19. Model / Forecast Lab

Separate predictive skill from trading skill.

## 19.1 ModelAdapter interface

```python
class ModelAdapter(Protocol):
    def fit(self, train: DatasetSlice) -> ModelArtifact: ...
    def predict(self, model: ModelArtifact, test: DatasetSlice) -> ForecastFrame: ...
```

Adapters:

- sklearn;
- LightGBM;
- XGBoost optional;
- PyTorch;
- Qlib;
- custom semantic/JEV model;
- simple statistical baselines.

## 19.2 Mandatory baselines

Every model competes against trivial baselines:

- zero forecast;
- persistence;
- moving average;
- simple linear model;
- current production model;
- random or permuted target where relevant.

## 19.3 Forecast metrics

Depending on target:

Regression:
- MAE;
- MSE;
- robust loss;
- rank IC;
- Pearson IC;
- calibration slope/intercept;
- residual autocorrelation;
- Diebold-Mariano vs baseline.

Classification/probability:
- Brier score;
- log loss;
- calibration curve;
- ECE;
- reliability by regime;
- AUC only as secondary if appropriate.

Volatility:
- QLIKE;
- calibration;
- realized-vs-predicted.

Prediction market:
- Brier/log loss vs resolved outcomes;
- calibration by probability bucket;
- edge vs market probability;
- transaction-cost-aware expected value.

## 19.4 Calibration

Probability/uncertainty estimates must be calibrated using training/validation only.

Never fit calibration on sealed OOS.

---

# 20. Falsification Stack

The validator returns evidence, not a single score.

## 20.1 Layer A — data integrity

Hard block:

- timestamp violation;
- unknown revision handling;
- unrepairable order-book gaps for strategies needing books;
- impossible universe membership;
- duplicate/invalid keys;
- feature available after decision time;
- unknown venue rules;
- data source mismatch.

## 20.2 Layer B — leak detection

Implement multiple independent techniques:

1. static DSL checks;
2. prefix invariance;
3. truncated-data recomputation;
4. future-column poisoning;
5. Freqtrade-style signal perturbation concept;
6. normalization-window audit;
7. train/test overlap audit;
8. label overlap audit;
9. universe membership audit.

### Prefix invariance

For decision function `f`:

```text
f(data[:T]) for timestamps <= T
```

must equal:

```text
f(data[:T+k]) for timestamps <= T
```

for past-only features.

Deliberately plant known leaks in CI so the detector is proven to fire.

## 20.3 Layer C — chronological validation

Use:

- expanding walk-forward;
- rolling walk-forward;
- purged K-fold;
- group-purged folds for asset/generalization questions.

The split strategy must match deployment:

- future on same asset;
- unseen assets;
- unseen markets;
- unseen regimes;
- combination thereof.

## 20.4 Layer D — CPCV

Use CPCV to obtain multiple alternative OOS paths.

Important interpretation:

CPCV reconstructed paths are **robustness distributions**, not a literal historical production chronology. Do not market them as “the true OOS equity curve.”

Store:

- path return;
- Sharpe;
- max drawdown;
- turnover;
- trade count;
- cost sensitivity;
- worst quantile;
- median;
- dispersion.

## 20.5 Layer E — PBO

Use CSCV/PBO to estimate how often the in-sample-selected strategy underperforms OOS.

Report:

- PBO;
- IS/OOS performance pairs;
- degradation slope;
- number of configurations in family.

Do not define a universal threshold as truth. Policy thresholds can start conservative and be calibrated on synthetic/reference tasks.

## 20.6 Layer F — PSR / DSR

Track:

- observed Sharpe;
- benchmark Sharpe;
- skew;
- kurtosis;
- effective trial count;
- variance of trial Sharpes.

Never compute DSR with a fabricated trial count.

## 20.7 Layer G — SPA / Reality Check / MCS

Use `arch.bootstrap`:

- SPA against benchmark;
- StepM where appropriate;
- Model Confidence Set for multiple competing forecast models.

Use block bootstrap appropriate to serial dependence.

Block length must be recorded.

## 20.8 Layer H — permutation / placebo

Create null distributions by:

- permuting labels in blocks;
- circularly shifting signal;
- phase/randomized return surrogate where defensible;
- AR(1)-matched placebo signals;
- random entry with matched holding period;
- random feature with matched autocorrelation;
- random strategy generator with same complexity/search budget.

A null should preserve enough structure that it is a meaningful competitor.

## 20.9 Layer I — parameter stability

For every important parameter:

- evaluate local neighborhood;
- measure gradient/curvature of performance;
- identify isolated spike;
- compute fraction of nearby configurations that remain viable.

Reject “needle in haystack” candidates unless there is strong mechanistic justification and forward evidence.

## 20.10 Layer J — feature ablation

Run:

- leave-one-feature-out;
- leave-one-group-out;
- mechanism ablation;
- replace feature with lagged/null version.

For ensembles, measure marginal value relative to current combined forecast.

## 20.11 Layer K — regime robustness

Regimes are diagnostics, not excuses for post-hoc cherry-picking.

Predefined regimes can include:

- trend direction;
- realized vol quantile;
- liquidity/spread;
- funding;
- risk-on/off;
- session/time-of-day;
- market stress.

Also allow unsupervised regime detection, but never use retrospective regime labels as if known prospectively unless the online detection process is simulated.

## 20.12 Layer L — delay sensitivity

Evaluate signal at:

```text
0
+1 bar
+2 bars
+5 bars
```

or milliseconds for HFT.

If edge disappears under a tiny realistic delay, classify as execution-sensitive and require higher-fidelity data.

## 20.13 Layer M — cost sensitivity

Stress:

- base fee;
- 1.25×;
- 1.5×;
- 2×;
- pessimistic spread;
- adverse slippage;
- maker → taker substitution.

Report break-even cost.

## 20.14 Layer N — capacity

Historical replay does not solve counterfactual market impact.

Stress size:

```text
0.25×
0.5×
1×
2×
5×
```

Use:

- depth participation;
- ADV participation;
- spread;
- queue assumptions;
- conservative impact functions.

Output:

- expected PnL vs capital;
- Sharpe vs size;
- break-even size;
- maximum recommended canary size.

## 20.15 Layer O — statistical power

Return one of:

```text
REJECT
UNDERPOWERED
RESEARCH_SUPPORTED
CONDITIONAL
MODEL_RISK
BLOCKED
```

For UNDERPOWERED report:

- observed effect;
- minimum detectable effect;
- approximate additional observations required;
- which evidence is insufficient.

Do not mislabel “not significant” as “no effect.”

---

# 21. Independent Referee Plane

The internal validator must not be trusted merely because we wrote good tests.

## 21.1 Penrose adapter

Export a frozen claim bundle containing:

- strategy/factor definition;
- source hash;
- search denominator;
- data manifest;
- return series;
- costs;
- declared primary metric;
- family metadata.

Penrose result becomes a referee record.

Treat Penrose as independent evidence, not canonical truth.

## 21.2 Nullius adapter

Use Nullius especially for:

- prefix invariance;
- placebos;
- DSR/PBO cross-check;
- forecast tests;
- negative control behavior.

## 21.3 Reference math

Maintain small independent formula implementations for:

- Sharpe;
- PSR;
- DSR worked examples;
- basic bootstrap;
- drawdown;
- turnover.

The purpose is not performance; it is differential testing.

## 21.4 Disagreement policy

If internal and external implementations disagree materially:

```text
verdict = MODEL_RISK
promotion = blocked
```

Do not select the more favorable result.

---

# 22. Sealed Holdout Service

This is a security boundary.

## 22.1 Process separation

Research worker credentials cannot read sealed partitions.

A separate service owns confirmation data.

## 22.2 Freeze before reveal

CandidateManifest must freeze:

- source;
- parameters;
- model;
- features;
- data definitions;
- costs;
- venue rules;
- execution model;
- primary metric;
- pass/fail policy.

Hash it.

Only the hash is submitted to holdout service.

## 22.3 Holdout lease

```text
holdout_id
candidate_hash
family_id
dataset_partition
issued_at
consumed_at
status
```

Status:

```text
AVAILABLE
LEASED
CONSUMED
INVALIDATED
```

Single-use means results cannot be rerun after parameter edits.

## 22.4 Contamination rules

After a candidate family consumes a holdout:

- descendants cannot call the same interval “unseen.”
- new confirmation requires:
  - later forward data;
  - different predeclared universe;
  - a genuinely untouched partition.

## 22.5 Progressive reveal

Historical data is finite.

Use tiers:

```text
Discovery
Validation
Research holdout
Sealed confirmation
Forward shadow
```

The ultimate clean data source is *future market data not yet observed at research time*.

---

# 23. Portfolio Construction

Do not bake portfolio allocation into every alpha model.

Pipeline:

```text
Forecasts
  ↓
Expected returns / risk estimates
  ↓
skfolio
  ↓
TargetPortfolio
```

## 23.1 Initial supported optimizers

Start with simple robust choices:

- constrained mean-risk;
- risk budgeting;
- minimum variance;
- hierarchical approaches;
- equal risk/equal weight baselines.

Do not start with highly complex optimizer stacks.

## 23.2 Constraints

Support:

- max asset weight;
- min/max gross exposure;
- net exposure;
- leverage;
- asset-class/group caps;
- venue caps;
- stablecoin/counterparty caps;
- turnover cap;
- target volatility;
- minimum cash;
- no-trade bands.

## 23.3 Forecast uncertainty

If forecast uncertainty is available, reduce allocation to uncertain forecasts.

Do not let a high point estimate dominate without uncertainty.

## 23.4 Portfolio validation

Portfolio model itself must be walk-forward tested.

Avoid fitting covariance/expected-return estimates using test periods.

CPCV is useful for robustness distributions; chronological walk-forward remains necessary for operational interpretation.

---

# 24. Execution Planner

Execution Planner translates target exposure/weights into bounded trading workflows.

## 24.1 Directional modes

- immediate marketable;
- passive limit;
- TWAP;
- POV;
- simple sliced limit;
- hedge-first or hedge-after;
- rebalance no-trade band.

## 24.2 Market-making mode

MM bypasses TargetPortfolio and produces OrderIntent directly.

Controller inputs:

- fair value/probability;
- L2/L3 book;
- inventory;
- volatility;
- adverse-selection estimate;
- queue estimates;
- related market prices;
- spread;
- venue fees/rebates.

Controller output:

```text
create_quote
replace_quote
cancel_quote
hedge
pause
```

Adopt Hummingbot’s Controller/Executor separation as a conceptual pattern, but run actual execution through Nautilus.

---

# 25. NautilusTrader Integration

NautilusTrader is the canonical runtime.

## 25.1 Adapter boundary

QuantLab strategy logic should not expose Nautilus types everywhere.

Implement:

```text
QuantLab OrderIntent
    ↓
Nautilus adapter
    ↓
Nautilus Order / Strategy / ExecutionAlgorithm
```

and:

```text
Nautilus market event
    ↓
QuantLab normalized MarketState
```

## 25.2 Simulation profiles

Define explicit profiles:

### BAR_RESEARCH

- bars only;
- conservative next-bar timing;
- not certification-grade for execution-sensitive strategies.

### L1_VALIDATION

- quotes/trades;
- spread;
- probabilistic fill/slippage where appropriate.

### L2_EXECUTION

- L2 book;
- trade execution;
- liquidity consumption;
- queue position where supported;
- latency model.

### L3_EXECUTION

- full market-by-order when available;
- strictest replay.

## 25.3 Versioning

Nautilus version is part of every experiment manifest.

Do not silently upgrade.

When upgrading:

1. run golden execution cases;
2. rerun simulator parity suite;
3. compare PnL/fills on fixed tapes;
4. require explicit approval if material differences.

## 25.4 Known limitation

Even L2/L3 replay cannot know how the market would have changed in response to our historical orders.

Document that clearly.

---

# 26. HftBacktest Integration

For MM/HFT finalists, run independent replay.

Compare:

- fills;
- queue wait;
- fill probability;
- maker/taker fraction;
- spread capture;
- adverse selection;
- inventory trajectory;
- PnL.

## 26.1 Disagreement thresholds

Do not begin with hard universal percentages.

Create an execution discrepancy report:

```text
metric
nautilus
hftbacktest
absolute_delta
relative_delta
```

Classify material divergence by strategy risk.

Any unexplained material divergence blocks promotion.

---

# 27. Prediction Market / Polymarket Profile

Prediction markets have special semantics.

## 27.1 Data contracts

Store:

- event;
- market;
- outcome token;
- complementary outcome relation;
- resolution source;
- market open/close;
- tick size;
- fee/rebate rules;
- settlement state;
- disputes/invalidations if applicable.

## 27.2 Probability invariants

For complementary binary outcomes, monitor:

```text
P(YES) + P(NO) ≈ 1
```

after accounting for spread/fees.

Relative-value strategies may compare:

- related outcomes;
- nested markets;
- same real-world event across venues;
- market probability vs external model.

## 27.3 MM-specific tests

Must include:

- self-liquidity filtering;
- queue priority;
- cancel/replace latency;
- partial fills;
- stale quote risk;
- resolution risk;
- inventory imbalance;
- correlated-market hedge failure;
- maker rebate sensitivity;
- taker fallback cost;
- book gap handling.

---

# 28. Hyperliquid / CEX Profile

Track:

- funding;
- margin;
- leverage;
- liquidation model;
- position mode;
- tick/lot;
- fee tier;
- maker/taker;
- API/rate limits;
- venue status.

For perpetuals, funding is a first-class cash flow in both backtests and live reconciliation.

---

# 29. Risk Supervisor

Risk is outside strategy code.

## 29.1 Hierarchy

Policies:

```text
GLOBAL
  → ACCOUNT
    → VENUE
      → STRATEGY
        → INSTRUMENT
```

Tighter rule wins.

## 29.2 Pre-trade limits

- max order notional;
- max position;
- max gross;
- max net;
- max leverage;
- max venue exposure;
- max asset exposure;
- max correlated group exposure;
- max inventory;
- price-deviation guard;
- order-rate/cancel-rate guard.

## 29.3 Runtime limits

- daily loss;
- rolling loss;
- drawdown;
- unexpected slippage;
- reconciliation mismatch;
- feed staleness;
- sequence gap;
- latency spike;
- repeated rejection;
- strategy heartbeat failure;
- venue health failure.

## 29.4 Kill switch

Kill behavior configurable:

- cancel all;
- stop new orders;
- reduce only;
- flatten;
- venue disconnect.

Kill switch can be triggered by operator or supervisor, never vetoed by strategy/AI.

---

# 30. AI Agent Architecture

Use separate roles with capability-scoped tools.

## 30.1 Researcher

Can:

- query knowledge graph;
- read allowed discovery/CV data summaries;
- propose hypotheses;
- propose DSL factors;
- request experiments.

Cannot:

- execute arbitrary host code;
- access sealed OOS;
- access live secrets;
- promote.

## 30.2 Builder

Can:

- implement DSL/compiler/test code;
- write candidate code in sandbox;
- run unit tests.

Cannot:

- network from candidate sandbox;
- read production credentials;
- sign artifacts.

## 30.3 Data Auditor

Can:

- inspect schemas;
- run prefix invariance;
- inspect PIT lineage;
- block bad data.

Cannot:

- alter raw data.

## 30.4 Statistician

Can:

- compute evidence;
- run reference tests;
- compare models.

Cannot:

- edit candidate after seeing results.

## 30.5 Execution Critic

Can:

- run Nautilus/HftBacktest;
- vary latency/cost/capacity;
- classify execution risk.

Cannot:

- submit live orders.

## 30.6 Allocator

Can:

- run portfolio optimization under fixed constraints.

Cannot:

- change risk policy.

---

# 31. AI Feedback Hygiene

An adaptive researcher can overfit to validation feedback even without direct OOS access.

Mitigations:

1. generate candidates in frozen batches;
2. preregister batch budget;
3. do not expose sealed OOS;
4. expose failure classes rather than every favorable micro-metric where possible;
5. rate-limit structural mutation depth;
6. preserve family lineage;
7. charge all descendants to family search accounting;
8. periodically compare generator methods against null generators;
9. measure OOS survival by generator type.

---

# 32. Research-Process Benchmark

The system must evaluate not only strategies but **how strategies are generated**.

Track per generator:

```text
candidate_count
API/token cost
CPU/GPU cost
wall compute
valid candidates
CV survivors
sealed-OOS survivors
forward survivors
median OOS decay
correlation among survivors
capacity-adjusted value
```

Generator types:

- literature grounded;
- mechanism grounded;
- LLM free ideation;
- constrained LLM DSL;
- GP;
- trajectory evolution;
- random grammar;
- human ideas;
- mutation of existing winners.

This lets the system answer:

> Which research process produces the most credible edge per unit of search and cost?

---

# 33. Generated Code Sandbox

Treat generated code as hostile.

## 33.1 Initial sandbox

Rootless Docker with:

- network disabled;
- read-only root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges`;
- CPU quota;
- memory quota;
- PID quota;
- ephemeral writable temp directory;
- approved read-only dataset mount;
- no Docker socket;
- no SSH agent;
- no cloud credentials;
- no exchange credentials;
- seccomp profile.

Docker is not a perfect security boundary. It is an acceptable initial isolation layer for a single-user research machine if the host threat model is understood.

For stronger hostile-code isolation later:

- gVisor;
- Firecracker microVM;
- dedicated isolated host.

## 33.2 Output contract

Generated code may emit only approved artifacts:

- metrics JSON;
- forecast Parquet;
- model artifact;
- candidate manifest;
- logs.

---

# 34. Signed Deployment Artifacts

Promotion creates an immutable DeploymentManifest.

Contents:

```text
candidate_hash
strategy_code_hash
model_hash
feature_manifest_hash
dataset_reference
dependency_lock_hash
container_digest
validation_policy_hash
evidence_bundle_hash
sealed_holdout_receipt
venue_spec_hash
execution_model_hash
risk_policy_hash
approved_at
```

Sign with an Ed25519 deployment key stored outside research containers.

Live runner verifies signature before loading.

A code edit invalidates signature.

---

# 35. Capability Token for Order Execution

Order routing should require a short-lived capability issued by Risk Supervisor.

Token binds:

```text
deployment_hash
strategy_id
account_id
venue
allowed_instruments
max_notional
expiry
nonce
```

One-time or bounded-use token depending on runtime design.

Research/LLM processes can never mint these.

---

# 36. Live Event Journal

Record enough state to reconstruct a live session.

Events:

- market data arrival;
- venue timestamp;
- local receive timestamp;
- feature-ready timestamp;
- forecast;
- portfolio target;
- risk decision;
- order intent;
- order send;
- ACK/reject;
- cancel;
- fill;
- fee;
- funding;
- reconciliation;
- portfolio state;
- strategy state;
- risk state.

Each event includes:

```text
live_session_id
sequence
event_time
local_monotonic_time
deployment_hash
payload
previous_hash
hash
```

Journal is append-only.

---

# 37. Latency Telemetry

For latency-sensitive strategies capture:

```text
exchange_event_time
network_receive_time
parser_complete_time
feature_ready_time
strategy_decision_time
risk_approval_time
wire_send_time
exchange_ack_time
fill_exchange_time
fill_receive_time
```

Build empirical distributions:

- feed latency;
- decision latency;
- risk latency;
- send/ACK latency;
- cancel latency;
- fill reporting latency.

Replay measured distributions into execution simulation.

---

# 38. Execution Calibration Loop

Compare simulation predictions to shadow/live.

Example:

```text
predicted maker fill rate: 78%
observed maker fill rate: 61%

predicted adverse selection: 1.1 bps
observed: 2.8 bps
```

Fit a new execution model version.

Important:

- calibration dataset is versioned;
- execution model gets new hash;
- strategies validated against old model do not silently inherit new model;
- material model changes trigger revalidation.

---

# 39. Champion / Challenger

Never replace a live champion directly with a new candidate.

```text
Champion → real capital
Challenger A → shadow
Challenger B → shadow
Challenger C → shadow
```

Promotion path:

```text
research-supported
→ shadow
→ paper if needed
→ tiny canary
→ larger canary
→ champion
```

Demotion path:

```text
active
→ degraded
→ quarantine
→ stop / reduce
```

---

# 40. Drift / Alpha Decay Lifecycle

Factor lifecycle:

```text
DISCOVERED
VALIDATED
ACTIVE
DECAYING
QUARANTINED
RETIRED
```

Monitor:

- live IC/rank IC;
- forecast calibration;
- residuals;
- live-vs-backtest decay;
- turnover;
- hit rate;
- regime concentration;
- correlation to other factors;
- capacity/slippage;
- feature distribution;
- model residual distribution.

Drift does not auto-deploy a retrained model.

Retraining produces a new candidate that re-enters validation.

---

# 41. Security Threat Model

## 41.1 Threats

### Generated code exfiltration
Mitigation: no network/secrets; sandbox.

### Prompt injection from papers/web data
Mitigation:
- retrieved text treated as data;
- no tool instructions accepted from documents;
- structured extraction;
- capability-scoped tools.

### Sealed holdout leakage
Mitigation:
- separate service/credentials;
- no research filesystem access;
- access log;
- one-time lease.

### Trial ledger tampering
Mitigation:
- append-only;
- hash chain;
- signed checkpoints;
- DB permissions.

### Credential theft
Mitigation:
- research workers have no live credentials;
- execution secrets only in execution service.

### Strategy bypass of risk
Mitigation:
- risk service between intent and execution;
- live execution requires capability token.

### Dependency compromise
Mitigation:
- pinned lockfile;
- SBOM;
- vulnerability scan;
- hash verification;
- limited dependency set.

### Malicious data
Mitigation:
- schema validation;
- source fingerprints;
- quality flags;
- quarantine.

### Replay mismatch
Mitigation:
- event journal;
- deployment hash in every decision;
- deterministic engine tests.

---

# 42. Dependency / License Policy

Core dependency preference:

```text
MIT
BSD-2/3
Apache-2.0
ISC
```

NautilusTrader LGPL-3.0 is acceptable as a separated library/runtime dependency, but distribution/commercial packaging must preserve its license obligations and should receive a legal review.

Avoid introducing GPL/AGPL code into the core unless the distribution consequences are explicitly accepted.

Maintain:

```text
LICENSES.md
SBOM.spdx.json
```

Run automated license scan in CI.

---

# 43. Reproducibility Envelope

Every research result must be reconstructable from:

```text
git SHA
uv.lock hash
container digest
Python version
OS/architecture
random seeds
dataset manifest
feature manifest
candidate source hash
model artifact hash
venue spec
execution model
validation config
```

`quantlab reproduce <trial_id>` should create a clean environment and reproduce the result within defined numerical tolerance.

---

# 44. CI / Test Strategy

This project should have more testing of *research validity* than ordinary application code.

## 44.1 Unit tests

Every:

- DSL operator;
- metric;
- splitter adapter;
- data parser;
- risk rule;
- hash function;
- manifest serialization.

## 44.2 Property-based tests

Use Hypothesis.

Examples:

- purged training samples never overlap test label windows;
- increasing fee cannot improve PnL in fee-only deterministic model;
- target weights satisfy constraints;
- timestamps never move backward;
- normalized book never has negative size;
- hash is stable under dictionary key order.

## 44.3 Metamorphic tests

Examples:

### Prefix invariance
Adding future rows cannot change historical feature values.

### Scale invariance
If a return-only strategy is supposed to be price-scale invariant, multiplying all prices by 10 should not change signals.

### Delay monotonicity
For a strategy whose only change is added execution delay, unrealistic improvement triggers review.

### Transaction-cost monotonicity
Higher costs should not improve gross-equivalent strategy value except explicit rebates/behavior changes.

## 44.4 Differential tests

Compare:

- internal DSR vs purgedcv;
- internal/reference SPA examples vs arch;
- internal leak detection vs Nullius;
- internal falsification result vs Penrose where supported;
- Nautilus vs HftBacktest execution statistics;
- FastScreen vs simple handwritten reference on simple strategies.

## 44.5 Synthetic null calibration

Generate:

- IID noise;
- AR(1) returns;
- GARCH volatility;
- regime-switching process with no directional signal;
- random factors with realistic autocorrelation.

Search hundreds/thousands of strategies.

Verify promotion rate remains acceptably low.

## 44.6 Planted-edge calibration

Generate weak known signal.

Verify the validator detects it at a reasonable power level.

A validator that rejects everything is not useful.

## 44.7 Leakage red team

Plant:

- `shift(-1)`;
- centered rolling mean;
- full-sample z-score;
- full-sample quantile;
- revised macro value backfilled;
- future universe membership;
- timestamp timezone offset;
- target-derived feature.

CI must prove these are caught.

## 44.8 Execution golden tapes

Create tiny deterministic order-book sequences where expected fills are known manually.

Test:

- market buy;
- passive limit;
- partial fill;
- cancel;
- queue ahead;
- price move;
- trade aggressor side;
- latency.

## 44.9 Live replay test

A recorded live session must reproduce:

- market state sequence;
- strategy decisions;
- order intents;
- risk outcomes.

Differences require a reason code.

---

# 45. Promotion Gates

No single scalar determines promotion.

## G0 — Platform self-test

Requirements:

- null calibration passes;
- planted leak tests pass;
- planted weak edge test passes;
- ledger integrity passes.

## G1 — Data integrity

Requirements:

- PIT compliant;
- no unresolved critical gaps;
- venue spec known;
- universe correct;
- quality report clean enough for strategy class.

## G2 — Basic economics

Requirements:

- positive after realistic base costs;
- enough observations/trades for next stage;
- not obviously dominated by baseline;
- no impossible exposure.

## G3 — Research robustness

Requirements:

- walk-forward acceptable;
- purged CV acceptable;
- CPCV distribution not pathological;
- parameter neighborhood not a single spike;
- ablation supports mechanism.

## G4 — Selection-bias correction

Review:

- raw/effective trials;
- PSR;
- DSR;
- PBO;
- SPA/MCS where appropriate;
- family lineage.

## G5 — Independent referees

Penrose/Nullius/reference math must not expose unexplained contradictions.

## G6 — Sealed OOS

Frozen candidate evaluated once.

## G7 — Portfolio value

Candidate must add marginal portfolio value, not merely standalone Sharpe.

## G8 — Execution validation

Nautilus realistic simulation.

MM/HFT additionally requires HftBacktest comparison.

## G9 — Capacity

Survives expected capital plus stress multipliers.

## G10 — Shadow

Live market, no capital.

## G11 — Canary

Small bounded capital.

## G12 — Production

Eligible for champion allocation.

---

# 46. Verdict Policy

Use semantic verdicts.

## REJECT

Evidence is sufficient to conclude candidate fails one or more required criteria.

## UNDERPOWERED

Data cannot resolve claimed effect.

## RESEARCH_SUPPORTED

Candidate survives research stack but is not yet a live-profit claim.

## CONDITIONAL

Edge appears dependent on explicitly declared regime/constraint.

## MODEL_RISK

Independent models/referees materially disagree.

## BLOCKED

Data/system problem prevents valid conclusion.

No verdict should say “profitable” based solely on historical tests.

---

# 47. Metrics Policy

Do not create a giant composite “magic score” for final certification.

Use a score only for cheap candidate ranking inside a declared search stage.

Promotion should use a vector of evidence and explicit gates.

Candidate reports should include:

- total/gross/net return;
- Sharpe;
- Sortino;
- max drawdown;
- Calmar;
- turnover;
- trade count;
- holding time;
- exposure;
- fee/slippage breakdown;
- funding;
- hit rate;
- payoff distribution;
- skew/tails;
- PSR/DSR/PBO;
- walk-forward distribution;
- CPCV distribution;
- parameter stability;
- regime stability;
- cost/delay/capacity curves;
- forecast skill;
- marginal portfolio contribution.

---

# 48. Performance Architecture

Optimize only after profiling.

## 48.1 Python first

Use Polars lazy queries and vectorized NumPy.

## 48.2 Numba only where clear

Use for tight numerical loops not expressible efficiently in Polars.

## 48.3 Rust later

Move only measured bottlenecks:

- DSL expression kernels;
- massive FastScreen simulation;
- order-book preprocessing;
- high-frequency feature kernels.

Expose through PyO3.

Avoid premature Rust rewrite.

---

# 49. Persistence Model

## 49.1 PostgreSQL tables

Core:

```text
studies
hypothesis_families
hypotheses
candidates
candidate_lineage
trials
trial_metrics
ledger_events
dataset_manifests
feature_manifests
model_artifacts
evidence_bundles
holdout_leases
candidate_manifests
deployment_manifests
risk_policies
venue_specs
live_sessions
```

Large arrays/returns do not belong in row-by-row PostgreSQL.

Store large artifacts in Parquet/object files with hash references.

## 49.2 Durable jobs

Do not introduce Redis/Celery initially unless necessary.

Use PostgreSQL job table with:

```sql
SELECT ...
FOR UPDATE SKIP LOCKED
```

to claim work.

Job fields:

```text
job_id
job_type
payload
status
attempts
locked_by
locked_at
next_run_at
error
```

---

# 50. API Boundaries

Initial internal services:

## `research-api`

- create study;
- submit hypothesis;
- generate batch;
- run screen;
- run validation;
- get evidence.

## `holdout-service`

- accept candidate manifest;
- verify hash;
- consume holdout;
- return signed receipt.

## `execution-service`

- load signed deployment;
- run shadow/paper/live;
- expose health.

## `risk-service`

- evaluate order intent;
- issue capability token;
- kill/pause.

For MVP, research modules can run in one process. Service boundaries become real when secrets/holdout security require them.

---

# 51. CLI

Examples:

```bash
quantlab data ingest ...
quantlab data audit ...
quantlab study create ...
quantlab hypothesis add ...
quantlab generate batch ...
quantlab screen run ...
quantlab validate run ...
quantlab referee run ...
quantlab holdout submit ...
quantlab evidence show ...
quantlab portfolio build ...
quantlab execution simulate ...
quantlab shadow start ...
quantlab live replay ...
quantlab ledger verify ...
quantlab reproduce TRIAL_ID
```

CLI commands must output machine-readable JSON with optional human formatting.

---

# 52. Configuration

Use versioned YAML/TOML config validated by Pydantic.

Never allow untracked environment variables to alter research semantics.

Environment variables may provide:

- secrets;
- filesystem paths;
- service endpoints.

Research logic must come from hashed config.

---

# 53. Logging

Structured JSON fields:

```text
timestamp
level
service
run_id
study_id
trial_id
candidate_id
deployment_hash
event_type
message
```

Never log:

- API keys;
- signing secrets;
- exchange credentials;
- raw private account secrets.

---

# 54. Observability

Production metrics:

## System

- CPU/memory;
- worker queue;
- job age;
- exception count.

## Data

- feed age;
- gap count;
- sequence discontinuity;
- row rate;
- stale feature count.

## Execution

- order send rate;
- rejects;
- cancels;
- fill ratio;
- maker/taker;
- slippage;
- latency percentiles;
- reconciliation mismatch.

## Strategy

- exposure;
- PnL;
- drawdown;
- forecast quality;
- turnover;
- live/backtest delta.

## Risk

- blocked orders;
- active lockouts;
- kill-switch status.

---

# 55. Failure-Mode Matrix

## Data failure

Symptoms:
- unusual alpha jump;
- missing intervals;
- revised values in history.

Response:
- quarantine dataset;
- invalidate descendant features/trials;
- rerun only after manifest correction.

## Statistical failure

Symptoms:
- high raw Sharpe, low DSR;
- PBO high;
- SPA not superior.

Response:
- reject or underpowered;
- do not “tune around” without new preregistered family.

## Parameter fragility

Symptoms:
- one isolated optimum.

Response:
- reject/conditional;
- require stronger forward evidence.

## Execution disagreement

Symptoms:
- Nautilus strong, HftBacktest weak.

Response:
- MODEL_RISK;
- inspect queue/latency/fill assumptions.

## Live decay

Symptoms:
- forecast IC collapses;
- slippage worsens.

Response:
- degrade allocation;
- quarantine if thresholds crossed;
- create new research candidate, no silent retrain.

## Venue failure

Symptoms:
- connection loss;
- stale book;
- reconciliation mismatch.

Response:
- stop new risk;
- cancel/flatten based on policy.

---

# 56. Single-Developer Build Strategy

The solo developer should not attempt all layers at once.

The build order must maximize information gained per unit of engineering effort.

**Revision 1.1 ordering:** Phase -1 (below) now precedes Phase 0. The original ordering put the first major go/no-go after four phases of platform engineering — contracts, PIT data model, ledger, FastScreen, and the full falsification stack — before any empirical answer existed. That sequencing risked spending months building an exquisitely engineered machine whose main output was increasingly sophisticated evidence that there is no edge. The existence test must come first, using off-the-shelf tools on existing research artifacts.

---

# Phase -1 — Empirical Existence / Information Test (added in Revision 1.1)

**Purpose.** Answer one question before any platform code is written:

> When our best existing candidates are evaluated with a substantially stronger falsification procedure, does anything remain interesting enough to justify more machinery?

This phase is executed entirely with existing research artifacts and off-the-shelf tools. **No QuantLab platform components are built here** — no TemporalObservation abstraction, no hash-chained ledger, no FastScreen engine, no sealed-holdout service, no DSL, no agent architecture.

## Frozen research universe (declared before testing)

Do not cherry-pick the two candidates that currently look best — that selection would itself be laundered into the results. Freeze a research universe containing:

1. all serious previously tested hypotheses (full family list, not just survivors);
2. known failures (must stay dead);
3. currently interesting candidates;
4. several deliberately random/null strategies;
5. one deliberately leaky strategy;
6. one planted weak-but-real edge if constructible.

Declare before any run: family definitions, trial counts, primary metrics, horizons, cost model, validation method, promotion criteria. Where prior research kept an audit ledger of experiments, mine it for the family/trial accounting — do not build a new ledger system; a CSV/SQLite table suffices for this phase.

## Validator self-test comes first

This phase tests two things simultaneously:

- **The strategies:** does anything survive?
- **The validator:** does it kill noise, catch the planted leak, retain the planted weak edge, and emit UNDERPOWERED where the data cannot resolve the claim?

If the harness cannot distinguish known nulls from planted edges, halt — every downstream verdict is noise. This is §45 G0 pulled forward to before the platform exists.

## Execution order

1. Power gate first: MinTRL/MinBTL and effective-sample checks per candidate — a candidate whose data cannot resolve its claimed effect size is UNDERPOWERED by construction; record it and skip compute.
2. Validator calibration on the null/leak/planted fixtures.
3. Walk-forward and purged K-fold evaluation.
4. CPCV path distribution + PBO.
5. PSR/DSR with family-scoped effective-trial deflation.
6. Placebo/permutation tests.
7. Nullius pass: prefix-invariance, matched placebos, leakage negative controls.
8. Optional Penrose pass as external referee (it ships as engine+adapters, not a turnkey service — treat standing it up as its own bounded task, not a blocker).
9. Verdicts per candidate.

## Tooling (use, do not build)

- `purgedcv` — walk-forward, PurgedKFold/PurgedGroupKFold, CPCV/CSCV, PBO, PSR/DSR, MinTRL/MinBTL, effective_n_trials.
- `nullius` — prefix-invariance leak probes, skill placebos, negative controls, forecast diagnostics (v0.1.0; use as cross-check, not sole authority).
- `penrose` — external referee where practical (family-scoped deflation, locked holdout semantics).
- Small hand-rolled reference calculations for independent cross-checks.

Penrose's current scope (search-family accounting, search-size-aware PSR/DSR, single-use locked holdout, power verdicts, purged CV, placebo/null calibration, hash-chained audit events) already covers most of what the spec originally assigned to owned components. Policy: **use before build** — implement a missing capability only when Penrose/Nullius/purgedcv create a concrete, named gap. The QuantLab lineage ledger (hypothesis → family → data version → generator → code → execution model → live outcome) remains justified long-term because it tracks provenance beyond what any referee records, but for Phase -1 it is a flat table.

## Data adequacy is feature-dependent — gate per candidate

Do not generalize one dataset's scarcity to the whole program. Price/trend hypotheses may have years of usable history; venue-specific funding feeds may have ~90 days; L2 order-book data may have ~2 weeks. Evaluate power per candidate per feature. A global "the data is thin" conclusion is as wrong as a global "the data is fine."

## Explicitly out of scope for Phase -1

- NautilusTrader, HftBacktest, execution modeling
- market making, Polymarket/prediction-market profiles
- DSL, agent roles, sandbox
- sealed-holdout service, hash-chained ledger, manifests
- live risk supervisor, signed artifacts, capability tokens

~2 weeks of L2 data can validate pipeline mechanics; it cannot convince anyone an MM strategy has durable edge across regimes. These layers are removed from the MVP path entirely until a candidate that needs them survives.

## Verdicts

Per candidate: RESEARCH_SUPPORTED / WATCH / UNDERPOWERED / KILL / MODEL_RISK / BLOCKED (§46 semantics).

## Decision tree

```text
                    Phase -1
                       │
           ┌───────────┴────────────┐
           │                        │
           ▼                        ▼
    credible survivor          zero survivors
           │                        │
           ▼                        ▼
 Phase 0+ has earned           diagnose WHY before
 the right to exist            building anything:
                               ┌────────┼─────────┐
                               ▼        ▼         ▼
                          hypothesis  data    venue
                           quality  scarcity economics
                               │        │         │
                               ▼        ▼         ▼
                          better    acquire/   different
                          ideas or   accrue    horizon or
                          sources    data      instrument
```

- If everything is UNDERPOWERED because data is thin → the next investment is **data accumulation/acquisition**, not architecture.
- If everything is well-powered and KILL → the next investment is **better hypotheses / different information sources**, not architecture.
- If something survives → the architecture has earned the right to exist; proceed to Phase 0.

## Scientific honesty notes

- Zero survivors among N tested families bounds the *tested hypothesis space* — it does not prove the venue has no exploitable alpha (cross-sectional, conditional, other-horizon, cross-venue, flow/event-driven effects may remain untested). Record the conclusion precisely.
- No amount of CPCV/PBO/DSR machinery manufactures independent samples. These methods control the false-discovery *rate* and use limited history more efficiently; they cannot turn a short track record into a rich one.
- Any in-flight forward evidence (e.g., live shadow/paper challengers) continues in parallel — Phase -1 backtest validation is a second leg, not a replacement for forward confirmation.

## Acceptance criteria

- Frozen manifest exists before any evaluation run (candidates, families, trial counts, metrics, costs, criteria).
- Validator kills all nulls, catches the planted leak, retains the planted weak edge, and emits UNDERPOWERED on the deliberately thin candidate.
- Every real candidate receives a semantic verdict with evidence.
- A written diagnose-WHY conclusion on the zero-survivor branch, or a promotion recommendation on the survivor branch.

---

# 57. Phase 0 — Repository / Contracts / Reproducibility Skeleton

## Deliverables

- repository;
- `uv` environment;
- CI;
- formatting/types/tests;
- domain contracts;
- canonical hashing;
- config hashing;
- artifact directories;
- SQLite dev metadata;
- basic CLI;
- reproducibility envelope.

## Acceptance criteria

- fresh clone → one command test;
- deterministic hash tests;
- candidate/data/config manifests serializable;
- CI on every commit;
- dependency lock committed;
- no production secrets in repo.

Do not build trading logic yet.

---

# 58. Phase 1 — Data Truth + Trial Ledger

## Deliverables

- TemporalObservation;
- LabelWindow;
- raw → normalized → PIT pipeline;
- DuckDB PIT queries;
- Parquet manifests;
- point-in-time universe;
- Pandera validation;
- immutable ledger;
- hash chain;
- study/hypothesis/candidate/trial entities.

## Acceptance criteria

- revised synthetic macro series returns correct vintage for arbitrary historical timestamp;
- feature available at 12:00:08 is inaccessible at 12:00:05;
- prefix-invariance test works;
- changing old ledger payload breaks chain verification;
- current BTC dataset can be imported into manifest model without altering source data.

---

# 59. Phase 2 — FastScreen + Baselines

## Deliverables

- vector target-exposure engine;
- basic fees/slippage/delay;
- benchmark strategies;
- deterministic metrics;
- cost attribution.

## Acceptance criteria

- analytical buy-and-hold golden case;
- known simple strategy matches independent reference;
- deterministic runs;
- transaction-cost monotonicity;
- next-bar timing tests.

Then port existing BTC strategy exactly and verify its existing benchmark.

---

# 60. Phase 3 — Core Falsification Stack

## Deliverables

- walk-forward;
- purged K-fold;
- CPCV;
- PBO;
- PSR/DSR;
- SPA/MCS;
- permutation/placebo;
- parameter stability;
- ablation;
- regime diagnostics;
- delay/cost curves;
- power/UNDERPOWERED verdict.

## Acceptance criteria

- null-world calibration suite;
- planted weak edge suite;
- deliberately leaky strategies rejected;
- internal metrics differential-tested against purgedcv/arch;
- no candidate can skip search accounting.

This is the first major go/no-go point.

---

# 61. Phase 4 — Independent Referees + Sealed Holdout

## Deliverables

- Penrose export adapter;
- Nullius adapter;
- referee disagreement handling;
- sealed holdout separate process;
- one-use holdout leases;
- signed holdout receipts.

## Acceptance criteria

- research process cannot read holdout files;
- same candidate can consume holdout once only;
- post-result edit changes hash and is rejected;
- referee disagreement returns MODEL_RISK.

At this point the research MVP is scientifically meaningful.

---

# 62. Phase 5 — Typed DSL + Hypothesis Generation

## Deliverables

- typed DSL;
- safe parser;
- canonical AST;
- operator metadata;
- complexity score;
- AST novelty;
- semantic hypothesis structure;
- LLM → hypothesis → DSL tool;
- family lineage.

## Acceptance criteria

- future operators impossible;
- full-sample operators impossible unless explicitly research-only;
- invalid type expressions rejected;
- structurally duplicate candidate linked to existing family;
- AI cannot emit executable arbitrary code through DSL route.

---

# 63. Phase 6 — Knowledge-Grounded Agent Research

## Deliverables

- document ingestion;
- mechanism extraction;
- paper/mechanism graph;
- research retrieval;
- generator types;
- frozen candidate batches;
- generator benchmark.

## Acceptance criteria

- every hypothesis cites mechanism/source or is explicitly tagged exploratory;
- LLM cannot grade its own sealed result;
- generator cost/trials/survivors tracked;
- random baseline generator included.

---

# 64. Phase 7 — Model Lab + Portfolio Construction

## Deliverables

- ModelAdapter;
- LightGBM/sklearn baseline;
- forecast metrics;
- calibration;
- skfolio adapter;
- constraints;
- marginal portfolio contribution.

## Acceptance criteria

- model evaluation separate from trading PnL;
- training/calibration use no test data;
- portfolio optimizer respects constraints;
- candidate can be rejected despite strong standalone Sharpe if marginal portfolio value is poor.

---

# 65. Phase 8 — Nautilus Execution Validation

## Deliverables

- QuantLab ↔ Nautilus contracts;
- BAR/L1/L2 profiles;
- fee/latency models;
- VenueSpec mapping;
- golden execution tapes;
- batch candidate replay.

## Acceptance criteria

- identical candidate logic reused;
- fill/accounting parity tests pass;
- version pinned;
- strategy report exposes execution assumptions.

Do not deploy real money.

---

# 66. Phase 9 — HftBacktest + Market-Making Validation

## Deliverables

- common L2/L3 tape adapter;
- MM controller;
- Nautilus replay;
- HftBacktest replay;
- discrepancy report;
- queue/latency calibration hooks.

## Acceptance criteria

- same deterministic toy tape produces explainable fills in both;
- material disagreements block candidate;
- Polymarket/venue-specific queue/fee assumptions explicit.

---

# 67. Phase 10 — Shadow Runtime + Event Journal + Risk Supervisor

## Deliverables

- live data;
- zero-capital decisions;
- Risk Supervisor;
- event journal;
- latency telemetry;
- replay;
- deployment manifest signing.

## Acceptance criteria

- no research process holds exchange credentials;
- unsigned strategy cannot run;
- risk kills strategy even if strategy process hangs/misbehaves;
- shadow session is replayable.

---

# 68. Phase 11 — Canary / Champion-Challenger

## Deliverables

- canary sizing policy;
- challenger shadows;
- live-vs-sim comparison;
- automatic downgrade alerts;
- manual promotion workflow.

## Acceptance criteria

- challenger cannot auto-promote;
- allocation bounded;
- risk rules independent;
- live telemetry feeds research only as a new versioned dataset.

---

# 69. First Real Benchmark — Existing BTC Research

Do this before building expensive execution infrastructure.

*Revision 1.1: this benchmark is now operationalized as Phase -1 (inserted before §57) — run with off-the-shelf tools (purgedcv/Nullius/Penrose) on existing research artifacts, before any QuantLab platform code exists. The candidate classes and stop conditions below apply there.*

## Dataset

Use existing historical BTC/crypto research dataset with:

- price;
- current trend signals;
- on-chain/flow features;
- any semantic/social features already available;
- realistic availability timestamps where possible.

## Candidate classes

1. current strongest existing rule;
2. known failed strategies;
3. intentionally leaky versions;
4. random strategies;
5. simple literature-grounded candidates;
6. LLM-generated DSL candidates.

## Questions

1. Can QuantLab reproduce current results?
2. Does it detect intentional leaks?
3. Does it reject known garbage?
4. Does it retain anything believed to be robust?
5. Does it find new candidates?
6. Do those candidates survive sealed OOS?
7. Does the AI generator outperform random/GP/human baselines in credible survivors per trial?

## Stop condition

If the validator cannot distinguish known nulls from planted/known weak edges, do not proceed.

If AI-generated candidates do not outperform simpler baselines after proper selection correction, retain the validator but abandon elaborate autonomous generation.

---

# 70. Initial Baseline Strategy Test Matrix

Include:

```text
Buy & Hold
Cash
SMA trend
Dual SMA trend
Momentum
Mean reversion
Random signal
Random persistent signal
Future-leaked signal
Full-sample-normalized signal
Existing BTC rule
```

For every one, store expected qualitative result.

---

# 71. Research Budget Policy

Every study declares limits:

```text
max candidates
max optimizer trials
max LLM calls
max CPU
max GPU
max cost
```

No agent may silently expand the budget because results look close.

A new budget requires a new study amendment in the ledger.

---

# 72. Cost Accounting

Track per experiment:

- LLM tokens/cost;
- CPU seconds;
- GPU seconds;
- data vendor cost allocation;
- simulator compute;
- storage.

Use in generator meta-analysis:

```text
credible_survivors / $100
credible_survivors / 1k trials
```

---

# 73. Data Leakage Checklist for Every New Feature

Engineer must answer:

1. When did the real-world event happen?
2. When was it publicly published?
3. When could our source have delivered it?
4. When did our pipeline ingest it?
5. Is it revised later?
6. What lag/rolling window does it use?
7. Is normalization fit only on history?
8. Is universe membership PIT?
9. Could a missing-value fill import future information?
10. Can prefix invariance detect a violation?

Feature does not enter production research until checklist passes.

---

# 74. Strategy Review Checklist

Before promotion:

## Economics

- What mechanism creates edge?
- Why should it persist?
- Who is likely on the other side?
- Why is it not arbitraged away?
- What capacity/crowding risk exists?

## Data

- PIT?
- revisions?
- source quality?
- survivorship?
- missingness?
- latency?

## Statistics

- trials?
- DSR?
- PBO?
- SPA?
- power?
- parameter stability?
- regime stability?

## Execution

- fees?
- spread?
- slippage?
- latency?
- queue?
- funding?
- market impact?

## Portfolio

- correlation?
- marginal contribution?
- concentration?
- turnover?

## Operational

- failure behavior?
- stale feed?
- kill switch?
- reconciliation?

---

# 75. AI Coding Task Contract Template

Every coding-agent assignment should look like:

```text
TITLE:
Implement TemporalObservation PIT selector

OBJECTIVE:
Return the latest observation legally available at query_time while preserving revisions.

CONTEXT:
- canonical contract: src/quantlab/contracts/temporal.py
- data store: DuckDB
- timestamps are UTC

ALLOWED FILES:
- src/quantlab/data/pit/*
- tests/unit/data/*
- tests/property/data/*

INVARIANTS:
- observation with available_time > query_time must never be returned
- later revisions must not leak backward
- deterministic ordering
- no mutation of raw data

REQUIRED TESTS:
1. basic retrieval
2. multiple revisions
3. equal timestamps
4. missing observation
5. property test over random revision timelines
6. planted future-revision leak must fail

DELIVERABLE:
- implementation
- tests
- short design note

DO NOT:
- modify unrelated modules
- add dependencies without approval
- weaken assertions to pass tests
```

Use small, bounded tasks rather than “build QuantLab.”

---

# 76. Definition of Done for Any Module

A module is not done when code compiles.

Required:

- typed public API;
- docstring/README;
- unit tests;
- property/metamorphic test if relevant;
- negative/failure tests;
- deterministic behavior documented;
- dependency/license check;
- performance benchmark if hot path;
- logging/metrics where operational;
- migration/backward compatibility if persisted state changes.

---

# 77. Pull Request Review Template

Every PR should state:

```text
Problem
Design
Alternatives considered
Data/research invariants affected
New dependencies
New failure modes
Tests
Reproducibility impact
Performance impact
Security impact
License impact
```

For statistical code additionally:

```text
Reference paper/formula
Independent implementation checked against
Synthetic null test
Synthetic positive-control test
```

---

# 78. Versioning

Version separately:

```text
QuantLab core
Data schema
DSL
Validation policy
VenueSpec
Risk policy
Execution model
Deployment manifest schema
```

Research results must reference exact versions.

---

# 79. Upgrade Policy

No “pip install -U” on production environments.

Dependency upgrades:

1. branch;
2. lock update;
3. CI;
4. null calibration;
5. golden strategies;
6. execution parity if relevant;
7. explicit merge.

---

# 80. Backup / Recovery

Back up:

- PostgreSQL;
- Trial Ledger;
- manifests;
- signed deployment manifests;
- event journals;
- source code;
- configuration;
- signing public keys.

Raw market data can be reacquired only if source guarantees exist; otherwise back it up too.

Restore drills should verify ledger chain.

---

# 81. Secrets

Keep separate:

```text
RESEARCH environment:
  LLM key maybe
  no exchange keys

HOLDOUT service:
  holdout storage credentials
  no exchange keys

EXECUTION:
  exchange credentials
  deployment public key
  no LLM keys

SIGNER:
  deployment private key
  no exchange credentials
```

Use least privilege.

---

# 82. Polymarket/Prediction-Market Edge Families to Support

Examples to design for, not assumptions of profitability:

- cross-market logical consistency;
- complementary-outcome parity;
- related-event conditional consistency;
- model-vs-market fair probability;
- latency of external information incorporation;
- market-making spread capture;
- inventory-controlled quoting;
- cross-venue hedge;
- resolution-risk discount;
- fee/rebate microstructure.

Each family must have custom nulls and execution stress.

---

# 83. Directional Crypto Edge Families to Support

- trend;
- carry/funding;
- cross-sectional momentum;
- volatility/risk premium;
- flow/on-chain;
- ETF/exchange flow;
- semantic/social;
- macro interactions;
- liquidity;
- basis;
- relative value;
- regime-conditioned combinations.

The framework must not privilege technical upstreams over other data classes.

---

# 84. Semantic / Social Feature Special Rules

Semantic data has unique leakage risk.

Store:

```text
original content ID
content publish time
crawl receive time
model start time
model completion time
model version
prompt hash
output
```

The semantic score’s availability is no earlier than model completion.

If historical content was collected later from an archive, do not pretend it was available live unless historical delivery latency is modeled.

---

# 85. LLM Feature Reproducibility

LLM outputs can change across versions/providers.

For generated research artifacts store:

- model provider;
- model identifier;
- exact prompt;
- system prompt hash;
- temperature;
- seed if supported;
- response hash;
- raw response artifact.

For semantic features in historical research, freeze the generated feature dataset. Do not expect API reruns to reproduce byte-identical outputs.

---

# 86. Causal Analysis

Causal tools may be useful for:

- confounder identification;
- sensitivity analysis;
- mechanism testing.

They cannot turn observational trading data into guaranteed causal truth.

Any causal conclusion must state assumptions.

Causal diagnostics are advisory, not automatic promotion gates.

---

# 87. Model Uncertainty

Optional conformal/uncertainty tooling can be used, but financial nonstationarity often violates standard exchangeability assumptions.

Always:

- test coverage over time/regimes;
- report empirical coverage;
- do not rely on theoretical guarantee if assumptions fail.

---

# 88. Regime Modeling

Prefer prospective features:

- realized vol;
- trend;
- spread/liquidity;
- funding;
- macro state available at time.

If using hidden-state/cluster model, simulate online fitting.

Never classify all history with a full-sample model and then claim that regime was observable at the time.

---

# 89. Handling Multiple Horizons

A factor can be useful at 5m and useless at 1d.

Each hypothesis declares horizon.

Search history should distinguish meaningful horizon families but prevent trivial reset by testing adjacent horizons repeatedly.

LabelWindow must match horizon exactly.

---

# 90. Missing Data Policy

Every feature defines allowed missing behavior:

```text
ERROR
DROP_SAMPLE
FORWARD_FILL(max_age)
ZERO_IS_MEANINGFUL
MODEL_IMPUTE
```

No global blanket `fill_null(0)`.

Imputation model itself must be PIT and trained on historical data only.

---

# 91. Corporate/Instrument Lifecycle

If later extended beyond crypto:

- splits/dividends;
- mergers;
- symbol changes;
- delistings;
- survivorship;
- point-in-time fundamentals;
- holiday/session calendars.

Architecture must support them even if initial MVP focuses on crypto.

---

# 92. Time Synchronization

Live host must monitor clock offset.

Use NTP/PTP appropriate to strategy latency needs.

Event journal stores monotonic local time in addition to wall-clock UTC where relevant.

Clock drift above policy threshold can trigger degradation/pause for latency-sensitive strategies.

---

# 93. Market-Impact Honesty

Never report simulated PnL as if our hypothetical historical orders would not have changed the market.

Capacity report must explicitly state:

```text
historical replay assumes exogenous historical market path
impact is modeled, not observed
```

The best evidence comes from canary/live fills.

---

# 94. Research UI — Later

Do not build UI until CLI and data contracts stabilize.

When built, prioritize:

- lineage graph;
- study/trial table;
- “why killed?” explanations;
- holdout state;
- sensitivity curves;
- execution discrepancy;
- live-vs-sim;
- risk state.

Avoid gamified “top Sharpe leaderboard” as primary view.

---

# 95. Report Format

Every candidate gets machine JSON plus human Markdown.

Suggested report:

```text
1. Hypothesis
2. Data provenance
3. Search history
4. Forecast skill
5. Economic performance
6. Validation
7. Multiple-testing evidence
8. Robustness
9. Independent referees
10. Execution assumptions
11. Capacity
12. Portfolio contribution
13. Known failure modes
14. Verdict
15. Next action
```

---

# 96. Candidate Promotion Is a State Machine

```text
DRAFT
GENERATED
SCREENED
VALIDATED
REFEREED
FROZEN
CONFIRMED
PORTFOLIO_APPROVED
EXECUTION_VALIDATED
SHADOW
CANARY
ACTIVE
DEGRADED
QUARANTINED
RETIRED
REJECTED
```

Illegal transitions must raise errors.

Example:

```text
GENERATED → LIVE
```

is impossible.

---

# 97. Research Integrity Audit Command

Implement:

```bash
quantlab audit study STUDY_ID
```

Report:

- missing trials;
- modified artifacts;
- ledger chain;
- candidate family counts;
- holdout access;
- config inconsistencies;
- missing hashes;
- unsupported dependency version;
- unresolved data-quality warnings.

---

# 98. Emergency Operational Procedures

Document:

## Feed outage
- stop new orders;
- cancel passive orders where stale quote risk exists;
- reconcile when feed returns.

## Exchange API outage
- stop strategy;
- use alternate monitoring channel if available;
- no blind retries beyond bounded policy.

## Reconciliation mismatch
- disable trading;
- fetch authoritative account state;
- repair manually/automatically under controlled procedure.

## Risk service outage
Fail closed for new risk.

## Signer outage
Existing approved runtime may continue under policy; no new deployment.

---

# 99. Data Retention

Keep indefinitely if feasible:

- research metadata;
- ledger;
- manifests;
- signed candidate/deployment records;
- null calibration results.

Market data retention based on cost/rights.

For expensive L2/L3, prioritize periods used by production candidates and live sessions.

---

# 100. What Not to Optimize Early

Do not optimize:

- dashboard design;
- distributed compute;
- microservice count;
- generalized plugin system;
- every exchange;
- arbitrary asset classes;
- GPU cluster;
- multi-user RBAC.

Optimize:

- correctness;
- data lineage;
- leak resistance;
- experiment accounting;
- reproducibility;
- scientific calibration.

---

# 101. P0 Engineering Backlog

The following tickets are blocking for the research MVP. **Revision 1.1: the entire P0 backlog is gated behind the Phase -1 existence test** — do not start P0 work until Phase -1 produces at least one credible survivor, or a well-diagnosed zero-survivor conclusion that identifies hypothesis/data acquisition (not platform) as the next investment.

### P0-001 Repository scaffold
### P0-002 Pydantic contract package
### P0-003 canonical JSON hashing
### P0-004 config hashing
### P0-005 SQLite/Postgres metadata schema
### P0-006 Alembic migrations
### P0-007 TemporalObservation
### P0-008 LabelWindow
### P0-009 DatasetManifest
### P0-010 Parquet catalog
### P0-011 DuckDB query layer
### P0-012 PIT revision selector
### P0-013 PIT universe selector
### P0-014 Pandera OHLCV schema
### P0-015 social/semantic temporal schema
### P0-016 data-quality report
### P0-017 append-only ledger
### P0-018 ledger hash chain verifier
### P0-019 Study model
### P0-020 HypothesisFamily model
### P0-021 Hypothesis model
### P0-022 Candidate model
### P0-023 Trial model
### P0-024 lineage DAG
### P0-025 FastScreen exposure engine
### P0-026 FastScreen cost model
### P0-027 benchmark metrics
### P0-028 baseline strategies
### P0-029 existing BTC strategy adapter
### P0-030 walk-forward adapter
### P0-031 purged K-fold adapter
### P0-032 CPCV adapter
### P0-033 PSR/DSR adapter
### P0-034 PBO adapter
### P0-035 arch SPA adapter
### P0-036 parameter-neighborhood tester
### P0-037 cost stress
### P0-038 delay stress
### P0-039 ablation framework
### P0-040 null-world generators
### P0-041 planted-edge generator
### P0-042 prefix-invariance detector
### P0-043 future-leak red-team fixtures
### P0-044 power/UNDERPOWERED logic
### P0-045 EvidenceBundle
### P0-046 deterministic verdict engine
### P0-047 reproduce command
### P0-048 study audit command
### P0-049 statistical calibration CI suite
### P0-050 research MVP report generator

Completion of P0 answers whether the core project is worth continuing.

---

# 102. P1 Engineering Backlog

### P1-001 Penrose adapter
### P1-002 Nullius adapter
### P1-003 referee discrepancy policy
### P1-004 holdout storage partition
### P1-005 holdout service credentials
### P1-006 CandidateManifest
### P1-007 single-use holdout lease
### P1-008 signed holdout receipt
### P1-009 typed DSL base types
### P1-010 operator registry
### P1-011 parser
### P1-012 canonical AST
### P1-013 compiler to Polars
### P1-014 complexity metric
### P1-015 AST novelty
### P1-016 semantic similarity
### P1-017 family assignment engine
### P1-018 hypothesis generator tool
### P1-019 candidate batch preregistration
### P1-020 LLM run metadata
### P1-021 generator benchmark framework
### P1-022 knowledge document ingestion
### P1-023 mechanism extraction
### P1-024 knowledge graph
### P1-025 negative-result memory
### P1-026 Optuna trial bridge
### P1-027 research cost accounting
### P1-028 model adapter base
### P1-029 LightGBM adapter
### P1-030 forecast evaluation
### P1-031 calibration
### P1-032 skfolio adapter
### P1-033 portfolio constraint model
### P1-034 portfolio marginal-value report

---

# 103. P2 Engineering Backlog

### P2-001 Nautilus adapter
### P2-002 BacktestVenue profile builder
### P2-003 VenueSpec
### P2-004 effective-dated fees
### P2-005 latency model registry
### P2-006 execution golden tapes
### P2-007 L2 catalog ingestion
### P2-008 queue simulation config
### P2-009 liquidity consumption config
### P2-010 execution evidence report
### P2-011 HftBacktest adapter
### P2-012 common tape exporter
### P2-013 execution discrepancy report
### P2-014 MM controller contract
### P2-015 inventory controller
### P2-016 Polymarket market model
### P2-017 Hyperliquid market model
### P2-018 capacity stress engine
### P2-019 live data service
### P2-020 signed DeploymentManifest
### P2-021 risk policy engine
### P2-022 capability token
### P2-023 execution service
### P2-024 live event journal
### P2-025 replay command
### P2-026 latency telemetry
### P2-027 shadow runner
### P2-028 canary policy
### P2-029 champion/challenger
### P2-030 drift/decay state machine

---

# 104. Recommended First Pull Requests

Keep early PRs tiny.

1. repo + toolchain;
2. IDs + canonical hashing;
3. TemporalObservation + tests;
4. LabelWindow + overlap property tests;
5. DatasetManifest;
6. DuckDB PIT selector;
7. future-revision leak tests;
8. Trial Ledger;
9. hash-chain verification;
10. FastScreen basic exposure;
11. buy-and-hold golden test;
12. existing BTC baseline;
13. purgedcv wrapper;
14. Null-world test;
15. planted-leak test.

Do not start with AI agents.

---

# 105. Go / No-Go Checkpoints

## Checkpoint 0 — Empirical existence (Phase -1, added Revision 1.1)

Proceed to Phase 0 only if the frozen-universe falsification spike on existing data either (a) produces at least one credible survivor, or (b) produces a diagnosed zero-survivor conclusion whose remediation is hypothesis/data acquisition — in which case fund that, not platform work. If the validator itself fails calibration (cannot kill nulls, misses the planted leak, cannot emit UNDERPOWERED), halt and fix the harness.

## Checkpoint A — Data integrity

Proceed only if PIT and leakage tests are reliable.

## Checkpoint B — Statistical calibration

Proceed only if null worlds mostly die and planted weak edges can survive at reasonable power.

## Checkpoint C — Current strategy audit

Proceed only if the system can reproduce and intelligently challenge existing research.

## Checkpoint D — AI generation

Proceed only if constrained AI research produces more credible survivors than random/simple search.

## Checkpoint E — Execution

Proceed to live infrastructure only after at least one research-supported candidate survives sealed OOS and realistic costs.

---

# 106. What “Best of the Best” Means Here

It does **not** mean putting every available library into the same repository.

It means assigning one strong component to one responsibility and preserving independent critics.

Final responsibility map:

```text
Data truth              → QuantLab
Hypothesis generation   → QuantLab agents + literature graph
Factor representation   → QuantLab typed DSL
Search scheduling       → Optuna / custom generators
Experiment truth        → QuantLab Trial Ledger
Fast elimination        → QuantLab FastScreen
Temporal CV             → purgedcv + QuantLab policies
Multiple comparison     → arch + QuantLab family accounting
Portfolio               → skfolio
Internal falsification  → QuantLab
External referee        → Penrose
Leak/reference referee  → Nullius
Execution truth         → NautilusTrader
HFT/MM second oracle    → HftBacktest
Live risk               → QuantLab independent supervisor
Deployment authority    → signed QuantLab manifest
AI                      → proposer/builder, never judge+jailer+trader
```

---

# 107. Final Engineering Principle

When faced with a design choice, prefer the option that makes a false edge harder to promote even if it makes research slower.

The project’s core competitive advantage is not faster backtests.

It is this:

```text
AI creates hypotheses faster than humans
                    +
the system distrusts AI more rigorously than humans normally do
                    =
high research throughput without unrestricted p-hacking
```

If that premise proves empirically useful on the existing crypto research dataset, expand the system.

If it does not, stop.

---

# 108. Verified Source / Reference Map (snapshot: 2026-09-23)

These are the main external components and ideas used in this specification. Versions and APIs must be rechecked before implementation upgrades.

## Execution and simulation

- NautilusTrader repository:
  https://github.com/nautechsystems/nautilus_trader
- NautilusTrader releases:
  https://github.com/nautechsystems/nautilus_trader/releases
- Nautilus backtesting:
  https://nautilustrader.io/docs/latest/concepts/backtesting/
- Nautilus data/venue granularity:
  https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/
- Nautilus trade execution / queue position:
  https://nautilustrader.io/docs/latest/concepts/backtesting/trade-execution/
- Nautilus fill models:
  https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models/
- Nautilus behavioral models:
  https://nautilustrader.io/docs/latest/concepts/behavioral_models/
- HftBacktest:
  https://github.com/nkaz001/hftbacktest
  https://hftbacktest.readthedocs.io/

## Research workflow / agentic quant

- Investing Algorithm Framework:
  https://github.com/coding-kitties/investing-algorithm-framework
- Microsoft RD-Agent:
  https://github.com/microsoft/RD-Agent
- Microsoft RD-Agent(Q) paper page:
  https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/
- AlphaAgent:
  https://github.com/toininoi/alphaagent
  https://doi.org/10.1145/3711896.3736838
- QuantaAlpha:
  https://github.com/QuantaAlpha/QuantaAlpha
  https://arxiv.org/abs/2602.07085
- AlphaEvo:
  https://github.com/Zangir/AlphaEvo
- Alpha Factor Agents:
  https://github.com/lucawuerker/alpha-factor-agents

## Statistical validation / falsification

- purgedcv:
  https://github.com/eslazarev/purged-cross-validation
  https://pypi.org/project/purgedcv/
- arch SPA / Reality Check / MCS:
  https://bashtage.github.io/arch/devel/multiple-comparison/multiple-comparison-reference.html
- Penrose:
  https://github.com/PattersonResearch/Penrose
  https://www.penrose.systems/docs/
- Nullius:
  https://github.com/blu3c0ral/nullius
- skfolio:
  https://github.com/skfolio/skfolio
  https://skfolio.org/user_guide/model_selection.html
- Freqtrade lookahead analysis (idea/reference only):
  https://www.freqtrade.io/en/stable/lookahead-analysis/
- Freqtrade recursive analysis:
  https://www.freqtrade.io/en/stable/recursive-analysis/

## Search and portfolio

- Optuna:
  https://optuna.org/
  https://optuna.readthedocs.io/
- skfolio optimization:
  https://skfolio.org/user_guide/optimization.html

## Data / tooling

- Polars:
  https://pola.rs/
- DuckDB:
  https://duckdb.org/
- DuckDB ASOF join:
  https://duckdb.org/docs/stable/sql/query_syntax/from
- Pandera:
  https://pandera.readthedocs.io/
- MLflow:
  https://mlflow.org/docs/latest/
- Feast (optional):
  https://feast.dev/

## Market-making architecture inspiration

- Hummingbot Controllers:
  https://hummingbot.org/strategies/v2-strategies/controllers/

---

# 109. Final Build Instruction to the Engineer / Coding Agent

Do **not** start by implementing the full directory tree.

Start at Phase -1 and only create modules needed by the next acceptance test. Phase -1 runs the empirical existence test with off-the-shelf tools on existing research artifacts — the vertical slice below is executed in zero-platform form (purgedcv + Nullius + reference math + a flat trial table) before any QuantLab module exists.

Every implementation step must answer:

1. What invariant does this enforce?
2. What false-positive research failure does it prevent?
3. What independent test proves the detector itself works?
4. What artifact is written to the Trial Ledger?
5. Can the result be reproduced from a clean checkout?
6. Does this increase the attack surface or license burden?
7. Is this required before the next empirical go/no-go checkpoint?

The first complete vertical slice must be:

```text
existing BTC dataset
    ↓
immutable PIT manifest
    ↓
existing strategy + several null strategies
    ↓
FastScreen
    ↓
Trial Ledger
    ↓
walk-forward + purged CV + CPCV
    ↓
DSR/PBO/SPA
    ↓
Nullius/Penrose cross-check
    ↓
sealed OOS
    ↓
evidence report
```

Only after this slice proves that the research process gives useful information should the project proceed to autonomous hypothesis generation or live execution. Under Revision 1.1, the slice's *logic* is mandatory but its first execution is zero-platform — platform components (immutable manifest, FastScreen, hash-chained ledger, sealed holdout) are built in Phase 0+ only if Phase -1 justifies them.

That sequence is mandatory.

---

# 110. Final Definition of the Product

QuantLab OS is a system that:

> **generates financial hypotheses aggressively, records every search honestly, attacks each apparent edge with independent falsification, protects truly unseen data from adaptive research, models execution conservatively, and allows only immutable validated artifacts to reach independently controlled capital.**

That is the product.

Everything else is implementation detail.

---

# 111. Revision 1.1 — Critical Design Review Errata (2026-09-24)

An adversarial review of this specification (v1.0) was conducted before implementation. Findings and dispositions:

## Accepted findings

1. **The empirical go/no-go gate was too late.** v1.0 placed the first major go/no-go after Phase 0 (contracts/reproducibility), Phase 1 (PIT data + ledger), Phase 2 (FastScreen), and Phase 3 (full falsification) — substantial platform engineering before any empirical answer. **Fix:** Phase -1 inserted (see before §57). The existence test now runs first, on existing artifacts, with off-the-shelf tools.

2. **Data scarcity is a fundamental wall.** CPCV/PBO/DSR/SPA control false-discovery rate and use limited history efficiently; they do not create independent samples or regimes. Thin data yields honestly-calibrated UNDERPOWERED/REJECT — useful, but zero tradeable output. **Fix:** sample adequacy is now the *first* test inside Phase -1 (power gate before evaluation), and the zero-survivor branch explicitly routes to data-acquisition rather than architecture.

3. **Penrose duplication.** Penrose's current scope — search-family accounting, search-size-aware PSR/DSR, single-use locked holdout, power verdicts, purged CV, placebo/null calibration, hash-chained audit events — covers most of what v1.0 assigned to owned components. **Fix:** use-before-build policy adopted; owned implementations only for concrete named gaps. The QuantLab *lineage* ledger (hypothesis → family → data version → generator → code → execution model → live outcome) remains justified because it tracks provenance beyond referee scope, but is a flat table until Phase 1.

4. **Hypothesis quality is the bottleneck, not validation quality.** If inputs are weak hypotheses + commodity data + crowded horizons, the finest falsification stack produces high-quality rejection reports. **Fix:** QuantLab earns further investment only when (a) an existing hypothesis survives stronger validation, or (b) evidence shows better hypothesis/data generation meaningfully increases candidate quality.

5. **Venue realism / thin L2.** Weeks of order-book history cannot support market-making validation across regimes. **Fix:** Nautilus, HftBacktest, MM, and Polymarket profiles are removed from the MVP path entirely (already late-phase; now explicitly gated on a surviving candidate that requires them).

## Partially accepted / corrected

6. **"Zero survivors measured zero alpha" is an overclaim.** N tested families failing bounds the tested hypothesis space on the tested data under the tested protocol — it does not prove the venue has no exploitable alpha (cross-sectional, conditional interactions, other horizons, cross-venue, flow/event-driven, maker economics may remain untested). Record conclusions at the correct scope.

7. **Data scarcity is feature-dependent, not global.** Price/trend hypotheses may have years of usable history even where venue-specific feeds (funding ~90d, L2 ~weeks) are thin. Power gates apply per candidate per feature — never a global "data is thin" verdict.

## Net effect on the plan

```text
v1.0:  Phase 0 → 1 → 2 → 3 → [first real go/no-go] → ...
v1.1:  Phase -1 (existence test, zero platform) → diagnosed branch → Phase 0 only if earned
```

The 114-ticket P0/P1/P2 backlog is unchanged in content but is now correctly gated: it begins only after the cheap empirical question is answered.
