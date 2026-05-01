"""Scheda immobile — add / edit form a tab."""
from __future__ import annotations

import streamlit as st

import db

ENERGY_CLASSES = ["A4", "A3", "A2", "A1", "A", "B", "C", "D", "E", "F", "G"]
STATUS_OPTIONS = [(s["id"], f"{s['emoji']}  {s['label']}") for s in db.STATUSES]

TIPOLOGIE = [
    "", "Appartamento", "Attico", "Mansarda", "Loft", "Villa",
    "Villetta a schiera", "Bilocale", "Trilocale", "Rustico/Casale",
    "Open space", "Altro",
]
CONTRATTI = ["Vendita", "Affitto"]
STATI_IMMOBILE = [
    "", "Nuovo / In costruzione", "Ottimo / Ristrutturato",
    "Buono / Abitabile", "Da ristrutturare",
]
DISPONIBILITA = ["", "Libero", "Occupato", "Libero da rogito", "Su richiesta"]
ARREDATO = ["", "Non arredato", "Solo cucina", "Parzialmente arredato", "Arredato"]
CUCINE = ["", "Cucinotto", "Angolo cottura", "Abitabile", "Semi-abitabile", "A vista"]
GIARDINI = ["Nessuno", "Privato", "Comune"]
RISC_TIPI = ["", "Autonomo", "Centralizzato", "Assente"]
RISC_ALIM = [
    "", "Gas", "GPL", "Gasolio", "Pellet", "Pompa di calore",
    "Elettrico", "Solare", "Teleriscaldamento", "Altro",
]
RISC_DIFF = ["", "Radiatori", "Aria", "Pavimento", "Stufa", "Altro"]
CLIMA = [
    "", "Assente", "Predisposizione", "Autonoma fredda",
    "Autonoma caldo/freddo", "Centralizzata",
]
ESPOSIZIONI = ["", "Interna", "Esterna", "Doppia"]
ALTRE_CARATTERISTICHE = [
    "Fibra ottica", "Infissi doppi", "Infissi triplo vetro", "Porta blindata",
    "Impianto TV centralizzato", "Videocitofono", "Allarme",
    "Cancello elettrico", "Camino", "Domotica", "Pannelli solari",
    "Fotovoltaico", "Inferriate",
]


def _empty() -> dict:
    return {
        "id": None, "label": "", "indirizzo": "", "prezzo": 0, "mq": 0,
        "locali": 2, "piano": "", "ascensore": 0, "anno": 2000,
        "classe_energetica": "C", "spese_cond": 0, "posto_auto": 0,
        "note": "", "foto_url": "", "stato": "visit",
        "mutuo_anticipo": 20, "mutuo_anni": 25, "mutuo_tasso": 3.5,
        "tipologia": "", "contratto": "Vendita", "stato_immobile": "",
        "disponibilita": "", "arredato": "", "piani_edificio": 0,
        "camere": 1, "bagni": 1, "cucina": "",
        "balcone": 0, "terrazzo": 0, "giardino_tipo": "Nessuno",
        "cantina": 0, "posto_auto_desc": "", "accesso_disabili": 0,
        "riscaldamento_tipo": "", "riscaldamento_alimentazione": "",
        "riscaldamento_diffusione": "", "climatizzazione": "",
        "esposizione": "", "altre_caratteristiche": "", "contatto_id": None,
    }


def _split_altre(s: str | None) -> list[str]:
    return [x for x in (s or "").split(";") if x]


def _join_altre(items: list[str]) -> str:
    return ";".join(items)


def _select_idx(value, options: list[str]) -> int:
    try:
        return options.index(value or "")
    except ValueError:
        return 0


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

    contatti = db.list_contatti()
    agenzie_by_id = {a["id"]: a for a in db.list_agenzie()}
    contatto_options: list[tuple[int | None, str]] = [(None, "— Nessun agente")]
    for c in contatti:
        ag_nome = agenzie_by_id.get(c.get("agenzia_id"), {}).get("nome")
        suffix = f" — {ag_nome}" if ag_nome else " — Senza agenzia"
        contatto_options.append((c["id"], f"{c['nome']}{suffix}"))

    with st.form("scheda_form", clear_on_submit=False):
        tab_anag, tab_caratt, tab_edif, tab_agente = st.tabs(
            ["Anagrafica", "Caratteristiche", "Edificio & impianti", "Agente & note"]
        )

        # ----------------------------------------------------- Anagrafica ---
        with tab_anag:
            c1, c2 = st.columns([1, 1])
            with c1:
                label = st.text_input("Etichetta *", value=data["label"],
                                      placeholder="Es. Trilocale Navigli")
            with c2:
                indirizzo = st.text_input("Indirizzo *",
                                          value=data["indirizzo"] or "",
                                          placeholder="Via, civico, città")

            c3, c4 = st.columns(2)
            with c3:
                tipologia = st.selectbox(
                    "Tipologia", TIPOLOGIE,
                    index=_select_idx(data.get("tipologia"), TIPOLOGIE),
                )
            with c4:
                contratto_idx = (CONTRATTI.index(data.get("contratto") or "Vendita")
                                 if (data.get("contratto") or "Vendita") in CONTRATTI
                                 else 0)
                contratto = st.selectbox("Contratto", CONTRATTI,
                                         index=contratto_idx)

            c5, c6, c7 = st.columns(3)
            with c5:
                prezzo = st.number_input("Prezzo richiesto (€) *", min_value=0,
                                         value=int(data["prezzo"] or 0), step=5000)
            with c6:
                mq = st.number_input("Superficie (mq) *", min_value=0,
                                     value=int(data["mq"] or 0), step=1)
            with c7:
                spese = st.number_input("Spese condominiali (€/mese)",
                                        min_value=0,
                                        value=int(data["spese_cond"] or 0),
                                        step=10)

            foto_url = st.text_input("URL foto", value=data["foto_url"] or "",
                                     placeholder="https://...")

        # ------------------------------------------------ Caratteristiche ---
        with tab_caratt:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                locali = st.number_input("Locali", min_value=1, max_value=20,
                                         value=int(data["locali"] or 2))
            with c2:
                camere = st.number_input("Camere da letto", min_value=0,
                                         max_value=20,
                                         value=int(data["camere"] or 0))
            with c3:
                bagni = st.number_input("Bagni", min_value=0, max_value=10,
                                        value=int(data["bagni"] or 1))
            with c4:
                piano = st.text_input("Piano", value=str(data["piano"] or ""),
                                      placeholder="Es. 2, T, R")

            c5, c6, c7 = st.columns(3)
            with c5:
                cucina = st.selectbox(
                    "Cucina", CUCINE,
                    index=_select_idx(data.get("cucina"), CUCINE),
                )
            with c6:
                arredato = st.selectbox(
                    "Arredato", ARREDATO,
                    index=_select_idx(data.get("arredato"), ARREDATO),
                )
            with c7:
                esposizione = st.selectbox(
                    "Esposizione", ESPOSIZIONI,
                    index=_select_idx(data.get("esposizione"), ESPOSIZIONI),
                )

            c8, c9, c10, c11 = st.columns(4)
            with c8:
                ascensore = st.checkbox("Ascensore",
                                        value=bool(data["ascensore"]))
            with c9:
                balcone = st.checkbox("Balcone",
                                      value=bool(data.get("balcone")))
            with c10:
                terrazzo = st.checkbox("Terrazzo",
                                       value=bool(data.get("terrazzo")))
            with c11:
                cantina = st.checkbox("Cantina",
                                      value=bool(data.get("cantina")))

            c12, c13, c14 = st.columns(3)
            with c12:
                giardino_tipo = st.selectbox(
                    "Giardino", GIARDINI,
                    index=_select_idx(data.get("giardino_tipo") or "Nessuno",
                                      GIARDINI),
                )
            with c13:
                posto_auto = st.checkbox("Posto auto",
                                         value=bool(data["posto_auto"]))
            with c14:
                posto_auto_desc = st.text_input(
                    "Descrizione posto auto",
                    value=data.get("posto_auto_desc") or "",
                    placeholder="Es. 1 in box privato",
                )

        # ------------------------------------------- Edificio & impianti ---
        with tab_edif:
            c1, c2, c3 = st.columns(3)
            with c1:
                anno = st.number_input("Anno costruzione", min_value=1700,
                                       max_value=2100,
                                       value=int(data["anno"] or 2000))
            with c2:
                piani_edificio = st.number_input(
                    "Piani edificio", min_value=0, max_value=200,
                    value=int(data.get("piani_edificio") or 0),
                )
            with c3:
                classe_idx = (
                    ENERGY_CLASSES.index(data["classe_energetica"])
                    if data["classe_energetica"] in ENERGY_CLASSES else 6
                )
                classe = st.selectbox("Classe energetica", ENERGY_CLASSES,
                                      index=classe_idx)

            c4, c5 = st.columns(2)
            with c4:
                stato_immobile = st.selectbox(
                    "Stato immobile", STATI_IMMOBILE,
                    index=_select_idx(data.get("stato_immobile"), STATI_IMMOBILE),
                )
            with c5:
                disponibilita = st.selectbox(
                    "Disponibilità", DISPONIBILITA,
                    index=_select_idx(data.get("disponibilita"), DISPONIBILITA),
                )

            accesso_disabili = st.checkbox(
                "Accesso disabili",
                value=bool(data.get("accesso_disabili")),
            )

            st.markdown(
                '<div class="cs-section-title" style="margin-top:1.4rem">'
                'Riscaldamento & climatizzazione</div>',
                unsafe_allow_html=True,
            )
            c6, c7, c8, c9 = st.columns(4)
            with c6:
                risc_tipo = st.selectbox(
                    "Riscaldamento", RISC_TIPI,
                    index=_select_idx(data.get("riscaldamento_tipo"), RISC_TIPI),
                )
            with c7:
                risc_alim = st.selectbox(
                    "Alimentazione", RISC_ALIM,
                    index=_select_idx(
                        data.get("riscaldamento_alimentazione"), RISC_ALIM
                    ),
                )
            with c8:
                risc_diff = st.selectbox(
                    "Diffusione", RISC_DIFF,
                    index=_select_idx(
                        data.get("riscaldamento_diffusione"), RISC_DIFF
                    ),
                )
            with c9:
                clima = st.selectbox(
                    "Climatizzazione", CLIMA,
                    index=_select_idx(data.get("climatizzazione"), CLIMA),
                )

            st.markdown(
                '<div class="cs-section-title" style="margin-top:1.4rem">'
                'Altre caratteristiche</div>',
                unsafe_allow_html=True,
            )
            altre_default = _split_altre(data.get("altre_caratteristiche"))
            altre_default = [x for x in altre_default if x in ALTRE_CARATTERISTICHE]
            altre = st.multiselect(
                "Seleziona le caratteristiche presenti",
                ALTRE_CARATTERISTICHE,
                default=altre_default,
            )

        # ----------------------------------------------- Agente & note ---
        with tab_agente:
            ids = [o[0] for o in contatto_options]
            labels = [o[1] for o in contatto_options]
            try:
                contatto_idx = ids.index(data.get("contatto_id"))
            except ValueError:
                contatto_idx = 0
            sel_contatto_label = st.selectbox(
                "Agente di riferimento", labels, index=contatto_idx,
                help="Aggiungi o gestisci agenti dalla pagina Rubrica.",
            )
            contatto_id = ids[labels.index(sel_contatto_label)]

            c1, _ = st.columns([1, 2])
            with c1:
                stato_ids = [s[0] for s in STATUS_OPTIONS]
                stato_lbls = [s[1] for s in STATUS_OPTIONS]
                try:
                    stato_idx = stato_ids.index(data["stato"] or "visit")
                except ValueError:
                    stato_idx = 0
                stato_label = st.selectbox("Stato workflow", stato_lbls,
                                           index=stato_idx)
                stato = stato_ids[stato_lbls.index(stato_label)]

            note = st.text_area(
                "Note", value=data["note"] or "",
                placeholder="Osservazioni, dettagli, da chiedere all'agente…",
                height=140,
            )

        submit_label = "Salva modifiche" if is_edit else "Crea scheda"
        submitted = st.form_submit_button(submit_label, type="primary",
                                          use_container_width=False)

    # link fuori dal form: gestione rubrica
    if st.button("Gestisci rubrica", key="scheda_open_rubrica"):
        st.switch_page(st.session_state["pages"]["rubrica"])

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
            "posto_auto": int(posto_auto),
            "note": note.strip(), "foto_url": foto_url.strip(),
            "stato": stato,
            "tipologia": tipologia or None,
            "contratto": contratto,
            "stato_immobile": stato_immobile or None,
            "disponibilita": disponibilita or None,
            "arredato": arredato or None,
            "piani_edificio": int(piani_edificio) if piani_edificio else None,
            "camere": int(camere),
            "bagni": int(bagni),
            "cucina": cucina or None,
            "balcone": int(balcone),
            "terrazzo": int(terrazzo),
            "giardino_tipo": giardino_tipo,
            "cantina": int(cantina),
            "posto_auto_desc": posto_auto_desc.strip() or None,
            "accesso_disabili": int(accesso_disabili),
            "riscaldamento_tipo": risc_tipo or None,
            "riscaldamento_alimentazione": risc_alim or None,
            "riscaldamento_diffusione": risc_diff or None,
            "climatizzazione": clima or None,
            "esposizione": esposizione or None,
            "altre_caratteristiche": _join_altre(altre),
            "contatto_id": contatto_id,
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
