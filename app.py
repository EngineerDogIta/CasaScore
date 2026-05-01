"""CasaScore — Streamlit entry point.

Sets up the page, loads the design-system CSS, then defers to
`st.navigation` for routing (URL-based, with the official multipage
pattern from docs.streamlit.io).
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import db
import nav

STYLES_PATH = Path(__file__).resolve().parent / "assets" / "styles.css"


# =============================================================== bootstrap ===

st.set_page_config(
    page_title="CasaScore — Trova la tua prima casa",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()


@st.cache_data(show_spinner=False)
def _load_styles() -> str:
    return STYLES_PATH.read_text(encoding="utf-8")


st.markdown(f"<style>{_load_styles()}</style>", unsafe_allow_html=True)


# =================================================================== state ===

st.session_state.setdefault("selected_id", None)
st.session_state.setdefault("edit_id", None)


# =============================================================== sidebar 1 ===
# Brand mark — must render before `st.navigation` so it appears at the top.

with st.sidebar:
    st.markdown(
        '<div class="cs-brand">Casa<em>Score</em></div>'
        '<div class="cs-brand-tag">La tua prima casa, valutata bene.</div>',
        unsafe_allow_html=True,
    )


# ============================================================== navigation ===

st.session_state["pages"] = nav.build()
selected = st.navigation(list(st.session_state["pages"].values()))


# =============================================================== sidebar 2 ===
# Custom controls below the auto-generated nav widget.

with st.sidebar:
    immobili_list = db.list_immobili()
    st.markdown(
        f'<div class="cs-section-title" style="margin-top:.5rem">'
        f'Archivio · {len(immobili_list)}</div>',
        unsafe_allow_html=True,
    )

    if immobili_list:
        sel_options = [im["id"] for im in immobili_list]
        sel_labels = {
            im["id"]: f"{im['label']}  ·  €  {int(im['prezzo'] or 0):,}".replace(",", ".")
            for im in immobili_list
        }
        try:
            idx = sel_options.index(st.session_state["selected_id"])
        except (ValueError, TypeError):
            idx = 0
        chosen = st.selectbox(
            "Apri immobile", sel_options,
            index=idx,
            format_func=lambda x: sel_labels[x],
            label_visibility="collapsed",
            key="sidebar_property_picker",
        )
        if chosen != st.session_state["selected_id"]:
            st.session_state["selected_id"] = chosen
            st.switch_page(st.session_state["pages"]["immobili"])
    else:
        st.markdown(
            '<p style="font-size:.82rem;color:var(--muted)">'
            'Nessun immobile ancora.</p>',
            unsafe_allow_html=True,
        )

    if st.button("＋ Nuova scheda", use_container_width=True, type="primary"):
        st.session_state["edit_id"] = None
        st.switch_page(st.session_state["pages"]["scheda"])


# =================================================================== run ===

selected.run()
