"""SQLite layer for CasaScore.

All persistence lives here: schema bootstrap, seed data, and CRUD helpers.
Connections are short-lived and managed via context managers. Read-side
helpers are cached via `st.cache_data`; every writer calls `_invalidate()`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import streamlit as st

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


def _invalidate() -> None:
    """Drop all cached read results. Called after every mutation."""
    st.cache_data.clear()


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

@st.cache_data(show_spinner=False)
def list_criteri() -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM criteri ORDER BY id")]


# --------------------------------------------------------------- immobili ---

@st.cache_data(show_spinner=False)
def list_immobili() -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM immobili ORDER BY created_at DESC"
        )]


@st.cache_data(show_spinner=False)
def get_immobile(immobile_id: int) -> dict[str, Any] | None:
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM immobili WHERE id = ?", (immobile_id,)
        ).fetchone()
        return dict(row) if row else None


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
            (*values, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        new_id = cur.lastrowid
        for crit in c.execute("SELECT nome, peso_default FROM criteri"):
            c.execute(
                "INSERT INTO valutazioni (immobile_id, criterio, peso, voto) "
                "VALUES (?, ?, ?, 0)",
                (new_id, crit["nome"], crit["peso_default"]),
            )
    _invalidate()
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
    _invalidate()


def delete_immobile(immobile_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM immobili WHERE id = ?", (immobile_id,))
    _invalidate()


def update_stato(immobile_id: int, stato: str) -> None:
    update_immobile(immobile_id, {"stato": stato})


# ------------------------------------------------------------ valutazioni ---

@st.cache_data(show_spinner=False)
def get_valutazioni(immobile_id: int) -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM valutazioni WHERE immobile_id = ? ORDER BY id",
            (immobile_id,),
        )]


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
    _invalidate()


def bulk_upsert_valutazioni(immobile_id: int, items: Iterable[dict[str, Any]]) -> None:
    rows = [
        (immobile_id, item["criterio"],
         float(item.get("peso", 1.0)), int(item.get("voto", 0)))
        for item in items
    ]
    if not rows:
        return
    with get_conn() as c:
        c.executemany(
            """
            INSERT INTO valutazioni (immobile_id, criterio, peso, voto)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(immobile_id, criterio)
            DO UPDATE SET peso = excluded.peso, voto = excluded.voto
            """,
            rows,
        )
    _invalidate()


# ----------------------------------------------------------------- score ---

def weighted_score(valutazioni: Iterable[dict[str, Any]]) -> float | None:
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


@st.cache_data(show_spinner=False)
def score_for(immobile_id: int) -> float | None:
    return weighted_score(get_valutazioni(immobile_id))
