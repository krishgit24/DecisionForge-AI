"""New analysis: input form -> review ratings -> results dashboard."""
import pandas as pd
import streamlit as st

import config
import database
import decision_service as ds
import scoring_engine as se
import ui_components as ui
import utils
from ai_service import AIServiceError, DecisionAnalyzer, GeminiProvider, OpenAIProvider
from sample_data import SAMPLE_LABEL, SAMPLES

utils.setup_page("New Analysis", "🧭")
S = st.session_state
for key, default in (("na_stage", "input"), ("na_analysis", None), ("na_saved_id", None),
                     ("na_error", None), ("na_last_request", None)):
    S.setdefault(key, default)

LIVE, SAMPLE = "Live GenAI", "Sample demo"
ALT_AI, ALT_OWN = "Let AI suggest alternatives", "I'll enter them myself"
CRIT_AI, CRIT_OWN = "Let AI suggest criteria and starting weights", "Define my own"
TYPE_BENEFIT, TYPE_COST = "Benefit (higher is better)", "Cost (lower is better)"
DEFAULT_CRITERIA = pd.DataFrame({
    "Criterion": ["Cost", "Time Required", "Complexity", "Scalability", "Maintainability"],
    "Type": [TYPE_COST, TYPE_COST, TYPE_COST, TYPE_BENEFIT, TYPE_BENEFIT],
    "Weight (0-10)": [8.0, 8.0, 6.0, 5.0, 5.0],
})


def reset_flow() -> None:
    S.na_stage, S.na_analysis, S.na_saved_id, S.na_error = "input", None, None, None


def fill_example() -> None:
    ex = SAMPLES["tech_stack"]
    S.na_title, S.na_desc = ex["title"], ex["description"]
    S.na_budget, S.na_time = ex["constraints"]["budget"], ex["constraints"]["time"]
    S.na_team, S.na_other = ex["constraints"]["team"], ex["constraints"]["other"]
    S.na_alt_mode, S.na_crit_mode = ALT_AI, CRIT_AI


def make_analyzer() -> DecisionAnalyzer:
    provider = GeminiProvider if config.get_provider_name() == "gemini" else OpenAIProvider
    return DecisionAnalyzer(provider())


def run_live(request) -> None:
    S.na_last_request = request
    try:
        with st.spinner("Analysing your decision with the AI… this can take 10–40 seconds."):
            analysis = ds.run_live_analysis(request, make_analyzer())
    except AIServiceError as exc:
        S.na_error = {"message": exc.message, "kind": exc.kind, "retryable": exc.retryable}
        return
    S.na_error, S.na_analysis, S.na_stage, S.na_saved_id = None, analysis, "review", None
    st.rerun()


def run_sample(key: str) -> None:
    S.na_error, S.na_analysis, S.na_stage, S.na_saved_id = None, ds.load_sample(key), "review", None
    st.rerun()


# ============================== INPUT STAGE ================================= #
def input_stage() -> None:
    utils.hero("Make a confident choice", "Turn a real-world decision into a clear, side-by-side comparison.")
    has_key = config.has_api_key()
    S.setdefault("na_mode", LIVE if has_key else SAMPLE)
    st.markdown("Start with a sample to explore the app, or use live AI to analyse your own decision.")
    mode = st.radio("Choose how to begin", [LIVE, SAMPLE], horizontal=True, key="na_mode",
                    help=f"Live mode uses {config.get_provider_display_name()}. Sample mode uses example data.")

    if mode == SAMPLE:
        st.info(f"{SAMPLE_LABEL}. Pick a scenario to explore the complete analysis flow. No API call is made.",
                icon="🧪")
        key = st.selectbox("Sample scenario", list(SAMPLES), format_func=lambda k: SAMPLES[k]["label"], key="na_sample")
        sample = SAMPLES[key]
        with st.container(border=True):
            st.markdown(f"**{sample['title']}**")
            st.write(sample["description"])
            st.caption(" · ".join(v for v in sample["constraints"].values() if v))
        if st.button("Load sample analysis", type="primary", key="na_load_sample"):
            run_sample(key)
        return

    if not has_key:
        st.warning(
            f"No {config.get_provider_display_name()} API key is configured, so live analysis is unavailable. "
            "Add your key to the local .env file and restart, or switch to Sample demo.",
            icon="🔑")
    st.button("✨ Fill with an example decision", on_click=fill_example, key="na_fill")

    with st.container(border=True):
        st.subheader("Your decision")
        st.text_input("Decision title *", key="na_title", placeholder="Choose a technology stack for our college project")
        st.text_area("Decision description *", key="na_desc", height=110,
                     placeholder="Describe what you need to decide, your goals and any context.")

    with st.container(border=True):
        st.subheader("Options to compare")
        S.setdefault("na_alt_mode", ALT_AI)
        alt_mode = st.radio("Where do the alternatives come from?", [ALT_AI, ALT_OWN], horizontal=True, key="na_alt_mode")
        if alt_mode == ALT_AI:
            st.slider("How many alternatives should the AI suggest?", config.MIN_ALTERNATIVES,
                      config.MAX_ALTERNATIVES, 4, key="na_alt_count")
        else:
            st.text_area(f"Alternatives ({config.MIN_ALTERNATIVES}–{config.MAX_ALTERNATIVES}, one per line)",
                         key="na_alt_text", height=120, placeholder="Python + Streamlit\nDjango\nMERN stack")

    with st.container(border=True):
        st.subheader("Your constraints")
        st.caption("Optional context helps the AI make more relevant suggestions.")
        c1, c2 = st.columns(2)
        c1.text_input("Budget / cost limits", key="na_budget", placeholder="Almost no budget")
        c2.text_input("Time available", key="na_time", placeholder="4 weeks")
        c3, c4 = st.columns(2)
        c3.text_input("Team size / resources", key="na_team", placeholder="3 members, strong in Python")
        c4.text_input("Other restrictions or preferences", key="na_other", placeholder="Must run offline")

    with st.container(border=True):
        st.subheader("What matters most?")
        S.setdefault("na_crit_mode", CRIT_AI)
        crit_mode = st.radio("Evaluation criteria", [CRIT_AI, CRIT_OWN], horizontal=True, key="na_crit_mode")
        st.caption("A **higher weight means a criterion is more important** (0–10). You can change weights again after the analysis.")
        edited = None
        if crit_mode == CRIT_AI:
            st.slider("How many criteria should the AI suggest?", config.MIN_CRITERIA, config.MAX_CRITERIA, 5, key="na_crit_count")
        else:
            edited = st.data_editor(
                DEFAULT_CRITERIA.copy(), key="na_crit_editor", num_rows="dynamic", hide_index=True, width="stretch",
                column_config={
                    "Criterion": st.column_config.TextColumn("Criterion", max_chars=60),
                    "Type": st.column_config.SelectboxColumn("Type", options=[TYPE_BENEFIT, TYPE_COST], required=True),
                    "Weight (0-10)": st.column_config.NumberColumn("Weight (0-10)", min_value=0, max_value=10, step=0.5),
                })
            st.caption(f"Choose {config.MIN_CRITERIA}–{config.MAX_CRITERIA} criteria. *Cost* criteria are ones where lower is better "
                       "(money, time, complexity).")
        st.text_input("Priorities note (optional)", key="na_prio", placeholder="Cost matters more than scalability")

    ready = has_key
    if st.button("🚀 Generate analysis", type="primary", disabled=not ready, key="na_generate"):
        criteria_rows = []
        if edited is not None:
            for _, row in edited.iterrows():
                criteria_rows.append({
                    "name": row.get("Criterion"),
                    "direction": "cost" if row.get("Type") == TYPE_COST else "benefit",
                    "weight": None if pd.isna(row.get("Weight (0-10)")) else row.get("Weight (0-10)")})
        request, errors = ds.validate_request(
            title=S.get("na_title", ""), description=S.get("na_desc", ""),
            alternatives=utils.parse_lines(S.get("na_alt_text", "")), use_ai_alternatives=alt_mode == ALT_AI,
            ai_alternative_count=S.get("na_alt_count", 4), criteria=criteria_rows, use_ai_criteria=crit_mode == CRIT_AI,
            ai_criteria_count=S.get("na_crit_count", 5), budget=S.get("na_budget", ""), time_limit=S.get("na_time", ""),
            team=S.get("na_team", ""), other_constraints=S.get("na_other", ""), priorities_note=S.get("na_prio", ""))
        if errors:
            S.na_error = None
            for message in errors:
                st.error(message)
        else:
            run_live(request)

    if S.na_error:
        ui.render_ai_error(S.na_error)
        if S.na_error.get("retryable") and S.na_last_request is not None:
            if st.button("🔄 Retry analysis", key="na_retry"):
                run_live(S.na_last_request)
                if S.na_error:
                    st.rerun()


# ============================== REVIEW STAGE ================================ #
def review_stage() -> None:
    analysis = S.na_analysis
    utils.hero("Review the ratings", "Check the AI's estimates and edit anything that doesn't match your knowledge.")
    ui.banner(analysis)
    with st.container(border=True):
        st.subheader(analysis["title"])
        considerations = analysis.get("summary", {}).get("key_considerations") or []
        if considerations:
            st.markdown("**Key considerations:** " + " · ".join(considerations))
        w_rows = [{"Criterion": c["name"], "Type": c["direction"].title(), "Starting weight": analysis["weights"][c["name"]],
                   "Meaning": c.get("description", "")} for c in analysis["criteria"]]
        st.dataframe(pd.DataFrame(w_rows), hide_index=True, width="stretch")
        st.caption("Starting weights can be changed on the results page without another AI call.")

    alts = [a["name"] for a in analysis["alternatives"]]
    crits = [c["name"] for c in analysis["criteria"]]
    df = pd.DataFrame([[analysis["ratings"][a][c] for c in crits] for a in alts], index=alts, columns=crits)
    st.markdown("#### Raw ratings (1–10)")
    st.caption("For **benefit** criteria a higher rating is better. For **cost ↓** criteria a higher rating means *more* "
               "cost/effort/time (worse); the engine inverts it automatically.")
    cfg = {c["name"]: st.column_config.NumberColumn(
        c["name"] + (" ↓" if c["direction"] == "cost" else ""), min_value=1, max_value=10, step=0.5, required=True)
        for c in analysis["criteria"]}
    edited = st.data_editor(df, key=f"na_ratings_{analysis['uid']}", column_config=cfg, width="stretch")

    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("✅ Confirm & show results", type="primary", key="na_confirm"):
        if edited.isna().any().any():
            st.error("Every rating must be filled in with a number from 1 to 10.")
            return
        new_ratings = {a: {c: float(edited.loc[a, c]) for c in crits} for a in alts}
        candidate = {**analysis, "ratings": new_ratings}
        try:
            ds.compute_results(candidate)
        except se.ScoringError as exc:
            st.error(str(exc))
            return
        analysis["ratings_edited"] = any(abs(new_ratings[a][c] - analysis["ratings"][a][c]) > 1e-9 for a in alts for c in crits)
        analysis["ratings"] = new_ratings
        analyzer = None
        if analysis["mode"] == "live":
            try:
                analyzer = make_analyzer()
            except AIServiceError:
                analyzer = None
        with st.spinner("Generating the recommendation explanation…"):
            ds.attach_recommendation(analysis, analyzer)
        S.na_stage = "results"
        st.rerun()
    if b2.button("← Start over", key="na_back"):
        reset_flow()
        st.rerun()


# ============================== RESULTS STAGE =============================== #
def results_stage() -> None:
    analysis = S.na_analysis
    prefix = f"new_{analysis['uid']}"
    weights = ui.get_current_weights(analysis, prefix)
    b1, b2, _ = st.columns([1, 1, 3])
    label = "💾 Update saved analysis" if S.na_saved_id else "💾 Save analysis"
    if b1.button(label, type="primary", key="na_save"):
        try:
            results = ds.compute_results(analysis, weights)
            analysis["weights"] = dict(weights)
            if S.na_saved_id:
                database.update_weights(S.na_saved_id, weights, results)
                st.toast(f"Saved analysis #{S.na_saved_id} updated.")
            else:
                S.na_saved_id = database.save_analysis(analysis, results)
                st.toast(f"Saved as analysis #{S.na_saved_id}. Open Analysis History to view it.")
        except (database.DatabaseError, se.ScoringError) as exc:
            st.error(f"Could not save: {exc}")
    if b2.button("➕ New analysis", key="na_new"):
        reset_flow()
        st.rerun()
    if S.na_saved_id:
        st.caption(f"Saved as analysis #{S.na_saved_id}.")
    ui.render_results(analysis, prefix)


stage = S.na_stage
if stage == "review" and S.na_analysis:
    review_stage()
elif stage == "results" and S.na_analysis:
    results_stage()
else:
    input_stage()
