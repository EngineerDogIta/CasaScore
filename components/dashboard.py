"""Dashboard comparativa — table + cards, sortable + status filters."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import db

STATUS_BY_ID = {s["id"]: s for s in db.STATUSES}


def _status_pill(stato: str) -> str:
    s = STATUS_BY_ID.get(stato or "visit", db.STATUSES[0])
    return (f'<span class="cs-pill cs-pill-{s["id"]}">'
            f'<span>{s["emoji"]}</span><span>{s["label"]}</span></span>')


def _fmt_eur(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"€ {int(v):,}".replace(",", ".")


def _fmt_num(v, suffix: str = "") -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{int(v)}{suffix}"


def render() -> None:
    immobili = [dict(r) for r in db.list_immobili()]

    st.markdown(
        """
        <div class="cs-page-head">
          <h1 class="cs-display">Dashboard</h1>
          <p class="cs-sub">Confronta gli immobili affiancati e ordina per quello che conta di più.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not immobili:
        st.markdown(
            '<div class="cs-empty">'
            '<div style="font-size:1.05rem;color:var(--ink);margin-bottom:.4rem">'
            'Ancora nessun immobile.</div>'
            '<div style="margin-bottom:1.2rem">'
            'Crea la tua prima scheda per iniziare a confrontare e valutare.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("＋ Crea la prima scheda", type="primary",
                         use_container_width=True, key="dash_empty_cta"):
                st.session_state["edit_id"] = None
                st.session_state["page"] = "Nuovo / Modifica"
                st.rerun()
        return

    rows = []
    for im in immobili:
        score = db.score_for(im["id"])
        rows.append({
            "id": im["id"],
            "label": im["label"],
            "indirizzo": im["indirizzo"] or "",
            "prezzo": im["prezzo"],
            "mq": im["mq"],
            "eur_mq": (im["prezzo"] / im["mq"]) if (im["prezzo"] and im["mq"]) else None,
            "punteggio": score,
            "stato": im["stato"] or "visit",
        })
    df = pd.DataFrame(rows)

    # ----- aggregate strip ------------------------------------------------
    fav_count = int((df["stato"] == "favorite").sum())
    avg_price = df["prezzo"].mean() if not df["prezzo"].isna().all() else None
    avg_score = df["punteggio"].dropna().mean() if df["punteggio"].notna().any() else None

    a, b, c, d = st.columns(4)
    a.markdown(_stat("Totale immobili", str(len(df))), unsafe_allow_html=True)
    b.markdown(_stat("Preferiti", str(fav_count)), unsafe_allow_html=True)
    c.markdown(_stat("Prezzo medio", _fmt_eur(avg_price)), unsafe_allow_html=True)
    d.markdown(
        _stat("Voto medio", f"{avg_score:.1f}" if avg_score is not None else "—",
              accent=True),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ----- controls -------------------------------------------------------
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        sort_by = st.selectbox(
            "Ordina per",
            ["Punteggio (alto→basso)", "Prezzo (basso→alto)",
             "Prezzo (alto→basso)", "€/mq (basso→alto)", "Mq (alto→basso)"],
            index=0,
        )
    with f2:
        status_options = ["Tutti"] + [
            f"{s['emoji']} {s['label']}" for s in db.STATUSES
        ]
        status_filter = st.selectbox("Stato", status_options, index=0)
    with f3:
        view = st.radio("Vista", ["Card", "Tabella"], index=0,
                        horizontal=True, label_visibility="collapsed")

    if status_filter != "Tutti":
        wanted = [s["id"] for s in db.STATUSES
                  if f"{s['emoji']} {s['label']}" == status_filter][0]
        df = df[df["stato"] == wanted]

    sort_map = {
        "Punteggio (alto→basso)": ("punteggio", False),
        "Prezzo (basso→alto)": ("prezzo", True),
        "Prezzo (alto→basso)": ("prezzo", False),
        "€/mq (basso→alto)": ("eur_mq", True),
        "Mq (alto→basso)": ("mq", False),
    }
    col, asc = sort_map[sort_by]
    df = df.sort_values(col, ascending=asc, na_position="last")

    if df.empty:
        st.markdown('<div class="cs-empty">Nessun immobile con questo filtro.</div>',
                    unsafe_allow_html=True)
        return

    if view == "Tabella":
        _render_table(df)
    else:
        _render_cards(df, immobili)


# --------------------------------------------------------------------- views ---

def _render_table(df: pd.DataFrame) -> None:
    show = df.copy()
    show["Prezzo"] = show["prezzo"].apply(_fmt_eur)
    show["Mq"] = show["mq"].apply(lambda v: _fmt_num(v, " mq"))
    show["€/mq"] = show["eur_mq"].apply(
        lambda v: f"€ {int(v):,}".replace(",", ".") if v else "—"
    )
    show["Punteggio"] = show["punteggio"].apply(
        lambda v: f"{v:.1f}" if v is not None and not pd.isna(v) else "—"
    )
    show["Stato"] = show["stato"].apply(
        lambda s: f"{STATUS_BY_ID[s]['emoji']} {STATUS_BY_ID[s]['label']}"
    )
    show = show.rename(columns={"label": "Etichetta", "indirizzo": "Indirizzo"})
    st.dataframe(
        show[["Etichetta", "Indirizzo", "Prezzo", "Mq", "€/mq",
              "Punteggio", "Stato"]],
        hide_index=True, use_container_width=True,
    )


def _render_cards(df: pd.DataFrame, immobili: list[dict]) -> None:
    by_id = {im["id"]: im for im in immobili}
    cols = st.columns(2)
    for i, (_, row) in enumerate(df.iterrows()):
        im = by_id[row["id"]]
        score = row["punteggio"]
        score_html = (f'<div class="cs-card-score">{score:.1f}'
                      f'<span>/5</span></div>'
                      if score is not None and not pd.isna(score)
                      else '<div class="cs-card-score cs-card-score-empty">—</div>')
        eur_mq = (f"€ {int(row['eur_mq']):,}".replace(",", ".") + " /mq"
                  if row["eur_mq"] else "—")
        photo = ""
        if im.get("foto_url"):
            photo = (f'<div class="cs-card-photo">'
                     f'<img src="{im["foto_url"]}" '
                     f'onerror="this.parentElement.style.display=\'none\'"/></div>')
        with cols[i % 2]:
            st.markdown(
                f"""
                <div class="cs-card">
                  {photo}
                  <div class="cs-card-body">
                    <div class="cs-card-row1">
                      <div>
                        <div class="cs-card-label">{im["label"]}</div>
                        <div class="cs-card-addr">{im["indirizzo"] or ""}</div>
                      </div>
                      {score_html}
                    </div>
                    <div class="cs-card-stats">
                      <div><span class="cs-cap">Prezzo</span><span class="cs-val">{_fmt_eur(row["prezzo"])}</span></div>
                      <div><span class="cs-cap">Superficie</span><span class="cs-val">{int(row["mq"])} mq</span></div>
                      <div><span class="cs-cap">€/mq</span><span class="cs-val">{eur_mq}</span></div>
                      <div><span class="cs-cap">Locali</span><span class="cs-val">{im["locali"] or "—"}</span></div>
                    </div>
                    <div class="cs-card-foot">{_status_pill(row["stato"])}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns([1, 1, 1])
            if b1.button("Apri", key=f"open_{row['id']}",
                         use_container_width=True):
                st.session_state["selected_id"] = int(row["id"])
                st.session_state["page"] = "Immobili"
                st.rerun()
            if b2.button("Modifica", key=f"edit_{row['id']}",
                         use_container_width=True):
                st.session_state["edit_id"] = int(row["id"])
                st.session_state["page"] = "Nuovo / Modifica"
                st.rerun()
            new_stato = b3.selectbox(
                "Stato", [s["id"] for s in db.STATUSES],
                index=[s["id"] for s in db.STATUSES].index(row["stato"]),
                format_func=lambda x: f"{STATUS_BY_ID[x]['emoji']} {STATUS_BY_ID[x]['label']}",
                key=f"stato_{row['id']}", label_visibility="collapsed",
            )
            if new_stato != row["stato"]:
                db.update_stato(int(row["id"]), new_stato)
                st.rerun()


# ---------------------------------------------------------------- helpers ---

def _stat(label: str, value: str, *, accent: bool = False) -> str:
    cls = "cs-stat-accent" if accent else ""
    return f"""
    <div class="cs-stat {cls}">
      <div class="cs-stat-label">{label}</div>
      <div class="cs-stat-value">{value}</div>
    </div>
    """
