# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (one-time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Reset all data
rm casascore.db   # recreated on next start by db.init_db()
```

There is no test suite, linter, or build step. The project pins only `streamlit==1.40.2` and `pandas==2.2.3`; SQLite comes from stdlib.

## Architecture

Single-process Streamlit app, no external services, no auth. All UI is Italian.

**Entry point — [app.py](app.py)**
- Calls `db.init_db()` on every load (idempotent: `CREATE TABLE IF NOT EXISTS` + seeds default criteria).
- Holds a large CSS block (~400 lines) defining the design system: sage/dusty palette, `.cs-*` classes, ring-progress score card. UI components emit raw HTML using these classes via `st.markdown(..., unsafe_allow_html=True)`.
- Sidebar-driven router: `st.session_state["page"]` switches between Dashboard / Immobili / Nuovo-Modifica / Calcolatore / Impostazioni. `selected_id` and `edit_id` carry cross-page selection. Page changes call `st.rerun()`.

**Persistence — [db.py](db.py)**
- SQLite at `casascore.db` (gitignored). Connections are short-lived via the `get_conn()` context manager, which auto-commits on exit and enables foreign keys.
- Three tables: `immobili` (properties + their per-property mortgage sliders `mutuo_anticipo/anni/tasso`), `criteri` (named scoring criteria with default weights), `valutazioni` (per-property × per-criterion `(peso, voto)` rows, unique on `(immobile_id, criterio)`, cascade-deleted with the property).
- `DEFAULT_CRITERIA` and `STATUSES` are the source of truth for the seeded scoring dimensions and the four property states (`visit` / `visited` / `favorite` / `rejected`). Status IDs are stored as strings in `immobili.stato`.
- `insert_immobile` automatically creates a `valutazioni` row for every existing criterion with `voto=0`. `valutazione.render` does a backfill if criteria were added after the property was created.
- `weighted_score` ignores votes ≤ 0 (treated as "not yet rated") and returns `None` when no criterion has been voted — UI must handle the `None` case.

**Components — [components/](components/)**
Each module exposes a `render(...)` function called by the router:
- [scheda.py](components/scheda.py) — add/edit form. `render(immobile_id | None)`; `None` means new.
- [valutazione.py](components/valutazione.py) — per-criterion 1–5 sliders + per-property weight overrides. Persists on every rerun via `bulk_upsert_valutazioni`.
- [dashboard.py](components/dashboard.py) — comparative view (cards/table), filters, aggregate stats. Builds a pandas DataFrame from `db.list_immobili()` joined with computed scores.
- [mutuo.py](components/mutuo.py) — French-amortization calculator. `calc_rata(prezzo, anticipo_pct, anni, tasso_pct)` is pure and reused by both the inline per-property block and the standalone Calcolatore page. The inline `render()` writes slider state back to the property (`mutuo_*` columns).

## Conventions worth knowing

- Domain language is Italian (`immobile`, `criterio`, `valutazione`, `prezzo`, `mq`, `locali`). Match this when adding fields or labels — don't mix English domain terms.
- Streamlit widget keys are namespaced by `immobile_id` (e.g. `f"voto_{immobile['id']}_{criterio}"`) so multiple properties can coexist on a page without state collisions. Preserve this pattern.
- Currency/number formatting uses Italian convention: `f"{n:,.0f}".replace(",", ".")` for thousands separators. There's no shared helper — it's inlined throughout.
- The CSS lives only in `app.py`. New components should reuse existing `.cs-*` classes (`cs-card`, `cs-section-title`, `cs-metric`, `cs-score-card`, etc.) rather than introducing inline styles.
- Schema changes require updating `init_db()` *and* handling existing DBs — `CREATE TABLE IF NOT EXISTS` will not add new columns. Either bump with an explicit `ALTER TABLE` migration or document that users must delete `casascore.db`.
