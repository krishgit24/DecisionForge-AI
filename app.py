"""DecisionForge AI landing page."""
import streamlit as st

import config
import utils

utils.setup_page("Home", "🧭")

utils.hero(
    "DecisionForge AI",
    "A clearer way to compare choices. Explore options, weigh what matters, and understand why a result ranks first.",
)

st.markdown("### From a difficult decision to a reasoned choice")
st.markdown(
    "Describe the decision in everyday language. DecisionForge helps structure the comparison, "
    "then shows how your priorities shape the result."
)

c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.markdown("#### :material/auto_awesome: AI helps you explore")
    st.write("Suggests options and criteria, drafts strengths and risks, and estimates ratings for you to review.")
with c2.container(border=True):
    st.markdown("#### :material/functions: Scores stay transparent")
    st.write("A consistent scoring method turns your ratings and priorities into a reproducible ranking.")
with c3.container(border=True):
    st.markdown("#### :material/tune: You stay in control")
    st.write("Review estimates, edit ratings, adjust priorities, and save the comparison for later.")

if config.has_api_key():
    st.success(
        f"Live analysis is ready with {config.get_provider_display_name()}. You can also use sample scenarios.",
        icon=":material/bolt:")
else:
    st.info(
        "Try a guided sample now. Live AI analysis becomes available when a provider key is configured.",
        icon=":material/science:")

st.markdown("### How it works")
steps = st.columns(4)
for col, number, title, detail in zip(
    steps,
    ("01", "02", "03", "04"),
    ("Describe", "Review", "Compare", "Save"),
    (
        "Add your decision and constraints, or load a sample.",
        "Check the proposed options, criteria, and ratings.",
        "Adjust priorities and see scores update immediately.",
        "Keep your analysis in local history.",
    ),
):
    with col.container(border=True):
        st.caption(number)
        st.markdown(f"#### {title}")
        st.write(detail)

st.markdown("### Ready to get started?")
left, right = st.columns([1, 2], vertical_alignment="center")
with left:
    st.page_link("pages/1_New_Analysis.py", label="Start an analysis", icon=":material/arrow_forward:")
with right:
    st.caption("No key needed to explore sample scenarios. Your saved analyses stay on this device.")
