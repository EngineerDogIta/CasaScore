"""Dashboard comparativa — table + cards, sortable + status filters."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import db
from formatters import (
    fmt_eur, fmt_int, fmt_score, stat_card, status, status_label,
    status_pill_html,
)


def render() -> None:
    immobili = db.list_immobili()

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
        _render_empty_state()
        return

    df = _build_dataframe(immobili)
    _render_aggregate_strip(df)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    df = _apply_filters_and_sort(df)
    if df.empty:
        st.markdown('<div class="cs-empty">Nessun immobile con questo filtro.</div>',
                    unsafe_allow_html=True)
        return

    if st.session_state.get("dashboard_view", "Card") == "Tabella":
        _render_table(df)
    else:
        _render_cards(df, {im["id"]: im for im in immobili})


# ---------------------------------------------------------------- sections ---

def _render_empty_state() -> None:
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
    _, c2, _ = st.columns([1, 1, 1])
    with c2:
        if st.button("＋ Crea la prima scheda", type="primary",
                     use_container_width=True, key="dash_empty_cta"):
            st.session_state["edit_id"] = None
            st.switch_page(st.session_state["pages"]["scheda"])


def _build_dataframe(immobili: list[dict]) -> pd.DataFrame:
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
    return pd.DataFrame(rows)


def _render_aggregate_strip(df: pd.DataFrame) -> None:
    fav_count = int((df["stato"] == "favorite").sum())
    avg_price = df["prezzo"].mean() if not df["prezzo"].isna().all() else None
    avg_score = df["punteggio"].dropna().mean() if df["punteggio"].notna().any() else None

    a, b, c, d = st.columns(4)
    a.markdown(stat_card("Totale immobili", str(len(df))), unsafe_allow_html=True)
    b.markdown(stat_card("Preferiti", str(fav_count)), unsafe_allow_html=True)
    c.markdown(stat_card("Prezzo medio", fmt_eur(avg_price)), unsafe_allow_html=True)
    d.markdown(
        stat_card("Voto medio", fmt_score(avg_score), accent=True),
        unsafe_allow_html=True,
    )


def _apply_filters_and_sort(df: pd.DataFrame) -> pd.DataFrame:
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        sort_by = st.selectbox(
            "Ordina per",
            ["Punteggio (alto→basso)", "Prezzo (basso→alto)",
             "Prezzo (alto→basso)", "€/mq (basso→alto)", "Mq (alto→basso)"],
            index=0,
        )
    with f2:
        status_options = ["Tutti"] + [status_label(s["id"]) for s in db.STATUSES]
        status_filter = st.selectbox("Stato", status_options, index=0)
    with f3:
        st.radio(
            "Vista", ["Card", "Tabella"], index=0, horizontal=True,
            key="dashboard_view", label_visibility="collapsed",
        )

    if status_filter != "Tutti":
        wanted = next(s["id"] for s in db.STATUSES
                      if status_label(s["id"]) == status_filter)
        df = df[df["stato"] == wanted]

    sort_map = {
        "Punteggio (alto→basso)": ("punteggio", False),
        "Prezzo (basso→alto)": ("prezzo", True),
        "Prezzo (alto→basso)": ("prezzo", False),
        "€/mq (basso→alto)": ("eur_mq", True),
        "Mq (alto→basso)": ("mq", False),
    }
    col, asc = sort_map[sort_by]
    return df.sort_values(col, ascending=asc, na_position="last")


# --------------------------------------------------------------------- views ---

def _render_table(df: pd.DataFrame) -> None:
    show = df.assign(
        Stato=df["stato"].apply(status_label),
    ).rename(columns={
        "label": "Etichetta",
        "indirizzo": "Indirizzo",
        "prezzo": "Prezzo",
        "mq": "Mq",
        "eur_mq": "€/mq",
        "punteggio": "Punteggio",
    })[["Etichetta", "Indirizzo", "Prezzo", "Mq", "€/mq", "Punteggio", "Stato"]]

    st.dataframe(
        show,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Etichetta": st.column_config.TextColumn(width="medium"),
            "Indirizzo": st.column_config.TextColumn(width="large"),
            "Prezzo": st.column_config.NumberColumn(format="€ %d"),
            "Mq": st.column_config.NumberColumn(format="%d mq"),
            "€/mq": st.column_config.NumberColumn(format="€ %d"),
            "Punteggio": st.column_config.ProgressColumn(
                format="%.1f", min_value=0.0, max_value=5.0,
            ),
            "Stato": st.column_config.TextColumn(width="small"),
        },
    )


def _render_cards(df: pd.DataFrame, by_id: dict[int, dict]) -> None:
    cols = st.columns(2)
    for i, (_, row) in enumerate(df.iterrows()):
        im = by_id[row["id"]]
        with cols[i % 2]:
            st.markdown(_card_html(im, row), unsafe_allow_html=True)
            _render_card_actions(int(row["id"]), row["stato"])


def _card_html(im: dict, row: pd.Series) -> str:
    score = row["punteggio"]
    score_html = (
        f'<div class="cs-card-score">{score:.1f}<span>/5</span></div>'
        if score is not None and not pd.isna(score)
        else '<div class="cs-card-score cs-card-score-empty">—</div>'
    )
    eur_mq_html = (
        f"€ {int(row['eur_mq']):,}".replace(",", ".") + " /mq"
        if row["eur_mq"] else "—"
    )
    photo = (
        f'<div class="cs-card-photo"><img src="{im["foto_url"]}" '
        f'onerror="this.parentElement.style.display=\'none\'"/></div>'
        if im.get("foto_url") else ""
    )
    return f"""
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
          <div><span class="cs-cap">Prezzo</span><span class="cs-val">{fmt_eur(row["prezzo"])}</span></div>
          <div><span class="cs-cap">Superficie</span><span class="cs-val">{fmt_int(row["mq"], " mq")}</span></div>
          <div><span class="cs-cap">€/mq</span><span class="cs-val">{eur_mq_html}</span></div>
          <div><span class="cs-cap">Locali</span><span class="cs-val">{im["locali"] or "—"}</span></div>
        </div>
        <div class="cs-card-foot">{status_pill_html(row["stato"])}</div>
      </div>
    </div>
    """


def _render_card_actions(immobile_id: int, current_stato: str) -> None:
    b1, b2, b3 = st.columns([1, 1, 1])
    if b1.button("Apri", key=f"open_{immobile_id}", use_container_width=True):
        st.session_state["selected_id"] = immobile_id
        st.switch_page(st.session_state["pages"]["immobili"])
    if b2.button("Modifica", key=f"edit_{immobile_id}", use_container_width=True):
        st.session_state["edit_id"] = immobile_id
        st.switch_page(st.session_state["pages"]["scheda"])
    new_stato = b3.selectbox(
        "Stato", [s["id"] for s in db.STATUSES],
        index=[s["id"] for s in db.STATUSES].index(current_stato),
        format_func=lambda x: status_label(x),
        key=f"stato_{immobile_id}", label_visibility="collapsed",
    )
    if new_stato != current_stato:
        db.update_stato(immobile_id, new_stato)
        st.rerun()
