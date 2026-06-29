import os
import pytest
from holder_radar import bigquery_cohort as bq, config


# --- 純函式:cohort_metrics(免 GCP,隨時跑)---

def test_cohort_metrics_splits_by_155_days_and_prices_sth():
    # as_of 2026-06-29 → 155 天界線約 2026-01-25
    breakdown = [
        {"d": "2020-01-01", "btc": 10.0},   # 老 → LTH
        {"d": "2026-06-01", "btc": 2.0},    # 近 → STH @ 60000
        {"d": "2026-06-02", "btc": 1.0},    # 近 → STH @ 90000
    ]
    prices = {"2026-06-01": 60000.0, "2026-06-02": 90000.0}
    m = bq.cohort_metrics(breakdown, "2026-06-29", prices)
    assert m["lth_btc"] == 10.0
    assert m["sth_btc"] == 3.0
    assert m["circulating_btc"] == 13.0
    assert m["sth_cost_basis"] == (2 * 60000 + 1 * 90000) / 3  # = 70000


def test_cohort_metrics_sth_cost_none_when_prices_missing():
    m = bq.cohort_metrics([{"d": "2026-06-01", "btc": 2.0}], "2026-06-29", {})
    assert m["sth_cost_basis"] is None


# --- BigQuery(需 GCP 憑證,無則略過)---

@pytest.mark.bigquery
def test_breakdown_query_dry_run_under_free_limit(bq_client):
    # dry-run 免費、不計額度 → 回歸守門
    sql = bq.build_age_breakdown_query("2026-06-29")
    scanned = bq.dry_run_scan_bytes(bq_client, sql)
    assert scanned < config.FREE_SCAN_BYTES_LIMIT, \
        f"掃描 {scanned / 1e12:.2f}TB ≥ 1TB 免費額度,需改增量/分區"


@pytest.mark.bigquery
@pytest.mark.skipif(not os.getenv("RUN_BQ_QUERIES"),
                    reason="真跑查詢吃 ~0.45TB/月額度;設 RUN_BQ_QUERIES=1 才跑")
def test_sth_cost_basis_matches_reference(bq_client):
    from holder_radar import prices
    px = prices.daily_history(180)
    r = bq.run_cohort(bq_client, "2026-06-29", px)
    assert 0.7 < r["lth_btc"] / r["circulating_btc"] < 0.9   # raw UTXO-age ~83%
    assert 60_000 < r["sth_cost_basis"] < 80_000             # 對照報導 ~$71.4k
