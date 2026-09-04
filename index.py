"""
PashuRakshak backend — Flask app.

Serves the dashboard pages and two small JSON APIs:
  POST /api/triage   -> rule-based risk scoring for a single symptom report
  GET  /api/reports  -> list of recent reports (for the map/chart/table)
  POST /api/reports  -> save a report (also runs triage) -- used once the
                        farmer form is wired to persist, not required for
                        the triage demo itself

Data persistence is optional: if SUPABASE_URL / SUPABASE_KEY are set as
environment variables, reports are read from and written to a `reports`
table in Supabase. Otherwise the app falls back to an in-memory list so
the prototype still works end-to-end without any backend configured.

Deploy target: Vercel (Python serverless function). vercel.json routes
all requests to this file.
"""

import os
import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)

# ---------------------------------------------------------------------
# Optional Supabase client. Falls back to in-memory storage if the
# environment variables aren't set -- keeps local/demo use frictionless.
# ---------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

_MEMORY_REPORTS = []  # used only when Supabase isn't configured


# ---------------------------------------------------------------------
# Rule-based triage engine
#
# This is intentionally simple and explainable -- a real deployment
# would refine weights with veterinary input, but every rule here maps
# to a specific, named clinical/epidemiological signal so it's honest
# to demo and easy to justify to judges.
# ---------------------------------------------------------------------

HIGH_RISK_SYMPTOMS = {"lesions", "swelling", "death"}
MODERATE_RISK_SYMPTOMS = {"fever", "milk_drop", "diarrhea"}
LOW_RISK_SYMPTOMS = {"lameness", "loss_appetite"}

SYMPTOM_LABELS = {
    "fever": "fever",
    "lesions": "mouth/foot lesions",
    "loss_appetite": "loss of appetite",
    "lameness": "lameness",
    "diarrhea": "diarrhoea",
    "milk_drop": "sudden milk drop",
    "swelling": "swelling/nodules",
    "death": "sudden death",
}


def score_report(payload: dict) -> dict:
    symptoms = set(payload.get("symptoms") or [])
    affected_count = int(payload.get("affected_count") or 1)
    days_since_onset = int(payload.get("days_since_onset") or 0)

    score = 0

    # Symptom severity
    score += 3 * len(symptoms & HIGH_RISK_SYMPTOMS)
    score += 2 * len(symptoms & MODERATE_RISK_SYMPTOMS)
    score += 1 * len(symptoms & LOW_RISK_SYMPTOMS)

    # Cluster signal: multiple animals affected at once suggests
    # contagious spread rather than an isolated issue.
    if affected_count >= 5:
        score += 4
    elif affected_count >= 2:
        score += 2

    # Onset recency: a fast-developing case is more urgent than a
    # slow, weeks-old complaint.
    if days_since_onset <= 1:
        score += 2
    elif days_since_onset <= 3:
        score += 1

    if score >= 7:
        level, label = "high", "High"
    elif score >= 3:
        level, label = "moderate", "Moderate"
    else:
        level, label = "low", "Low"

    named = [SYMPTOM_LABELS.get(s, s) for s in symptoms]
    symptom_text = ", ".join(named) if named else "the symptoms described"

    if level == "high":
        message = (
            f"{symptom_text.capitalize()} across {affected_count} animal(s), "
            f"reported within {days_since_onset} day(s), matches a pattern "
            f"associated with fast-spreading disease (e.g. FMD, lumpy skin "
            f"disease)."
        )
        next_step = "Isolate affected animals now and contact your nearest veterinary officer today."
    elif level == "moderate":
        message = (
            f"{symptom_text.capitalize()} reported. Not an immediate outbreak "
            f"signal, but worth a veterinary check, especially if more animals "
            f"show symptoms."
        )
        next_step = "Monitor closely over the next 48 hours and schedule a vet visit if symptoms continue."
    else:
        message = f"{symptom_text.capitalize()} reported at low severity and limited spread."
        next_step = "Continue routine monitoring. Report again if symptoms worsen or spread to more animals."

    return {
        "score": score,
        "risk_level": level,
        "risk_label": label,
        "message": message,
        "next_step": next_step,
    }


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

DEMO_ADVISORIES = [
    {
        "title": "Suspected lumpy skin disease cluster — Wai taluka",
        "body": "3 herds reporting nodular skin lesions and fever within 5 km. Isolate affected animals and avoid moving cattle across villages.",
        "severity": "high",
        "issued_by": "Dept. of Animal Husbandry, Maharashtra",
        "date": "today",
    },
    {
        "title": "Seasonal foot-rot risk — post-monsoon",
        "body": "Waterlogged sheds raise lameness risk. Keep bedding dry and inspect hooves weekly.",
        "severity": "moderate",
        "issued_by": "Dept. of Animal Husbandry, Maharashtra",
        "date": "3 days ago",
    },
]


@app.route("/")
def home():
    return render_template("index.html", active="home", advisories=DEMO_ADVISORIES)


@app.route("/report")
def report_page():
    return render_template("report.html", active="report")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", active="dashboard")


@app.route("/alerts")
def alerts_page():
    return render_template("alerts.html", active="alerts", advisories=DEMO_ADVISORIES)


@app.route("/records")
def records_page():
    return render_template("records.html", active="records")


# ---------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------

@app.route("/api/triage", methods=["POST"])
def api_triage():
    payload = request.get_json(force=True, silent=True) or {}
    result = score_report(payload)
    return jsonify(result)


@app.route("/api/reports", methods=["GET"])
def api_reports_list():
    if supabase:
        res = supabase.table("reports").select("*").order("date", desc=True).limit(100).execute()
        return jsonify(res.data)
    return jsonify(_MEMORY_REPORTS)


@app.route("/api/reports", methods=["POST"])
def api_reports_create():
    payload = request.get_json(force=True, silent=True) or {}
    triage = score_report(payload)

    record = {
        "village": payload.get("village", "Unknown"),
        "lat": payload.get("lat"),
        "lng": payload.get("lng"),
        "animal_type": payload.get("animal_type"),
        "symptoms": payload.get("symptoms") or [],
        "affected_count": payload.get("affected_count", 1),
        "notes": payload.get("notes", ""),
        "risk_level": triage["risk_level"],
        "date": datetime.date.today().isoformat(),
    }

    if supabase:
        supabase.table("reports").insert(record).execute()
    else:
        _MEMORY_REPORTS.append(record)

    return jsonify({**record, **triage}), 201


# Local dev entrypoint. On Vercel, the `app` object above is imported
# directly by the Python runtime -- this block never runs there.
if __name__ == "__main__":
    app.run(debug=True, port=5000)
