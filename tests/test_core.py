from holder_radar import config, judge, store, prices, notify
from holder_radar.judge import Signal

BASE = dict(lth_btc=15.0, sth_btc=4.0, circulating_btc=19.0,
            sth_cost_basis=71400.0, lth_cost_basis=30000.0, price=72000.0)


# --- config ---
def test_sth_boundary_is_155_days():
    assert config.STH_MAX_AGE_SECONDS == 13_392_000
    assert config.FREE_SCAN_BYTES_LIMIT == 1_000_000_000_000


# --- judge ---
def test_price_crossing_down_sth_cost_emits_alert():
    sigs = judge.detect({**BASE, "price": 70000.0}, {**BASE, "price": 72000.0}, [])
    s = next(s for s in sigs if s.kind == "sth_cross_down")
    assert s.level == "alert" and "套牢" in s.zh and "成本線" in s.zh


def test_no_cross_when_both_days_above():
    sigs = judge.detect({**BASE, "price": 73000.0}, {**BASE, "price": 72000.0}, [])
    assert all(s.kind != "sth_cross_down" for s in sigs)


def test_lth_supply_new_high_emits_info():
    hist = [{**BASE, "lth_btc": 14.0}, {**BASE, "lth_btc": 14.5}]
    sigs = judge.detect({**BASE, "lth_btc": 15.0}, hist[-1], hist)
    assert any(s.kind == "lth_supply_high" for s in sigs)


def test_summarize_zh_mentions_underwater_and_has_no_advice():
    z = judge.summarize_zh({**BASE, "price": 60000.0})
    assert "套牢" in z
    for banned in ["買進", "賣出", "進場", "目標價"]:
        assert banned not in z


# --- store ---
def test_store_upsert_latest_and_idempotent(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    row = {"date": "2026-06-28", **BASE}
    store.upsert_cohort(conn, row)
    store.upsert_cohort(conn, row)  # 再寫一次,不應重複
    assert store.last_processed_date(conn) == "2026-06-28"
    assert store.latest(conn)["sth_cost_basis"] == 71400.0
    assert len(store.recent(conn, 10)) == 1


# --- prices ---
class _Resp:
    def __init__(self, j): self._j = j
    def raise_for_status(self): pass
    def json(self): return self._j


def test_current_btc_usd():
    assert prices.current_btc_usd(get=lambda *a, **k: _Resp({"bitcoin": {"usd": 60195.0}})) == 60195.0


def test_daily_history_maps_date_to_price():
    h = prices.daily_history(1, get=lambda *a, **k: _Resp({"prices": [[1750000000000, 60000.0]]}))
    assert list(h.values()) == [60000.0]


# --- notify ---
def test_format_message_includes_disclaimer():
    msg = notify.format_message([Signal("sth_cross_down", "alert", "跌穿成本線")])
    assert "跌穿成本線" in msg and "非投資建議" in msg


def test_line_adapter_posts_to_correct_recipient():
    calls = []

    class R:
        def raise_for_status(self): pass

    def fake_post(url, **kw):
        calls.append((url, kw))
        return R()

    notify.LineAdapter("tok", "U123", post=fake_post).send([Signal("x", "alert", "hi")])
    assert "line.me" in calls[0][0]
    assert calls[0][1]["json"]["to"] == "U123"
