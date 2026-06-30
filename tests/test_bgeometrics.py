from holder_radar import bgeometrics as bg


class _R:
    def __init__(self, j): self._j = j
    def raise_for_status(self): pass
    def json(self): return self._j


def test_pick_value_skips_timestamp_and_links():
    item = {"unixTs": "1751155200", "sthRealizedPrice": "69911.62",
            "_links": {"self": {"href": "x"}}}
    assert bg._pick_value(item) == 69911.62


def test_fetch_cohort_maps_metrics_and_date():
    data = {
        "sthRealizedPrices": ("sthRealizedPrice", "69911.62"),
        "lthRealizedPrices": ("lthRealizedPrice", "49213.04"),
        "longTermHodlerSupplyBtcs": ("longTermHodlerSupplyBtc", 16_650_381.99),
        "shortTermHodlerSupplyBtcs": ("shortTermHodlerSupplyBtc", 3_399_372.27),
    }

    def fake_get(url, params=None, **kw):
        ep = url.rsplit("/", 1)[-1]
        field, val = data[ep]
        item = {"unixTs": "1", field: val,
                "_links": {"self": {"href": f"https://x/{ep}/2026-06-29"}}}
        return _R({"_embedded": {ep: [item]}})

    c = bg.fetch_cohort(get=fake_get)
    assert c["sth_cost_basis"] == 69911.62
    assert c["lth_cost_basis"] == 49213.04
    assert c["circulating_btc"] == 16_650_381.99 + 3_399_372.27
    assert c["cohort_date"] == "2026-06-29"
