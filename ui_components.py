"""Reusable Streamlit components, mainly the results dashboard."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts
import decision_service as ds
import scoring_engine as se
from sample_data import SAMPLE_LABEL

DISCLAIMER = ("Ratings are **AI-generated estimates** (or sample values) on a 1–10 scale, not objective measurements "
              "unless you supply real data. Scores and rankings are **calculated by Python**, not by the AI.")


# --------------------------------------------------------------------------- #
# Weights
# --------------------------------------------------------------------------- #
def weight_key(prefix: str, idx: int) -> str:
    return f"{prefix}_w_{idx}"


def get_current_weights(analysis: dict, prefix: str) -> dict:
    out = {}
    for i, c in enumerate(analysis["criteria"]):
        value = st.session_state.get(weight_key(prefix, i))
        out[c["name"]] = float(value) if value is not None else float(analysis["weights"][c["name"]])
    return out


def _reset_weights(analysis: dict, prefix: str) -> None:
    for i, c in enumerate(analysis["criteria"]):
        st.session_state[weight_key(prefix, i)] = float(analysis["original_weights"][c["name"]])


def render_ai_error(error: dict) -> None:
    icon = {"rate_limit": "⏳", "timeout": "⌛", "connection": "📡", "auth": "🔑", "unsupported": "🚫"}.get(error.get("kind"), "⚠️")
    st.error(error["message"], icon=icon)


def banner(analysis: dict) -> None:
    if analysis.get("mode") == "sample":
        st.warning(f"**{SAMPLE_LABEL}.** Predefined example data, not produced by an LLM. "
                   "Scoring, charts and weight changes below are fully live.", icon="🧪")
    else:
        st.success(f"Live GenAI analysis · model `{analysis.get('model')}`. {DISCLAIMER}", icon="🤖")


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def render_results(analysis: dict, prefix: str) -> None:
    criteria = analysis["criteria"]
    crit_names = [c["name"] for c in criteria]
    directions = {c["name"]: c["direction"] for c in criteria}

    banner(analysis)
    weights = get_current_weights(analysis, prefix)
    try:
        results = ds.compute_results(analysis, weights)
    except se.ScoringError as exc:
        st.error(f"{exc} Showing the original weights instead.")
        weights = dict(analysis["original_weights"])
        results = ds.compute_results(analysis, weights)

    # A. Decision summary --------------------------------------------------
    with st.container(border=True):
        st.subheader(analysis["title"])
        st.write(analysis.get("summary", {}).get("restated_decision") or analysis["description"])
        c = analysis.get("constraints", {})
        labels = [("Budget", c.get("budget")), ("Time", c.get("time")), ("Team", c.get("team")),
                  ("Other", c.get("other")), ("Priorities", c.get("priorities_note"))]
        shown = [f"**{k}:** {v}" for k, v in labels if v]
        if shown:
            st.markdown("  \n".join(shown))
        m1, m2, m3 = st.columns(3)
        m1.metric("Alternatives", len(analysis["alternatives"]))
        m2.metric("Criteria", len(criteria))
        m3.metric("Source", "Sample demo" if analysis.get("mode") == "sample" else "Live GenAI")

    # B. Recommendation ----------------------------------------------------
    top = results[0]
    rec = analysis.get("recommendation") or ds.deterministic_recommendation(analysis, results)
    with st.container(border=True):
        left, right = st.columns([3, 1])
        left.markdown("#### 🏆 Recommended alternative")
        left.markdown(f"### {top.alternative}")
        right.metric("Weighted score", f"{se.round_score(top.score):.2f} / 10")
        if top.tied_with:
            st.info("Tied on score with: " + ", ".join(top.tied_with) + ". The tie is broken by the most heavily weighted criteria.")
        st.markdown(ds.why_ranked_first(analysis, results, weights))
        st.markdown(f"**Main caveat:** {ds.main_caveat(analysis, results)}")
        st.divider()
        src = {"ai": "AI explanation (written for the original weights)", "sample": "Sample explanation (not live AI)",
               "deterministic": "Calculated summary"}.get(rec.get("source"), "Explanation")
        st.markdown(f"**{src}**")
        st.write(rec["explanation"])
        if rec.get("main_caveat"):
            st.caption("Caveat: " + rec["main_caveat"])
        if rec.get("warning"):
            st.warning(rec["warning"])
        if rec.get("source") == "ai" and rec.get("weights") != weights:
            st.caption("⚠️ Your weights differ from those used for this explanation; the ranking above reflects your current weights.")
        note = ds.initial_recommendation_note(analysis, results)
        if note:
            (st.warning if note[0] == "disagree" else st.info)(note[1])

    # Interactive weights --------------------------------------------------
    with st.container(border=True):
        st.subheader("⚖️ Adjust criterion importance")
        st.caption("A **higher weight means the criterion is more important** (0 = ignored, 10 = critical). "
                   "For cost-type criteria the weight is the importance of keeping that cost *low*. "
                   "Scores recalculate instantly in Python; no AI call is made.")
        cols = st.columns(min(3, len(criteria)))
        for i, crit in enumerate(criteria):
            key = weight_key(prefix, i)
            st.session_state.setdefault(key, float(analysis["weights"][crit["name"]]))
            suffix = " ↓ cost" if crit["direction"] == "cost" else ""
            cols[i % len(cols)].slider(crit["name"] + suffix, 0.0, 10.0, step=0.5, key=key,
                                       help=crit.get("description") or None)
        st.button("↺ Reset to original weights", key=f"{prefix}_reset", on_click=_reset_weights,
                  args=(analysis, prefix))
        summary = ds.weight_change_summary(analysis, weights)
        if summary:
            st.info(summary, icon="🔁")
        else:
            st.caption("Using the original weights.")

    # Tabs -----------------------------------------------------------------
    tab_cmp, tab_alt, tab_risk, tab_trade, tab_assume = st.tabs(
        ["📊 Ranking & charts", "🧩 Alternatives", "⚠️ Risks", "↔️ Trade-offs", "📝 Assumptions & limits"])

    with tab_cmp:
        df = ds.results_dataframe(analysis, results)
        cfg = {"Final Score": st.column_config.ProgressColumn("Final Score", min_value=0, max_value=10, format="%.2f"),
               "Rank": st.column_config.NumberColumn("Rank", width="small")}
        st.dataframe(df, hide_index=True, width="stretch", column_config=cfg)
        st.caption("Criterion columns show **normalised** scores (1–10, higher is always better; cost criteria are inverted). "
                   "Final Score = Σ(weight × score) ÷ Σ(weight).")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Final weighted scores**")
            st.plotly_chart(charts.score_bar_chart(results), width="stretch", key=f"{prefix}_bar")
        with c2:
            st.markdown("**Criterion weights (share of importance)**")
            st.plotly_chart(charts.weights_chart(weights), width="stretch", key=f"{prefix}_wchart")
        view = st.radio("Criterion-level view", ["Heatmap", "Grouped bars"], horizontal=True, key=f"{prefix}_view")
        fig = charts.ratings_heatmap(results, crit_names) if view == "Heatmap" else charts.grouped_bar_chart(results, crit_names)
        st.plotly_chart(fig, width="stretch", key=f"{prefix}_crit")

    with tab_alt:
        info = {a["name"]: a for a in analysis["alternatives"]}
        for r in results:
            a = info[r.alternative]
            with st.expander(f"#{r.rank} · {a['name']} — {se.round_score(r.score):.2f}/10", expanded=r.rank == 1):
                if a.get("description"):
                    st.caption(a["description"])
                s, w, u = st.columns(3)
                s.markdown("**Strengths**\n" + "\n".join(f"- {x}" for x in a["strengths"]))
                w.markdown("**Weaknesses**\n" + "\n".join(f"- {x}" for x in a["weaknesses"]))
                u.markdown("**Suitable use cases**\n" + ("\n".join(f"- {x}" for x in a.get("suitable_use_cases", [])) or "- —"))
                rows = [{"Criterion": c, "Type": directions[c].title(), "Raw rating (estimate)": r.raw_ratings[c],
                         "Normalised": se.round_score(r.criterion_scores[c]),
                         "Rationale": (analysis.get("rationales", {}).get(r.alternative, {}) or {}).get(c, "")}
                        for c in crit_names]
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    with tab_risk:
        risks = analysis.get("risks") or []
        if not risks:
            st.info("No risks were recorded for this analysis.")
        else:
            st.table(pd.DataFrame([{"Alternative": x["alternative"], "Risk": x["description"], "Potential impact": x["impact"],
                                    "Likelihood (qualitative)": x["likelihood"], "Mitigation": x["mitigation"]} for x in risks]))
        st.caption("Likelihood labels are qualitative judgements, not statistically calibrated probabilities.")

    with tab_trade:
        trade = {t["alternative"]: t for t in analysis.get("tradeoffs") or []}
        if not trade:
            st.info("No trade-off analysis was recorded.")
        for r in results:
            t = trade.get(r.alternative)
            if t:
                with st.container(border=True):
                    st.markdown(f"**#{r.rank} {r.alternative}**")
                    g, s = st.columns(2)
                    g.markdown(f"✅ **You gain:** {t['gains']}")
                    s.markdown(f"❌ **You sacrifice:** {t['sacrifices']}")

    with tab_assume:
        def _block(title: str, items: list | None) -> None:
            st.markdown(f"**{title}**")
            for item in items or ["—"]:
                st.markdown(f"- {item}")
        _block("Assumptions that could affect the ranking", analysis.get("assumptions"))
        _block("Limitations", analysis.get("limitations"))
        _block("Verify before a real-world decision", analysis.get("verify_before_deciding"))
        st.markdown("**About the numbers**")
        st.markdown("- " + DISCLAIMER)
        if analysis.get("ratings_edited"):
            st.markdown("- You edited some ratings before confirming this analysis.")
        if analysis.get("mode") == "sample":
            st.markdown(f"- {SAMPLE_LABEL}.")
