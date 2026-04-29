"""Mortgage calculator widget — French amortization."""
from __future__ import annotations

import streamlit as st

import db


def calc_rata(prezzo: float, anticipo_pct: float, anni: int, tasso_pct: float) -> dict:
    prezzo = float(prezzo or 0)
    anticipo_pct = float(anticipo_pct or 0)
    anni = int(anni or 0)
    tasso_pct = float(tasso_pct or 0)

    anticipo = prezzo * anticipo_pct / 100
    capitale = prezzo - anticipo
    if capitale <= 0 or anni <= 0:
        return {"rata": 0.0, "capitale": max(0.0, capitale), "anticipo": anticipo,
                "totale": 0.0, "interessi": 0.0}
    r = tasso_pct / 100 / 12
    n = anni * 12
    if r == 0:
        rata = capitale / n
    else:
        rata = capitale * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    totale = rata * n
    return {
        "rata": rata, "capitale": capitale, "anticipo": anticipo,
        "totale": totale, "interessi": totale - capitale,
    }


def render(immobile: dict, *, key_prefix: str = "mutuo") -> None:
    """Inline mortgage block. Persists slider values back to the DB."""
    prezzo = immobile.get("prezzo") or 0

    st.markdown('<div class="cs-section-title">Calcolatore mutuo</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        anticipo = st.slider(
            "Anticipo %", 0, 80,
            int(immobile.get("mutuo_anticipo") or 20),
            step=5, key=f"{key_prefix}_anticipo_{immobile['id']}",
        )
    with c2:
        anni = st.slider(
            "Durata (anni)", 5, 40,
            int(immobile.get("mutuo_anni") or 25),
            step=5, key=f"{key_prefix}_anni_{immobile['id']}",
        )
    with c3:
        tasso = st.slider(
            "Tasso %", 0.5, 8.0,
            float(immobile.get("mutuo_tasso") or 3.5),
            step=0.1, key=f"{key_prefix}_tasso_{immobile['id']}",
        )

    res = calc_rata(prezzo, anticipo, anni, tasso)

    db.update_immobile(immobile["id"], {
        "mutuo_anticipo": anticipo, "mutuo_anni": anni, "mutuo_tasso": tasso,
    })

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(_metric("Rata mensile", f"€ {res['rata']:,.0f}", accent=True),
                unsafe_allow_html=True)
    m2.markdown(_metric("Capitale", f"€ {res['capitale']:,.0f}"),
                unsafe_allow_html=True)
    m3.markdown(_metric("Anticipo", f"€ {res['anticipo']:,.0f}"),
                unsafe_allow_html=True)
    m4.markdown(_metric("Interessi totali", f"€ {res['interessi']:,.0f}"),
                unsafe_allow_html=True)


def _metric(label: str, value: str, *, accent: bool = False) -> str:
    color = "var(--sage-deep)" if accent else "var(--ink)"
    return f"""
    <div class="cs-metric">
      <div class="cs-metric-label">{label}</div>
      <div class="cs-metric-value" style="color:{color}">{value}</div>
    </div>
    """
