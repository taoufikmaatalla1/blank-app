"""Interface language (English or French) for the owner's own use.

Only the screens are translated. Everything that leaves the app (supplier messages,
Amazon listings, keywords) stays in English, and data is stored in English: statuses
are translated for display only.

Usage: t("Save") or t("Added {n} supplier(s).", n=3). English text is the key; a
missing French translation falls back to English.
"""

from __future__ import annotations

import streamlit as st

from .i18n_fr import FR

LANGUAGES = {"en": "English", "fr": "Français"}


def lang() -> str:
    try:
        return st.session_state.get("lang", "en")
    except Exception:  # outside a Streamlit run (tests, API)
        return "en"


def t(text: str, **kw) -> str:
    out = FR.get(text, text) if lang() == "fr" else text
    return out.format(**kw) if kw else out


def cols(config: dict, columns=()) -> dict:
    """Translate the labels of a dataframe's column_config (and of columns not listed in it)."""
    out = {}
    for name in list(columns) + [c for c in config if c not in columns]:
        v = config.get(name)
        if v is None:
            out[name] = t(name)
        elif isinstance(v, str):
            out[name] = t(v)
        elif isinstance(v, dict):
            v = dict(v)
            v["label"] = t(v.get("label") or name)
            if v.get("help"):
                v["help"] = t(v["help"])
            out[name] = v
        else:
            out[name] = v
    return out


def to_display(df, column: str):
    """Statuses are stored in English; show them translated in an editable table."""
    if lang() == "fr" and column in df:
        df = df.copy()
        df[column] = df[column].map(lambda v: FR.get(v, v) if isinstance(v, str) else v)
    return df


def from_display(df, column: str):
    if lang() == "fr" and column in df:
        back = {v: k for k, v in FR.items()}
        df = df.copy()
        df[column] = df[column].map(lambda v: back.get(v, v) if isinstance(v, str) else v)
    return df


def options(values: list[str]) -> list[str]:
    return [t(v) for v in values]


def table(df, column_config: dict | None = None, status_cols=(), **kw) -> None:
    """st.dataframe with translated column headers (and translated status cells)."""
    for c in status_cols:
        df = to_display(df, c)
    if lang() == "fr":
        config = {t(k): v for k, v in (column_config or {}).items()}
        df = df.rename(columns=lambda c: t(c) if isinstance(c, str) else c)
    else:
        config = column_config or {}
    kw.setdefault("hide_index", True)
    kw.setdefault("width", "stretch")
    st.dataframe(df, column_config=config, **kw)
