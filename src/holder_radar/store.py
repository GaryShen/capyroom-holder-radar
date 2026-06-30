"""SQLite 快取 cohort 時序。自架者 clone 即有種子快照,之後只算增量。"""
import sqlite3

SCHEMA = """CREATE TABLE IF NOT EXISTS cohort(
  date TEXT PRIMARY KEY, lth_btc REAL, sth_btc REAL, circulating_btc REAL,
  sth_cost_basis REAL, lth_cost_basis REAL, price REAL, cohort_date TEXT)"""
# date = 該列的價格日期(每日免費更新);cohort_date = cohort 真正算出來的日期(BigQuery 快照日)。
# 每日路把凍結的 cohort 複製到今天,但保留原 cohort_date,儀表板才能誠實標示。


def init_db(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    try:  # 舊 DB 遷移:補欄位
        conn.execute("ALTER TABLE cohort ADD COLUMN cohort_date TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("UPDATE cohort SET cohort_date = date WHERE cohort_date IS NULL")
    conn.commit()
    return conn


def upsert_cohort(conn, row: dict) -> None:
    row = {**row, "cohort_date": row.get("cohort_date") or row["date"]}
    conn.execute(
        """INSERT INTO cohort VALUES(:date,:lth_btc,:sth_btc,:circulating_btc,
           :sth_cost_basis,:lth_cost_basis,:price,:cohort_date)
           ON CONFLICT(date) DO UPDATE SET lth_btc=excluded.lth_btc, sth_btc=excluded.sth_btc,
           circulating_btc=excluded.circulating_btc, sth_cost_basis=excluded.sth_cost_basis,
           lth_cost_basis=excluded.lth_cost_basis, price=excluded.price,
           cohort_date=excluded.cohort_date""", row)
    conn.commit()


def last_processed_date(conn) -> str | None:
    return conn.execute("SELECT MAX(date) d FROM cohort").fetchone()["d"]


def recent(conn, n: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cohort ORDER BY date DESC LIMIT ?", (n,))]


def latest(conn) -> dict | None:
    rows = recent(conn, 1)
    return rows[0] if rows else None
