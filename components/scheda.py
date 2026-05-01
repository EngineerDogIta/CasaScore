"""Scheda immobile — add / edit form."""
from __future__ import annotations

import streamlit as st

import db

ENERGY_CLASSES = ["A4", "A3", "A2", "A1", "A", "B", "C", "D", "E", "F", "G"]
STATUS_OPTIONS = [(s["id"], f"{s['emoji']}  {s['label']}") for s in db.STATUSES]
OUTDOOR_OPTIONS = ["Nessuno", "Balcone", "Terrazzo", "Giardino"]


def _empty() -> dict:
    return {
        "id": None, "label": "", "indirizzo": "", "prezzo": 0, "mq": 0,
        "locali": 2, "piano": "", "ascensore": 0, "anno": 2000,
        "classe_energetica": "C", "spese_cond": 0, "posto_auto": 0,
        "giardino": "Nessuno", "note": "", "foto_url": "", "stato": "visit",
        "mutuo_anticipo": 20, "mutuo_anni": 25, "mutuo_tasso": 3.5,
    }


def render(immobile_id: int | None = None) -> None:
    existing = db.get_immobile(immobile_id) if immobile_id else None
    data = dict(existing) if existing else _empty()
    is_edit = existing is not None

    title = "Modifica immobile" if is_edit else "Nuova scheda immobile"
    subtitle = ("Aggiorna i dati di questa proprietà." if is_edit
                else "Inserisci i dettagli per iniziare a confrontarla.")

    st.markdown(
        f"""
        <div class="cs-page-head">
          <h1 class="cs-display">{title}</h1>
          <p class="cs-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    foto_preview = data.get("foto_url") or ""
    if foto_preview:
        st.markdown(
            f'<div class="cs-photo-preview"><img src="{foto_preview}" '
            f'onerror="this.style.display=\'none\'"/></div>',
            unsafe_allow_html=True,
        )

    with st.form("scheda_form", clear_on_submit=False):
        st.markdown('<div class="cs-section-title">Anagrafica</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            label = st.text_input("Etichetta *", value=data["label"],
                                  placeholder="Es. Trilocale Navigli")
        with c2:
            indirizzo = st.text_input("Indirizzo *", value=data["indirizzo"] or "",
                                      placeholder="Via, civico, città")

        c3, c4, c5 = st.columns(3)
        with c3:
            prezzo = st.number_input("Prezzo richiesto (€) *", min_value=0,
                                     value=int(data["prezzo"] or 0), step=5000)
        with c4:
            mq = st.number_input("Superficie (mq) *", min_value=0,
                                 value=int(data["mq"] or 0), step=1)
        with c5:
            spese = st.number_input("Spese condominiali (€/mese)", min_value=0,
                                    value=int(data["spese_cond"] or 0), step=10)

        st.markdown('<div class="cs-section-title">Caratteristiche</div>',
                    unsafe_allow_html=True)
        c6, c7, c8, c9 = st.columns(4)
        with c6:
            locali = st.number_input("Locali", min_value=1, max_value=20,
                                     value=int(data["locali"] or 2))
        with c7:
            piano = st.text_input("Piano", value=str(data["piano"] or ""),
                                  placeholder="Es. 2, T, R")
        with c8:
            anno = st.number_input("Anno costruzione", min_value=1700,
                                   max_value=2100,
                                   value=int(data["anno"] or 2000))
        with c9:
            classe_idx = (ENERGY_CLASSES.index(data["classe_energetica"])
                          if data["classe_energetica"] in ENERGY_CLASSES else 6)
            classe = st.selectbox("Classe energetica", ENERGY_CLASSES,
                                  index=classe_idx)

        c10, c11, c12 = st.columns(3)
        with c10:
            ascensore = st.checkbox("Ascensore",
                                    value=bool(data["ascensore"]))
        with c11:
            posto_auto = st.checkbox("Posto auto",
                                     value=bool(data["posto_auto"]))
        with c12:
            outdoor_val = data["giardino"] or "Nessuno"
            if outdoor_val not in OUTDOOR_OPTIONS:
                OUTDOOR_OPTIONS.append(outdoor_val)
            giardino = st.selectbox("Esterno", OUTDOOR_OPTIONS,
                                    index=OUTDOOR_OPTIONS.index(outdoor_val))

        st.markdown('<div class="cs-section-title">Stato &amp; media</div>',
                    unsafe_allow_html=True)
        c13, c14 = st.columns([1, 2])
        with c13:
            stato_ids = [s[0] for s in STATUS_OPTIONS]
            stato_lbls = [s[1] for s in STATUS_OPTIONS]
            try:
                stato_idx = stato_ids.index(data["stato"] or "visit")
            except ValueError:
                stato_idx = 0
            stato_label = st.selectbox("Stato", stato_lbls, index=stato_idx)
            stato = stato_ids[stato_lbls.index(stato_label)]
        with c14:
            foto_url = st.text_input("URL foto", value=data["foto_url"] or "",
                                     placeholder="https://...")

        note = st.text_area("Note", value=data["note"] or "",
                            placeholder="Osservazioni, dettagli, da chiedere all'agente…",
                            height=110)

        submit_label = "Salva modifiche" if is_edit else "Crea scheda"
        submitted = st.form_submit_button(submit_label, type="primary",
                                          use_container_width=False)

    if submitted:
        if not label.strip() or not indirizzo.strip() or prezzo <= 0 or mq <= 0:
            st.error("Compila i campi obbligatori contrassegnati con *.")
            return

        payload = {
            "label": label.strip(), "indirizzo": indirizzo.strip(),
            "prezzo": float(prezzo), "mq": float(mq),
            "locali": int(locali), "piano": piano.strip(),
            "ascensore": int(ascensore), "anno": int(anno),
            "classe_energetica": classe, "spese_cond": float(spese),
            "posto_auto": int(posto_auto), "giardino": giardino,
            "note": note.strip(), "foto_url": foto_url.strip(),
            "stato": stato,
        }
        if is_edit:
            db.update_immobile(immobile_id, payload)
            st.toast("Scheda aggiornata.", icon="✅")
        else:
            new_id = db.insert_immobile({
                **payload,
                "mutuo_anticipo": data["mutuo_anticipo"],
                "mutuo_anni": data["mutuo_anni"],
                "mutuo_tasso": data["mutuo_tasso"],
            })
            st.session_state["selected_id"] = new_id
            st.toast("Scheda creata. Ora puoi valutarla.", icon="✅")
        st.switch_page(st.session_state["pages"]["immobili"])
