import os
import json
import base64
import urllib.request
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template, redirect

try:
    from supabase import create_client
except Exception:
    create_client = None


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)


# ============================================================
# FEATURE BLUEPRINT
# ============================================================

feature_bp = None
FEATURE_BLUEPRINT_ERROR = None

try:
    from api.feature_routes import feature_bp
    app.register_blueprint(feature_bp)
except Exception as exc:
    FEATURE_BLUEPRINT_ERROR = str(exc)
    print("Feature blueprint could not be loaded:", repr(exc))


# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_PUBLISHABLE_KEY = os.environ.get(
    "SUPABASE_PUBLISHABLE_KEY",
    ""
)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

ROLE_ACCESS_CODE = os.environ.get(
    "ROLE_ACCESS_CODE",
    "SATARA-VET-2026"
)


# ============================================================
# SUPABASE
# ============================================================

supabase = None
SUPABASE_INIT_ERROR = None

if SUPABASE_URL and SUPABASE_KEY and create_client:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception as exc:
        SUPABASE_INIT_ERROR = str(exc)
        print(
            "Supabase initialization failed:",
            repr(exc)
        )
        supabase = None


# ============================================================
# MEMORY FALLBACK
# ============================================================

_MEMORY_REPORTS = []
_MEMORY_ANIMALS = []


# ============================================================
# RISK ENGINE
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
# UTILITY
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
# AI RISK ENGINE
# ============================================================

def score_report(data):

    symptoms = normalize_symptoms(
        data.get("symptoms", [])
    )

    animal_type = str(
        data.get("animal_type", "unknown")
    ).lower()

    affected_count = max(
        safe_int(
            data.get("affected_count"),
            1
        ),
        1
    )

    days_since_onset = max(
        safe_int(
            data.get("days_since_onset"),
            0
        ),
        0
    )

    vaccination_status = str(
        data.get(
            "vaccination_status",
            "unknown"
        )
    ).lower()

    score = 0
    factors = []

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

    if vaccination_status in {
        "unknown",
        "not_vaccinated",
        "overdue"
    }:

        score += 2

        factors.append({
            "factor": "vaccination protection uncertain/overdue",
            "impact": "moderate",
            "points": 2
        })

    if animal_type in {
        "cattle",
        "buffalo",
        "goat",
        "sheep"
    }:
        score += 1

    risk_score = min(
        100,
        round((score / 30) * 100)
    )

    if risk_score >= 70:
        risk_level = "HIGH"

    elif risk_score >= 35:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    signal_count = (
        len(symptoms)
        + 1
        + (1 if days_since_onset else 0)
        + (
            1
            if vaccination_status != "unknown"
            else 0
        )
    )

    confidence = min(
        95,
        50 + signal_count * 8
    )

    if risk_level == "HIGH":

        recommendation = (
            "Isolate affected animals where practical, "
            "avoid unnecessary movement, and contact "
            "a veterinarian promptly."
        )

    elif risk_level == "MODERATE":

        recommendation = (
            "Monitor affected animals closely, record "
            "progression, review vaccination status, "
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
            "This result is a screening/triage aid "
            "and does not replace veterinary diagnosis."
        )
    }


# ============================================================
# GEMINI IMAGE SCREENING
# ============================================================

def gemini_image_screen(
    image_bytes,
    mime_type="image/jpeg"
):

    if not GEMINI_API_KEY:
        return None

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = """
You are assisting a livestock-health triage system.

Analyze the provided livestock image for visible
signs that may require veterinary attention.

Do NOT give a definitive diagnosis.

Return JSON with exactly this structure:

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
        "v1beta/models/gemini-2.0-flash:"
        "generateContent?key="
        + GEMINI_API_KEY
    )

    try:

        req = urllib.request.Request(
            url,
            data=json.dumps(
                payload
            ).encode("utf-8"),
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

        text = (
            text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        return json.loads(text)

    except Exception as exc:

        print(
            "Gemini image screening failed:",
            repr(exc)
        )

        return None


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route("/")
def home():
    return redirect("/login")


@app.route("/login")
def login_page():

    return render_template(
        "login.html",
        supabase_url=SUPABASE_URL,
        supabase_publishable_key=(
            SUPABASE_PUBLISHABLE_KEY
        )
    )


@app.route("/vet/cases")
def vet_cases_page():

    return render_template(
        "vet_cases.html",
        supabase_url=SUPABASE_URL,
        supabase_publishable_key=(
            SUPABASE_PUBLISHABLE_KEY
        )
    )


@app.route("/vaccination")
def vaccination_page():

    return render_template(
        "vaccination.html",
        supabase_url=SUPABASE_URL,
        supabase_publishable_key=(
            SUPABASE_PUBLISHABLE_KEY
        )
    )


@app.route("/animals")
def animals_page():

    return render_template(
        "animals.html",
        supabase_url=SUPABASE_URL,
        supabase_publishable_key=(
            SUPABASE_PUBLISHABLE_KEY
        )
    )


@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )


@app.route("/dashboard/farmer")
def dashboard_farmer():

    return render_template(
        "dashboard_farmer.html"
    )


@app.route("/dashboard/vet")
def dashboard_vet():

    return render_template(
        "dashboard_vet.html"
    )


@app.route("/report")
def report_page():

    return render_template(
        "report.html"
    )


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

    if len(image_bytes) > 8 * 1024 * 1024:

        return jsonify({
            "success": False,
            "error": (
                "Image too large. "
                "Maximum size is 8 MB."
            )
        }), 413

    mime_type = (
        image.mimetype
        or "image/jpeg"
    )

    ai_result = gemini_image_screen(
        image_bytes,
        mime_type
    )

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
            "Image screening is an assistive tool "
            "and does not provide a definitive "
            "veterinary diagnosis."
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

        except Exception as exc:

            print(
                "Supabase report insert failed:",
                repr(exc)
            )

    report = dict(report)

    report["id"] = len(
        _MEMORY_REPORTS
    ) + 1

    _MEMORY_REPORTS.append(report)

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

            if response.data is not None:
                return response.data

        except Exception as exc:

            print(
                "Supabase report fetch failed:",
                repr(exc)
            )

    return list(
        reversed(_MEMORY_REPORTS)
    )


# ============================================================
# REPORT API
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

    now = datetime.now(timezone.utc)

    report = {
        "village": data.get("village", "Satara"),
        "block": data.get("block"),
        "district": data.get("district", "Satara"),

        # Support both old frontend fields (lat/lng)
        # and the normalized database fields.
        "latitude": data.get("latitude", data.get("lat")),
        "longitude": data.get("longitude", data.get("lng")),

        "animal_id": data.get("animal_id"),
        "animal_type": data.get("animal_type", "unknown"),

        "symptoms": normalize_symptoms(
            data.get("symptoms", [])
        ),

        "affected_count": result["affected_count"],
        "days_since_onset": result["days_since_onset"],
        "notes": data.get("notes", ""),

        "risk_level": result["risk_level"],
        "risk_score": result["risk_score"],

        "reported_by": data.get("reported_by"),
        "date": now.date().isoformat(),
        "created_at": now.isoformat(),

        "confidence": result["confidence"],
        "risk_factors": result["factors"],

        "case_status": data.get(
            "case_status",
            "UNDER_REVIEW"
        ),
        "vet_verified": False,
        "vet_notes": None,
        "diagnosis": None,
        "treatment": None,
        "verified_at": None
    }

    saved = save_report(report)

    return jsonify({
        "success": True,
        "report": saved,
        "risk": result
    })


# ============================================================
# ANIMAL REGISTRY HELPERS
# ============================================================

def build_animal_payload(data):

    allowed = {
        "animal_tag",
        "species",
        "breed",
        "sex",
        "age",
        "owner_name",
        "village",
        "block",
        "latitude",
        "longitude",
        "vaccination_status",
        "treatment_history"
    }

    payload = {}

    for field in allowed:

        if field in data:

            value = data.get(field)

            if isinstance(value, str):
                value = value.strip()

            payload[field] = value

    return payload


# ============================================================
# ANIMAL REGISTRY API
# ============================================================

@app.route(
    "/api/animals",
    methods=["GET", "POST"]
)
def animals_api():

    if request.method == "GET":

        if not supabase:

            return jsonify({
                "success": True,
                "animals": list(
                    reversed(
                        _MEMORY_ANIMALS
                    )
                ),
                "demo": True
            })

        try:

            response = (
                supabase
                .table("animals")
                .select("*")
                .order(
                    "created_at",
                    desc=True
                )
                .limit(1000)
                .execute()
            )

            return jsonify({
                "success": True,
                "animals": response.data or []
            })

        except Exception as exc:

            print(
                "Animal fetch failed:",
                repr(exc)
            )

            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    data = request.get_json(
        silent=True
    ) or {}

    species = str(
        data.get("species") or ""
    ).strip()

    if not species:

        return jsonify({
            "success": False,
            "error": "Animal species is required."
        }), 400

    payload = build_animal_payload(data)

    if not supabase:

        animal = {
            "id": len(_MEMORY_ANIMALS) + 1,
            **payload,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        _MEMORY_ANIMALS.append(animal)

        return jsonify({
            "success": True,
            "animal": animal,
            "demo": True
        }), 201

    try:

        response = (
            supabase
            .table("animals")
            .insert(payload)
            .execute()
        )

        saved = (
            response.data[0]
            if response.data
            else payload
        )

        return jsonify({
            "success": True,
            "animal": saved
        }), 201

    except Exception as exc:

        print(
            "Animal insert failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# GET SINGLE ANIMAL
# ============================================================

@app.route(
    "/api/animals/<animal_id>",
    methods=["GET"]
)
def get_animal(animal_id):

    if not supabase:

        for animal in _MEMORY_ANIMALS:

            if str(
                animal.get("id")
            ) == str(animal_id):

                return jsonify({
                    "success": True,
                    "animal": animal,
                    "demo": True
                })

        return jsonify({
            "success": False,
            "error": "Animal not found."
        }), 404

    try:

        response = (
            supabase
            .table("animals")
            .select("*")
            .eq("id", animal_id)
            .limit(1)
            .execute()
        )

        if not response.data:

            return jsonify({
                "success": False,
                "error": "Animal not found."
            }), 404

        return jsonify({
            "success": True,
            "animal": response.data[0]
        })

    except Exception as exc:

        print(
            "Single animal fetch failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# UPDATE ANIMAL
# ============================================================

@app.route(
    "/api/animals/<animal_id>",
    methods=["PUT"]
)
def update_animal(animal_id):

    data = request.get_json(
        silent=True
    ) or {}

    payload = build_animal_payload(data)

    if "species" in payload:

        payload["species"] = str(
            payload["species"]
        ).strip()

        if not payload["species"]:

            return jsonify({
                "success": False,
                "error": (
                    "Animal species "
                    "cannot be empty."
                )
            }), 400

    if not payload:

        return jsonify({
            "success": False,
            "error": "No fields to update."
        }), 400

    if not supabase:

        for animal in _MEMORY_ANIMALS:

            if str(
                animal.get("id")
            ) == str(animal_id):

                animal.update(payload)

                return jsonify({
                    "success": True,
                    "animal": animal,
                    "demo": True
                })

        return jsonify({
            "success": False,
            "error": "Animal not found."
        }), 404

    try:

        response = (
            supabase
            .table("animals")
            .update(payload)
            .eq("id", animal_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "success": False,
                "error": "Animal not found."
            }), 404

        return jsonify({
            "success": True,
            "animal": response.data[0]
        })

    except Exception as exc:

        print(
            "Animal update failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# DELETE ANIMAL
# ============================================================

@app.route(
    "/api/animals/<animal_id>",
    methods=["DELETE"]
)
def delete_animal(animal_id):

    if not supabase:

        original_count = len(
            _MEMORY_ANIMALS
        )

        _MEMORY_ANIMALS[:] = [
            animal
            for animal in _MEMORY_ANIMALS
            if str(
                animal.get("id")
            ) != str(animal_id)
        ]

        if len(_MEMORY_ANIMALS) == original_count:

            return jsonify({
                "success": False,
                "error": "Animal not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Animal deleted successfully.",
            "demo": True
        })

    try:

        (
            supabase
            .table("animals")
            .delete()
            .eq("id", animal_id)
            .execute()
        )

        return jsonify({
            "success": True,
            "message": "Animal deleted successfully."
        })

    except Exception as exc:

        print(
            "Animal delete failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# OFFICIAL DASHBOARD
# ============================================================

@app.route("/dashboard/official")
def dashboard_official():

    reports = get_reports()

    block_data = {}

    for report in reports:

        block = str(
            report.get("block") or "Unknown"
        ).strip()

        village = str(
            report.get("village") or "Unknown"
        ).strip()

        if block not in block_data:

            block_data[block] = {
                "block": block,
                "villages": set(),
                "open_reports": 0,
                "high_risk": 0
            }

        block_data[block]["villages"].add(village)

        status = str(
            report.get("case_status")
            or report.get("status")
            or "OPEN"
        ).upper()

        if status not in {
            "CLOSED",
            "REJECTED",
            "RESOLVED"
        }:
            block_data[block]["open_reports"] += 1

        if str(
            report.get("risk_level") or ""
        ).upper() == "HIGH":

            block_data[block]["high_risk"] += 1

    block_summary = []

    for data in block_data.values():

        block_summary.append({
            "block": data["block"],
            "villages_reporting": len(
                data["villages"]
            ),
            "open_reports": data["open_reports"],
            "high_risk": data["high_risk"]
        })

    block_summary.sort(
        key=lambda item: item["open_reports"],
        reverse=True
    )

    totals = {
        "total_open_reports": sum(
            x["open_reports"]
            for x in block_summary
        ),
        "total_high_risk": sum(
            x["high_risk"]
            for x in block_summary
        ),
        "blocks_reporting": len(
            block_summary
        ),
        "vaccination_coverage": 0
    }

    if supabase:

        try:

            vaccination_response = (
                supabase
                .table("vaccination_records")
                .select("*")
                .execute()
            )

            if vaccination_response.data:
                totals["vaccination_coverage"] = 100

        except Exception as exc:

            print(
                "Vaccination dashboard error:",
                repr(exc)
            )

    return render_template(
        "dashboard_official.html",
        totals=totals,
        block_summary=block_summary,
        reports=reports
    )


# ============================================================
# DISTRICT OFFICER DASHBOARD
# ============================================================

@app.route("/dashboard/district")
def dashboard_district():

    # --------------------------------------------------------
    # DISTRICT SELECTOR
    # --------------------------------------------------------

    district_name = (
        request.args.get(
            "district",
            "Satara"
        ).strip()
        or "Satara"
    )

    reports = get_reports()

    # --------------------------------------------------------
    # LOAD ANIMALS
    # --------------------------------------------------------

    animals = []

    if supabase:

        try:

            response = (
                supabase
                .table("animals")
                .select("*")
                .limit(5000)
                .execute()
            )

            animals = response.data or []

        except Exception as exc:

            print(
                "District animal dashboard error:",
                repr(exc)
            )

    else:

        animals = list(
            _MEMORY_ANIMALS
        )

    # --------------------------------------------------------
    # LOAD VACCINATION RECORDS
    # --------------------------------------------------------

    vaccinations = []

    if supabase:

        try:

            response = (
                supabase
                .table("vaccination_records")
                .select("*")
                .limit(5000)
                .execute()
            )

            vaccinations = response.data or []

        except Exception as exc:

            print(
                "District vaccination dashboard error:",
                repr(exc)
            )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def clean(value):
        return str(value or "").strip()

    def report_status(report):

        return clean(
            report.get("case_status")
            or report.get("status")
            or ""
        ).upper()

    def report_risk(report):

        return clean(
            report.get("risk_level")
            or report.get("risk")
            or ""
        ).upper()

    def vaccinated_status(value):

        return clean(value).upper() in {
            "VACCINATED",
            "UP_TO_DATE",
            "COMPLETED",
            "FULLY_VACCINATED"
        }

    def death_report(report):

        status = report_status(report)

        if status in {
            "DEATH",
            "DIED",
            "DECEASED"
        }:
            return True

        symptoms = clean(
            report.get("symptoms")
        ).lower()

        return any(
            word in symptoms
            for word in [
                "death",
                "deaths",
                "died",
                "dead",
                "mortality"
            ]
        )

    # --------------------------------------------------------
    # DATA STRUCTURES
    # --------------------------------------------------------

    village_data = {}
    block_data = {}

    def get_village(name, block_name="Unknown"):

        name = clean(name) or "Unknown Village"

        if name not in village_data:

            village_data[name] = {
                "name": name,
                "block": clean(block_name)
                    or "Unknown",
                "animals": 0,
                "vaccinated_animals": set(),
                "report_count": 0,
                "affected_animals": 0,
                "active_cases": 0,
                "high_risk": 0,
                "deaths": 0,
                "suspected_outbreak": False
            }

        return village_data[name]

    def get_block(name):

        name = clean(name) or "Unknown Block"

        if name not in block_data:

            block_data[name] = {
                "name": name,
                "animals": 0,
                "vaccinated_animals": set(),
                "report_count": 0,
                "affected_animals": 0,
                "active_cases": 0,
                "high_risk": 0,
                "deaths": 0,
                "suspected_outbreak": False,
                "villages": set()
            }

        return block_data[name]

    # --------------------------------------------------------
    # ANIMAL REGISTRY
    # --------------------------------------------------------

    animal_map = {}

    for animal in animals:

        animal_id = clean(
            animal.get("id")
        )

        if animal_id:
            animal_map[animal_id] = animal

        village_name = animal.get("village")
        block_name = animal.get("block")

        village = get_village(
            village_name,
            block_name
        )

        block = get_block(block_name)

        village["animals"] += 1

        block["animals"] += 1

        block["villages"].add(
            village["name"]
        )

        if vaccinated_status(
            animal.get("vaccination_status")
        ):

            if animal_id:

                village[
                    "vaccinated_animals"
                ].add(animal_id)

                block[
                    "vaccinated_animals"
                ].add(animal_id)

    # --------------------------------------------------------
    # VACCINATION RECORDS
    # --------------------------------------------------------

    for vaccination in vaccinations:

        animal_id = clean(
            vaccination.get("animal_id")
        )

        animal = animal_map.get(
            animal_id
        )

        if animal:

            village = get_village(
                animal.get("village"),
                animal.get("block")
            )

            block = get_block(
                animal.get("block")
            )

            block["villages"].add(
                village["name"]
            )

            if animal_id:

                village[
                    "vaccinated_animals"
                ].add(animal_id)

                block[
                    "vaccinated_animals"
                ].add(animal_id)

    # --------------------------------------------------------
    # REPORT ANALYTICS
    # --------------------------------------------------------

    for report in reports:

        village_name = report.get(
            "village"
        )

        block_name = report.get(
            "block"
        )

        village = get_village(
            village_name,
            block_name
        )

        block = get_block(
            block_name
        )

        block["villages"].add(
            village["name"]
        )

        village["report_count"] += 1
        block["report_count"] += 1

        # Affected animals
        affected = max(
            safe_int(
                report.get(
                    "affected_count"
                ),
                1
            ),
            1
        )

        village[
            "affected_animals"
        ] += affected

        block[
            "affected_animals"
        ] += affected

        # Active cases
        status = report_status(
            report
        )

        if status not in {
            "CLOSED",
            "REJECTED",
            "RESOLVED"
        }:

            village[
                "active_cases"
            ] += 1

            block[
                "active_cases"
            ] += 1

        # High risk
        risk = report_risk(
            report
        )

        if risk == "HIGH":

            village[
                "high_risk"
            ] += 1

            block[
                "high_risk"
            ] += 1

        # Deaths
        if death_report(report):

            village[
                "deaths"
            ] += affected

            block[
                "deaths"
            ] += affected

        # Outbreak signal
        if (
            risk == "HIGH"
            and affected >= 5
        ):

            village[
                "suspected_outbreak"
            ] = True

            block[
                "suspected_outbreak"
            ] = True

    # --------------------------------------------------------
    # VILLAGE SUMMARIES
    # --------------------------------------------------------

    villages = []

    for data in village_data.values():

        if (
            data["high_risk"] >= 3
            or data["deaths"] >= 3
            or data["suspected_outbreak"]
        ):

            risk_level = "HIGH"

        elif (
            data["high_risk"] >= 1
            or data["active_cases"] >= 3
            or data["deaths"] >= 1
        ):

            risk_level = "WATCH"

        else:

            risk_level = "LOW"

        animals_count = data[
            "animals"
        ]

        vaccinated_count = len(
            data["vaccinated_animals"]
        )

        coverage = (
            round(
                (
                    vaccinated_count
                    / animals_count
                ) * 100,
                1
            )
            if animals_count > 0
            else 0
        )

        villages.append({
            "name": data["name"],
            "village": data["name"],
            "block": data["block"],
            "animals": animals_count,
            "vaccinated_animals":
                vaccinated_count,
            "vaccination_coverage":
                coverage,
            "report_count":
                data["report_count"],
            "affected_animals":
                data["affected_animals"],
            "active_cases":
                data["active_cases"],
            "high_risk":
                data["high_risk"],
            "deaths":
                data["deaths"],
            "suspected_outbreak":
                data["suspected_outbreak"],
            "risk":
                risk_level,
            "risk_level":
                risk_level
        })

    villages.sort(
        key=lambda x: (
            {
                "HIGH": 3,
                "WATCH": 2,
                "LOW": 1
            }.get(
                x["risk_level"],
                0
            ),
            x["active_cases"],
            x["high_risk"],
            x["deaths"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # BLOCK SUMMARIES
    # --------------------------------------------------------

    blocks = []

    for data in block_data.values():

        animals_count = data[
            "animals"
        ]

        vaccinated_count = len(
            data["vaccinated_animals"]
        )

        coverage = (
            round(
                (
                    vaccinated_count
                    / animals_count
                ) * 100,
                1
            )
            if animals_count > 0
            else 0
        )

        if (
            data["high_risk"] >= 5
            or data["deaths"] >= 5
            or data["suspected_outbreak"]
        ):

            risk_level = "HIGH"

        elif (
            data["high_risk"] >= 1
            or data["active_cases"] >= 5
            or data["deaths"] >= 1
        ):

            risk_level = "WATCH"

        else:

            risk_level = "LOW"

        blocks.append({
            "name": data["name"],
            "block": data["name"],
            "villages": len(
                data["villages"]
            ),
            "animals": animals_count,
            "vaccinated_animals":
                vaccinated_count,
            "vaccination_coverage":
                coverage,
            "report_count":
                data["report_count"],
            "affected_animals":
                data["affected_animals"],
            "active_cases":
                data["active_cases"],
            "high_risk":
                data["high_risk"],
            "deaths":
                data["deaths"],
            "suspected_outbreak":
                data["suspected_outbreak"],
            "risk":
                risk_level,
            "risk_level":
                risk_level
        })

    blocks.sort(
        key=lambda x: (
            {
                "HIGH": 3,
                "WATCH": 2,
                "LOW": 1
            }.get(
                x["risk_level"],
                0
            ),
            x["active_cases"],
            x["high_risk"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # DISTRICT TOTALS
    # --------------------------------------------------------

    total_animals = len(
        animals
    )

    vaccinated_animal_ids = set()

    for animal in animals:

        animal_id = clean(
            animal.get("id")
        )

        if (
            animal_id
            and vaccinated_status(
                animal.get(
                    "vaccination_status"
                )
            )
        ):

            vaccinated_animal_ids.add(
                animal_id
            )

    # Vaccination records
    for vaccination in vaccinations:

        animal_id = clean(
            vaccination.get("animal_id")
        )

        if animal_id:
            vaccinated_animal_ids.add(
                animal_id
            )

    vaccinated_animals = len(
        vaccinated_animal_ids
    )

    vaccination_coverage = (
        round(
            (
                vaccinated_animals
                / total_animals
            ) * 100,
            1
        )
        if total_animals > 0
        else 0
    )

    active_cases = sum(
        1
        for report in reports
        if report_status(report)
        not in {
            "CLOSED",
            "REJECTED",
            "RESOLVED"
        }
    )

    high_risk_cases = sum(
        1
        for report in reports
        if report_risk(report) == "HIGH"
    )

    affected_animals = sum(
        max(
            safe_int(
                report.get(
                    "affected_count"
                ),
                1
            ),
            1
        )
        for report in reports
    )

    deaths = sum(
        max(
            safe_int(
                report.get(
                    "affected_count"
                ),
                1
            ),
            1
        )
        for report in reports
        if death_report(report)
    )

    high_risk_villages = sum(
        1
        for village in villages
        if village["risk_level"] == "HIGH"
    )

    suspected_outbreaks = sum(
        1
        for village in villages
        if village["suspected_outbreak"]
    )

    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    alerts = []

    for village in villages:

        if village["risk_level"] == "HIGH":

            alerts.append({
                "type": "HIGH RISK",
                "severity": "HIGH",
                "village":
                    village["village"],
                "block":
                    village["block"],
                "title":
                    f"High-risk village: "
                    f"{village['village']}",
                "message": (
                    f"{village['high_risk']} "
                    f"high-risk cases and "
                    f"{village['active_cases']} "
                    f"active cases detected."
                )
            })

        elif village[
            "suspected_outbreak"
        ]:

            alerts.append({
                "type": "OUTBREAK",
                "severity": "HIGH",
                "village":
                    village["village"],
                "block":
                    village["block"],
                "title":
                    f"Possible outbreak: "
                    f"{village['village']}",
                "message": (
                    f"{village['affected_animals']} "
                    "animals affected. "
                    "Immediate veterinary review "
                    "recommended."
                )
            })

        elif village["deaths"] > 0:

            alerts.append({
                "type": "MORTALITY",
                "severity": "MEDIUM",
                "village":
                    village["village"],
                "block":
                    village["block"],
                "title":
                    f"Animal deaths: "
                    f"{village['village']}",
                "message": (
                    f"{village['deaths']} "
                    "death(s) detected."
                )
            })

        elif village[
            "active_cases"
        ] >= 3:

            alerts.append({
                "type": "WATCH",
                "severity": "MEDIUM",
                "village":
                    village["village"],
                "block":
                    village["block"],
                "title":
                    f"Multiple active cases: "
                    f"{village['village']}",
                "message": (
                    "Multiple active disease "
                    "cases require monitoring."
                )
            })

    # --------------------------------------------------------
    # RECENT CASES
    # --------------------------------------------------------

    recent_cases = []

    for report in reports[:50]:

        recent_cases.append({
            "id": report.get("id"),
            "village": report.get(
                "village",
                "Unknown"
            ),
            "block": report.get(
                "block",
                "Unknown"
            ),
            "animal_type": report.get(
                "animal_type",
                "Unknown"
            ),
            "risk_level": report.get(
                "risk_level",
                "LOW"
            ),
            "case_status": report.get(
                "case_status",
                "UNDER_REVIEW"
            ),
            "affected_count": report.get(
                "affected_count",
                0
            ),
            "created_at": report.get(
                "created_at"
            )
        })

    # --------------------------------------------------------
    # TOTALS OBJECT
    # --------------------------------------------------------

    totals = {
        "total_villages":
            len(villages),

        "total_animals":
            total_animals,

        "active_cases":
            active_cases,

        "high_risk_cases":
            high_risk_cases,

        "high_risk_villages":
            high_risk_villages,

        "suspected_outbreaks":
            suspected_outbreaks,

        "deaths":
            deaths,

        "affected_animals":
            affected_animals,

        "vaccination_records":
            len(vaccinations),

        "vaccinated_animals":
            vaccinated_animals,

        "vaccination_coverage":
            vaccination_coverage,

        "blocks":
            len(blocks)
    }

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "district_dashboard.html",
        district_name=(
            f"{district_name} District"
        ),
        totals=totals,
        blocks=blocks,
        villages=villages,
        alerts=alerts,
        recent_cases=recent_cases
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "success": True,

        "app": "PashuRakshak AI",

        "status": "healthy",

        "supabase": bool(
            supabase
        ),

        "supabase_init_error":
            SUPABASE_INIT_ERROR,

        "image_ai": bool(
            GEMINI_API_KEY
        ),

        "feature_blueprint":
            bool(feature_bp),

        "feature_blueprint_error":
            FEATURE_BLUEPRINT_ERROR,

        "animal_registry":
            True,

        "environment": {

            "SUPABASE_URL":
                bool(SUPABASE_URL),

            "SUPABASE_KEY":
                bool(SUPABASE_KEY),

            "SUPABASE_PUBLISHABLE_KEY":
                bool(
                    SUPABASE_PUBLISHABLE_KEY
                ),

            "GEMINI_API_KEY":
                bool(GEMINI_API_KEY)
        },

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat()
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
# LOCAL DEVELOPMENT
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
