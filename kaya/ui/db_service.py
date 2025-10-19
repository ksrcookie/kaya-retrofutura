# kaya/ui/db_service.py
from __future__ import annotations
import sqlite3, json
from pathlib import Path
from typing import List, Dict, Any

def _dict_factory(cursor, row):
    d = {}
    for i, col in enumerate(cursor.description):
        d[col[0]] = row[i]
    return d

SCHEMA = """
CREATE TABLE IF NOT EXISTS people(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dob TEXT,
    country TEXT,
    city TEXT,
    education TEXT,
    family TEXT,         -- JSON array
    meta TEXT,           -- JSON blob (freeform)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS trg_people_updated
AFTER UPDATE ON people
BEGIN
  UPDATE people SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""

class DBService:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = _dict_factory
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.executescript(SCHEMA)
        self.conn.commit()

    # -------- PEOPLE ----------
    def list_people(self, q: str='') -> List[Dict[str,Any]]:
        cur = self.conn.cursor()
        if q:
            q = f"%{q.lower()}%"
            cur.execute("""
                SELECT * FROM people
                WHERE lower(name) LIKE ? OR lower(country) LIKE ? OR lower(city) LIKE ?
                ORDER BY updated_at DESC
            """, (q,q,q))
        else:
            cur.execute("SELECT * FROM people ORDER BY updated_at DESC")
        return cur.fetchall()

    def get_person(self, pid: int) -> Dict[str,Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM people WHERE id=?", (pid,))
        return cur.fetchone()

    def create_person(self, data: Dict[str,Any]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO people(name, dob, country, city, education, family, meta)
            VALUES(?,?,?,?,?,?,?)
        """, (
            data.get('name','New Person'),
            data.get('dob',''),
            data.get('country',''),
            data.get('city',''),
            data.get('education',''),
            json.dumps(data.get('family',[]), ensure_ascii=False),
            json.dumps(data.get('meta',{}), ensure_ascii=False),
        ))
        self.conn.commit()
        return int(cur.lastrowid)

    def update_person(self, pid: int, data: Dict[str,Any]):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE people
            SET name=?, dob=?, country=?, city=?, education=?, family=?, meta=?
            WHERE id=?
        """, (
            data.get('name',''),
            data.get('dob',''),
            data.get('country',''),
            data.get('city',''),
            data.get('education',''),
            json.dumps(data.get('family',[]), ensure_ascii=False),
            json.dumps(data.get('meta',{}), ensure_ascii=False),
            pid
        ))
        self.conn.commit()

    def delete_person(self, pid: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM people WHERE id=?", (pid,))
        self.conn.commit()
