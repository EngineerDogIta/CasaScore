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

# Colonne aggiunte rispetto allo schema legacy. La migrazione idempotente
# in `_migrate_schema()` garantisce che vengano create su DB esistenti.
EXPECTED_COLUMNS: dict[str, str] = {
    "tipologia": "TEXT",
    "contratto": "TEXT DEFAULT 'Vendita'",
    "stato_immobile": "TEXT",
    "disponibilita": "TEXT",
    "arredato": "TEXT",
    "piani_edificio": "INTEGER",
    "camere": "INTEGER",
    "bagni": "INTEGER DEFAULT 1",
    "cucina": "TEXT",
    "balcone": "INTEGER DEFAULT 0",
    "terrazzo": "INTEGER DEFAULT 0",
    "giardino_tipo": "TEXT",
    "cantina": "INTEGER DEFAULT 0",
    "posto_auto_desc": "TEXT",
    "accesso_disabili": "INTEGER DEFAULT 0",
    "riscaldamento_tipo": "TEXT",
    "riscaldamento_alimentazione": "TEXT",
    "riscaldamento_diffusione": "TEXT",
    "climatizzazione": "TEXT",
    "esposizione": "TEXT",
    "altre_caratteristiche": "TEXT",
    "contatto_id": "INTEGER REFERENCES contatti(id) ON DELETE SET NULL",
}


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
    """Create tables if missing, run idempotent migrations, seed criteri."""
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

            CREATE TABLE IF NOT EXISTS agenzie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                indirizzo TEXT,
                telefono TEXT,
                email TEXT,
                sito TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contatti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agenzia_id INTEGER REFERENCES agenzie(id) ON DELETE SET NULL,
                nome TEXT NOT NULL,
                ruolo TEXT,
                telefono TEXT,
                email TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        _migrate_schema(c)
        existing = {r["nome"] for r in c.execute("SELECT nome FROM criteri")}
        for nome, peso in DEFAULT_CRITERIA:
            if nome not in existing:
                c.execute(
                    "INSERT INTO criteri (nome, peso_default) VALUES (?, ?)",
                    (nome, peso),
                )


def _migrate_schema(c: sqlite3.Connection) -> None:
    """Aggiunge colonne mancanti a `immobili` e migra il legacy `giardino`."""
    have = {r["name"] for r in c.execute("PRAGMA table_info(immobili)")}
    for col, ddl in EXPECTED_COLUMNS.items():
        if col not in have:
            c.execute(f"ALTER TABLE immobili ADD COLUMN {col} {ddl}")

    if "giardino" in have:
        rows = c.execute(
            "SELECT id, giardino FROM immobili WHERE giardino IS NOT NULL"
        ).fetchall()
        for row in rows:
            val = (row["giardino"] or "").strip()
            if val == "Balcone":
                c.execute("UPDATE immobili SET balcone = 1 WHERE id = ?", (row["id"],))
            elif val == "Terrazzo":
                c.execute("UPDATE immobili SET terrazzo = 1 WHERE id = ?", (row["id"],))
            elif val == "Giardino":
                c.execute(
                    "UPDATE immobili SET giardino_tipo = 'Privato' WHERE id = ?",
                    (row["id"],),
                )
        if sqlite3.sqlite_version_info >= (3, 35, 0):
            c.execute("ALTER TABLE immobili DROP COLUMN giardino")


# ---------------------------------------------------------------- criteri ---

@st.cache_data(show_spinner=False)
def list_criteri() -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM criteri ORDER BY id")]


# --------------------------------------------------------------- immobili ---

_IMMOBILE_FIELDS: tuple[str, ...] = (
    "label", "indirizzo", "prezzo", "mq", "locali", "piano",
    "ascensore", "anno", "classe_energetica", "spese_cond",
    "posto_auto", "note", "foto_url", "stato",
    "mutuo_anticipo", "mutuo_anni", "mutuo_tasso",
    "tipologia", "contratto", "stato_immobile", "disponibilita",
    "arredato", "piani_edificio", "camere", "bagni", "cucina",
    "balcone", "terrazzo", "giardino_tipo", "cantina",
    "posto_auto_desc", "accesso_disabili",
    "riscaldamento_tipo", "riscaldamento_alimentazione",
    "riscaldamento_diffusione", "climatizzazione", "esposizione",
    "altre_caratteristiche", "contatto_id",
)


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
    values = [data.get(f) for f in _IMMOBILE_FIELDS]
    with get_conn() as c:
        cur = c.execute(
            f"INSERT INTO immobili ({', '.join(_IMMOBILE_FIELDS)}, created_at) "
            f"VALUES ({', '.join(['?'] * len(_IMMOBILE_FIELDS))}, ?)",
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


# ----------------------------------------------------------------- agenzie ---

_AGENZIA_FIELDS: tuple[str, ...] = (
    "nome", "indirizzo", "telefono", "email", "sito", "note",
)


@st.cache_data(show_spinner=False)
def list_agenzie() -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM agenzie ORDER BY nome COLLATE NOCASE"
        )]


@st.cache_data(show_spinner=False)
def get_agenzia(agenzia_id: int) -> dict[str, Any] | None:
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM agenzie WHERE id = ?", (agenzia_id,)
        ).fetchone()
        return dict(row) if row else None


def insert_agenzia(data: dict[str, Any]) -> int:
    values = [data.get(f) for f in _AGENZIA_FIELDS]
    with get_conn() as c:
        cur = c.execute(
            f"INSERT INTO agenzie ({', '.join(_AGENZIA_FIELDS)}, created_at) "
            f"VALUES ({', '.join(['?'] * len(_AGENZIA_FIELDS))}, ?)",
            (*values, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        new_id = cur.lastrowid
    _invalidate()
    return new_id


def update_agenzia(agenzia_id: int, data: dict[str, Any]) -> None:
    if not data:
        return
    cols = ", ".join(f"{k} = ?" for k in data)
    with get_conn() as c:
        c.execute(
            f"UPDATE agenzie SET {cols} WHERE id = ?",
            (*data.values(), agenzia_id),
        )
    _invalidate()


def delete_agenzia(agenzia_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM agenzie WHERE id = ?", (agenzia_id,))
    _invalidate()


# ----------------------------------------------------------------- contatti ---

_CONTATTO_FIELDS: tuple[str, ...] = (
    "agenzia_id", "nome", "ruolo", "telefono", "email", "note",
)


@st.cache_data(show_spinner=False)
def list_contatti(agenzia_id: int | None = None) -> list[dict[str, Any]]:
    """Ritorna i contatti. Se `agenzia_id` è specificato filtra per agenzia,
    altrimenti ritorna tutti i contatti (in ordine alfabetico)."""
    with get_conn() as c:
        if agenzia_id is None:
            rows = c.execute(
                "SELECT * FROM contatti ORDER BY nome COLLATE NOCASE"
            )
        else:
            rows = c.execute(
                "SELECT * FROM contatti WHERE agenzia_id = ? "
                "ORDER BY nome COLLATE NOCASE",
                (agenzia_id,),
            )
        return [dict(r) for r in rows]


@st.cache_data(show_spinner=False)
def list_contatti_orfani() -> list[dict[str, Any]]:
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM contatti WHERE agenzia_id IS NULL "
            "ORDER BY nome COLLATE NOCASE"
        )]


@st.cache_data(show_spinner=False)
def get_contatto(contatto_id: int) -> dict[str, Any] | None:
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM contatti WHERE id = ?", (contatto_id,)
        ).fetchone()
        return dict(row) if row else None


def insert_contatto(data: dict[str, Any]) -> int:
    values = [data.get(f) for f in _CONTATTO_FIELDS]
    with get_conn() as c:
        cur = c.execute(
            f"INSERT INTO contatti ({', '.join(_CONTATTO_FIELDS)}, created_at) "
            f"VALUES ({', '.join(['?'] * len(_CONTATTO_FIELDS))}, ?)",
            (*values, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        new_id = cur.lastrowid
    _invalidate()
    return new_id


def update_contatto(contatto_id: int, data: dict[str, Any]) -> None:
    if not data:
        return
    cols = ", ".join(f"{k} = ?" for k in data)
    with get_conn() as c:
        c.execute(
            f"UPDATE contatti SET {cols} WHERE id = ?",
            (*data.values(), contatto_id),
        )
    _invalidate()


def delete_contatto(contatto_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM contatti WHERE id = ?", (contatto_id,))
    _invalidate()
