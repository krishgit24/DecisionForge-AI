"""Shared Streamlit helpers: page setup, styling and sidebar."""
from __future__ import annotations

import streamlit as st

import config
import database

CSS = """
<style>
div.block-container { padding-top: 2.2rem; max-width: 1280px; padding-bottom: 3rem; }
.stApp { background: #F7F9FC; }
.df-brand { font-size: 1.4rem; font-weight: 800; letter-spacing: -0.035em; color: #F8FAFC; line-height: 1.1; }
.df-brand span { color: #6EE7B7; }
.df-sub { font-size: 0.76rem; color: #CBD5E1; margin-top: 5px; }
.df-hero { background: linear-gradient(118deg, #102A43 0%, #145B66 56%, #087E75 100%);
           color: #fff; padding: 2rem 2.1rem; border: 1px solid #277D78; border-radius: 20px;
           margin: .2rem 0 1.5rem; box-shadow: 0 14px 32px rgba(16, 42, 67, .12); }
.df-hero h1 { color: #fff; margin: 0; padding: 0; font-size: clamp(2rem, 3.2vw, 2.8rem);
              line-height: 1.12; letter-spacing: -.035em; }
.df-hero p { margin: .65rem 0 0; color: #E1F5F1; font-size: 1.05rem; line-height: 1.55; max-width: 850px; }
.st-key-df_eyebrow p { color: #087E75; font-size: .78rem; font-weight: 700; letter-spacing: .09em;
                       text-transform: uppercase; margin-bottom: .35rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: #DFE7EF; border-radius: 16px; }
div.stButton > button[kind="primary"], div.stPageLink > a {
    border-radius: 10px; font-weight: 650; min-height: 2.7rem;
}
div.stButton > button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible {
    outline: 3px solid #F4B942 !important; outline-offset: 2px;
}
@media (max-width: 700px) {
    div.block-container { padding-top: 1rem; }
    .df-hero { padding: 1.45rem; border-radius: 15px; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def ensure_db() -> None:
    """Initialise the SQLite database once per browser session."""
    if st.session_state.get("db_ready"):
        return
    try:
        database.init_db()
        st.session_state["db_ready"] = True
        st.session_state["db_error"] = None
    except database.DatabaseError as exc:
        st.session_state["db_error"] = str(exc)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="df-brand">Decision<span>Forge</span> AI</div>'
                    '<div class="df-sub">Explainable GenAI decision analysis</div>', unsafe_allow_html=True)
        st.divider()
        if config.has_api_key():
            st.success(
                f"{config.get_provider_display_name()} live analysis ready · {config.get_provider_model()}",
                icon="✅")
        else:
            st.info("Sample analysis is ready. Add an API key to enable live AI.", icon="ℹ️")
        if st.session_state.get("db_error"):
            st.error(st.session_state["db_error"])
        st.caption("AI ratings are estimates. All scores are calculated transparently by Python.")


def setup_page(title: str, icon: str = "🧭") -> None:
    """Must be the first Streamlit call on every page."""
    st.set_page_config(page_title=f"{title} · {config.APP_NAME}", page_icon=icon,
                       layout="wide", initial_sidebar_state="expanded")
    inject_css()
    ensure_db()
    render_sidebar()


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="df-hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def parse_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]
