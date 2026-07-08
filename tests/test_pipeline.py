from holder_radar import cli, store, line_bot, export

SNAP = dict(date="2026-06-28", lth_btc=16.0, sth_btc=3.3, circulating_btc=19.3,
            sth_cost_basis=71400.0, lth_cost_basis=30000.0, price=72000.0)


class _Notifier:
    def __init__(self): self.sent = []
    def send(self, sigs): self.sent.append(sigs)


def test_daily_alerts_on_cross_down_and_writes_data_js(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    store.upsert_cohort(conn, SNAP)                       # 昨天:價 72000 ≥ 成本 71400
    n = _Notifier()
    px = {"2026-06-27": 73000.0, "2026-06-29": 70000.0}   # 今天跌到 70000 < 71400
    data_js = tmp_path / "data.js"
    sigs = cli.daily(conn, n, 70000.0, px, str(data_js))
    assert any(s.kind == "sth_cross_down" for s in sigs)
    assert n.sent                                         # alert 有推
    assert "window.RADAR_DATA" in data_js.read_text(encoding="utf-8")


def test_daily_uses_fresh_cohort_with_source_date(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    fresh = dict(lth_btc=16.65e6, sth_btc=3.4e6, circulating_btc=20.05e6,
                 sth_cost_basis=69911.0, lth_cost_basis=49213.0, cohort_date="2026-06-29")
    cli.daily(conn, None, 59000.0, {"2026-06-30": 59000.0}, str(tmp_path / "d.js"), fresh_cohort=fresh)
    row = store.latest(conn)
    assert row["sth_cost_basis"] == 69911.0
    assert row["date"] == "2026-06-30"          # 價格日期 = 今天
    assert row["cohort_date"] == "2026-06-29"   # cohort 日期 = 來源日


def test_daily_no_push_when_price_stays_above(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")
    store.upsert_cohort(conn, SNAP)
    n = _Notifier()
    px = {"2026-06-29": 80000.0}
    cli.daily(conn, n, 80000.0, px, str(tmp_path / "d.js"))
    assert not n.sent


def test_snapshot_stores_cohort(tmp_path):
    conn = store.init_db(tmp_path / "t.sqlite")

    class _Src:
        def run(self): return dict(lth_btc=16.6, sth_btc=3.3, circulating_btc=19.9,
                                   sth_cost_basis=70451.0, lth_cost_basis=None)
    cli.snapshot(conn, _Src(), "2026-06-29", price=59247.0)
    assert store.latest(conn)["sth_cost_basis"] == 70451.0


def test_export_forward_fills_cost_and_builds_donut():
    price_by_date = {"2026-06-27": 60000.0, "2026-06-28": 59900.0, "2026-06-29": 59247.0}
    snaps = [dict(date="2026-06-28", lth_btc=16.6, sth_btc=3.3, circulating_btc=19.9,
                  sth_cost_basis=70451.0, lth_cost_basis=None, price=59900.0)]
    latest = snaps[0]
    d = export.build_dashboard_data(price_by_date, snaps, latest)
    assert d["price"][-1] == 59247.0
    assert d["cost"][-1] == 70451.0                       # 由快照 forward-fill
    assert d["cost"][0] == 70451.0                        # 開頭回填第一個已知值
    assert d["donut"]["lth_pct"] == round(16.6 / 19.9, 4)
    assert d["latest"]["underwater"] is True              # 59247 < 70451


def test_line_handle_query_returns_state_and_disclaimer():
    reply = line_bot.handle_query({"price": 59247.0, **SNAP})
    assert "非投資建議" in reply


def test_make_notifier_picks_channel_by_env():
    LINE = dict(LINE_TOKEN="t", LINE_TO="U1")
    TG = dict(TG_TOKEN="t", TG_CHAT_ID="-100")
    assert cli.make_notifier({}) is None                       # 都沒設 → 不推
    assert cli.make_notifier(LINE).name == "LINE"
    assert cli.make_notifier(TG).name == "Telegram"
    assert cli.make_notifier({**LINE, **TG}).name == "LINE"    # 都設 → LINE 優先
    assert cli.make_notifier({"LINE_TOKEN": "t"}) is None      # 只設一半 → 視為沒設,不炸
    assert cli.make_notifier({"TG_TOKEN": "t"}) is None
