# Harmony systematic screen — two-stage with holdout

Universe: 5488 numeric columns of harmony_master_clean (2010-01-01 -> 2026-09-20).
Signal lagged 1d. Return open-to-open. Discovery <=2024-12-31,
holdout >=2025-01-01. BH-FDR q=0.1; holdout needs same-sign IC + p<0.1. Caveat: provider publication lag (FRED/BIS)
not modeled — treat confirmed FRED hits as leads requiring a
lag-shifted re-declaration before any family is built.

## horizon 21d — tested 4576, FDR-pass 3565, CONFIRMED 2052

| column | ic_disc | p_disc | ic_hold | p_hold | status |
|---|---|---|---|---|---|
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2019-20_bear | -0.5839 | 3.38e-44 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_1 | -0.4978 | 4.37e-32 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_5 | -0.4915 | 4.36e-31 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2018-19_bear | -0.4834 | 1.25e-35 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_10 | -0.4760 | 1.02e-28 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__price | -0.4699 | 8.92e-28 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__trace | -0.4699 | 8.92e-28 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__best_1 | -0.4656 | 3.13e-27 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__worst_5 | -0.4648 | 4.70e-27 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_2_etf_balance_2_light__arkb | -0.4485 | 4.19e-21 | +0.2662 | 2.00e-08 | fdr-pass,holdout-fail |
| defillama_chain_tvl_bsc__tvl_usd | -0.4316 | 1.02e-77 | -0.3269 | 1.88e-17 | **CONFIRMED** |
| coc_btconchain_etfs_etf_volume_etf_volume_light__spot_price | -0.4298 | 3.78e-19 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_volume_1w_etf_volume_1w_light__spot_price | -0.4298 | 3.78e-19 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flowsvsprice_etf_flowsvsprice_light__price_usd | -0.4294 | 4.15e-19 | -0.1625 | 8.07e-04 | **CONFIRMED** |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__price | -0.4276 | 3.17e-22 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__trace | -0.4276 | 3.17e-22 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__worst_1 | -0.4275 | 2.93e-22 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_2_etf_balance_2_light__btco | +0.4230 | 1.78e-18 | -0.3087 | 4.25e-11 | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__best_1 | -0.4004 | 3.12e-19 | +nan | nan | fdr-pass,holdout-fail |
| bgeo_archive_loss_lth__v1 | +0.3960 | 2.66e-17 | +0.1031 | 2.42e-02 | **CONFIRMED** |
| bgeo_report_bitcoin_halving_cycle_g__1st_halving | -0.3860 | 4.34e-52 | +nan | nan | fdr-pass,holdout-fail |
| bgeo_report_tmp__1st_halving | -0.3860 | 4.34e-52 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2013-15_bear | -0.3825 | 5.93e-28 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_1_etf_balance_1_light__arkb | -0.3810 | 9.73e-15 | -0.0244 | 6.20e-01 | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_mvrv_etf_mvrv_light__etf_mvrv | -0.3772 | 1.97e-14 | -0.0239 | 6.27e-01 | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_1_etf_balance_1_light__total_etf_aum | -0.3759 | 2.49e-14 | -0.2444 | 3.04e-07 | **CONFIRMED** |
| coc_extra_btconchain_capitalrotation_crypto_pricedingold_crypto_pricedingold_light__eth_xau | -0.3664 | 4.25e-60 | -0.2326 | 1.17e-06 | **CONFIRMED** |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__best_5 | -0.3634 | 1.20e-15 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_flows_1_1w_etf_flows_1_1w_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_etf_flows_0_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_mvrv_etf_mvrv_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__price_usd | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_profitloss_1_1d_etf_flows_profitloss_1_1d_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_1_etf_flows_1_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_profitloss_1_1w_etf_flows_profitloss_1_1w_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_1_1m_etf_flows_1_1m_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_1w_etf_flows_0_1w_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_1m_etf_flows_0_1m_light__price | -0.3620 | 1.39e-13 | -0.1633 | 7.57e-04 | **CONFIRMED** |
| coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__market_cap_change | -0.3580 | 2.77e-13 | -0.1660 | 6.14e-04 | **CONFIRMED** |
| coc_extra_btconchain_technical_price_minus_bestworst_2016-06-01_price_minus_bestworst_2016-06-01_light__worst_10 | +0.3576 | 3.62e-18 | +nan | nan | fdr-pass,holdout-fail |

## horizon 7d — tested 4576, FDR-pass 3218, CONFIRMED 1696

| column | ic_disc | p_disc | ic_hold | p_hold | status |
|---|---|---|---|---|---|
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2019-20_bear | -0.3857 | 5.27e-16 | +nan | nan | fdr-pass,holdout-fail |
| bgeo_archive_coinbase_premium__v1 | +0.3552 | 6.36e-28 | +0.2969 | 1.07e-14 | **CONFIRMED** |
| coc_btconchain_realised_realised_drawdowns_bull_realisedloss_realised_drawdowns_bull_realisedloss_light__2011-15_in_loss | +0.2984 | 2.63e-20 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_drawdowns_bull_technical_drawdowns_bull_light__2011-15_drawdown | +0.2979 | 1.89e-17 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__worst_5 | -0.2970 | 1.76e-10 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_2_etf_balance_2_light__btco | +0.2921 | 9.55e-09 | -0.1576 | 1.18e-03 | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_5 | -0.2906 | 4.41e-10 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_1 | -0.2901 | 4.71e-10 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2018-19_bear | -0.2802 | 4.53e-11 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__worst_10 | -0.2797 | 2.18e-09 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_rsi14_1d_technical_rsi14_1d_light__overbought | -0.2719 | 6.88e-16 | +nan | nan | fdr-pass,holdout-fail |
| bgeo_report_tmp__1st_halving | -0.2695 | 3.15e-24 | +nan | nan | fdr-pass,holdout-fail |
| bgeo_report_bitcoin_halving_cycle_g__1st_halving | -0.2695 | 3.15e-24 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__price | -0.2682 | 1.11e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__trace | -0.2682 | 1.11e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2019-01-01_price_minus_bestworst_2019-01-01_light__best_1 | -0.2681 | 1.09e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__price | -0.2671 | 1.34e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__trace | -0.2671 | 1.34e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_2_etf_balance_2_light__arkb | -0.2669 | 1.96e-07 | +0.1516 | 1.83e-03 | fdr-pass,holdout-fail |
| coc_btconchain_realised_realised_drawdowns_bull_realisedloss_realised_drawdowns_bull_realisedloss_light__genesis_to_2011_in_loss | +0.2666 | 7.25e-06 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_1_etf_balance_1_light__total_etf_aum | -0.2650 | 2.42e-07 | -0.1564 | 1.29e-03 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flowsvsprice_etf_flowsvsprice_light__price_usd | -0.2642 | 2.66e-07 | -0.0994 | 4.22e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_volume_etf_volume_light__spot_price | -0.2640 | 2.72e-07 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_volume_1w_etf_volume_1w_light__spot_price | -0.2640 | 2.72e-07 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_extra_btconchain_technical_technical_drawdowns_bear_technical_drawdowns_bear_light__2013-15_bear | -0.2615 | 7.25e-13 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__worst_1 | -0.2599 | 3.35e-08 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_entities_mstr_msty_mstr_msty_light__btc | -0.2564 | 2.90e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_extra_btconchain_entities_msty_strk_strf_yield_msty_msty_strk_strf_yield_msty_light__btc | -0.2564 | 2.90e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| defillama_chain_tvl_bsc__tvl_usd | -0.2539 | 1.35e-24 | -0.1867 | 2.31e-06 | **CONFIRMED** |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__best_1 | -0.2409 | 3.51e-07 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_etfs_etf_balance_1_etf_balance_1_light__arkb | -0.2405 | 3.22e-06 | -0.0387 | 4.31e-01 | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_technical_drawdowns_bull_technical_drawdowns_bull_light__genesis_to_2011_drawdown | +0.2384 | 6.88e-05 | +nan | nan | fdr-pass,holdout-fail |
| coc_extra_btconchain_technical_price_minus_bestworst_2021-11-01_price_minus_bestworst_2021-11-01_light__worst_10 | -0.2349 | 7.08e-07 | +nan | nan | fdr-pass,holdout-fail |
| coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__market_cap_change | -0.2343 | 4.37e-06 | -0.1021 | 3.68e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_1_1w_etf_flows_1_1w_light__price | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_mvrv_etf_mvrv_light__price | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_1w_etf_flows_0_1w_light__price | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_etf_flows_0_light__price | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_etfs_etf_flows_0_1m_etf_flows_0_1m_light__price | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |
| coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__price_usd | -0.2342 | 4.44e-06 | -0.1003 | 4.03e-02 | **CONFIRMED** |

## Distinct factors among CONFIRMED (dedup by dataset-group)

| horizon | group | representative | ic_disc | ic_hold | n_group_cols |
|---|---|---|---|---|---|
| 21 | defillama_chain_tvl | defillama_chain_tvl_bsc__tvl_usd | -0.432 | -0.327 | 5 |
| 21 | coc_btconchain_etfs | coc_btconchain_etfs_etf_volume_etf_volume_light__spot_price | -0.430 | -0.163 | 54 |
| 21 | bgeo_archive_loss | bgeo_archive_loss_lth__v1 | +0.396 | +0.103 | 1 |
| 21 | coc_extra_btconchain | coc_extra_btconchain_capitalrotation_crypto_pricedingold_crypto_pricedingold_light__eth_xau | -0.366 | -0.233 | 307 |
| 21 | coc_btconchain_demand | coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__price_usd | -0.362 | -0.163 | 45 |
| 7 | bgeo_archive_coinbase | bgeo_archive_coinbase_premium__v1 | +0.355 | +0.297 | 1 |
| 21 | coc_btconchain_pricing | coc_btconchain_pricing_pricing_yearlycostbasis_pricing_yearlycostbasis_light__2021 | -0.324 | -0.238 | 370 |
| 21 | bgeo_archive_supply | bgeo_archive_supply_retention_r_6m__v1 | +0.305 | +0.152 | 7 |
| 21 | bgeo_archive_bgeometrics | bgeo_archive_bgeometrics_index_market_peaks__v1 | -0.290 | -0.138 | 2 |
| 21 | bgeo_report_bitcoin | bgeo_report_bitcoin_distribution_addr_g__crab | +0.280 | +0.068 | 95 |
| 21 | bgeo_archive_crab | bgeo_archive_crab_addr__v1 | +0.280 | +0.068 | 1 |
| 21 | bgeo_archive_oi | bgeo_archive_oi_binance__v1 | -0.277 | -0.304 | 18 |
| 21 | coc_btconchain_derivatives | coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__binance | -0.269 | -0.239 | 81 |
| 21 | coc_btconchain_mining | coc_btconchain_mining_puellmultiple_puellmultiple_light__mean-0.85sd | -0.266 | -0.229 | 43 |
| 7 | coc_btconchain_etfs | coc_btconchain_etfs_etf_balance_1_etf_balance_1_light__total_etf_aum | -0.265 | -0.156 | 38 |
| 7 | coc_extra_btconchain | coc_extra_btconchain_entities_mstr_msty_mstr_msty_light__btc | -0.256 | -0.100 | 279 |
| 21 | yahoo_cme_eth | yahoo_cme_eth_futures__adj_close | -0.255 | -0.399 | 5 |
| 21 | binance_um_metrics | binance_um_metrics__sum_open_interest_value__last | -0.255 | -0.310 | 17 |
| 7 | defillama_chain_tvl | defillama_chain_tvl_bsc__tvl_usd | -0.254 | -0.187 | 5 |
| 21 | bgeo_archive_stablecoin | bgeo_archive_stablecoin_dai__v1 | -0.251 | -0.139 | 3 |
| 21 | coc_btconchain_cointime | coc_btconchain_cointime_pricing_mvrv_cointime_0_pricing_mvrv_cointime_0_light__median | -0.250 | -0.235 | 86 |
| 21 | bgeo_archive_shrimp | bgeo_archive_shrimp_coin__v1 | +0.247 | +0.176 | 1 |
| 7 | coc_btconchain_demand | coc_btconchain_demand_inflowcomparison_2024-01-01_inflowcomparison_2024-01-01_light__market_cap_change | -0.234 | -0.102 | 33 |
| 21 | defillama_stablecoin_frax | defillama_stablecoin_frax__circulating_usd | -0.227 | -0.116 | 1 |
| 21 | coc_btconchain_realised | coc_btconchain_realised_signal_realisedpnl_momentum_all_signal_realisedpnl_momentum_all_light__profit_momentum | +0.225 | +0.102 | 76 |
| 21 | bgeo_archive_demand | bgeo_archive_demand_average_btc_price__v1 | -0.225 | -0.247 | 1 |
| 21 | defillama_stablecoin_dai | defillama_stablecoin_dai__circulating_usd | -0.204 | -0.245 | 1 |
| 21 | blockchain_api_cost | blockchain_api_cost-per-transaction__value | -0.203 | -0.122 | 1 |
| 21 | bybit_btcusdt_mark | bybit_btcusdt_mark_daily__close | -0.199 | -0.247 | 4 |
| 21 | bybit_btcusdt_perp | bybit_btcusdt_perp_daily__close | -0.199 | -0.247 | 5 |
| 21 | bybit_btcusdt_index | bybit_btcusdt_index_daily__close | -0.199 | -0.248 | 4 |
| 21 | bgeo_archive_stablecoins | bgeo_archive_stablecoins__v1 | -0.196 | -0.166 | 1 |
| 21 | bgeo_archive_humpback | bgeo_archive_humpback_addr__v1 | +0.195 | +0.249 | 2 |
| 21 | bgeo_archive_funding | bgeo_archive_funding_rate_btc_price_alfabitcoin__v1 | -0.193 | -0.258 | 2 |
| 21 | bgeo_archive_liquidity | bgeo_archive_liquidity_stress_btc_price__v1 | -0.192 | -0.247 | 1 |
| 21 | bgeo_archive_coinbase | bgeo_archive_coinbase_premium__v1 | +0.190 | +0.171 | 2 |
| 21 | bgeo_archive_bitcoin | bgeo_archive_bitcoin_macro_index_btc_price__v1 | -0.189 | -0.247 | 1 |
| 21 | yahoo_coin | yahoo_coin__high | -0.187 | -0.340 | 5 |
| 21 | open_daily_btc | open_daily_btc_exchange_reserve_usd__value | -0.185 | -0.222 | 6 |
| 21 | coc_btconchain_supply | coc_btconchain_supply_circulating_issuance_eth_circulating_issuance_eth_light__price | -0.185 | -0.376 | 322 |
| 7 | coc_btconchain_pricing | coc_btconchain_pricing_pricing_yearlycostbasis_pricing_yearlycostbasis_light__2021 | -0.182 | -0.167 | 369 |
| 7 | bgeo_archive_oi | bgeo_archive_oi_binance__v1 | -0.181 | -0.171 | 16 |
| 21 | bgeo_archive_btc | bgeo_archive_btc_ohlc_1h__v3 | -0.176 | -0.247 | 11 |
| 7 | binance_um_metrics | binance_um_metrics__sum_open_interest_value__min | -0.176 | -0.169 | 8 |
| 21 | binance_um_futures | binance_um_futures__close | -0.175 | -0.248 | 5 |
| 21 | bitmex_xbtusd_daily | bitmex_xbtusd_daily__open | -0.175 | -0.247 | 10 |
| 21 | bgeo_archive_orderbook | bgeo_archive_orderbook_depth_btc_price__v1 | -0.173 | -0.247 | 1 |
| 21 | deribit_btc_perpetual | deribit_btc_perpetual_daily__open | -0.170 | -0.247 | 4 |
| 21 | bgeo_archive_volatility | bgeo_archive_volatility_btc_price__v1 | -0.170 | -0.247 | 1 |
| 7 | coc_btconchain_derivatives | coc_btconchain_derivatives_derivatives_futures_oi_byexchange_0_derivatives_futures_oi_byexchange_0_light__binance | -0.169 | -0.167 | 64 |

Interpretation: groups sharing the same sign/mechanism are ONE factor, not independent leads. The dominant confirmed factor is valuation-level mean reversion (price/AUM/TVL levels high -> 21d reversion). Independent leads require residualization against that factor before declaration.