"""Shared formatting helpers (Italian currency / numbers / status pill)."""
from __future__ import annotations

from typing import Any

import db


_STATUS_BY_ID = {s["id"]: s for s in db.STATUSES}


def fmt_eur(v: Any) -> str:
    """Italian-style currency, e.g. 1234567 -> '€ 1.234.567'. None/NaN -> '—'."""
    if v is None:
        return "—"
    try:
        n = int(v)
    except (TypeError, ValueError):
        return "—"
    return f"€ {n:,}".replace(",", ".")


def fmt_int(v: Any, suffix: str = "") -> str:
    """Integer with optional suffix; None/NaN -> '—'."""
    if v is None:
        return "—"
    try:
        return f"{int(v)}{suffix}"
    except (TypeError, ValueError):
        return "—"


def fmt_score(v: Any) -> str:
    """Weighted score with one decimal; None -> '—'."""
    if v is None:
        return "—"
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return "—"


def status(stato: str | None) -> dict[str, str]:
    """Resolve a status id to its full record. Falls back to the first status."""
    return _STATUS_BY_ID.get(stato or "visit", db.STATUSES[0])


def status_pill_html(stato: str | None) -> str:
    s = status(stato)
    return (f'<span class="cs-pill cs-pill-{s["id"]}">'
            f'<span>{s["emoji"]}</span><span>{s["label"]}</span></span>')


def status_label(stato: str | None) -> str:
    s = status(stato)
    return f"{s['emoji']} {s['label']}"


def metric_card(label: str, value: str, *, accent: bool = False) -> str:
    """Render a `.cs-metric` tile as raw HTML (markdown-injected)."""
    color = "var(--sage-deep)" if accent else "var(--ink)"
    return (
        f'<div class="cs-metric">'
        f'<div class="cs-metric-label">{label}</div>'
        f'<div class="cs-metric-value" style="color:{color}">{value}</div>'
        f'</div>'
    )


def stat_card(label: str, value: str, *, accent: bool = False) -> str:
    """Render a `.cs-stat` tile as raw HTML."""
    cls = "cs-stat-accent" if accent else ""
    return (
        f'<div class="cs-stat {cls}">'
        f'<div class="cs-stat-label">{label}</div>'
        f'<div class="cs-stat-value">{value}</div>'
        f'</div>'
    )
