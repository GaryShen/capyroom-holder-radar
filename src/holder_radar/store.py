"""SQLite 快取 cohort 時序。自架者 clone 即有種子快照,之後只算增量。"""
import sqlite3

SCHEMA = """CREATE TABLE IF NOT EXISTS cohort(
  date TEXT PRIMARY KEY, lth_btc REAL, sth_btc REAL, circulating_btc REAL,
  sth_cost_basis REAL, lth_cost_basis REAL, price REAL)"""


def init_db(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def upsert_cohort(conn, row: dict) -> None:
    conn.execute(
        """INSERT INTO cohort VALUES(:date,:lth_btc,:sth_btc,:circulating_btc,
           :sth_cost_basis,:lth_cost_basis,:price)
           ON CONFLICT(date) DO UPDATE SET lth_btc=excluded.lth_btc, sth_btc=excluded.sth_btc,
           circulating_btc=excluded.circulating_btc, sth_cost_basis=excluded.sth_cost_basis,
           lth_cost_basis=excluded.lth_cost_basis, price=excluded.price""", row)
    conn.commit()


def last_processed_date(conn) -> str | None:
    return conn.execute("SELECT MAX(date) d FROM cohort").fetchone()["d"]


def recent(conn, n: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cohort ORDER BY date DESC LIMIT ?", (n,))]


def latest(conn) -> dict | None:
    rows = recent(conn, 1)
    return rows[0] if rows else None
