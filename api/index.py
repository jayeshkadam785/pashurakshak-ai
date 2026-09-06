# ============================================================
# HOME
# ============================================================

@app.route("/login")
def login_page():
    return render_template(
        "login.html",
        supabase_url=SUPABASE_URL or "",
        supabase_key=SUPABASE_KEY or ""
    )

@app.route("/vet/cases")
def vet_cases_page():
    return render_template("vet_cases.html")


@app.route("/vaccination")
def vaccination_page():
    return render_template("vaccination.html")


@app.route("/")
def home():

    try:
        return render_template("index.html")

    except Exception:
        return jsonify({
            "app": "PashuRakshak AI",
            "status": "running"
        })

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
