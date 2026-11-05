"""Shared Streamlit helpers: page setup, styling and sidebar."""
from __future__ import annotations

import streamlit as st

import config
import database

CSS = """
<style>
.df-brand-lockup { padding: .35rem 0 .75rem; }
.df-brand-mark { display: inline-flex; align-items: center; justify-content: center;
                 width: 2.2rem; height: 2.2rem; margin-right: .55rem;
                 border-radius: .7rem; background: #55D6B0; color: #102A31;
                 font-size: 1.1rem; font-weight: 800; vertical-align: middle; }
.df-brand { display: inline; font-size: 1.25rem; font-weight: 800;
            letter-spacing: -.035em; color: #F8FAFC; line-height: 1.1; vertical-align: middle; }
.df-brand span { color: #75E1C0; }
.df-sub { font-size: .79rem; color: #C5D6D7; margin: .5rem 0 0; line-height: 1.45; }
.df-sidebar-label { color: #94B2B4; font-size: .68rem; font-weight: 750;
                    letter-spacing: .12em; margin: .35rem 0 .55rem; }
.df-sidebar-note { border: 1px solid #31525A; border-radius: .8rem;
                   padding: .75rem .8rem; background: #1C3C45; margin: .3rem 0 .8rem; }
.df-sidebar-note strong { color: #F3F7F6; font-size: .88rem; }
.df-sidebar-note p { color: #C5D6D7; font-size: .76rem; line-height: 1.5; margin: .3rem 0 0; }
.df-hero { background: linear-gradient(118deg, #14343C 0%, #17615C 58%, #138777 100%);
           color: #fff; padding: 2rem 2.1rem; border: 1px solid #277D78; border-radius: 20px;
           margin: .2rem 0 1.5rem; box-shadow: 0 14px 32px rgba(16, 42, 67, .14); }
.df-hero h1 { color: #fff; margin: 0; padding: 0; font-size: clamp(2rem, 3.2vw, 2.8rem);
              line-height: 1.12; letter-spacing: -.035em; }
.df-hero p { margin: .65rem 0 0; color: #E1F5F1; font-size: 1.05rem; line-height: 1.55; max-width: 850px; }
.st-key-df_eyebrow p { color: #087F73; font-size: .78rem; font-weight: 700; letter-spacing: .09em;
                       text-transform: uppercase; margin-bottom: .35rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: #D7E3DF; border-radius: 16px; }
div.stButton > button[kind="primary"], div.stPageLink > a {
    border-radius: 10px; font-weight: 650; min-height: 2.7rem;
}
div.stButton > button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible {
    outline: 3px solid #F4B942 !important; outline-offset: 2px;
}
@media (max-width: 700px) {
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
        st.markdown(
            '<div class="df-brand-lockup">'
            '<span class="df-brand-mark" aria-hidden="true">D</span>'
            '<span class="df-brand">Decision<span>Forge</span> AI</span>'
            '<div class="df-sub">A clearer way to compare important choices.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown('<div class="df-sidebar-label">ANALYSIS MODE</div>', unsafe_allow_html=True)
        if config.has_api_key():
            st.success(f"{config.get_provider_display_name()} is ready · {config.get_provider_model()}",
                       icon=":material/bolt:")
        else:
            st.info("Sample analysis is ready. Live AI is not configured.", icon=":material/science:")
        if st.session_state.get("db_error"):
            st.error(st.session_state["db_error"])
        st.markdown(
            '<div class="df-sidebar-label">THE WORKFLOW</div>'
            '<div class="df-sidebar-note"><strong>1 &nbsp; Describe</strong>'
            '<p>Set the decision, options and constraints.</p></div>'
            '<div class="df-sidebar-note"><strong>2 &nbsp; Review</strong>'
            '<p>Check or edit AI rating estimates.</p></div>'
            '<div class="df-sidebar-note"><strong>3 &nbsp; Compare</strong>'
            '<p>Adjust priorities and see the ranking update.</p></div>'
            '<div class="df-sidebar-note"><strong>4 &nbsp; Save</strong>'
            '<p>Revisit your analysis from History.</p></div>',
            unsafe_allow_html=True,
        )
        st.caption("AI ratings are estimates. Python calculates every score.")


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
