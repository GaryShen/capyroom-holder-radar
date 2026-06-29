from holder_radar import cli, store, line_bot

BASE = dict(lth_btc=15.0, sth_btc=4.0, circulating_btc=19.0,
            sth_cost_basis=71400.0, lth_cost_basis=30000.0)


class _Source:
    def run(self): return dict(BASE)


class _Notifier:
    def __init__(self): self.sent = []
    def send(self, sigs): self.sent.append(sigs)


def test_run_daily_persists_and_alerts_on_cross_down(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    store.upsert_cohort(conn, {"date": "2026-06-28", "price": 72000.0, **BASE})  # 昨天在線上
    n = _Notifier()
    sigs = cli.run_daily(conn, _Source(), n, "2026-06-29", price=70000.0)  # 今天跌穿
    assert store.last_processed_date(conn) == "2026-06-29"
    assert any(s.kind == "sth_cross_down" for s in sigs)
    assert n.sent  # alert 有推


def test_run_daily_no_push_when_only_info(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    store.upsert_cohort(conn, {"date": "2026-06-28", "price": 80000.0, **BASE})
    n = _Notifier()
    cli.run_daily(conn, _Source(), n, "2026-06-29", price=80000.0)  # 沒跨界
    assert not n.sent  # 只有 info 不推,省額度


def test_line_handle_query_returns_state_and_disclaimer():
    reply = line_bot.handle_query({"price": 60195.0, **BASE})
    assert "71,400" in reply and "非投資建議" in reply
