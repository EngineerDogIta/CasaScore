"""Rubrica — gestione agenzie immobiliari e relativi contatti."""
from __future__ import annotations

from html import escape

import streamlit as st

import db


def render() -> None:
    st.markdown(
        """
        <div class="cs-page-head">
          <h1 class="cs-display">Rubrica agenti</h1>
          <p class="cs-sub">Agenzie immobiliari e contatti utili per ogni proprietà.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 1])
    with col_right:
        if st.button("Nuova agenzia", type="primary",
                     use_container_width=True, key="rubrica_new_agenzia"):
            _agenzia_dialog(None)

    agenzie = db.list_agenzie()
    if not agenzie and not db.list_contatti_orfani():
        st.markdown(
            '<div class="cs-empty">Nessuna agenzia o contatto. '
            'Inizia aggiungendo una nuova agenzia.</div>',
            unsafe_allow_html=True,
        )
        return

    for agenzia in agenzie:
        _render_agenzia(agenzia)

    orfani = db.list_contatti_orfani()
    if orfani:
        st.markdown(
            '<div class="cs-section-title" style="margin-top:2rem">'
            'Contatti senza agenzia</div>',
            unsafe_allow_html=True,
        )
        _render_contatti_block(None, orfani)


# --------------------------------------------------------------- sezioni ---

def _render_agenzia(agenzia: dict) -> None:
    nome = escape(agenzia["nome"] or "")
    rows: list[str] = []
    if agenzia.get("indirizzo"):
        rows.append(f"📍 {escape(agenzia['indirizzo'])}")
    if agenzia.get("telefono"):
        rows.append(f"📞 {escape(agenzia['telefono'])}")
    if agenzia.get("email"):
        rows.append(f"✉️ {escape(agenzia['email'])}")
    if agenzia.get("sito"):
        rows.append(f"🌐 {escape(agenzia['sito'])}")
    body_lines = "<br>".join(rows) if rows else (
        '<span style="color:var(--muted)">Nessun recapito</span>'
    )

    st.markdown(
        f"""
        <div class="cs-card"><div class="cs-card-body">
          <div class="cs-card-row1">
            <div>
              <div class="cs-card-label">{nome}</div>
              <div class="cs-card-addr" style="margin-top:.5rem;line-height:1.55">{body_lines}</div>
            </div>
          </div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )

    if agenzia.get("note"):
        st.markdown(
            f'<div class="cs-help" style="margin-top:-.6rem">'
            f'{escape(agenzia["note"])}</div>',
            unsafe_allow_html=True,
        )

    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("Modifica", key=f"agenzia_edit_{agenzia['id']}",
                     use_container_width=True):
            _agenzia_dialog(agenzia["id"])
    with c2:
        st.markdown('<div class="cs-danger-zone">', unsafe_allow_html=True)
        if st.button("Elimina", key=f"agenzia_del_{agenzia['id']}",
                     use_container_width=True):
            _confirm_delete_agenzia(agenzia["id"], agenzia["nome"])
        st.markdown('</div>', unsafe_allow_html=True)

    contatti = db.list_contatti(agenzia["id"])
    with st.expander(f"Contatti ({len(contatti)})", expanded=False):
        _render_contatti_block(agenzia["id"], contatti)


def _render_contatti_block(agenzia_id: int | None, contatti: list[dict]) -> None:
    if contatti:
        for c in contatti:
            _render_contatto_row(c)
    else:
        st.markdown(
            '<div style="color:var(--muted);font-size:.9rem;padding:.4rem 0">'
            'Nessun contatto.</div>',
            unsafe_allow_html=True,
        )

    key = f"new_contatto_{agenzia_id or 'orfani'}"
    if st.button("Nuovo contatto", key=key, use_container_width=False):
        _contatto_dialog(None, agenzia_id=agenzia_id)


def _render_contatto_row(contatto: dict) -> None:
    parts = []
    if contatto.get("ruolo"):
        parts.append(f"<span class='cs-cap'>{escape(contatto['ruolo'])}</span>")
    if contatto.get("telefono"):
        parts.append(f"📞 {escape(contatto['telefono'])}")
    if contatto.get("email"):
        parts.append(f"✉️ {escape(contatto['email'])}")
    meta = "  ·  ".join(parts) if parts else (
        "<span style='color:var(--muted)'>—</span>"
    )

    col_text, col_edit, col_del = st.columns([6, 1, 1])
    with col_text:
        st.markdown(
            f'<div style="padding:.45rem 0">'
            f'<div style="font-weight:600;color:var(--ink)">{escape(contatto["nome"])}</div>'
            f'<div style="font-size:.85rem;color:var(--ink-soft);margin-top:.15rem">{meta}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_edit:
        if st.button("✏️", key=f"contatto_edit_{contatto['id']}",
                     use_container_width=True):
            _contatto_dialog(contatto["id"])
    with col_del:
        st.markdown('<div class="cs-danger-zone">', unsafe_allow_html=True)
        if st.button("🗑️", key=f"contatto_del_{contatto['id']}",
                     use_container_width=True):
            _confirm_delete_contatto(contatto["id"], contatto["nome"])
        st.markdown('</div>', unsafe_allow_html=True)


# --------------------------------------------------------------- dialoghi ---

@st.dialog("Agenzia")
def _agenzia_dialog(agenzia_id: int | None) -> None:
    existing = db.get_agenzia(agenzia_id) if agenzia_id else None
    data = dict(existing) if existing else {}
    suffix = str(agenzia_id) if agenzia_id else "new"

    nome = st.text_input("Nome *", value=data.get("nome") or "",
                         key=f"agenzia_nome_{suffix}",
                         placeholder="Es. Tecnocasa Centro")
    indirizzo = st.text_input("Indirizzo", value=data.get("indirizzo") or "",
                              key=f"agenzia_indirizzo_{suffix}")
    c1, c2 = st.columns(2)
    with c1:
        telefono = st.text_input("Telefono", value=data.get("telefono") or "",
                                 key=f"agenzia_tel_{suffix}")
    with c2:
        email = st.text_input("Email", value=data.get("email") or "",
                              key=f"agenzia_email_{suffix}")
    sito = st.text_input("Sito web", value=data.get("sito") or "",
                         key=f"agenzia_sito_{suffix}",
                         placeholder="https://...")
    note = st.text_area("Note", value=data.get("note") or "",
                        key=f"agenzia_note_{suffix}", height=80)

    cb1, cb2 = st.columns(2)
    if cb1.button("Annulla", use_container_width=True,
                  key=f"agenzia_cancel_{suffix}"):
        st.rerun()
    if cb2.button("Salva", type="primary", use_container_width=True,
                  key=f"agenzia_save_{suffix}"):
        if not nome.strip():
            st.error("Il nome è obbligatorio.")
            return
        payload = {
            "nome": nome.strip(),
            "indirizzo": indirizzo.strip() or None,
            "telefono": telefono.strip() or None,
            "email": email.strip() or None,
            "sito": sito.strip() or None,
            "note": note.strip() or None,
        }
        if agenzia_id:
            db.update_agenzia(agenzia_id, payload)
            st.toast("Agenzia aggiornata.", icon="✅")
        else:
            db.insert_agenzia(payload)
            st.toast("Agenzia creata.", icon="✅")
        st.rerun()


@st.dialog("Contatto")
def _contatto_dialog(contatto_id: int | None,
                     agenzia_id: int | None = None) -> None:
    existing = db.get_contatto(contatto_id) if contatto_id else None
    data = dict(existing) if existing else {"agenzia_id": agenzia_id}
    suffix = str(contatto_id) if contatto_id else "new"

    nome = st.text_input("Nome *", value=data.get("nome") or "",
                         key=f"contatto_nome_{suffix}",
                         placeholder="Es. Mario Rossi")
    ruolo = st.text_input("Ruolo", value=data.get("ruolo") or "",
                          key=f"contatto_ruolo_{suffix}",
                          placeholder="Es. Agente immobiliare, Direttore")

    agenzie = db.list_agenzie()
    options = [(None, "— Nessuna agenzia")] + [(a["id"], a["nome"]) for a in agenzie]
    ids = [o[0] for o in options]
    labels = [o[1] for o in options]
    try:
        idx = ids.index(data.get("agenzia_id"))
    except ValueError:
        idx = 0
    sel_label = st.selectbox("Agenzia", labels, index=idx,
                             key=f"contatto_agenzia_{suffix}")
    sel_agenzia = ids[labels.index(sel_label)]

    c1, c2 = st.columns(2)
    with c1:
        telefono = st.text_input("Telefono", value=data.get("telefono") or "",
                                 key=f"contatto_tel_{suffix}")
    with c2:
        email = st.text_input("Email", value=data.get("email") or "",
                              key=f"contatto_email_{suffix}")
    note = st.text_area("Note", value=data.get("note") or "",
                        key=f"contatto_note_{suffix}", height=80)

    cb1, cb2 = st.columns(2)
    if cb1.button("Annulla", use_container_width=True,
                  key=f"contatto_cancel_{suffix}"):
        st.rerun()
    if cb2.button("Salva", type="primary", use_container_width=True,
                  key=f"contatto_save_{suffix}"):
        if not nome.strip():
            st.error("Il nome è obbligatorio.")
            return
        payload = {
            "agenzia_id": sel_agenzia,
            "nome": nome.strip(),
            "ruolo": ruolo.strip() or None,
            "telefono": telefono.strip() or None,
            "email": email.strip() or None,
            "note": note.strip() or None,
        }
        if contatto_id:
            db.update_contatto(contatto_id, payload)
            st.toast("Contatto aggiornato.", icon="✅")
        else:
            db.insert_contatto(payload)
            st.toast("Contatto creato.", icon="✅")
        st.rerun()


@st.dialog("Eliminare agenzia?")
def _confirm_delete_agenzia(agenzia_id: int, nome: str) -> None:
    st.markdown(
        f"Stai per eliminare **{escape(nome)}**. "
        "I contatti associati restano in rubrica come 'senza agenzia'."
    )
    c1, c2 = st.columns(2)
    if c1.button("Annulla", use_container_width=True,
                 key=f"del_ag_cancel_{agenzia_id}"):
        st.rerun()
    if c2.button("Elimina", type="primary", use_container_width=True,
                 key=f"del_ag_ok_{agenzia_id}"):
        db.delete_agenzia(agenzia_id)
        st.toast(f"'{nome}' eliminata.", icon="🗑️")
        st.rerun()


@st.dialog("Eliminare contatto?")
def _confirm_delete_contatto(contatto_id: int, nome: str) -> None:
    st.markdown(
        f"Stai per eliminare **{escape(nome)}**. "
        "Gli immobili collegati a questo contatto perderanno l'associazione."
    )
    c1, c2 = st.columns(2)
    if c1.button("Annulla", use_container_width=True,
                 key=f"del_co_cancel_{contatto_id}"):
        st.rerun()
    if c2.button("Elimina", type="primary", use_container_width=True,
                 key=f"del_co_ok_{contatto_id}"):
        db.delete_contatto(contatto_id)
        st.toast(f"'{nome}' eliminato.", icon="🗑️")
        st.rerun()
