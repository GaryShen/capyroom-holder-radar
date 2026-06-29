"""BigQuery 測試需 GCP 憑證(GOOGLE_CLOUD_PROJECT + ADC)。沒設就自動略過。"""
import os
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "bigquery: 需 GCP 憑證的測試")


def pytest_collection_modifyitems(config, items):
    if os.getenv("GOOGLE_CLOUD_PROJECT"):
        return
    skip = pytest.mark.skip(reason="無 GOOGLE_CLOUD_PROJECT,略過 BigQuery 測試")
    for item in items:
        if "bigquery" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def bq_client():
    from google.cloud import bigquery
    return bigquery.Client()
