import os
import pytest
from holder_radar import bigquery_cohort as bq, config

pytestmark = pytest.mark.bigquery  # 需 GCP 憑證,無則整檔略過


def test_supply_query_dry_run_under_free_limit(bq_client):
    # dry-run 免費、不計額度 → 永遠可跑,當回歸守門
    sql = bq.build_supply_query("2026-06-29")
    scanned = bq.dry_run_scan_bytes(bq_client, sql)
    assert scanned < config.FREE_SCAN_BYTES_LIMIT, \
        f"掃描 {scanned / 1e12:.2f}TB ≥ 1TB 免費額度,需改增量/分區"


@pytest.mark.skipif(not os.getenv("RUN_BQ_QUERIES"),
                    reason="真跑查詢會吃 ~0.45TB/月額度;設 RUN_BQ_QUERIES=1 才跑")
def test_supply_numbers_are_plausible(bq_client):
    # 已驗證 2026-06-29:流通 19.93M、LTH 16.64M(83.5%)、STH 3.29M(16.5%)
    r = bq.run_supply(bq_client, "2026-06-29")
    assert 18e6 < r["circulating_btc"] < 21e6        # 流通量 ~19.x M
    lth_pct = r["lth_btc"] / r["circulating_btc"]
    assert 0.7 < lth_pct < 0.9                        # raw UTXO-age 版 ~83%(Glassnode 調整版 ~79%)
