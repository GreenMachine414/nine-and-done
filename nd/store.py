"""Persistence: one row per league save (JSON state) + one row per played game (box score / events).

Backends:
  - PostgreSQL when DATABASE_URL is set (Railway), via psycopg 3
  - SQLite file otherwise (local play)

Every save belongs to an owner (an anonymous per-browser id) so visitors only ever see their own leagues.
Saves created before ownership existed (owner IS NULL) stay visible locally.
"""
import json
import os
import sqlite3
import threading
import time
from collections import OrderedDict

CACHE_SIZE = 24


class _SQLite:
    kind = "sqlite"

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS saves (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, team TEXT, season INTEGER, phase TEXT,
            record TEXT, updated REAL, data TEXT, owner TEXT);
        CREATE TABLE IF NOT EXISTS games (
            save_id INTEGER, gid TEXT, season INTEGER, data TEXT, PRIMARY KEY (save_id, gid));
        """)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(saves)")}
        if "owner" not in cols:
            self.db.execute("ALTER TABLE saves ADD COLUMN owner TEXT")
        self.db.commit()

    def run(self, sql, params=(), fetch=None, many=False):
        cur = self.db.executemany(sql, params) if many else self.db.execute(sql, params)
        out = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else None
        self.db.commit()
        return out


class _Postgres:
    kind = "postgres"

    def __init__(self, url):
        import psycopg  # only needed in production
        self.psycopg = psycopg
        self.url = url
        self.conn = None
        self._connect()
        self.run("""CREATE TABLE IF NOT EXISTS saves (
            id BIGSERIAL PRIMARY KEY, name TEXT, team TEXT, season INTEGER, phase TEXT,
            record TEXT, updated DOUBLE PRECISION, data TEXT, owner TEXT)""")
        self.run("ALTER TABLE saves ADD COLUMN IF NOT EXISTS owner TEXT")
        self.run("CREATE INDEX IF NOT EXISTS saves_owner ON saves(owner)")
        self.run("""CREATE TABLE IF NOT EXISTS games (
            save_id BIGINT, gid TEXT, season INTEGER, data TEXT, PRIMARY KEY (save_id, gid))""")

    def _connect(self):
        self.conn = self.psycopg.connect(self.url, autocommit=True)

    def run(self, sql, params=(), fetch=None, many=False):
        sql = sql.replace("?", "%s")
        for attempt in (0, 1):
            try:
                with self.conn.cursor() as cur:
                    if many:
                        cur.executemany(sql, params)
                    else:
                        cur.execute(sql, params)
                    if fetch == "one":
                        return cur.fetchone()
                    if fetch == "all":
                        return cur.fetchall()
                    return None
            except (self.psycopg.OperationalError, self.psycopg.InterfaceError):
                if attempt:
                    raise
                try:
                    self.conn.close()
                except Exception:  # noqa
                    pass
                self._connect()   # Railway may drop idle connections; reconnect once and retry


class Store:
    def __init__(self, path, url=None):
        self.db = _Postgres(url) if url else _SQLite(path)
        self.kind = self.db.kind
        self.lock = threading.RLock()
        self.cache = OrderedDict()   # sid -> (owner, league)

    # ---------------------------------------------------------------- helpers
    def _meta(self, L):
        t = L["teams"][L["user"]]
        titles = t.get("titles", 0)
        return (L["name"], f'{t["city"]} {t["name"]}', L["season"], L["phase"],
                f'{t["w"]}-{t["l"]}' + (f" · {titles}🏆" if titles else ""), time.time())

    def _remember(self, sid, owner, L):
        self.cache[sid] = (owner, L)
        self.cache.move_to_end(sid)
        while len(self.cache) > CACHE_SIZE:
            self.cache.popitem(last=False)

    @staticmethod
    def _allowed(row_owner, owner):
        return row_owner is None or row_owner == owner

    # ---------------------------------------------------------------- saves
    def list_saves(self, owner):
        with self.lock:
            rows = self.db.run("SELECT id, name, team, season, phase, record, updated FROM saves "
                               "WHERE owner = ? OR owner IS NULL ORDER BY updated DESC", (owner,), fetch="all")
        return [dict(zip(("id", "name", "team", "season", "phase", "record", "updated"), r)) for r in rows]

    def create(self, L, owner):
        with self.lock:
            row = self.db.run("INSERT INTO saves (name, team, season, phase, record, updated, data, owner) "
                              "VALUES (?,?,?,?,?,?,?,?) RETURNING id",
                              (*self._meta(L), json.dumps(L), owner), fetch="one")
            sid = int(row[0])
            self._remember(sid, owner, L)
            return sid

    def load(self, sid, owner):
        """The league, or None if it doesn't exist or belongs to someone else."""
        sid = int(sid)
        with self.lock:
            hit = self.cache.get(sid)
            if hit:
                if not self._allowed(hit[0], owner):
                    return None
                self.cache.move_to_end(sid)
                return hit[1]
            row = self.db.run("SELECT data, owner FROM saves WHERE id = ?", (sid,), fetch="one")
            if not row or not self._allowed(row[1], owner):
                return None
            L = json.loads(row[0])
            self._remember(sid, row[1], L)
            return L

    def save(self, sid, L):
        with self.lock:
            self.db.run("UPDATE saves SET name=?, team=?, season=?, phase=?, record=?, updated=?, data=? "
                        "WHERE id=?", (*self._meta(L), json.dumps(L), int(sid)))

    def delete(self, sid, owner):
        sid = int(sid)
        with self.lock:
            row = self.db.run("SELECT owner FROM saves WHERE id = ?", (sid,), fetch="one")
            if not row or not self._allowed(row[0], owner):
                return False
            self.db.run("DELETE FROM saves WHERE id = ?", (sid,))
            self.db.run("DELETE FROM games WHERE save_id = ?", (sid,))
            self.cache.pop(sid, None)
            return True

    # ---------------------------------------------------------------- games
    def put_games(self, sid, docs):
        if not docs:
            return
        with self.lock:
            self.db.run("INSERT INTO games (save_id, gid, season, data) VALUES (?,?,?,?) "
                        "ON CONFLICT (save_id, gid) DO UPDATE SET season = excluded.season, data = excluded.data",
                        [(int(sid), d["gid"], d["s"], json.dumps(d)) for d in docs], many=True)

    def get_game(self, sid, gid):
        with self.lock:
            row = self.db.run("SELECT data FROM games WHERE save_id = ? AND gid = ?", (int(sid), gid), fetch="one")
        return json.loads(row[0]) if row else None
