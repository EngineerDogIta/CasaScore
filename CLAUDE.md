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

### File map

```
app.py                  Entry point — bootstrap, CSS injection, sidebar, st.navigation router
nav.py                  Page registry — builds the dict passed to st.navigation
db.py                   SQLite layer — schema, seed data, CRUD, caching, scoring
formatters.py           Shared HTML/text formatters for currency, scores, status pills
assets/styles.css       Full design-system CSS (~400 lines) — loaded once, cached
components/
  dashboard.py          Comparative view: stat strip, cards/table, filters, sort
  immobili.py           Per-property detail page: facts, extras, notes, delete dialog
  scheda.py             Add/edit form (anagrafica, caratteristiche, stato, media)
  valutazione.py        Per-criterion 1–5 sliders + per-property weight overrides
  mutuo.py              French-amortization calculator — inline per-property block
  calcolatore.py        Standalone mortgage calculator page (stateless, no DB)
  impostazioni.py       Read-only preview of scoring criteria and default weights
  __init__.py           Empty — makes components/ a package
.streamlit/config.toml  Theme (sage palette) and server settings
```

### Entry point — [app.py](app.py)

- Calls `db.init_db()` on every script run (idempotent).
- Loads `assets/styles.css` into a `<style>` block via `@st.cache_data` so the file is read once.
- Initialises `st.session_state` defaults: `selected_id`, `edit_id`.
- Renders the brand mark in the sidebar *before* `st.navigation` so it appears above the auto-generated nav links.
- Uses `st.navigation(list(pages.values()))` for URL-based routing. The page dict is built by `nav.build()` and stored on `st.session_state["pages"]` so any component can call `st.switch_page(st.session_state["pages"]["<key>"])`.
- Renders a property picker `st.selectbox` + "＋ Nuova scheda" button in the sidebar below the nav widget.

### Page registry — [nav.py](nav.py)

`build()` returns a `dict[str, st.Page]` keyed by short names (`"dashboard"`, `"immobili"`, `"scheda"`, `"calcolatore"`, `"impostazioni"`). The `scheda` entry uses a thin `_scheda_page` adapter that reads `edit_id` from session state, because `st.Page` callables take no arguments.

### Persistence — [db.py](db.py)

- SQLite at `casascore.db` (gitignored). Connections are short-lived via `get_conn()`, a context manager that sets `row_factory = sqlite3.Row`, enables foreign keys, and auto-commits on exit.
- Read helpers (`list_immobili`, `get_immobile`, `list_criteri`, `get_valutazioni`, `score_for`) are decorated with `@st.cache_data`. Every write calls `_invalidate()` which calls `st.cache_data.clear()`, keeping the cache coherent.
- Three tables:
  - `immobili` — property record + per-property mortgage slider state (`mutuo_anticipo`, `mutuo_anni`, `mutuo_tasso`).
  - `criteri` — named scoring criteria with `peso_default`. Seeded from `DEFAULT_CRITERIA` on every `init_db()` call (additive only — existing rows are never touched).
  - `valutazioni` — per-property × per-criterion `(peso, voto)` rows, unique on `(immobile_id, criterio)`, cascade-deleted when the property is deleted.
- `DEFAULT_CRITERIA` and `STATUSES` are the canonical source of truth for scoring dimensions and property states (`visit` / `visited` / `favorite` / `rejected`). Status IDs are stored as strings.
- `insert_immobile` immediately creates a `valutazioni` row for every existing criterion (`voto=0`). `valutazione.render` back-fills if criteria were added after the property was created.
- `weighted_score(valutazioni)` ignores votes ≤ 0 and returns `None` when nothing has been voted. UI must handle the `None` case everywhere.
- `bulk_upsert_valutazioni` is the preferred write path for the evaluation widget — it diffs before writing to avoid unnecessary cache invalidations.

### Formatters — [formatters.py](formatters.py)

Shared helpers consumed by all components. Never inline format logic in new code — extend this module instead.

| Function | Purpose |
|---|---|
| `fmt_eur(v)` | Italian currency: `1234567` → `"€ 1.234.567"`. `None`/non-numeric → `"—"` |
| `fmt_int(v, suffix)` | Integer with optional suffix; `None` → `"—"` |
| `fmt_score(v)` | One-decimal score; `None` → `"—"` |
| `status(stato)` | Resolve status id → full record dict (falls back to `"visit"`) |
| `status_label(stato)` | `"❤️ Preferito"` style string |
| `status_pill_html(stato)` | `<span class="cs-pill cs-pill-{id}">…</span>` |
| `metric_card(label, value, accent)` | `.cs-metric` tile as raw HTML |
| `stat_card(label, value, accent)` | `.cs-stat` tile as raw HTML |

### Components — [components/](components/)

Each module exposes a top-level `render(...)` function called by the router.

**[dashboard.py](components/dashboard.py)** — comparative view. Builds a pandas DataFrame from `db.list_immobili()` + `db.score_for()`. Renders a 4-column aggregate strip, then filter/sort controls (status, sort key, card/table toggle), then either `_render_cards` (2-column grid) or `_render_table` (st.dataframe with column configs).

**[immobili.py](components/immobili.py)** — per-property detail. Reads `selected_id` from session state. Renders header (label + status pill + Modifica/Elimina buttons), optional photo, facts grid (8 metrics in 4 columns), extras pills (ascensore/posto auto/giardino), notes card, then delegates to `valutazione.render` and `mutuo.render`. Delete uses `@st.dialog` for a confirmation modal.

**[scheda.py](components/scheda.py)** — add/edit form. `render(immobile_id | None)`; `None` means new property. Uses a single `st.form` to batch all inputs. Required fields: `label`, `indirizzo`, `prezzo > 0`, `mq > 0`. On submit, calls `db.insert_immobile` or `db.update_immobile` then `st.switch_page("immobili")`.

**[valutazione.py](components/valutazione.py)** — scoring widget. Decorated with `@st.fragment` so slider interactions only re-run this block. For each criterion: name label, peso `number_input` (0.1–3.0), voto `slider` (0–5). Diffs against last-saved state and calls `db.bulk_upsert_valutazioni` only for changed rows. Renders the score ring card at the bottom.

**[mutuo.py](components/mutuo.py)** — mortgage calculator. `calc_rata(prezzo, anticipo_pct, anni, tasso_pct)` is a pure function (French amortization). The `render(immobile)` function is `@st.fragment`-wrapped; it persists slider values back to `mutuo_*` columns only when they change.

**[calcolatore.py](components/calcolatore.py)** — standalone page. Stateless: no DB reads or writes. Calls `calc_rata` from `mutuo.py` directly.

**[impostazioni.py](components/impostazioni.py)** — read-only criteria list. Shows `nome` + `peso_default` for each criterion. Criteria can only be seeded via `DEFAULT_CRITERIA` in `db.py`; there is no add/edit UI yet.

### Design system — [assets/styles.css](assets/styles.css)

CSS custom properties (defined on `:root`):

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

## Italian localisation & legal context

This app targets the Italian residential real estate market. Every feature must be consistent with Italian language conventions, number formats, and the regulatory framework that governs Italian property transactions.

### Language — non-negotiable rules

- **Every user-facing string must be in Italian.** This includes labels, button text, error messages, tooltips, empty-state copy, and toast notifications. Never write UI text in English.
- **Domain vocabulary is fixed.** Use the Italian terms below exactly — do not substitute English synonyms, even in comments that end up in rendered text:

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
| `giardino` | garden / outdoor area |
| `spese condominiali` | condominium maintenance fees |
| `classe energetica` | energy performance class |
| `mutuo` | mortgage |
| `rata` | monthly instalment |
| `anticipo` | down payment |
| `tasso` | interest rate |
| `indirizzo` | address |
| `note` | free-text notes |
| `stato` | property status in the workflow |

- **Status labels** (`da visitare`, `visitato`, `preferito`, `scartato`) are defined in `db.STATUSES` and rendered via `formatters.status_label`. Never hard-code them in components.

### Number and currency formatting

Italian convention differs from the C/US locale: **periods are thousands separators and commas are decimal separators** (e.g. `€ 1.234.567,00`). The app displays only integer euro amounts, so commas never appear in practice, but be careful with any future decimal currency display.

- Always use `formatters.fmt_eur(v)` for euro amounts — it produces `"€ 1.234.567"`.
- Always use `formatters.fmt_int(v, suffix)` for unit quantities (mq, locali, anni).
- Never use Python's default `f"{n:,}"` (produces `1,234,567`) — replace commas with periods: `f"{n:,}".replace(",", ".")`.
- The em dash `"—"` is the canonical placeholder for missing/null values. Use it consistently.

### Energy performance class (classe energetica)

The `classe_energetica` field stores an Italian energy class label. The valid values — `A4 A3 A2 A1 A B C D E F G` — follow the **national energy classification scale** defined by the *Decreto Ministeriale 26 giugno 2015 "Linee guida nazionali per la certificazione energetica degli edifici"*, issued under *D.Lgs. 192/2005* (transposing EU Directive 2010/31/EU on the energy performance of buildings).

Key implications for the codebase:
- `ENERGY_CLASSES` in `scheda.py` must always be ordered best → worst: `["A4","A3","A2","A1","A","B","C","D","E","F","G"]`. Do not reorder.
- An APE (*Attestato di Prestazione Energetica*) is legally mandatory for any property sale or rental in Italy. If the app ever displays or validates APE data it must respect this ordering.
- Adding a new class requires checking whether Italian law has introduced it — do not invent classes.

### Condominium fees (spese condominiali)

`spese_cond` stores the monthly condominium fee in euros. These fees are governed by **artt. 1117–1139 del Codice Civile** and the *Legge 220/2012* (riforma del condominio). Key facts for any feature work:

- Fees are due monthly and split between ordinary and extraordinary maintenance. The app stores a single combined figure — a reasonable simplification for a scoring tool.
- If the app ever distinguishes ordinary (`ordinarie`) vs extraordinary (`straordinarie`) fees, the terms must match Italian condominium law usage exactly.
- The unit is always `€/mese` (euros per month) — display it that way.

### Mortgage calculator (mutuo)

`calc_rata` in `mutuo.py` implements **ammortamento alla francese** (French / constant-instalment amortization), which is the standard mortgage structure used by Italian banks.

The three parameters map to regulated concepts:

| Field | Italian term | Notes |
|---|---|---|
| `mutuo_anticipo` | anticipo / acconto | Down payment as a percentage of purchase price. Italian banks typically cap LTV at 80% (Banca d'Italia *Circolare 285/2013*, Parte Prima, Tit. IV, Cap. 3), meaning the minimum anticipo is 20%. The slider is capped at 80% (maximum anticipo) accordingly. |
| `mutuo_tasso` | TAN | *Tasso Annuo Nominale* — the nominal annual rate. This is **not** the TAEG (*Tasso Annuo Effettivo Globale*), which includes fees and charges. If the app ever adds a TAEG field, label it explicitly. |
| `mutuo_anni` | durata | Loan term in years. Italian residential mortgages typically run 5–30 years; the slider allows up to 40 for flexibility. |

When displaying mortgage results, use the Italian terms: `rata mensile`, `capitale finanziato`, `anticipo`, `interessi totali`. Do not use English equivalents.

### Property status workflow

The four statuses in `db.STATUSES` model a typical Italian buyer's decision funnel:

| ID | Italian label | Meaning |
|---|---|---|
| `visit` | Da visitare | Shortlisted — visit not yet scheduled |
| `visited` | Visitato | Visit completed, still under evaluation |
| `favorite` | Preferito | Serious candidate |
| `rejected` | Scartato | Ruled out |

Status IDs are English slugs for code clarity, but the user never sees them — they always see the Italian label. Keep this separation intact.

---

## Conventions worth knowing

- **Domain language is Italian — see the localisation section above.** Every new label, message, field name, and piece of copy must be Italian. When in doubt, refer to the vocabulary table there.
- **Widget keys are namespaced by `immobile_id`** (e.g. `f"voto_{immobile['id']}_{criterio}"`). This prevents state collisions when multiple properties appear on the same page. Always follow this pattern for new per-property widgets.
- **Navigation uses `st.switch_page`**, not `st.rerun()`. To navigate programmatically: `st.switch_page(st.session_state["pages"]["<key>"])`.
- **CSS lives in `assets/styles.css`, not in Python.** New components must reuse existing `.cs-*` classes. Do not add inline styles for layout or theming — extend the CSS file if a new class is genuinely needed.
- **Formatters are centralised in `formatters.py`.** Use `fmt_eur`, `fmt_int`, `fmt_score`, `metric_card`, `stat_card`, etc. Do not re-implement formatting logic in components.
- **`@st.fragment`** is used on `valutazione.render` and `mutuo.render` so their sliders trigger only a partial re-run of their block. Apply this decorator to any new widget-heavy component where full-page reruns would feel sluggish.
- **Cache invalidation** is via `st.cache_data.clear()` (called by `db._invalidate()` after every write). Do not call `st.cache_data.clear()` directly from components — go through a `db.*` write function.
- **Schema changes** require updating `init_db()` *and* handling existing databases. `CREATE TABLE IF NOT EXISTS` will not add new columns to an existing table. Add an explicit `ALTER TABLE … ADD COLUMN` migration inside `init_db()`, or document that users must delete `casascore.db`.
- **`weighted_score` returns `None`** when no criterion has a positive vote. Every caller must guard against `None` before rendering or arithmetic.
