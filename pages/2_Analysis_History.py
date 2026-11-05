"""Saved analyses: list, open, update weights, delete (with confirmation)."""
import pandas as pd
import streamlit as st

import database
import decision_service as ds
import scoring_engine as se
import ui_components as ui
import utils

utils.setup_page("Analysis History", "🗂️")
S = st.session_state
utils.hero("Analysis history", "Saved analyses are stored locally in SQLite and survive app restarts.")

try:
    rows = database.list_analyses()
except database.DatabaseError as exc:
    st.error(str(exc))
    st.stop()

if not rows:
    st.info("No saved analyses yet. Run an analysis on the **New Analysis** page and press *Save analysis*.", icon="🗂️")
    st.page_link("pages/1_New_Analysis.py", label="Start a new analysis", icon="🧭")
    st.stop()

table = pd.DataFrame([{
    "ID": r["id"], "Title": r["title"], "Saved (UTC)": r["created_at"],
    "Source": "Sample demo" if r["mode"] == "sample" else "Live GenAI",
    "Alternatives": r["n_alternatives"], "Criteria": r["n_criteria"], "Top alternative": r["top_alternative"],
    "Top score": None if r["top_score"] is None else se.round_score(r["top_score"])} for r in rows])
st.dataframe(table, hide_index=True, width="stretch")

ids = [r["id"] for r in rows]
titles = {r["id"]: f"#{r['id']} · {r['title']}" for r in rows}
chosen = st.selectbox("Open a saved analysis", ids, format_func=lambda i: titles[i], key="hist_choice")

try:
    analysis = database.get_analysis(chosen)
except database.DatabaseError as exc:
    st.error(str(exc))
    st.stop()
if analysis is None:
    st.warning("That analysis no longer exists.")
    st.stop()

prefix = f"hist_{chosen}"
weights = ui.get_current_weights(analysis, prefix)
b1, b2, _ = st.columns([1.3, 1, 3])
if b1.button("💾 Save updated weights", key=f"{prefix}_save"):
    try:
        database.update_weights(chosen, weights, ds.compute_results(analysis, weights))
        st.toast("Updated weights saved.")
    except (database.DatabaseError, se.ScoringError) as exc:
        st.error(str(exc))
if b2.button("🗑️ Delete", key=f"{prefix}_del"):
    S["hist_confirm_delete"] = chosen

if S.get("hist_confirm_delete") == chosen:
    st.warning(f"Permanently delete analysis #{chosen}? This cannot be undone.", icon="⚠️")
    y, n, _ = st.columns([1.3, 1, 3])
    if y.button("Yes, delete permanently", type="primary", key=f"{prefix}_yes"):
        try:
            database.delete_analysis(chosen)
            S["hist_confirm_delete"] = None
            S.pop("hist_choice", None)
            st.rerun()
        except database.DatabaseError as exc:
            st.error(str(exc))
    if n.button("Cancel", key=f"{prefix}_no"):
        S["hist_confirm_delete"] = None
        st.rerun()

st.caption(f"Saved {analysis['created_at']} UTC · last updated {analysis['updated_at']} UTC")
ui.render_results(analysis, prefix)
