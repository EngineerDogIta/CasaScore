"""SQLite layer for CasaScore.

All persistence lives here: schema bootstrap, seed data, and CRUD helpers.
Connections are short-lived and managed via context managers.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent / "casascore.db"

DEFAULT_CRITERIA: list[tuple[str, float]] = [
    ("Luminosità", 1.0),
    ("Stato degli interni", 1.2),
    ("Zona / Quartiere", 1.3),
    ("Trasporti", 1.0),
    ("Silenzio (no rumore)", 0.9),
    ("Potenziale rivendita", 1.1),
]

STATUSES: list[dict[str, str]] = [
    {"id": "visit", "label": "Da visitare", "emoji": "👀"},
    {"id": "visited", "label": "Visitato", "emoji": "📅"},
    {"id": "favorite", "label": "Preferito", "emoji": "❤️"},
    {"id": "rejected", "label": "Scartato", "emoji": "❌"},
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if missing and seed default criteria."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS immobili (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                indirizzo TEXT,
                prezzo REAL,
                mq REAL,
                locali INTEGER,
                piano TEXT,
                ascensore INTEGER DEFAULT 0,
                anno INTEGER,
                classe_energetica TEXT,
                spese_cond REAL,
                posto_auto INTEGER DEFAULT 0,
                giardino TEXT,
                note TEXT,
                foto_url TEXT,
                stato TEXT DEFAULT 'visit',
                mutuo_anticipo REAL DEFAULT 20,
                mutuo_anni INTEGER DEFAULT 25,
                mutuo_tasso REAL DEFAULT 3.5,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS criteri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                peso_default REAL NOT NULL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS valutazioni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                immobile_id INTEGER NOT NULL,
                criterio TEXT NOT NULL,
                peso REAL NOT NULL DEFAULT 1.0,
                voto INTEGER NOT NULL DEFAULT 0,
                UNIQUE(immobile_id, criterio),
                FOREIGN KEY (immobile_id) REFERENCES immobili(id) ON DELETE CASCADE
            );
            """
        )
        existing = {r["nome"] for r in c.execute("SELECT nome FROM criteri")}
        for nome, peso in DEFAULT_CRITERIA:
            if nome not in existing:
                c.execute(
                    "INSERT INTO criteri (nome, peso_default) VALUES (?, ?)",
                    (nome, peso),
                )


# ---------------------------------------------------------------- criteri ---

def list_criteri() -> list[sqlite3.Row]:
    with get_conn() as c:
        return list(c.execute("SELECT * FROM criteri ORDER BY id"))


# --------------------------------------------------------------- immobili ---

def list_immobili() -> list[sqlite3.Row]:
    with get_conn() as c:
        return list(c.execute("SELECT * FROM immobili ORDER BY created_at DESC"))


def get_immobile(immobile_id: int) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM immobili WHERE id = ?", (immobile_id,)
        ).fetchone()


def insert_immobile(data: dict[str, Any]) -> int:
    fields = (
        "label", "indirizzo", "prezzo", "mq", "locali", "piano",
        "ascensore", "anno", "classe_energetica", "spese_cond",
        "posto_auto", "giardino", "note", "foto_url", "stato",
        "mutuo_anticipo", "mutuo_anni", "mutuo_tasso",
    )
    values = [data.get(f) for f in fields]
    with get_conn() as c:
        cur = c.execute(
            f"INSERT INTO immobili ({', '.join(fields)}, created_at) "
            f"VALUES ({', '.join(['?'] * len(fields))}, ?)",
            (*values, datetime.utcnow().isoformat(timespec="seconds")),
        )
        new_id = cur.lastrowid
        for crit in c.execute("SELECT nome, peso_default FROM criteri"):
            c.execute(
                "INSERT INTO valutazioni (immobile_id, criterio, peso, voto) "
                "VALUES (?, ?, ?, 0)",
                (new_id, crit["nome"], crit["peso_default"]),
            )
        return new_id


def update_immobile(immobile_id: int, data: dict[str, Any]) -> None:
    if not data:
        return
    cols = ", ".join(f"{k} = ?" for k in data)
    with get_conn() as c:
        c.execute(
            f"UPDATE immobili SET {cols} WHERE id = ?",
            (*data.values(), immobile_id),
        )


def delete_immobile(immobile_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM immobili WHERE id = ?", (immobile_id,))


def update_stato(immobile_id: int, stato: str) -> None:
    update_immobile(immobile_id, {"stato": stato})


# ------------------------------------------------------------ valutazioni ---

def get_valutazioni(immobile_id: int) -> list[sqlite3.Row]:
    with get_conn() as c:
        return list(
            c.execute(
                "SELECT * FROM valutazioni WHERE immobile_id = ? ORDER BY id",
                (immobile_id,),
            )
        )


def upsert_valutazione(immobile_id: int, criterio: str, peso: float, voto: int) -> None:
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO valutazioni (immobile_id, criterio, peso, voto)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(immobile_id, criterio)
            DO UPDATE SET peso = excluded.peso, voto = excluded.voto
            """,
            (immobile_id, criterio, peso, voto),
        )


def bulk_upsert_valutazioni(immobile_id: int, items: Iterable[dict[str, Any]]) -> None:
    for item in items:
        upsert_valutazione(
            immobile_id,
            item["criterio"],
            float(item.get("peso", 1.0)),
            int(item.get("voto", 0)),
        )


# ----------------------------------------------------------------- score ---

def weighted_score(valutazioni: Iterable[sqlite3.Row | dict[str, Any]]) -> float | None:
    total_w = 0.0
    s = 0.0
    for v in valutazioni:
        voto = v["voto"]
        peso = v["peso"]
        if voto and voto > 0:
            s += voto * peso
            total_w += peso
    if total_w == 0:
        return None
    return s / total_w


def score_for(immobile_id: int) -> float | None:
    return weighted_score(get_valutazioni(immobile_id))
