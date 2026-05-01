"""Impostazioni — read-only preview of the default scoring criteria."""
from __future__ import annotations

import streamlit as st

import db


def render() -> None:
    st.markdown(
        """
        <div class="cs-page-head">
          <h1 class="cs-display">Criteri di valutazione</h1>
          <p class="cs-sub">Pesi di default applicati a ogni nuova scheda. I pesi possono essere modificati per ciascun immobile.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    crits = db.list_criteri()
    rows_html = "".join(
        '<div class="cs-card-stats" style="grid-template-columns:3fr 1fr;'
        'margin-bottom:.5rem">'
        f'<div><span class="cs-cap">Criterio</span>'
        f'<span class="cs-val">{c["nome"]}</span></div>'
        f'<div><span class="cs-cap">Peso</span>'
        f'<span class="cs-val">{c["peso_default"]:.1f}</span></div>'
        '</div>'
        for c in crits
    )
    st.markdown(
        f'<div class="cs-card"><div class="cs-card-body">{rows_html}</div></div>',
        unsafe_allow_html=True,
    )
