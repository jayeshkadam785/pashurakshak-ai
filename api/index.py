"""
PashuRakshak backend — Flask app.

Serves the dashboard pages and two small JSON APIs:
  POST /api/triage   -> rule-based risk scoring for a single symptom report
  GET  /api/reports  -> list of recent reports (for the map/chart/table)
  POST /api/reports  -> save a report (also runs triage)

Onboarding: a first-time visitor is routed through /onboarding/language
then /onboarding/role before reaching the dashboard. Veterinary Officer
and District Official roles require an access code (demo-only gate --
see ROLE_ACCESS_CODE below).

Each role sees a different dashboard:
  farmer   -> dashboard_farmer.html (my animals / my reports / reminders)
  vet      -> dashboard_vet.html    (block-level case queue, map, chart)
  official -> dashboard_official.html (district-wide totals, block compare)

Data persistence is optional: if SUPABASE_URL / SUPABASE_KEY are set,
reports are read/written to Supabase; otherwise an in-memory list is
used so the prototype works end-to-end without any backend configured.

Deploy target: Vercel (Python serverless function).
"""

import os
import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static",
)

app.secret_key = os.environ.get("SECRET_KEY", "pashurakshak-dev-secret-change-me")

# ---------------------------------------------------------------------
# Optional Supabase client.
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

_MEMORY_REPORTS = []

# ---------------------------------------------------------------------
# Onboarding: languages, roles, translations
# ---------------------------------------------------------------------

LANGUAGES = {
    "en": {"name": "English", "native": "English"},
    "hi": {"name": "Hindi", "native": "हिन्दी"},
    "mr": {"name": "Marathi", "native": "मराठी"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી"},
}

ROLES = {
    "farmer": {
        "label": "Farmer",
        "icon": "🧑‍🌾",
        "desc": "Report symptoms, track your animals, get local advisories.",
        "requires_auth": False,
    },
    "vet": {
        "label": "Veterinary Officer",
        "icon": "🩺",
        "desc": "Review farmer reports, manage case triage, issue advisories.",
        "requires_auth": True,
    },
    "official": {
        "label": "District Official",
        "icon": "🏛️",
        "desc": "Monitor outbreak trends across villages and view aggregated dashboards.",
        "requires_auth": True,
    },
}

# Demo-only gate for privileged roles. In a real deployment this would
# check against a verified officer database, not a shared static code.
ROLE_ACCESS_CODE = os.environ.get("ROLE_ACCESS_CODE", "SATARA-VET-2026")

TRANSLATIONS = {
    "en": {
        "greeting": "Namaskar",
        "nav_home": "Home", "nav_report": "Report", "nav_dashboard": "Dashboard",
        "nav_alerts": "Alerts", "nav_records": "Animal records",
        "report_heading": "Report an animal health issue",
        "report_body": "Take a photo or describe symptoms — flagged reports are shared with your nearest veterinary officer for triage.",
        "start_report": "Start a report",
        "recent_advisories": "Recent advisories",
    },
    "hi": {
        "greeting": "नमस्कार",
        "nav_home": "होम", "nav_report": "रिपोर्ट", "nav_dashboard": "डैशबोर्ड",
        "nav_alerts": "सूचनाएं", "nav_records": "पशु रिकॉर्ड",
        "report_heading": "पशु स्वास्थ्य समस्या दर्ज करें",
        "report_body": "फोटो लें या लक्षण बताएं — चिन्हित रिपोर्ट आपके नज़दीकी पशु चिकित्सक के प��स भेजी जाती हैं।",
        "start_report": "रिपोर्ट शुरू करें",
        "recent_advisories": "हाल की सूचनाएं",
    },
    "mr": {
        "greeting": "नमस्कार",
        "nav_home": "मुख्यपृष्ठ", "nav_report": "अहवाल", "nav_dashboard": "डॅशबोर्ड",
        "nav_alerts": "सूचना", "nav_records": "जनावरांच्या नोंदी",
        "report_heading": "जनावराच्या आरोग्य समस्येची नोंद करा",
        "report_body": "फोटो घ्या किंवा लक्षणे सांगा — नोंदवलेले अहवाल जवळच्या पशुवैद्यकाकडे पाठवले जातात.",
        "start_report": "अहवाल सुरू करा",
        "recent_advisories": "अलीकडील सूचना",
    },
    "pa": {
        "greeting": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ",
        "nav_home": "ਹੋਮ", "nav_report": "ਰਿਪੋਰਟ", "nav_dashboard": "ਡੈਸ਼ਬੋਰਡ",
        "nav_alerts": "ਚੇਤਾਵਨੀਆਂ", "nav_records": "ਪਸ਼ੂ ਰਿਕਾਰਡ",
        "report_heading": "ਪਸ਼ੂ ਸਿਹਤ ਸਮੱਸਿਆ ਦਰਜ ਕਰੋ",
        "report_body": "ਫੋਟੋ ਲਓ ਜਾਂ ਲੱਛਣ ਦੱਸੋ — ਰਿਪੋਰਟ ਤੁਹਾਡੇ ਨਜ਼ਦੀਕੀ ਵੈਟਰਨਰੀ ਅਫ਼ਸਰ ਨੂੰ ਭੇਜੀ ਜਾਂਦੀ ਹੈ।",
        "start_report": "ਰਿਪੋਰਟ ਸ਼ੁਰੂ ਕਰੋ",
        "recent_advisories": "ਤਾਜ਼ਾ ਸੂਚਨਾਵਾਂ",
    },
    "gu": {
        "greeting": "નમસ્તે",
        "nav_home": "હોમ", "nav_report": "રિપોર્ટ", "nav_dashboard": "ડેશબોર્ડ",
        "nav_alerts": "ચેતવણીઓ", "nav_records": "પ્રાણી રેકોર્ડ",
        "report_heading": "પ્રાણી આરોગ્ય સમસ્યાની જાણ કરો",
        "report_body": "ફોટો લો અથવા લક્ષણો જણાવો — નોંધાયેલા અહેવાલો તમારા નજીકના પશુચિકિત્સકને મોકલવામાં આવે છે.",
        "start_report": "રિપોર્ટ શરૂ કરો",
        "recent_advisories": "તાજેતરની સૂચનાઓ",
    },
}


def t(key):
    lang = session.get("language", "en")
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return table.get(key, TRANSLATIONS["en"].get(key, key))


@app.context_processor
def inject_i18n():
    return {
        "t": t,
        "current_lang_label": session.get("language_label", "English"),
        "current_role_label": session.get("role_label"),
    }


ONBOARDING_ENDPOINTS = {
    "onboarding_language", "onboarding_language_post",
    "onboarding_role", "onboarding_role_post",
}


@app.before_request
def _require_onboarding():
    if request.path.startswith("/static") or request.path.startswith("/api"):
        return
    if request.endpoint in ONBOARDING_ENDPOINTS:
        return
    if "language" not in session:
        return redirect(url_for("onboarding_language"))
    if "role" not in session:
        return redirect(url_for("onboarding_role"))


@app.route("/onboarding/language", methods=["GET"])
def onboarding_language():
    return render_template("onboarding_language.html", languages=LANGUAGES, selected=session.get("language"))


@app.route("/onboarding/language", methods=["POST"])
def onboarding_language_post():
    code = request.form.get("language", "en")
    if code not in LANGUAGES:
        code = "en"
    session["language"] = code
    session["language_label"] = LANGUAGES[code]["native"]
    return redirect(url_for("onboarding_role"))


@app.route("/onboarding/role", methods=["GET"])
def onboarding_role():
    return render_template("onboarding_role.html", roles=ROLES, selected_role=session.get("role"), error=None)


@app.route("/onboarding/role", methods=["POST"])
def onboarding_role_post():
    role = request.form.get("role")
    if role not in ROLES:
        return render_template("onboarding_role.html", roles=ROLES, selected_role=None,
                                error="Please select a role to continue.")
    if ROLES[role]["requires_auth"]:
        code = (request.form.get("access_code") or "").strip()
        if code != ROLE_ACCESS_CODE:
            return render_template("onboarding_role.html", roles=ROLES, selected_role=role,
                                    error="Incorrect access code. Please check with your taluka office and try again.")
    session["role"] = role
    session["role_label"] = ROLES[role]["label"]
    return redirect(url_for("home"))


# ---------------------------------------------------------------------
# Rule-based triage engine
# ---------------------------------------------------------------------

HIGH_RISK_SYMPTOMS = {"lesions", "swelling", "death"}
MODERATE_RISK_SYMPTOMS = {"fever", "milk_drop", "diarrhea"}
LOW_RISK_SYMPTOMS = {"lameness", "loss_appetite"}

SYMPTOM_LABELS = {
    "fever": "fever", "lesions": "mouth/foot lesions", "loss_appetite": "loss of appetite",
    "lameness": "lameness", "diarrhea": "diarrhoea", "milk_drop": "sudden milk drop",
    "swelling": "swelling/nodules", "death": "sudden death",
}


def score_report(payload: dict) -> dict:
    symptoms = set(payload.get("symptoms") or [])
    affected_count = int(payload.get("affected_count") or 1)
    days_since_onset = int(payload.get("days_since_onset") or 0)

    score = 0
    score += 3 * len(symptoms & HIGH_RISK_SYMPTOMS)
    score += 2 * len(symptoms & MODERATE_RISK_SYMPTOMS)
    score += 1 * len(symptoms & LOW_RISK_SYMPTOMS)

    if affected_count >= 5:
        score += 4
    elif affected_count >= 2:
        score += 2

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
            f"associated with fast-spreading disease (e.g. FMD, lumpy skin disease)."
        )
        next_step = "Isolate affected animals now and contact your nearest veterinary officer today."
    elif level == "moderate":
        message = (
            f"{symptom_text.capitalize()} reported. Not an immediate outbreak "
            f"signal, but worth a veterinary check, especially if more animals show symptoms."
        )
        next_step = "Monitor closely over the next 48 hours and schedule a vet visit if symptoms continue."
    else:
        message = f"{symptom_text.capitalize()} reported at low severity and limited spread."
        next_step = "Continue routine monitoring. Report again if symptoms worsen or spread to more animals."

    return {
        "score": score, "risk_level": level, "risk_label": label,
        "message": message, "next_step": next_step,
    }


# ---------------------------------------------------------------------
# Demo data (in-memory, for judges/hackathon demo — no real DB required)
# ---------------------------------------------------------------------

DEMO_ADVISORIES = [
    {
        "title": "Suspected lumpy skin disease cluster — Wai taluka",
        "body": "3 herds reporting nodular skin lesions and fever within 5 km. Isolate affected animals and avoid moving cattle across villages.",
        "severity": "high", "issued_by": "Dept. of Animal Husbandry, Maharashtra", "date": "today",
    },
    {
        "title": "Seasonal foot-rot risk — post-monsoon",
        "body": "Waterlogged sheds raise lameness risk. Keep bedding dry and inspect hooves weekly.",
        "severity": "moderate", "issued_by": "Dept. of Animal Husbandry, Maharashtra", "date": "3 days ago",
    },
]

DEMO_BLOCK_SUMMARY = [
    {"block": "Satara", "villages_reporting": 9, "open_reports": 14, "high_risk": 3},
    {"block": "Wai", "villages_reporting": 6, "open_reports": 8, "high_risk": 2},
    {"block": "Koregaon", "villages_reporting": 4, "open_reports": 3, "high_risk": 0},
    {"block": "Phaltan", "villages_reporting": 5, "open_reports": 6, "high_risk": 1},
]

DEMO_DISTRICT_TOTALS = {
    "total_open_reports": 31,
    "total_high_risk": 6,
    "vaccination_coverage": 68,
    "blocks_reporting": 4,
}

DEMO_MY_ANIMALS = [
    {"tag_id": "COW-1042", "species": "Cattle", "breed": "Gir", "age": "4 yrs", "last_checkup": "12 Aug", "status": "healthy"},
    {"tag_id": "COW-1043", "species": "Cattle", "breed": "Gir", "age": "2 yrs", "last_checkup": "3 days ago", "status": "under observation"},
    {"tag_id": "GOAT-0231", "species": "Goat", "breed": "Osmanabadi", "age": "1 yr", "last_checkup": "1 month ago", "status": "healthy"},
]

DEMO_MY_REPORTS = [
    {"date": "3 days ago", "animal": "COW-1043", "symptoms": "Fever, loss of appetite", "status": "Under review", "risk": "moderate"},
    {"date": "2 weeks ago", "animal": "COW-1042", "symptoms": "Lameness", "status": "Resolved", "risk": "low"},
]

DEMO_VACCINATION_DUE = [
    {"animal": "COW-1042", "vaccine": "FMD booster", "due": "in 6 days"},
    {"animal": "GOAT-0231", "vaccine": "PPR vaccine", "due": "in 18 days"},
]


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html", active="home", advisories=DEMO_ADVISORIES)


@app.route("/report")
def report_page():
    return render_template("report.html", active="report")


@app.route("/dashboard")
def dashboard_page():
    role = session.get("role")

    if role == "vet":
        return render_template(
            "dashboard_vet.html", active="dashboard", role=role,
            open_reports=14, high_risk=3, villages_reporting=9,
        )

    if role == "official":
        return render_template(
            "dashboard_official.html", active="dashboard", role=role,
            block_summary=DEMO_BLOCK_SUMMARY, totals=DEMO_DISTRICT_TOTALS,
        )

    if role == "farmer":
        return render_template(
            "dashboard_farmer.html", active="dashboard", role=role,
            my_animals=DEMO_MY_ANIMALS, my_reports=DEMO_MY_REPORTS,
            vaccination_due=DEMO_VACCINATION_DUE,
        )

    return redirect(url_for("onboarding_role"))


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
        "lat": payload.get("lat"), "lng": payload.get("lng"),
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
