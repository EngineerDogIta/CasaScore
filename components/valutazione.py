"""Valutazione widget — per-criterion 1–5 sliders with live weighted score."""
from __future__ import annotations

import streamlit as st

import db


def render(immobile: dict) -> None:
    valutazioni = [dict(v) for v in db.get_valutazioni(immobile["id"])]
    if not valutazioni:
        # Backfill if criteria were added after the property
        for c in db.list_criteri():
            db.upsert_valutazione(immobile["id"], c["nome"],
                                  c["peso_default"], 0)
        valutazioni = [dict(v) for v in db.get_valutazioni(immobile["id"])]

    st.markdown('<div class="cs-section-title">Valutazione</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="cs-help">Voto da 1 a 5 per ciascun criterio. Il punteggio '
        'è una media pesata.</p>', unsafe_allow_html=True,
    )

    updated: list[dict] = []
    for v in valutazioni:
        c1, c2, c3 = st.columns([3, 1, 4])
        with c1:
            st.markdown(
                f'<div class="cs-crit-name">{v["criterio"]}</div>',
                unsafe_allow_html=True,
            )
        with c2:
            peso = st.number_input(
                "Peso", min_value=0.1, max_value=3.0,
                value=float(v["peso"]), step=0.1,
                key=f"peso_{immobile['id']}_{v['criterio']}",
                label_visibility="collapsed",
            )
        with c3:
            voto = st.slider(
                "Voto", 0, 5, int(v["voto"]),
                key=f"voto_{immobile['id']}_{v['criterio']}",
                label_visibility="collapsed",
            )
        updated.append({"criterio": v["criterio"], "peso": peso, "voto": voto})

    db.bulk_upsert_valutazioni(immobile["id"], updated)

    score = db.weighted_score(updated)
    _render_score(score)


def _render_score(score: float | None) -> None:
    if score is None:
        st.markdown(
            '<div class="cs-score-card cs-score-empty">'
            '<div class="cs-score-num">—</div>'
            '<div class="cs-score-cap">Nessun voto</div></div>',
            unsafe_allow_html=True,
        )
        return
    pct = (score / 5) * 100
    st.markdown(
        f"""
        <div class="cs-score-card">
          <div class="cs-score-ring" style="--pct:{pct:.1f}%">
            <div class="cs-score-ring-inner">
              <div class="cs-score-num">{score:.1f}</div>
              <div class="cs-score-cap">su 5</div>
            </div>
          </div>
          <div class="cs-score-text">
            <div class="cs-score-title">Punteggio complessivo</div>
            <div class="cs-score-sub">Media pesata sui criteri valutati</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
