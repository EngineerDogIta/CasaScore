"""Immobili — per-property detail page (header, facts, valutazione, mutuo)."""
from __future__ import annotations

import streamlit as st

import db
from components import mutuo, valutazione
from formatters import (
    fmt_eur, fmt_int, metric_card, status, status_pill_html,
)


def render() -> None:
    immobili = db.list_immobili()
    if not immobili:
        _render_empty_state()
        return

    ids = [im["id"] for im in immobili]
    if st.session_state.get("selected_id") not in ids:
        st.session_state["selected_id"] = ids[0]
    current = next(im for im in immobili
                   if im["id"] == st.session_state["selected_id"])

    _render_header(current)
    _render_photo(current)
    _render_facts(current)
    _render_extras(current)
    _render_notes(current)

    valutazione.render(current)
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    mutuo.render(db.get_immobile(current["id"]))


# --------------------------------------------------------------- sections ---

def _render_empty_state() -> None:
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


def _render_header(current: dict) -> None:
    s = status(current["stato"])

    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.markdown(
            f"""
            <div class="cs-page-head">
              <div style="display:flex;align-items:center;gap:.8rem;flex-wrap:wrap">
                <h1 class="cs-display" style="margin:0">{current["label"]}</h1>
                {status_pill_html(s["id"])}
              </div>
              <p class="cs-sub">{current["indirizzo"] or ""}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        if st.button("Modifica", use_container_width=True, key="detail_edit"):
            st.session_state["edit_id"] = current["id"]
            st.switch_page(st.session_state["pages"]["scheda"])
        st.markdown('<div class="cs-danger-zone">', unsafe_allow_html=True)
        if st.button("Elimina", use_container_width=True, key="detail_delete"):
            _confirm_delete(current["id"], current["label"])
        st.markdown('</div>', unsafe_allow_html=True)


def _render_photo(current: dict) -> None:
    if not current.get("foto_url"):
        return
    st.markdown(
        f'<div class="cs-photo-preview"><img src="{current["foto_url"]}" '
        f'onerror="this.parentElement.style.display=\'none\'"/></div>',
        unsafe_allow_html=True,
    )


def _render_facts(current: dict) -> None:
    st.markdown('<div class="cs-section-title">Dati chiave</div>',
                unsafe_allow_html=True)
    eur_mq = (
        fmt_eur(int(current["prezzo"] / current["mq"]))
        if current["prezzo"] and current["mq"] else "—"
    )
    facts = [
        ("Prezzo", fmt_eur(current["prezzo"])),
        ("Superficie", fmt_int(current["mq"], " mq")),
        ("€/mq", eur_mq),
        ("Locali", str(current["locali"] or "—")),
        ("Piano", current["piano"] or "—"),
        ("Anno", str(current["anno"] or "—")),
        ("Classe en.", current["classe_energetica"] or "—"),
        ("Spese cond.", f"{fmt_eur(current['spese_cond'])}/mese"),
    ]
    rows = st.columns(4)
    for i, (k, v) in enumerate(facts):
        rows[i % 4].markdown(metric_card(k, v), unsafe_allow_html=True)


def _render_extras(current: dict) -> None:
    extras = []
    if current["ascensore"]:
        extras.append("Ascensore")
    if current["posto_auto"]:
        extras.append("Posto auto")
    if current["giardino"] and current["giardino"] != "Nessuno":
        extras.append(current["giardino"])
    if not extras:
        return
    pills = "".join(
        f'<span class="cs-pill" style="background:var(--bg);'
        f'border:1px solid var(--line);color:var(--ink-soft)">{e}</span>'
        for e in extras
    )
    st.markdown(
        f"<div style='margin-top:.9rem;display:flex;gap:.5rem;flex-wrap:wrap'>"
        f"{pills}</div>",
        unsafe_allow_html=True,
    )


def _render_notes(current: dict) -> None:
    if not current["note"]:
        return
    st.markdown('<div class="cs-section-title">Note</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="cs-card"><div class="cs-card-body" '
        f'style="white-space:pre-wrap;font-size:.92rem;color:var(--ink-soft)">'
        f'{current["note"]}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- dialog ---

@st.dialog("Eliminare immobile?")
def _confirm_delete(immobile_id: int, label: str) -> None:
    st.markdown(
        f"Stai per eliminare **{label}**. "
        "Quest'azione cancella anche le valutazioni associate e non può essere annullata."
    )
    c1, c2 = st.columns(2)
    if c1.button("Annulla", use_container_width=True, key="confirm_cancel"):
        st.rerun()
    if c2.button("Elimina definitivamente", type="primary",
                 use_container_width=True, key="confirm_delete"):
        db.delete_immobile(immobile_id)
        st.session_state["selected_id"] = None
        st.toast(f"'{label}' eliminato.", icon="🗑️")
        st.switch_page(st.session_state["pages"]["dashboard"])
