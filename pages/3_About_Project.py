"""Project overview and scoring methodology."""
import streamlit as st

import config
import utils

utils.setup_page("About", "📘")
utils.hero(
    "About DecisionForge AI",
    "A decision-support project that pairs generative AI with explainable, reproducible scoring.",
)

ai, engine, user = st.columns(3)
with ai.container(border=True):
    st.markdown("#### :material/auto_awesome: Generative AI")
    st.write("Interprets the decision and drafts options, criteria, estimates, risks, and a plain-language explanation.")
with engine.container(border=True):
    st.markdown("#### :material/functions: Scoring engine")
    st.write("Validates ratings and weights, normalizes cost criteria, and calculates the ranking in Python.")
with user.container(border=True):
    st.markdown("#### :material/person: User review")
    st.write("You can edit estimates, change priorities, inspect trade-offs, and save the analysis locally.")

st.markdown("### A simple, auditable workflow")
st.markdown(
    "Decision description → AI-generated draft → user review → Python-calculated scores → "
    "interactive comparison and local history"
)

st.markdown("### How the score is calculated")
st.write(
    "Each option receives a 1–10 rating for each criterion. Benefit ratings stay as entered; "
    "cost ratings are inverted so a lower cost can contribute a higher score."
)
st.latex(r"r_{ij} = \begin{cases} raw_{ij} & \text{benefit} \\ 11 - raw_{ij} & \text{cost} \end{cases}")
st.latex(r"\text{Score}(i) = \frac{\sum_j w_j r_{ij}}{\sum_j w_j}")
st.caption(
    "Here, r is the normalized rating and w is the criterion weight. Changing weights recalculates "
    "the ranking in Python without another AI request."
)

with st.container(border=True):
    st.markdown("### What to keep in mind")
    st.write(
        "AI ratings are estimates, not verified facts. The result depends on the options, criteria, "
        "ratings, and weights you choose; use it to support judgment, not replace it."
    )

st.caption(
    f"Live provider: {config.get_provider_display_name()} · Model: {config.get_provider_model()} · "
    "History is stored locally with SQLite."
)
