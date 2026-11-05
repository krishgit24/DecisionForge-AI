"""DecisionForge AI landing page."""
import streamlit as st

import config
import utils

utils.setup_page("Home", "🧭")

utils.hero(
    "DecisionForge AI",
    "Make complex choices easier to compare. Set your priorities, review the reasoning, and see what drives the result.",
)

start, mode = st.columns([1, 2], vertical_alignment="center")
with start:
    st.page_link("pages/1_New_Analysis.py", label="Start an analysis", icon=":material/arrow_forward:")
with mode:
    if config.has_api_key():
        st.caption(f"Live analysis is ready with {config.get_provider_display_name()}. Sample scenarios are available too.")
    else:
        st.caption("Start with a sample scenario—no API key is needed.")

st.markdown("### Two parts. One clear comparison.")
ai, scoring = st.columns(2)
with ai.container(border=True):
    st.markdown("#### :material/auto_awesome: AI organizes the decision")
    st.write("It can suggest options and criteria, and draft ratings and trade-offs for you to review.")
with scoring.container(border=True):
    st.markdown("#### :material/functions: Python calculates the result")
    st.write("The weighted scores update as you change priorities. The AI never calculates the final ranking.")

st.markdown("### Your decision, step by step")
steps = st.columns(4)
for col, number, title, detail in zip(
    steps,
    ("01", "02", "03", "04"),
    ("Describe", "Review", "Adjust", "Save"),
    (
        "Enter your decision or choose a sample.",
        "Check and edit the suggested ratings.",
        "Change weights to explore different priorities.",
        "Reopen your comparison from History.",
    ),
):
    with col.container(border=True):
        st.caption(number)
        st.markdown(f"#### {title}")
        st.write(detail)

st.caption("AI-generated ratings are estimates. Review them before using a result to support a real decision.")
