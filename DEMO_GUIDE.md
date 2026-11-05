# DecisionForge AI — Demo Guide

## 0. Before you present (10 minutes of preparation)

1. Activate the virtual environment and run `python -m pytest -q` — all tests should pass.
2. Start the app: `streamlit run app.py`.
3. If using live mode, configure a newly generated Gemini API key in the local `.env`, then do a full dry run and note the model. Never reuse a key shared in chat. Live output varies, so do not memorise live numbers.
4. Prepare a fallback: the **Sample demo** mode works with no internet and no key. If the API fails during the demo, say so calmly and switch to it. It is clearly labelled *Sample Demo — Not Live AI Output*.
5. Optionally save one live analysis beforehand, so the History page already has an entry.
6. Close other windows; set browser zoom to ~90–100%.

Numbers you can safely quote **from the sample "tech stack" scenario** (deterministic):

| Weights | 1st | 2nd | 3rd | 4th |
|---|---|---|---|---|
| Original (cost 9, time 9, learning 6, scalability 3, maintainability 5, community 4) | Python + Streamlit 7.72 | Django + Bootstrap 7.28 | MERN 5.75 | Flutter + Firebase 5.14 |
| Revised (cost 3, time 5, learning 4, scalability 10, maintainability 7, community 4) | **Django + Bootstrap 7.24** | MERN 6.33 | Python + Streamlit 6.09 | Flutter + Firebase 6.03 |

The "project-management tools" sample is useful for showing the **disagreement note**: its qualitative initial suggestion is GitHub Projects, but the calculated leader is Trello (7.84 vs 7.51) under the default weights.

---

## 1. Five-minute live demonstration

| Time | Action | What to say |
|---|---|---|
| 0:00 | Slide/verbal intro | "Decisions with several options and conflicting goals are usually made by gut feeling. DecisionForge AI makes the reasoning explicit and explainable." |
| 0:20 | Open the app (Home page) | "AI writes the analysis; Python does the maths. That split is the core idea." |
| 0:40 | **New Analysis** → *Live GenAI* → click **Fill with an example decision** | "Our team of three has four weeks and almost no budget — which technology stack should we use?" Point out budget, time, team and the constraint fields. |
| 1:10 | Show criteria option "Let AI suggest criteria and starting weights" and alternatives "Let AI suggest" → **Generate analysis** | "I'm not listing options myself; the AI proposes alternatives and criteria." While the spinner runs: "The reply must be valid JSON that passes Pydantic validation." |
| 1:50 | **Review the ratings** page | "These ratings are AI *estimates*. I can edit any of them before confirming." Change one rating to show control. Click **Confirm & show results**. |
| 2:20 | Results: recommendation card, ranked table, bar chart, heatmap | "The score is a weighted average calculated by Python. The AI only explains it afterwards. Cost criteria are inverted so cheaper is better." |
| 3:00 | Weight sliders: **raise Scalability, lower Cost** | "No API call now — Python recalculates instantly." Read the blue impact box aloud. If the leader changed: "The recommendation changed because priorities changed." If not: "The leader stayed the same — the app tells us that too." |
| 3:40 | Click **Reset to original weights** | "Fully reproducible." |
| 3:50 | Click **Save analysis** | "Saved to local SQLite." |
| 4:00 | **Analysis History** → open the saved analysis | "It survives restarts. I can change weights again and update it." |
| 4:20 | **About Project** page (architecture diagram + formula) | Point to the green scoring engine: "The LLM never touches this box." Show the formula `Σ(w·r)/Σ(w)`. |
| 4:50 | Close | "Limitations: ratings are estimates and should be verified with real data. Future work: sensitivity analysis and more providers." |

**If the API is unavailable:** switch to *Sample demo* → "Choose a technology stack…" → Load → Confirm. Then do steps from 3:00 on; they are identical. Say clearly that this part is sample data.

---

## 2. 60-second project introduction (script)

"Our project is **DecisionForge AI**, an explainable generative-AI system for multi-criteria decision analysis. Many real decisions — which technology to use, which tool to buy — involve several options and conflicting goals. People usually decide informally, and chatbots give advice that is hard to verify. Our system asks the user for the decision, constraints and priorities; Gemini suggests alternatives and criteria and drafts strengths, weaknesses, risks and trade-offs. Crucially, the **ranking is not produced by the AI**: a separate Python scoring engine calculates a weighted score from 1 to 10, so every result can be reproduced. Users can edit the AI's ratings, change the importance of each criterion, and immediately see how the ranking changes. Analyses are saved in SQLite. We built it with Streamlit, Pandas, Plotly, Pydantic, SQLite and the Gemini API, and tested the core logic with automated tests."

## 3. Simple explanation of the role of GenAI

The AI does the parts that need language understanding: reading the problem, suggesting options and criteria, estimating how each option does on each criterion, listing risks and trade-offs, and explaining the final result in plain English. It does **not** decide the final ranking.

## 4. Simple explanation of weighted scoring

Give each option a 1–10 rating on every criterion. Cost-like criteria are flipped (11 − rating) so "cheaper" scores higher. Multiply each rating by how important that criterion is (its weight), add them up, and divide by the total weight. That is a weighted average, always between 1 and 10. Example: ratings 9 (cost) and 6 (quality) with weights 1 and 3 give (1×9 + 3×6) ÷ 4 = 6.75.

## 5. Why this is a GenAI project and not just a calculator

A calculator needs the alternatives, criteria and ratings typed in by the user. In DecisionForge AI the LLM **interprets free-text decisions, generates alternatives and criteria, produces the ratings and rationales, identifies risks and trade-offs, and writes the explanation** of the result — all as validated structured output. The deterministic engine makes that generative output auditable. Remove the LLM and the system has no content to score; remove the engine and the ranking is not reproducible. The project is the combination.

---

## 6. Likely viva questions and answers

**1. What problem does your project solve?**
It helps users compare options against their own goals and constraints in a transparent way, instead of relying on gut feeling or on an opaque chatbot answer.

**2. Which parts use generative AI and which don't?**
GenAI: interpreting the decision, suggesting alternatives/criteria, estimating ratings, strengths/weaknesses, risks, trade-offs and the explanation. Plain Python: validation, normalisation, weighted scoring, ranking, tie-breaking, weight-change analysis, charts and the database.

**3. How do you prevent the LLM from hallucinating?**
We cannot eliminate it, so we limit its impact: the prompt forbids inventing prices or benchmarks and requires assumptions to be listed; output must be valid JSON that passes Pydantic schemas and is reconciled with the user's input; ratings are shown as *estimates* and can be edited; the AI cannot set final scores; and the interface lists items to verify before a real decision.

**4. How reliable is the AI's output?**
Not guaranteed. Different runs can give different ratings. That is why there is a review/edit step, why labels say "AI-generated estimate", and why the ranking is recomputable from visible numbers. We have not measured accuracy and make no accuracy claims.

**5. What happens if the AI returns malformed JSON?**
The response is parsed and validated. If it fails, the app sends **one** repair request that includes the validation error. If that also fails the user sees a clear message and a Retry button. Retries are bounded, so there are no endless API calls.

**6. What if the API key is missing, the network is down or the rate limit is hit?**
Missing key: Live mode is disabled with an explanation, and Sample demo still works. Timeouts, connection errors, authentication errors and rate limits each produce a specific, friendly message without exposing the key.

**7. Why not let the LLM calculate the final ranking?**
LLMs are not reliable calculators and are non-deterministic. A Python engine is exact, unit-tested, reproducible and explainable. It also means weight changes need no extra API call.

**8. Explain your scoring formula.**
`Score(i) = Σ_j w_j · r_ij / Σ_j w_j`, where `r_ij` is the normalised 1–10 rating and `w_j` the weight. Benefit criteria use the rating as is; cost criteria use `11 − rating`.

**9. How do you treat cost criteria compared with benefit criteria?**
For a cost criterion the raw rating means "how much cost/effort/time". The engine converts it with `11 − raw`, so low cost produces a high normalised score. This avoids the common mistake of rewarding high cost.

**10. Is the scoring fair?**
It is consistent and transparent, not "objective". Fairness depends on the criteria chosen, the weights and the ratings. All three are visible and editable. The weighted-sum method is also compensatory: a very high score on one criterion can offset a low score on another.

**11. How are ties handled?**
Equal scores are broken by the normalised score on the most heavily weighted criterion, then the next one, then alphabetically — so the order is always the same. The interface also notes that a tie exists.

**12. What do the weights mean?**
A higher weight means the criterion is more important. For a cost criterion, the weight is the importance of keeping that cost low. Only the *relative* sizes matter, because the score is divided by the sum of weights.

**13. What happens when the user changes the weights?**
Python recalculates every score, the table and charts update, and the app compares the old and new rankings and states whether the leader changed. No AI call is made.

**14. What if the AI's recommendation disagrees with the calculated ranking?**
The interface shows a notice naming both, keeps the calculated ranking unchanged, and asks the user to review the assumptions and ratings. It does not silently overwrite either.

**15. What is unique about your project compared with asking ChatGPT?**
The structure and traceability: validated schemas, an independent scoring engine, editable ratings, instant what-if analysis, persistent history and honest labelling of estimates. (We have not run comparative experiments, so we do not claim better answers.)

**16. How do you handle API dependency?**
The scoring engine, database, charts and sample demo work offline. Only live analysis needs the API. The provider is behind an `LLMProvider` interface so it can be replaced without changing the scoring code.

**17. How is your API key protected?**
It is read from a `.env` file that is git-ignored, never hard-coded, never stored in SQLite, never shown in the UI, and error messages do not echo it. Tests check that it is not saved to the database or put in prompts.

**18. How do you know the scoring engine is correct?**
Automated pytest tests compare it with hand-calculated results and cover cost vs benefit handling, zero/negative/all-zero weights, invalid ratings, ties, bounds and recalculation. They run without any API key.

**19. What are the limitations?**
AI ratings are estimates and may be wrong or outdated; weighted-sum assumes independent, compensatory criteria; results depend on the weights; live mode needs internet and may cost money; single local user only.

**20. What would you improve next?**
Sensitivity analysis (at which weight does the winner change), other MCDA methods such as TOPSIS or AHP, importing real measured data, more LLM providers and report export.

**21. Why Streamlit and SQLite?**
Both run locally with no server setup, which suits a student project and demonstration. Streamlit gives a professional dashboard quickly; SQLite persists history in one file.

**22. How does Sample mode work, and is it honest?**
It loads predefined example data, not LLM output, and every screen is labelled *Sample Demo — Not Live AI Output*. Scoring, charts, weight changes and saving are real calculations on that data.
