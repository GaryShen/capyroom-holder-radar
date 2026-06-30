from holder_radar import bgeometrics as bg


class _R:
    def __init__(self, j): self._j = j
    def raise_for_status(self): pass
    def json(self): return self._j


def test_pick_value_skips_date_and_timestamp():
    assert bg._pick_value({"d": "2026-06-29", "unixTs": 1751155200,
                           "sthRealizedPrice": 71402.5}) == 71402.5


def test_pick_value_handles_string_numbers():
    assert bg._pick_value({"theDate": "2026-06-29", "value": "70451.0"}) == 70451.0


def test_fetch_cohort_maps_all_metrics():
    responses = {
        "sth-realized-price": {"d": "2026-06-29", "sthRealizedPrice": 70451.0},
        "lth-realized-price": {"d": "2026-06-29", "lthRealizedPrice": 30000.0},
        "long-term-holder-supply": {"d": "2026-06-29", "value": 16_640_000.0},
        "short-term-holder-supply": {"d": "2026-06-29", "value": 3_280_000.0},
    }

    def fake_get(url, **kw):
        for path, j in responses.items():
            if f"/{path}/last" in url:
                return _R(j)
        raise AssertionError(f"unexpected url: {url}")

    c = bg.fetch_cohort(get=fake_get)
    assert c["sth_cost_basis"] == 70451.0
    assert c["lth_cost_basis"] == 30000.0
    assert c["circulating_btc"] == 16_640_000.0 + 3_280_000.0
