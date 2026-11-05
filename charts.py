"""Plotly figures. All values come straight from ScoreResult objects."""
from __future__ import annotations

import plotly.graph_objects as go

import scoring_engine as se

LEADER = "#4F46E5"
OTHER = "#A5B4FC"
_MARGIN = dict(l=10, r=30, t=30, b=10)


def score_bar_chart(results) -> go.Figure:
    names = [r.alternative for r in results]
    scores = [se.round_score(r.score) for r in results]
    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker_color=[LEADER] + [OTHER] * (len(results) - 1),
        text=[f"{s:.2f}" for s in scores], textposition="outside",
        hovertemplate="%{y}: %{x:.2f}/10<extra></extra>"))
    fig.update_xaxes(range=[0, 10.8], title="Weighted score (1–10)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=110 + 55 * len(results), margin=_MARGIN, showlegend=False)
    return fig


def ratings_heatmap(results, criteria: list[str]) -> go.Figure:
    z = [[r.criterion_scores[c] for c in criteria] for r in results]
    fig = go.Figure(go.Heatmap(
        z=z, x=criteria, y=[r.alternative for r in results], zmin=1, zmax=10,
        text=[[f"{v:.1f}" for v in row] for row in z], texttemplate="%{text}",
        colorscale="Tealgrn", xgap=2, ygap=2,
        colorbar=dict(title="Score"), hovertemplate="%{y}<br>%{x}: %{z:.2f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=130 + 55 * len(results), margin=_MARGIN)
    return fig


def grouped_bar_chart(results, criteria: list[str]) -> go.Figure:
    fig = go.Figure()
    for c in criteria:
        fig.add_bar(name=c, x=[r.alternative for r in results],
                    y=[se.round_score(r.criterion_scores[c]) for r in results])
    fig.update_layout(barmode="group", height=380, margin=_MARGIN,
                      yaxis=dict(range=[0, 10.5], title="Normalised score (higher is better)"),
                      legend=dict(orientation="h", yanchor="top", y=-0.2))
    return fig


def weights_chart(weights: dict) -> go.Figure:
    total = sum(weights.values())
    items = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    pct = [(w / total * 100) if total > 0 else 0 for _, w in items]
    fig = go.Figure(go.Bar(
        x=pct, y=[k for k, _ in items], orientation="h", marker_color=LEADER,
        text=[f"{p:.1f}%" for p in pct], textposition="outside",
        hovertemplate="%{y}: %{x:.1f}% of total importance<extra></extra>"))
    fig.update_xaxes(range=[0, max(pct + [1]) * 1.25], title="Share of total importance (%)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=110 + 45 * len(items), margin=_MARGIN, showlegend=False)
    return fig
