"""Calcolatore — standalone mortgage calculator page."""
from __future__ import annotations

import streamlit as st

from components.mutuo import calc_rata
from formatters import fmt_eur, metric_card


def render() -> None:
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

    res = calc_rata(prezzo, anticipo, anni, tasso)

    st.markdown('<div class="cs-section-title">Risultato</div>',
                unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(metric_card("Rata mensile", fmt_eur(res["rata"]), accent=True),
                unsafe_allow_html=True)
    m2.markdown(metric_card("Capitale finanziato", fmt_eur(res["capitale"])),
                unsafe_allow_html=True)
    m3.markdown(metric_card("Anticipo", fmt_eur(res["anticipo"])),
                unsafe_allow_html=True)
    m4.markdown(metric_card("Interessi totali", fmt_eur(res["interessi"])),
                unsafe_allow_html=True)
