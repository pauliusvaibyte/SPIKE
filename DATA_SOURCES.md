# Data sources inventory — what's obtainable, what's blocked, what costs money

Audited 2026-09-23 by live API probing + vendor docs review.

## Free, in use (data_extended/)

| source | endpoint/method | depth obtained | status |
|---|---|---|---|
| HL `fundingHistory` | POST /info, 500 rows/call paginated | Jun 2023 -> now (~3.3y, ~28.9k rows/coin) x **7 coins** (BTC,SOL,ETH,XRP,DOGE,AVAX,LINK — expanded 2026-09-23 for round 6) | DONE |
| HL `candleSnapshot` | POST /info nested `req`, ~5000-bar lookback cap | 1d: full; 4h: 833d; 1h: 208d; 15m: 52d — x7 coins | DONE |
| Binance USD-M REST | fapi.binance.com, no key | funding since 2019, **1d+4h klines full-history (2019/2020 listing → now, ~2.2–2.6k d-bars/coin)**, **premiumIndexKlines 1d (~2.2–2.5k rows, mark-index basis)**, 1h klines 2y, OI/taker ~21-30d — x7 USDT perps | DONE |
| Sentinely harmony warehouse | `tools/export_harmony_extended.py` → `data_extended/harmony/harmony_extended.csv` | 59 cols / 6,107d: Bitstamp 2011+, Bitfinex 2013+, Coinbase 2015+, Binance spot 2017+, Bybit perp 2020+; Deribit funding 2019+; cross-venue funding aggregates; per-exchange OI; liquidations USD 2022-12+; DVOL 2021+; ATM IV + 25Δ skew (all tenors); MVRV/NUPL/SOPR-family/realized metrics; exchange balances; hashrate; F&G | DONE (follows upstream weekly harvest) |
| CoinMetrics community API | `tools/backfill_coinmetrics.py` (per-metric requests; curl subprocess — Cloudflare blocks urllib TLS) | btc_metrics_daily 2009-01-03 → 2026-09-22: priceusd, **flowin/flowoutexusd (N-leg UNFROZEN — was static 09-06 CSV)**, capmvrvcur, capmrktcurusd, adractcnt, txcnt, hashrate, splycur | DONE; paid metrics (sopr, nvtadj, caprealusd) probed & loudly skipped |

## Free but requires AWS credentials — BLOCKED PENDING USER SETUP

| source | contents | blocker |
|---|---|---|
| `s3://hyperliquid-archive` | L2 book snapshots `market_data/[date]/[hour]/l2Book/[coin].lz4`, `asset_ctxs` (funding/OI/mark) | requester-pays bucket: needs AWS account + awscli + lz4. Anonymous GET = 403 (verified) |
| `s3://hl-mainnet-node-data` | `node_fills_by_block` (all trades since Jul 2025), `node_raw_book_diffs_by_block` (Jan 2026+), `misc_events_by_block` (funding events) | same requester-pays creds; ~372GB full — targeted slices only |

To unblock: `aws configure` with any AWS account, `pip install lz4` or CLI lz4, then
targeted `aws s3 cp s3://hyperliquid-archive/market_data/<date>/<hour>/l2Book/BTC.lz4`
requests (~MBs per hour-file, bandwidth-billed).

## Paid / freemium (evaluated, not purchased)

| vendor | coverage | notes |
|---|---|---|
| 0xarchive.io | HL L2 order books Apr 2023+ (20-level, ~1.2s), trades, funding/OI May 2023+, liquidations BTC/ETH Jul 2025+, L4 order-level Mar 2026+ | turnkey REST + Parquet; would resolve OFI immediately. Pricing: check 0xarchive.io |
| Tardis.dev | HL since Oct 2024: incremental_book_L2, trades, derivative_ticker; fastBook (5-level, ~500ms) since Jun 2026 | free first-of-month sample CSVs without key; bulk = paid |

## Not obtainable (any price, public)

- Hyperliquid pre-launch anything (venue didn't exist before mid-2023)
- True tick-level mainnet book history before Oct 2024 (Tardis start) without 0xarchive
- Historical account positioning / long-short ratios on HL (not published)

## Live collection (bot, running untouched)

- funding journal ~hourly; L2 journal raised to per-cycle 5min 2026-09-23
  (dormant until daemon restart); OI + liquidation journals accruing.
- Shadow challenger journal: forward evidence for FRA-momentum (now moot as
  forward promotion evidence — round-2 KILL — but still worth collecting as
  forward-monitoring data).
