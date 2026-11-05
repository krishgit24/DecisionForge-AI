"""Predefined sample scenarios for demo mode.

Everything here is hand-written example data. It is NOT live AI output and the
ratings are illustrative estimates, not verified measurements. The UI labels
these results "Sample Demo — Not Live AI Output".
"""
from __future__ import annotations

SAMPLE_LABEL = "Sample Demo — Not Live AI Output"


def _ratings(table: dict) -> list[dict]:
    """{alt: {criterion: (rating, rationale)}} -> list of RatingItem dicts."""
    return [
        {"alternative": a, "criterion": c, "rating": v[0], "rationale": v[1]}
        for a, crits in table.items() for c, v in crits.items()
    ]


# --------------------------------------------------------------------------- #
# Scenario 1 - technology stack
# --------------------------------------------------------------------------- #
_TECH_CRITERIA = [
    ("Budget Cost", "cost", 9, "Money needed for hosting, services and tooling."),
    ("Time to Build", "cost", 9, "Effort needed to reach a working demo."),
    ("Learning Curve", "cost", 6, "How hard it is for this team to become productive."),
    ("Scalability", "benefit", 3, "Ability to grow beyond a demo."),
    ("Maintainability", "benefit", 5, "Ease of keeping the code organised."),
    ("Community Support", "benefit", 4, "Availability of tutorials and answers."),
]
_PS, _DJ, _ME, _FL = "Python + Streamlit", "Django + Bootstrap", "MERN (React + Node + MongoDB)", "Flutter + Firebase"
_TECH_RATINGS = {
    _PS: {"Budget Cost": (2, "Free, open source, runs locally."), "Time to Build": (2, "Dashboards need very little code."),
          "Learning Curve": (2, "Team already knows Python."), "Scalability": (3, "Built for prototypes, limited multi-user scale."),
          "Maintainability": (5, "Single-file apps get messy without structure."), "Community Support": (7, "Active, smaller than web giants.")},
    _DJ: {"Budget Cost": (2, "Free; simple hosting options."), "Time to Build": (5, "Models, views and templates take longer."),
          "Learning Curve": (6, "New framework concepts, but Python."), "Scalability": (7, "Proven for large sites."),
          "Maintainability": (8, "Opinionated structure helps teams."), "Community Support": (9, "Very mature ecosystem.")},
    _ME: {"Budget Cost": (3, "Free tooling; hosted DB may cost."), "Time to Build": (8, "Three layers to learn and wire up."),
          "Learning Curve": (8, "Limited JavaScript experience in team."), "Scalability": (8, "Widely used for scalable apps."),
          "Maintainability": (6, "Flexible but needs discipline."), "Community Support": (9, "Huge community.")},
    _FL: {"Budget Cost": (5, "Cloud usage limits and device testing."), "Time to Build": (8, "New language and cloud setup."),
          "Learning Curve": (8, "Dart and Firebase are new to the team."), "Scalability": (8, "Managed backend scales well."),
          "Maintainability": (6, "Good tooling, vendor lock-in."), "Community Support": (8, "Strong and growing.")},
}

TECH_STACK = {
    "key": "tech_stack",
    "label": "Choose a technology stack for a college project",
    "title": "Choose a technology stack for our college project",
    "description": (
        "Our three-member final-year team must deliver a working web application with a database "
        "and an interactive dashboard in four weeks. Everyone knows Python well; only one member "
        "has used JavaScript. We have almost no budget and need a reliable live demo on laptops."),
    "constraints": {"budget": "Almost no budget (free tools only)", "time": "4 weeks",
                    "team": "3 members; strong Python, limited JavaScript",
                    "other": "Must run locally for the demonstration"},
    "suggested_revised_weights": {"Budget Cost": 3, "Time to Build": 5, "Learning Curve": 4,
                                  "Scalability": 10, "Maintainability": 7, "Community Support": 4},
    "payload": {
        "summary": {"restated_decision": "Select the technology stack that best fits a three-person Python-skilled team delivering a demo-ready web app in four weeks with no budget.",
                    "key_considerations": ["Very short deadline", "Team is strongest in Python", "Free tooling only", "Reliable local demo"]},
        "alternatives": [
            {"name": _PS, "description": "Pure-Python web UI framework for data apps.",
             "strengths": ["Fastest path to a working dashboard", "No JavaScript needed", "Free and local"],
             "weaknesses": ["Limited to prototypes at scale", "Less control over custom UI"],
             "suitable_use_cases": ["Data dashboards", "Course projects and demos"],
             "key_advantage": "Fastest delivery with existing Python skills.", "main_disadvantage": "Limited scalability and UI customisation."},
            {"name": _DJ, "description": "Full-stack Python web framework with server-rendered pages.",
             "strengths": ["Mature, structured and secure by default", "Built-in ORM and admin", "Python-based"],
             "weaknesses": ["More boilerplate than Streamlit", "Slower to build an interactive dashboard"],
             "suitable_use_cases": ["Multi-user web apps", "Projects expected to grow"],
             "key_advantage": "Strong structure and scalability while staying in Python.", "main_disadvantage": "Needs more build time than the four-week plan comfortably allows."},
            {"name": _ME, "description": "JavaScript stack with React front end, Node.js API and MongoDB.",
             "strengths": ["Industry-relevant skills", "Highly flexible UI", "Huge ecosystem"],
             "weaknesses": ["Steep curve for this team", "Three layers to integrate"],
             "suitable_use_cases": ["Production-style SPAs", "Teams with JavaScript experience"],
             "key_advantage": "Flexible, scalable and widely used.", "main_disadvantage": "High learning and integration effort."},
            {"name": _FL, "description": "Cross-platform apps with a managed cloud backend.",
             "strengths": ["Managed backend", "One codebase for mobile and web"],
             "weaknesses": ["Dart and Firebase are new", "Cloud usage limits and lock-in"],
             "suitable_use_cases": ["Mobile-first apps"],
             "key_advantage": "Managed backend scales without server work.", "main_disadvantage": "Poor fit for the team's skills and timeline."},
        ],
        "criteria": [{"name": n, "description": d, "direction": dr, "suggested_weight": w} for n, dr, w, d in _TECH_CRITERIA],
        "ratings": _ratings(_TECH_RATINGS),
        "risks": [
            {"alternative": _PS, "description": "Requirements grow beyond what Streamlit handles well.", "impact": "Rewrite or compromised features late in the project.", "likelihood": "Medium", "mitigation": "Freeze scope early; separate logic from UI so it can be reused."},
            {"alternative": _DJ, "description": "Boilerplate consumes the four-week schedule.", "impact": "Dashboard features cut or unfinished.", "likelihood": "Medium", "mitigation": "Use generators and templates; build a thin vertical slice first."},
            {"alternative": _ME, "description": "Team spends time learning instead of building.", "impact": "Incomplete demo.", "likelihood": "High", "mitigation": "Assign the JavaScript-experienced member as lead and timebox learning."},
            {"alternative": "General", "description": "Ratings are estimates and may not match your team's real skills.", "impact": "Ranking could be misleading.", "likelihood": "Medium", "mitigation": "Edit ratings to reflect your own experience before deciding."},
        ],
        "tradeoffs": [
            {"alternative": _PS, "gains": "Speed, simplicity, low risk of missing the deadline.", "sacrifices": "Scalability and fine UI control."},
            {"alternative": _DJ, "gains": "Structure, scalability and maintainability in Python.", "sacrifices": "Extra build time."},
            {"alternative": _ME, "gains": "Flexibility and marketable skills.", "sacrifices": "Time and a steep learning curve."},
            {"alternative": _FL, "gains": "Managed backend and mobile reach.", "sacrifices": "Familiarity, simplicity and some cost control."},
        ],
        "assumptions": ["The project is a data-driven web app, not a mobile-first product.", "The team's Python skill is stronger than its JavaScript skill.", "Free tiers remain available (not verified)."],
        "limitations": ["Ratings are illustrative estimates, not benchmark results.", "Library versions, pricing and free-tier limits change and were not checked."],
        "verify_before_deciding": ["Confirm hosting or free-tier limits you rely on.", "Check your supervisor's technology requirements.", "Validate team skill levels honestly."],
        "initial_recommendation": {"alternative": _PS, "reasoning": "Best match for a short deadline, Python skills and a tiny budget."},
    },
    "recommendation": {
        "explanation": ("With the default priorities, cost, time and learning effort dominate the decision, and "
                        "Python + Streamlit performs best on all three, so it ranks first. Django is a credible second "
                        "choice that gains ground when scalability and maintainability matter more."),
        "main_caveat": "Streamlit is weaker on scalability, so confirm the project will not need to grow beyond a demo.",
    },
}

# --------------------------------------------------------------------------- #
# Scenario 2 - project-management tools
# --------------------------------------------------------------------------- #
_PM_CRITERIA = [
    ("Cost", "cost", 8, "Subscription cost for the team."),
    ("Setup Effort", "cost", 7, "Time needed before the team can work."),
    ("Ease of Use", "benefit", 9, "How quickly students become productive."),
    ("Collaboration", "benefit", 6, "Sharing, comments and assignments."),
    ("Reporting & Tracking", "benefit", 3, "Progress reports and sprint tracking."),
    ("Developer Tool Integration", "benefit", 4, "Connection to code repositories."),
]
_TR, _NO, _GH, _JI = "Trello", "Notion", "GitHub Projects", "Jira (free plan)"
_PM_RATINGS = {
    _TR: {"Cost": (2, "Free tier is usually sufficient."), "Setup Effort": (2, "Boards take minutes."),
          "Ease of Use": (9, "Very intuitive cards and lists."), "Collaboration": (7, "Comments and assignments."),
          "Reporting & Tracking": (4, "Basic without add-ons."), "Developer Tool Integration": (5, "Possible via power-ups.")},
    _NO: {"Cost": (3, "Free for small teams (verify)."), "Setup Effort": (5, "Flexible, so needs structuring."),
          "Ease of Use": (7, "Easy once templates are used."), "Collaboration": (9, "Strong shared docs and boards."),
          "Reporting & Tracking": (5, "Possible with databases."), "Developer Tool Integration": (4, "Limited native support.")},
    _GH: {"Cost": (1, "Included with GitHub."), "Setup Effort": (3, "Linked to the existing repository."),
          "Ease of Use": (5, "Less polished for non-developers."), "Collaboration": (7, "Issues, reviews and mentions."),
          "Reporting & Tracking": (5, "Basic insights and views."), "Developer Tool Integration": (10, "Native to the code workflow.")},
    _JI: {"Cost": (3, "Free plan limits apply (verify)."), "Setup Effort": (7, "Projects and workflows need configuring."),
          "Ease of Use": (4, "Feature-rich but heavy."), "Collaboration": (8, "Mature team workflows."),
          "Reporting & Tracking": (9, "Strong sprint and burndown reports."), "Developer Tool Integration": (8, "Good integrations.")},
}

PM_TOOLS = {
    "key": "pm_tools",
    "label": "Compare project-management tools for a student team",
    "title": "Pick a project-management tool for our student team",
    "description": (
        "A five-member student team needs a free tool to plan tasks, assign work and track progress "
        "during a ten-week software project. Some members are not developers."),
    "constraints": {"budget": "Free plans only", "time": "Ten-week project", "team": "5 students, mixed technical skill",
                    "other": "Quick onboarding needed"},
    "suggested_revised_weights": {"Cost": 5, "Setup Effort": 3, "Ease of Use": 4, "Collaboration": 6,
                                  "Reporting & Tracking": 8, "Developer Tool Integration": 9},
    "payload": {
        "summary": {"restated_decision": "Choose a free project-management tool that a mixed-skill five-person student team can adopt quickly.",
                    "key_considerations": ["Free plans only", "Mixed technical skill", "Quick onboarding", "Ten-week timeline"]},
        "alternatives": [
            {"name": _TR, "description": "Kanban boards of lists and cards.", "strengths": ["Extremely easy to learn", "Fast setup"],
             "weaknesses": ["Limited reporting", "Weak code integration by default"], "suitable_use_cases": ["Small teams with simple workflows"],
             "key_advantage": "Lowest onboarding effort.", "main_disadvantage": "Basic reporting."},
            {"name": _NO, "description": "Flexible workspace combining docs and boards.", "strengths": ["Docs and tasks in one place", "Strong collaboration"],
             "weaknesses": ["Needs structuring", "Limited developer integration"], "suitable_use_cases": ["Mixed documentation and planning"],
             "key_advantage": "Excellent shared documentation.", "main_disadvantage": "Setup requires design decisions."},
            {"name": _GH, "description": "Issue and board tracking inside GitHub.", "strengths": ["Native to the code workflow", "No extra account"],
             "weaknesses": ["Less friendly to non-developers", "Basic reporting"], "suitable_use_cases": ["Developer-centred teams"],
             "key_advantage": "Tight integration with the repository.", "main_disadvantage": "Steeper for non-technical members."},
            {"name": _JI, "description": "Industry-standard agile tracking.", "strengths": ["Powerful sprint reporting", "Industry-relevant skill"],
             "weaknesses": ["Heavy setup", "Overkill for small projects"], "suitable_use_cases": ["Teams practising formal agile"],
             "key_advantage": "Best reporting and agile tooling.", "main_disadvantage": "High setup and learning effort."},
        ],
        "criteria": [{"name": n, "description": d, "direction": dr, "suggested_weight": w} for n, dr, w, d in _PM_CRITERIA],
        "ratings": _ratings(_PM_RATINGS),
        "risks": [
            {"alternative": _JI, "description": "Setup overhead slows the first weeks.", "impact": "Team abandons the tool.", "likelihood": "High", "mitigation": "Use a starter template and a single board."},
            {"alternative": _TR, "description": "Reporting is too basic for later project phases.", "impact": "Manual progress reports.", "likelihood": "Medium", "mitigation": "Export or add reporting extras if needed."},
            {"alternative": "General", "description": "Free-plan limits can change.", "impact": "Unexpected restrictions mid-project.", "likelihood": "Low", "mitigation": "Check current plan limits before starting."},
        ],
        "tradeoffs": [
            {"alternative": _TR, "gains": "Immediate productivity.", "sacrifices": "Reporting depth."},
            {"alternative": _NO, "gains": "Docs and tasks together.", "sacrifices": "Time spent structuring."},
            {"alternative": _GH, "gains": "Close link to code.", "sacrifices": "Friendliness for non-developers."},
            {"alternative": _JI, "gains": "Professional agile reporting.", "sacrifices": "Simplicity and speed of setup."},
        ],
        "assumptions": ["Free plans cover a five-person team (not verified).", "Most members will use the tool daily."],
        "limitations": ["Ratings are illustrative estimates.", "Product features and plan limits change and were not checked."],
        "verify_before_deciding": ["Check each tool's current free-plan limits.", "Ask the team which tool they have used before."],
        # Deliberately differs from the calculated leader to demonstrate disagreement handling.
        "initial_recommendation": {"alternative": _GH, "reasoning": "Developer-friendly and free, assuming most members use GitHub."},
    },
    "recommendation": {
        "explanation": ("Under the default priorities, ease of use, low cost and quick setup carry the most weight, "
                        "which favours the simplest tool. The calculated ranking differs from the sample's initial "
                        "qualitative suggestion, so review the assumptions about the team's GitHub familiarity."),
        "main_caveat": "Check current free-plan limits and the team's comfort with each tool.",
    },
}

SAMPLES = {s["key"]: s for s in (TECH_STACK, PM_TOOLS)}
