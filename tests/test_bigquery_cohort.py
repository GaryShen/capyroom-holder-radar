import pytest
from holder_radar import bigquery_cohort as bq, config

pytestmark = pytest.mark.bigquery  # 需 GCP 憑證,無則整檔略過


def test_supply_query_dry_run_under_free_limit(bq_client):
    sql = bq.build_supply_query("2026-06-29")
    scanned = bq.dry_run_scan_bytes(bq_client, sql)
    assert scanned < config.FREE_SCAN_BYTES_LIMIT, \
        f"掃描 {scanned / 1e12:.2f}TB ≥ 1TB 免費額度,需改增量/分區"


def test_supply_numbers_are_plausible(bq_client):
    r = bq.run_supply(bq_client, "2026-06-29")
    assert 18e6 < r["circulating_btc"] < 21e6        # 流通量 ~19.x M
    lth_pct = r["lth_btc"] / r["circulating_btc"]
    assert 0.6 < lth_pct < 0.9                        # LTH 佔比對照報導 ~79%
