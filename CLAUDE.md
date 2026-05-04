# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (one-time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app (hot-reloads on save — see .streamlit/config.toml)
streamlit run app.py

# Reset all data
rm casascore.db   # recreated on next start by db.init_db()
```

No test suite, linter, or build step. The project pins only `streamlit==1.40.2` and `pandas==2.2.3`; SQLite comes from stdlib.

## Architecture

Single-process Streamlit app, no external services, no auth. All UI is Italian.

### Streamlit execution model

Every widget interaction re-runs `app.py` top-to-bottom. This is the mental model for the entire codebase:

- **`@st.cache_data`** memoises read functions globally across reruns. `_invalidate()` in `db.py` calls `st.cache_data.clear()` after every write, keeping reads coherent.
- **`@st.fragment`** limits a re-run to just that decorated block. Applied to `valutazione.render` and `mutuo.render` so slider drags don't re-render the entire page.
- **`st.session_state`** is the only persistent in-memory state between reruns. Keys used: `selected_id` (currently open property), `edit_id` (property being edited, or `None` for new), `pages` (the nav dict).

### Entry point — `app.py`

Calls `db.init_db()` (idempotent), injects the CSS, sets session state defaults, then runs in this order:
1. Sidebar brand mark (must precede `st.navigation` to appear above nav links)
2. `st.navigation(list(pages.values()))` — builds URL-based routing from `nav.build()`
3. Sidebar property picker (`st.selectbox`) + "＋ Nuova scheda" button
4. `selected.run()` — executes the active page

### Page registry — `nav.py`

`nav.build()` returns `dict[str, st.Page]` stored on `st.session_state["pages"]`. Keys: `"dashboard"`, `"immobili"`, `"scheda"`, `"calcolatore"`, `"impostazioni"`. The `scheda` entry uses a thin `_scheda_page` no-arg adapter that reads `edit_id` from session state, because `st.Page` callables take no arguments — unlike all other `render` functions, `scheda.render` takes `immobile_id | None`.

### Persistence — `db.py`

SQLite at `casascore.db` (gitignored). Connections are short-lived via `get_conn()`, a context manager that sets `row_factory = sqlite3.Row`, enables foreign keys, and auto-commits on exit.

Three tables:
- `immobili` — property record + per-property mortgage slider state (`mutuo_anticipo`, `mutuo_anni`, `mutuo_tasso`). Note that `ascensore` and `posto_auto` are INTEGER booleans (0/1), while `giardino` is TEXT (one of `["Nessuno", "Balcone", "Terrazzo", "Giardino"]` from `scheda.OUTDOOR_OPTIONS`).
- `criteri` — named scoring criteria with `peso_default`. Seeded from `DEFAULT_CRITERIA` on every `init_db()` call (additive-only — existing rows are never touched). The 6 defaults: `("Luminosità", 1.0)`, `("Stato degli interni", 1.2)`, `("Zona / Quartiere", 1.3)`, `("Trasporti", 1.0)`, `("Silenzio (no rumore)", 0.9)`, `("Potenziale rivendita", 1.1)`.
- `valutazioni` — per-property × per-criterion `(peso, voto)` rows, unique on `(immobile_id, criterio)`, cascade-deleted with the property.

Key DB patterns:
- `insert_immobile` immediately creates a `valutazioni` row for every existing criterion (`voto=0`). `valutazione.render` back-fills if criteria were added after property creation.
- `weighted_score(valutazioni)` ignores votes ≤ 0 and returns `None` when nothing has been voted. Guard against `None` at every call site.
- `bulk_upsert_valutazioni` is the preferred write path for the evaluation widget — it diffs before writing to avoid unnecessary cache invalidations.
- Schema migrations: `CREATE TABLE IF NOT EXISTS` won't add new columns to existing tables. Add `ALTER TABLE … ADD COLUMN` inside `init_db()` for new columns, or document that users must delete `casascore.db`.

### Formatters — `formatters.py`

Shared helpers consumed by all components. Never inline format logic — extend this module instead.

| Function | Purpose |
|---|---|
| `fmt_eur(v)` | Italian currency: `1234567` → `"€ 1.234.567"`. `None`/non-numeric → `"—"` |
| `fmt_int(v, suffix)` | Integer with optional suffix; `None` → `"—"` |
| `fmt_score(v)` | One-decimal score; `None` → `"—"` |
| `status(stato)` | Resolve status id → full record dict (falls back to `"visit"`) |
| `status_label(stato)` | `"❤️ Preferito"` style string |
| `status_pill_html(stato)` | `<span class="cs-pill cs-pill-{id}">…</span>` |
| `metric_card(label, value, accent)` | `.cs-metric` tile — use for per-property facts (immobili page) |
| `stat_card(label, value, accent)` | `.cs-stat` tile — use for aggregate stats (dashboard strip) |

### Components — `components/`

Each module exposes a top-level `render(...)` function. Components that take the full `immobile` dict (not just the ID) are `valutazione.render(immobile)` and `mutuo.render(immobile)` — both `@st.fragment`-wrapped. The pure amortization function `mutuo.calc_rata` is imported directly by `calcolatore.py` (that page makes no DB reads or writes).

### Design system — `assets/styles.css`

CSS custom properties on `:root`:

| Variable | Role |
|---|---|
| `--bg` `--surface` | Page / card backgrounds |
| `--ink` `--ink-soft` `--muted` | Text hierarchy |
| `--line` `--line-strong` | Borders and dividers |
| `--sage` `--sage-deep` `--sage-soft` | Primary brand colour (green) |
| `--dusty` `--dusty-soft` | Secondary accent (blue-grey) |
| `--warn` `--warn-soft` | Warning / visited state |
| `--rose` `--rose-soft` | Danger / rejected state |

Key CSS classes to reuse:

| Class | Purpose |
|---|---|
| `.cs-card` / `.cs-card-body` | Container card |
| `.cs-page-head` | Page title + subtitle block |
| `.cs-section-title` | Section header within a page |
| `.cs-display` | Large display `h1` |
| `.cs-sub` / `.cs-help` | Subtitle / helper text |
| `.cs-metric` / `.cs-metric-label` / `.cs-metric-value` | Stat tile (via `formatters.metric_card`) |
| `.cs-stat` / `.cs-stat-accent` | Aggregate stat tile (via `formatters.stat_card`) |
| `.cs-score-card` / `.cs-score-ring` | Weighted score display with CSS ring |
| `.cs-pill` / `.cs-pill-{status_id}` | Status badge (visit/visited/favorite/rejected) |
| `.cs-empty` | Empty-state placeholder block |
| `.cs-brand` / `.cs-brand-tag` | Sidebar logo and tagline |
| `.cs-danger-zone` | Red-tinted button wrapper |
| `.cs-photo-preview` | Full-width photo container |
| `.cs-crit-name` / `.cs-cap` / `.cs-val` | Criterion label / caption / value text |

CSS lives in `assets/styles.css`, not in Python. New components must reuse existing `.cs-*` classes. Do not add inline styles — extend the CSS file if a genuinely new class is needed.

## Italian localisation & legal context

This app targets the Italian residential real estate market. Every feature must be consistent with Italian language conventions, number formats, and the regulatory framework that governs Italian property transactions.

### Language — non-negotiable rules

**Every user-facing string must be in Italian.** Labels, buttons, errors, tooltips, empty-state copy, toast notifications — never English.

**Domain vocabulary is fixed.** Use these Italian terms exactly:

| Italian term | Meaning |
|---|---|
| `immobile` | property / real-estate unit |
| `scheda` | property record / data sheet |
| `criterio` / `criteri` | scoring criterion / criteria |
| `valutazione` | evaluation / scoring session |
| `voto` | score / rating (1–5 per criterion) |
| `peso` | weight (multiplier applied to a voto) |
| `punteggio` | computed weighted score |
| `prezzo` | asking price |
| `mq` | square metres (metri quadri) |
| `locali` | number of rooms |
| `piano` | floor |
| `ascensore` | lift / elevator |
| `posto auto` | parking space |
| `giardino` | outdoor area type (`"Nessuno"`, `"Balcone"`, `"Terrazzo"`, or `"Giardino"`) |
| `spese condominiali` | condominium maintenance fees |
| `classe energetica` | energy performance class |
| `mutuo` | mortgage |
| `rata` | monthly instalment |
| `anticipo` | down payment |
| `tasso` | interest rate |
| `indirizzo` | address |
| `note` | free-text notes |
| `stato` | property status in the workflow |

**Status labels** (`da visitare`, `visitato`, `preferito`, `scartato`) are defined in `db.STATUSES` and rendered via `formatters.status_label`. Never hard-code them in components.

### Number and currency formatting

Italian convention: **periods are thousands separators, commas are decimal separators** (`€ 1.234.567,00`). The app displays only integer euro amounts, but never use Python's default `f"{n:,}"` (produces `1,234,567`).

- Always use `formatters.fmt_eur(v)` for euro amounts.
- Always use `formatters.fmt_int(v, suffix)` for unit quantities (mq, locali, anni).
- Use `f"{n:,}".replace(",", ".")` if you must format inline.
- The em dash `"—"` is the canonical placeholder for missing/null values.

### Energy performance class (classe energetica)

`ENERGY_CLASSES` in `scheda.py` must always be ordered best → worst: `["A4","A3","A2","A1","A","B","C","D","E","F","G"]`. This order follows *Decreto Ministeriale 26 giugno 2015* under *D.Lgs. 192/2005*. Do not reorder and do not invent classes.

### Condominium fees (spese condominiali)

`spese_cond` stores the monthly fee in euros (`€/mese`). Governed by *artt. 1117–1139 del Codice Civile* and *Legge 220/2012*. The app stores a single combined figure (ordinary + extraordinary). If ever split, the terms `ordinarie` / `straordinarie` must match Italian condominium law exactly.

### Mortgage calculator (mutuo)

`calc_rata` implements **ammortamento alla francese** (French / constant-instalment amortization) — the standard Italian bank mortgage structure.

| Field | Italian term | Notes |
|---|---|---|
| `mutuo_anticipo` | anticipo / acconto | Down payment %. Italian banks typically cap LTV at 80% (Banca d'Italia *Circolare 285/2013*), so min anticipo is 20%. Slider max is 80%. |
| `mutuo_tasso` | TAN | Nominal annual rate. Not the TAEG (which includes fees). Label explicitly if TAEG is ever added. |
| `mutuo_anni` | durata | Loan term in years. Typical Italian range 5–30; slider allows up to 40. |

Display results with: `rata mensile`, `capitale finanziato`, `anticipo`, `interessi totali`.

### Property status workflow

| ID | Italian label | Meaning |
|---|---|---|
| `visit` | Da visitare | Shortlisted — visit not yet scheduled |
| `visited` | Visitato | Visit completed, still under evaluation |
| `favorite` | Preferito | Serious candidate |
| `rejected` | Scartato | Ruled out |

Status IDs are English slugs for code clarity; users always see the Italian label. Keep this separation intact.

## Conventions

- **Widget keys are namespaced by `immobile_id`** (e.g. `f"voto_{immobile['id']}_{criterio}"`). This prevents state collisions when multiple properties appear on the same page.
- **Navigate with `st.switch_page`**, not `st.rerun()`: `st.switch_page(st.session_state["pages"]["<key>"])`.
- **Do not call `st.cache_data.clear()` directly from components** — go through a `db.*` write function that calls `_invalidate()`.
- **Apply `@st.fragment`** to any new widget-heavy component where full-page reruns would feel sluggish.
