````python
import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime

from flask import Flask, jsonify, request, render_template

try:
    from supabase import create_client
except Exception:
    create_client = None


app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Optional Gemini Vision API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ROLE_ACCESS_CODE = os.environ.get(
    "ROLE_ACCESS_CODE",
    "SATARA-VET-2026"
)

supabase = None

if SUPABASE_URL and SUPABASE_KEY and create_client:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception:
        supabase = None


# Demo fallback when Supabase is unavailable
_MEMORY_REPORTS = []


# ============================================================
# BASIC DATA
# ============================================================

HIGH_RISK_SYMPTOMS = {
    "lesions": 4,
    "swelling": 3,
    "death": 6,
    "bleeding": 4,
    "difficulty_breathing": 5,
    "abortion": 5,
}

MODERATE_SYMPTOMS = {
    "fever": 3,
    "milk_drop": 3,
    "diarrhea": 3,
    "cough": 2,
    "nasal_discharge": 2,
    "loss_weight": 2,
}

LOW_RISK_SYMPTOMS = {
    "lameness": 1,
    "loss_appetite": 1,
    "weakness": 1,
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def normalize_symptoms(symptoms):
    if symptoms is None:
        return []

    if isinstance(symptoms, str):
        try:
            parsed = json.loads(symptoms)
            if isinstance(parsed, list):
                return [
                    str(x).strip().lower()
                    for x in parsed
                    if str(x).strip()
                ]
        except Exception:
            pass

        return [
            x.strip().lower()
            for x in symptoms.split(",")
            if x.strip()
        ]

    if isinstance(symptoms, list):
        return [
            str(x).strip().lower()
            for x in symptoms
            if str(x).strip()
        ]

    return []


# ============================================================
# ADVANCED EXPLAINABLE RISK ENGINE
# ============================================================

def score_report(data):
    """
    Explainable multi-signal livestock health risk engine.

    This is a decision-support / triage engine.
    It is NOT a veterinary diagnosis.
    """

    symptoms = normalize_symptoms(
        data.get("symptoms", [])
    )

    animal_type = str(
        data.get("animal_type", "unknown")
    ).lower()

    affected_count = max(
        safe_int(data.get("affected_count"), 1),
        1
    )

    days_since_onset = max(
        safe_int(data.get("days_since_onset"), 0),
        0
    )

    vaccination_status = str(
        data.get("vaccination_status", "unknown")
    ).lower()

    score = 0
    factors = []

    # --------------------------------------------------------
    # Symptom score
    # --------------------------------------------------------

    for symptom in symptoms:

        if symptom in HIGH_RISK_SYMPTOMS:
            weight = HIGH_RISK_SYMPTOMS[symptom]
            score += weight

            factors.append({
                "factor": symptom,
                "impact": "high",
                "points": weight
            })

        elif symptom in MODERATE_SYMPTOMS:
            weight = MODERATE_SYMPTOMS[symptom]
            score += weight

            factors.append({
                "factor": symptom,
                "impact": "moderate",
                "points": weight
            })

        elif symptom in LOW_RISK_SYMPTOMS:
            weight = LOW_RISK_SYMPTOMS[symptom]
            score += weight

            factors.append({
                "factor": symptom,
                "impact": "low",
                "points": weight
            })

    # --------------------------------------------------------
    # Multiple affected animals
    # --------------------------------------------------------

    if affected_count >= 10:
        score += 6

        factors.append({
            "factor": "10+ animals affected",
            "impact": "high",
            "points": 6
        })

    elif affected_count >= 5:
        score += 4

        factors.append({
            "factor": "5+ animals affected",
            "impact": "moderate",
            "points": 4
        })

    elif affected_count >= 2:
        score += 2

        factors.append({
            "factor": "multiple animals affected",
            "impact": "moderate",
            "points": 2
        })

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    if days_since_onset >= 7:
        score += 4

        factors.append({
            "factor": "symptoms present for 7+ days",
            "impact": "high",
            "points": 4
        })

    elif days_since_onset >= 3:
        score += 2

        factors.append({
            "factor": "symptoms present for 3+ days",
            "impact": "moderate",
            "points": 2
        })

    # --------------------------------------------------------
    # Vaccination
    # --------------------------------------------------------

    if vaccination_status in [
        "unknown",
        "not_vaccinated",
        "overdue"
    ]:

        score += 2

        factors.append({
            "factor": "vaccination protection uncertain/overdue",
            "impact": "moderate",
            "points": 2
        })

    # --------------------------------------------------------
    # Animal-specific adjustment
    # --------------------------------------------------------

    if animal_type in [
        "cattle",
        "buffalo",
        "goat",
        "sheep"
    ]:
        score += 1

    # --------------------------------------------------------
    # Convert to 0-100
    # --------------------------------------------------------

    risk_score = min(
        100,
        round((score / 30) * 100)
    )

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    if risk_score >= 70:
        risk_level = "HIGH"

    elif risk_score >= 35:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    signal_count = (
        len(symptoms)
        + (1 if affected_count else 0)
        + (1 if days_since_onset else 0)
        + (1 if vaccination_status != "unknown" else 0)
    )

    confidence = min(
        95,
        50 + signal_count * 8
    )

    # --------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------

    if risk_level == "HIGH":

        recommendation = (
            "Isolate affected animals where practical, "
            "avoid unnecessary movement, and contact a "
            "veterinarian promptly."
        )

    elif risk_level == "MODERATE":

        recommendation = (
            "Monitor the affected animals closely, "
            "record progression, review vaccination status, "
            "and consult a veterinary professional."
        )

    else:

        recommendation = (
            "Continue monitoring, maintain hygiene and "
            "preventive care, and report worsening symptoms."
        )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "confidence": confidence,
        "factors": factors,
        "recommendation": recommendation,
        "animal_type": animal_type,
        "affected_count": affected_count,
        "days_since_onset": days_since_onset,
        "screening_type": "AI-assisted decision support",
        "medical_disclaimer": (
            "This result is a screening/triage aid and "
            "does not replace veterinary diagnosis."
        )
    }


# ============================================================
# GEMINI VISION IMAGE SCREENING
# ============================================================

def gemini_image_screen(image_bytes, mime_type="image/jpeg"):
    """
    Optional Gemini Vision integration.

    API key MUST be stored in Vercel Environment Variables.
    Never put GEMINI_API_KEY in frontend or GitHub.
    """

    if not GEMINI_API_KEY:
        return None

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = """
You are assisting a livestock-health triage system.

Analyze the provided livestock image for visible signs
that may require veterinary attention.

Do NOT give a definitive diagnosis.

Return JSON with:

{
  "visible_signs": [],
  "possible_categories": [],
  "risk_level": "LOW|MODERATE|HIGH",
  "confidence": 0,
  "recommendation": ""
}

Focus only on visible signs.
If the image is unclear, say so.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_image
                        }
                    }
                ]
            }
        ]
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.0-flash:generateContent"
        "?key="
        + GEMINI_API_KEY
    )

    try:

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        text = (
            result
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        # Remove markdown JSON fences
        text = text.replace(
            "```json", ""
        ).replace(
            "```", ""
        ).strip()

        return json.loads(text)

    except Exception:
        return None


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    try:
        return render_template(
            "index.html"
        )

    except Exception:
        return jsonify({
            "app": "PashuRakshak AI",
            "status": "running"
        })


# ============================================================
# TRIAGE API
# ============================================================

@app.route(
    "/api/triage",
    methods=["POST"]
)
def triage():

    data = request.get_json(
        silent=True
    ) or {}

    result = score_report(data)

    return jsonify({
        "success": True,
        "result": result
    })


# ============================================================
# IMAGE SCREENING API
# ============================================================

@app.route(
    "/api/image-screen",
    methods=["POST"]
)
def image_screen():

    if "image" not in request.files:

        return jsonify({
            "success": False,
            "error": "No image uploaded"
        }), 400

    image = request.files["image"]

    image_bytes = image.read()

    if not image_bytes:

        return jsonify({
            "success": False,
            "error": "Empty image"
        }), 400

    # Limit approximately 8 MB
    if len(image_bytes) > 8 * 1024 * 1024:

        return jsonify({
            "success": False,
            "error": "Image too large. Maximum size is 8 MB."
        }), 413

    mime_type = (
        image.mimetype
        or "image/jpeg"
    )

    ai_result = gemini_image_screen(
        image_bytes,
        mime_type
    )

    # Demo fallback if Gemini is not configured
    if not ai_result:

        ai_result = {
            "visible_signs": [
                "Image screening service not configured"
            ],
            "possible_categories": [],
            "risk_level": "MODERATE",
            "confidence": 50,
            "recommendation": (
                "Image received successfully. "
                "Veterinary review is recommended."
            )
        }

    return jsonify({
        "success": True,
        "result": ai_result,
        "screening_type": "AI image screening",
        "medical_disclaimer": (
            "Image screening is an assistive tool and "
            "does not provide a definitive veterinary diagnosis."
        )
    })


# ============================================================
# REPORT STORAGE
# ============================================================

def save_report(report):

    if supabase:

        try:

            response = (
                supabase
                .table("reports")
                .insert(report)
                .execute()
            )

            if response.data:
                return response.data[0]

        except Exception:
            pass

    report["id"] = (
        len(_MEMORY_REPORTS) + 1
    )

    _MEMORY_REPORTS.append(
        report
    )

    return report


def get_reports():

    if supabase:

        try:

            response = (
                supabase
                .table("reports")
                .select("*")
                .order(
                    "created_at",
                    desc=True
                )
                .execute()
            )

            if response.data:
                return response.data

        except Exception:
            pass

    return list(
        reversed(_MEMORY_REPORTS)
    )


# ============================================================
# REPORTS GET / POST
# ============================================================

@app.route(
    "/api/reports",
    methods=["GET", "POST"]
)
def reports():

    if request.method == "GET":

        return jsonify({
            "success": True,
            "reports": get_reports()
        })

    data = request.get_json(
        silent=True
    ) or {}

    result = score_report(data)

    report = {
        "village": data.get(
            "village",
            "Satara"
        ),

        "block": data.get(
            "block"
        ),

        "lat": data.get(
            "lat"
        ),

        "lng": data.get(
            "lng"
        ),

        "animal_type": data.get(
            "animal_type",
            "unknown"
        ),

        "symptoms": normalize_symptoms(
            data.get("symptoms", [])
        ),

        "affected_count": result[
            "affected_count"
        ],

        "days_since_onset": result[
            "days_since_onset"
        ],

        "notes": data.get(
            "notes",
            ""
        ),

        "risk_level": result[
            "risk_level"
        ],

        "risk_score": result[
            "risk_score"
        ],

        "reported_by": data.get(
            "reported_by"
        ),

        "date": datetime.utcnow().date().isoformat(),

        "created_at": datetime.utcnow().isoformat(),

        "confidence": result[
            "confidence"
        ],

        "risk_factors": result[
            "factors"
        ]
    }

    saved = save_report(
        report
    )

    return jsonify({
        "success": True,
        "report": saved,
        "risk": result
    })


# ============================================================
# DASHBOARD ROUTES
# ============================================================

@app.route(
    "/dashboard"
)
def dashboard():

    return render_template(
        "dashboard.html"
    )


@app.route(
    "/dashboard/farmer"
)
def dashboard_farmer():

    return render_template(
        "dashboard_farmer.html"
    )


@app.route(
    "/dashboard/vet"
)
def dashboard_vet():

    return render_template(
        "dashboard_vet.html"
    )


@app.route(
    "/dashboard/official"
)
def dashboard_official():

    return render_template(
        "dashboard_official.html"
    )


# ============================================================
# REPORT PAGE
# ============================================================

@app.route(
    "/report"
)
def report_page():

    return render_template(
        "report.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/api/health"
)
def health():

    return jsonify({
        "success": True,
        "app": "PashuRakshak AI",
        "status": "healthy",
        "supabase": bool(supabase),
        "image_ai": bool(GEMINI_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ============================================================
# VERCEL ENTRY POINT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )
````
