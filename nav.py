"""Page registry for `st.navigation`.

Each entry is a `st.Page` wrapping a component's `render` callable. The dict
is rebuilt on every script run and stashed on `st.session_state["pages"]`
so any component can `st.switch_page(st.session_state["pages"]["<key>"])`.
"""
from __future__ import annotations

import streamlit as st

from components import calcolatore, dashboard, immobili, impostazioni, rubrica, scheda


def _scheda_page() -> None:
    """No-arg adapter — `scheda.render` reads `edit_id` from session_state."""
    scheda.render(st.session_state.get("edit_id"))


def build() -> dict[str, st.Page]:
    return {
        "dashboard": st.Page(
            dashboard.render, title="Dashboard",
            url_path="dashboard", default=True,
        ),
        "immobili": st.Page(
            immobili.render, title="Immobili",
            url_path="immobili",
        ),
        "scheda": st.Page(
            _scheda_page, title="Nuovo / Modifica",
            url_path="scheda",
        ),
        "calcolatore": st.Page(
            calcolatore.render, title="Calcolatore",
            url_path="calcolatore",
        ),
        "rubrica": st.Page(
            rubrica.render, title="Rubrica",
            url_path="rubrica",
        ),
        "impostazioni": st.Page(
            impostazioni.render, title="Impostazioni",
            url_path="impostazioni",
        ),
    }
