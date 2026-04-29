"""CasaScore — Streamlit entry point.

Sidebar-driven navigation across:
  * Dashboard (comparison)
  * Immobili (per-property detail w/ scoring + mortgage)
  * Nuovo / Modifica (form)
  * Calcolatore (standalone mortgage)
  * Impostazioni (default criteria preview)
"""
from __future__ import annotations

import streamlit as st

import db
from components import dashboard, mutuo, scheda, valutazione

st.set_page_config(
    page_title="CasaScore — Trova la tua prima casa",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()


# ============================================================ THEME / CSS ===

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #FAFAF7;
  --surface: #FFFFFF;
  --ink: #1C1C1A;
  --ink-soft: #4B4B47;
  --muted: #8A8A82;
  --line: #E8E6DF;
  --line-strong: #D4D2CA;
  --sage: #8FA694;
  --sage-deep: #5D7560;
  --sage-soft: #ECF0E9;
  --dusty: #9AABC4;
  --dusty-soft: #ECEFF5;
  --warn: #C99A57;
  --warn-soft: #F6EFE1;
  --rose: #C0806F;
  --rose-soft: #F5E8E4;
}

/* App background and base font */
html, body, [class*="css"], .stApp, .main, .block-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  color: var(--ink);
}
.stApp { background: var(--bg); }

/* Subtle dot grain (matches design) */
.stApp::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: radial-gradient(rgba(0,0,0,0.018) 1px, transparent 1px);
  background-size: 3px 3px; opacity: 0.5;
}

.block-container {
  padding-top: 2.2rem !important;
  padding-bottom: 4rem !important;
  max-width: 1280px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  font-family: 'Instrument Serif', Georgia, serif;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin-bottom: .25rem;
}

/* Headings */
.cs-display {
  font-family: 'Instrument Serif', Georgia, serif;
  font-weight: 400;
  letter-spacing: -0.015em;
  font-size: 2.4rem;
  line-height: 1.05;
  color: var(--ink);
  margin: 0 0 .35rem 0;
}
.cs-page-head { margin-bottom: 1.5rem; }
.cs-sub { color: var(--ink-soft); font-size: .95rem; margin: 0; }

.cs-section-title {
  font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-soft);
  margin: 1.4rem 0 .8rem 0;
}
.cs-help { font-size: 12px; color: var(--muted); margin: -.5rem 0 1rem 0; }

/* Inputs — soft, rounded, sage focus */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div, .stDateInput input {
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  color: var(--ink) !important;
  font-size: 14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus,
.stNumberInput input:focus {
  border-color: var(--sage) !important;
  box-shadow: 0 0 0 3px rgba(143,166,148,0.18) !important;
}
/* Field labels above inputs — uppercase but with strong contrast */
.stTextInput > label, .stTextArea > label, .stNumberInput > label,
.stSelectbox > label, .stSlider > label, .stDateInput > label,
.stMultiSelect > label, .stRadio > label, .stFileUploader > label,
[data-testid="stWidgetLabel"] > label,
[data-testid="stWidgetLabel"] {
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  color: var(--ink) !important;
  text-transform: uppercase !important;
  opacity: 1 !important;
}
.stTextInput > label p, .stTextArea > label p, .stNumberInput > label p,
.stSelectbox > label p, .stSlider > label p, .stDateInput > label p,
.stRadio > label p, [data-testid="stWidgetLabel"] p {
  color: var(--ink) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}

/* Checkbox: label is the field's purpose — readable, NOT uppercased */
.stCheckbox label, .stCheckbox label p,
.stCheckbox [data-testid="stWidgetLabel"],
.stCheckbox [data-testid="stWidgetLabel"] p {
  color: var(--ink) !important;
  font-size: 14px !important;
  font-weight: 400 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
}

/* Radio options (the choices, not the group label): inherit normal style */
.stRadio [role="radiogroup"] label,
.stRadio [role="radiogroup"] label p,
.stRadio [role="radiogroup"] label div {
  color: var(--ink) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  opacity: 1 !important;
}

/* Sidebar nav radio: bigger, dark, no uppercase */
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label,
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label p,
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label div {
  color: var(--ink) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  letter-spacing: 0.01em !important;
  text-transform: none !important;
  opacity: 1 !important;
}

/* Stronger placeholder contrast */
.stTextInput input::placeholder, .stTextArea textarea::placeholder,
.stNumberInput input::placeholder {
  color: #a8a89f !important;
  opacity: 1 !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--line) !important;
  background: var(--surface) !important;
  color: var(--ink) !important;
  font-weight: 500 !important;
  font-size: 14px !important;
  padding: .55rem 1rem !important;
  transition: all .15s !important;
}
.stButton > button:hover {
  border-color: var(--line-strong) !important;
  background: var(--bg) !important;
}
.stButton > button[kind="primary"], .stFormSubmitButton button {
  background: var(--sage-deep) !important;
  color: #fff !important;
  border-color: var(--sage-deep) !important;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton button:hover {
  background: #4d6450 !important;
  border-color: #4d6450 !important;
}

/* Sliders — sage filled track, neutral thumb tooltip and end-ticks */
.stSlider [data-baseweb="slider"] > div > div { background: var(--sage-deep) !important; }
.stSlider [role="slider"] {
  background: var(--sage-deep) !important;
  border: 3px solid var(--surface) !important;
  box-shadow: 0 0 0 1px var(--sage-deep) !important;
}
/* Min / max ticks at slider ends — kill the colored chip, plain text */
[data-testid="stTickBar"], [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {
  background: transparent !important;
  color: var(--muted) !important;
  font-size: 11px !important;
  font-weight: 400 !important;
  font-variant-numeric: tabular-nums;
}
/* Current value bubble above the thumb — sage instead of red */
[data-testid="stThumbValue"] {
  background: transparent !important;
  color: var(--sage-deep) !important;
  font-weight: 600 !important;
  font-variant-numeric: tabular-nums;
}

/* Number input stepper (+/-) — quiet light buttons, not heavy black */
.stNumberInput button,
[data-testid="stNumberInputStepUp"],
[data-testid="stNumberInputStepDown"] {
  background: var(--bg) !important;
  color: var(--ink-soft) !important;
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
.stNumberInput button:hover,
[data-testid="stNumberInputStepUp"]:hover,
[data-testid="stNumberInputStepDown"]:hover {
  background: var(--surface) !important;
  border-color: var(--line-strong) !important;
  color: var(--ink) !important;
}
.stNumberInput button svg, .stNumberInput button path {
  fill: currentColor !important;
}

/* Radio (horizontal) */
.stRadio [role="radiogroup"] { gap: .25rem; }
.stRadio label[data-baseweb="radio"] {
  background: var(--surface);
  border: 1px solid var(--line);
  padding: .35rem .8rem;
  border-radius: 8px;
}

/* Generic card */
.cs-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 1rem;
  transition: border-color .15s;
}
.cs-card:hover { border-color: var(--line-strong); }
.cs-card-photo { height: 160px; background: repeating-linear-gradient(135deg, #F0EEE6 0 12px, #E8E6DF 12px 24px); }
.cs-card-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cs-card-body { padding: 1rem 1.1rem 1.1rem; }
.cs-card-row1 { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: .9rem; }
.cs-card-label { font-size: 1.05rem; font-weight: 600; color: var(--ink); line-height: 1.2; }
.cs-card-addr { font-size: .82rem; color: var(--muted); margin-top: .15rem; }

.cs-card-score {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.9rem; line-height: 1;
  color: var(--sage-deep);
  white-space: nowrap;
}
.cs-card-score span { font-size: .9rem; color: var(--muted); margin-left: 2px; }
.cs-card-score-empty { color: var(--muted); }

.cs-card-stats {
  display: grid; grid-template-columns: repeat(2, 1fr);
  gap: .55rem .8rem; padding: .8rem; background: var(--bg);
  border-radius: 10px;
}
.cs-card-stats > div { display: flex; justify-content: space-between; align-items: baseline; font-size: .82rem; }
.cs-cap { color: var(--muted); }
.cs-val { color: var(--ink); font-weight: 500; font-variant-numeric: tabular-nums; }
.cs-card-foot { margin-top: .9rem; display: flex; gap: .5rem; align-items: center; }

/* Status pill */
.cs-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 500;
}
.cs-pill-visit { background: var(--dusty-soft); color: #4d6480; }
.cs-pill-visited { background: var(--warn-soft); color: #8a6328; }
.cs-pill-favorite { background: var(--rose-soft); color: #8b4a3c; }
.cs-pill-rejected { background: #ECECEC; color: #555; }

/* Stats strip */
.cs-stat {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; padding: 1rem 1.1rem;
}
.cs-stat-accent { background: var(--sage-soft); border-color: var(--sage-soft); }
.cs-stat-label {
  font-size: 11px; font-weight: 500; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-soft); margin-bottom: .35rem;
}
.cs-stat-value {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.65rem; color: var(--ink); line-height: 1.1;
}

/* Score card on detail page */
.cs-score-card {
  display: flex; align-items: center; gap: 1.2rem;
  padding: 1.2rem 1.4rem;
  background: var(--sage-soft);
  border: 1px solid #d8e2d4;
  border-radius: 16px;
  margin: 1rem 0 .5rem;
}
.cs-score-ring {
  --pct: 0%;
  width: 84px; height: 84px; border-radius: 50%; flex-shrink: 0;
  background: conic-gradient(var(--sage-deep) var(--pct), #d8e2d4 0);
  display: flex; align-items: center; justify-content: center;
}
.cs-score-ring-inner {
  width: 70px; height: 70px; background: var(--surface);
  border-radius: 50%; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.cs-score-num {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.55rem; line-height: 1; color: var(--ink);
}
.cs-score-cap { font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin-top: 2px; }
.cs-score-text .cs-score-title {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.3rem; color: var(--ink);
}
.cs-score-text .cs-score-sub { font-size: .85rem; color: var(--ink-soft); }
.cs-score-empty { background: var(--bg); border-color: var(--line); justify-content: center; }

/* Criterion row */
.cs-crit-name {
  font-size: .92rem; color: var(--ink); font-weight: 500;
  padding-top: .4rem;
}

/* Photo preview */
.cs-photo-preview {
  border-radius: 14px; overflow: hidden; margin-bottom: 1rem;
  border: 1px solid var(--line);
  max-height: 280px;
}
.cs-photo-preview img { width: 100%; max-height: 280px; object-fit: cover; display: block; }

/* Mortgage metric tiles */
.cs-metric {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 12px; padding: .8rem 1rem;
}
.cs-metric-label {
  font-size: 10px; font-weight: 500; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin-bottom: .3rem;
}
.cs-metric-value {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.4rem; line-height: 1.1; color: var(--ink);
  font-variant-numeric: tabular-nums;
}

/* Empty state */
.cs-empty {
  border: 1.5px dashed var(--line-strong);
  border-radius: 14px; padding: 3rem 1.5rem;
  text-align: center; color: var(--muted);
  background: var(--surface);
}

/* Detail header */
.cs-detail-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 1.5rem; margin-bottom: 1.4rem;
}

/* Tighten markdown spacing inside columns */
.element-container hr { display: none; }

/* Hide Streamlit chrome we don't want */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* Brand mark */
.cs-brand {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.7rem; line-height: 1;
  margin: 0 0 .2rem 0;
}
.cs-brand em { font-style: italic; color: var(--sage-deep); }
.cs-brand-tag { font-size: .8rem; color: var(--muted); margin-bottom: 1.2rem; }

/* Selectbox dropdown */
div[data-baseweb="popover"] { border-radius: 10px !important; }

/* Danger button — used by the Elimina action via session state */
.cs-danger-zone .stButton > button {
  color: var(--rose) !important;
  border-color: var(--line) !important;
  background: var(--surface) !important;
}
.cs-danger-zone .stButton > button:hover {
  background: var(--rose-soft) !important;
  border-color: var(--rose) !important;
  color: #8b4a3c !important;
}

/* Slider value bubble in older/newer DOM variants — catch-all */
.stSlider [data-baseweb="slider"] [role="slider"] + div,
.stSlider [data-baseweb="slider"] > div > div + div {
  color: var(--sage-deep) !important;
}

/* Form submit visually balanced */
.stFormSubmitButton button { padding: .6rem 1.4rem !important; }

/* Quieter dataframe header */
.stDataFrame thead tr th {
  background: var(--bg) !important;
  color: var(--ink-soft) !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 11px !important;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ============================================================== STATE ===

if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"
if "selected_id" not in st.session_state:
    st.session_state["selected_id"] = None
if "edit_id" not in st.session_state:
    st.session_state["edit_id"] = None


# ============================================================ SIDEBAR ===

with st.sidebar:
    st.markdown(
        '<div class="cs-brand">Casa<em>Score</em></div>'
        '<div class="cs-brand-tag">La tua prima casa, valutata bene.</div>',
        unsafe_allow_html=True,
    )

    pages = ["Dashboard", "Immobili", "Nuovo / Modifica",
             "Calcolatore", "Impostazioni"]
    current = st.session_state["page"]
    if current not in pages:
        current = "Dashboard"
    choice = st.radio(
        "Sezioni", pages, index=pages.index(current),
        label_visibility="collapsed",
    )
    if choice != st.session_state["page"]:
        st.session_state["page"] = choice
        st.rerun()

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    immobili = [dict(r) for r in db.list_immobili()]
    st.markdown(
        f'<div class="cs-section-title" style="margin-top:.5rem">'
        f'Archivio · {len(immobili)}</div>',
        unsafe_allow_html=True,
    )
    if immobili:
        sel_options = [im["id"] for im in immobili]
        sel_labels = {im["id"]: f"{im['label']}  ·  € {int(im['prezzo'] or 0):,}".replace(",", ".")
                      for im in immobili}
        try:
            idx = sel_options.index(st.session_state["selected_id"])
        except (ValueError, TypeError):
            idx = 0
        chosen = st.selectbox(
            "Apri immobile", sel_options,
            index=idx,
            format_func=lambda x: sel_labels[x],
            label_visibility="collapsed",
        )
        if chosen != st.session_state["selected_id"]:
            st.session_state["selected_id"] = chosen
            st.session_state["page"] = "Immobili"
            st.rerun()
    else:
        st.markdown('<p style="font-size:.82rem;color:var(--muted)">'
                    'Nessun immobile ancora.</p>', unsafe_allow_html=True)

    if st.button("＋ Nuova scheda", use_container_width=True, type="primary"):
        st.session_state["edit_id"] = None
        st.session_state["page"] = "Nuovo / Modifica"
        st.rerun()


# ============================================================ ROUTER ===

page = st.session_state["page"]

if page == "Dashboard":
    dashboard.render()

elif page == "Immobili":
    immobili = [dict(r) for r in db.list_immobili()]
    if not immobili:
        st.markdown(
            """
            <div class="cs-page-head">
              <h1 class="cs-display">Immobili</h1>
              <p class="cs-sub">Apri una scheda per valutarla, simulare il mutuo e tenere traccia dello stato.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="cs-empty">Non hai ancora aggiunto immobili. '
            'Crea la prima scheda dalla sidebar.</div>',
            unsafe_allow_html=True,
        )
    else:
        ids = [im["id"] for im in immobili]
        if st.session_state["selected_id"] not in ids:
            st.session_state["selected_id"] = ids[0]
        current = next(im for im in immobili
                       if im["id"] == st.session_state["selected_id"])

        # Header with title + status pill + edit button
        STATUS_BY_ID = {s["id"]: s for s in db.STATUSES}
        s = STATUS_BY_ID.get(current["stato"] or "visit", db.STATUSES[0])

        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(
                f"""
                <div class="cs-page-head">
                  <div style="display:flex;align-items:center;gap:.8rem;flex-wrap:wrap">
                    <h1 class="cs-display" style="margin:0">{current["label"]}</h1>
                    <span class="cs-pill cs-pill-{s['id']}">
                      <span>{s['emoji']}</span><span>{s['label']}</span>
                    </span>
                  </div>
                  <p class="cs-sub">{current["indirizzo"] or ""}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_b:
            if st.button("Modifica", use_container_width=True,
                         key="detail_edit"):
                st.session_state["edit_id"] = current["id"]
                st.session_state["page"] = "Nuovo / Modifica"
                st.rerun()
            st.markdown('<div class="cs-danger-zone">', unsafe_allow_html=True)
            if st.button("Elimina", use_container_width=True,
                         key="detail_delete"):
                db.delete_immobile(current["id"])
                st.session_state["selected_id"] = None
                st.session_state["page"] = "Dashboard"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Photo
        if current.get("foto_url"):
            st.markdown(
                f'<div class="cs-photo-preview"><img src="{current["foto_url"]}" '
                f'onerror="this.parentElement.style.display=\'none\'"/></div>',
                unsafe_allow_html=True,
            )

        # Quick facts
        st.markdown('<div class="cs-section-title">Dati chiave</div>',
                    unsafe_allow_html=True)
        facts = [
            ("Prezzo", f"€ {int(current['prezzo'] or 0):,}".replace(",", ".")),
            ("Superficie", f"{int(current['mq'] or 0)} mq"),
            ("€/mq", (f"€ {int(current['prezzo']/current['mq']):,}".replace(",", ".")
                     if current['prezzo'] and current['mq'] else "—")),
            ("Locali", str(current["locali"] or "—")),
            ("Piano", current["piano"] or "—"),
            ("Anno", str(current["anno"] or "—")),
            ("Classe en.", current["classe_energetica"] or "—"),
            ("Spese cond.", f"€ {int(current['spese_cond'] or 0)}/mese"),
        ]
        rows = st.columns(4)
        for i, (k, v) in enumerate(facts):
            rows[i % 4].markdown(
                f'<div class="cs-metric"><div class="cs-metric-label">{k}</div>'
                f'<div class="cs-metric-value">{v}</div></div>',
                unsafe_allow_html=True,
            )

        extras = []
        if current["ascensore"]: extras.append("Ascensore")
        if current["posto_auto"]: extras.append("Posto auto")
        if current["giardino"] and current["giardino"] != "Nessuno":
            extras.append(current["giardino"])
        if extras:
            st.markdown(
                "<div style='margin-top:.9rem;display:flex;gap:.5rem;flex-wrap:wrap'>"
                + "".join(
                    f'<span class="cs-pill" style="background:var(--bg);'
                    f'border:1px solid var(--line);color:var(--ink-soft)">{e}</span>'
                    for e in extras
                )
                + "</div>",
                unsafe_allow_html=True,
            )

        if current["note"]:
            st.markdown('<div class="cs-section-title">Note</div>',
                        unsafe_allow_html=True)
            st.markdown(
                f'<div class="cs-card"><div class="cs-card-body" '
                f'style="white-space:pre-wrap;font-size:.92rem;color:var(--ink-soft)">'
                f'{current["note"]}</div></div>',
                unsafe_allow_html=True,
            )

        # Valutazione + mortgage
        valutazione.render(current)
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        # Re-fetch updated mortgage fields
        fresh = dict(db.get_immobile(current["id"]))
        mutuo.render(fresh)

elif page == "Nuovo / Modifica":
    scheda.render(st.session_state.get("edit_id"))

elif page == "Calcolatore":
    st.markdown(
        """
        <div class="cs-page-head">
          <h1 class="cs-display">Calcolatore mutuo</h1>
          <p class="cs-sub">Stima rapida della rata mensile a tasso fisso (ammortamento alla francese).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        prezzo = st.number_input("Valore immobile (€)", min_value=0,
                                 value=300000, step=10000)
        anticipo = st.slider("Anticipo %", 0, 80, 20, step=5)
    with c2:
        anni = st.slider("Durata (anni)", 5, 40, 25, step=5)
        tasso = st.slider("Tasso annuo %", 0.5, 8.0, 3.5, step=0.1)

    res = mutuo.calc_rata(prezzo, anticipo, anni, tasso)
    st.markdown('<div class="cs-section-title">Risultato</div>',
                unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(
        f'<div class="cs-metric"><div class="cs-metric-label">Rata mensile</div>'
        f'<div class="cs-metric-value" style="color:var(--sage-deep)">'
        f'€ {res["rata"]:,.0f}</div></div>'.replace(",", "."),
        unsafe_allow_html=True,
    )
    m2.markdown(
        f'<div class="cs-metric"><div class="cs-metric-label">Capitale finanziato</div>'
        f'<div class="cs-metric-value">€ {res["capitale"]:,.0f}</div></div>'.replace(",", "."),
        unsafe_allow_html=True,
    )
    m3.markdown(
        f'<div class="cs-metric"><div class="cs-metric-label">Anticipo</div>'
        f'<div class="cs-metric-value">€ {res["anticipo"]:,.0f}</div></div>'.replace(",", "."),
        unsafe_allow_html=True,
    )
    m4.markdown(
        f'<div class="cs-metric"><div class="cs-metric-label">Interessi totali</div>'
        f'<div class="cs-metric-value">€ {res["interessi"]:,.0f}</div></div>'.replace(",", "."),
        unsafe_allow_html=True,
    )

elif page == "Impostazioni":
    st.markdown(
        """
        <div class="cs-page-head">
          <h1 class="cs-display">Criteri di valutazione</h1>
          <p class="cs-sub">Pesi di default applicati a ogni nuova scheda. I pesi possono essere modificati per ciascun immobile.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    crits = list(db.list_criteri())
    rows_html = "".join(
        f'<div class="cs-card-stats" style="grid-template-columns:3fr 1fr;'
        f'margin-bottom:.5rem">'
        f'<div><span class="cs-cap">Criterio</span>'
        f'<span class="cs-val">{c["nome"]}</span></div>'
        f'<div><span class="cs-cap">Peso</span>'
        f'<span class="cs-val">{c["peso_default"]:.1f}</span></div>'
        f'</div>'
        for c in crits
    )
    st.markdown(
        f'<div class="cs-card"><div class="cs-card-body">{rows_html}</div></div>',
        unsafe_allow_html=True,
    )
