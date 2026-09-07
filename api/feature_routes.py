```python
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

try:
    from supabase import create_client
except Exception:
    create_client = None


feature_bp = Blueprint("feature_bp", __name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = None
SUPABASE_INIT_ERROR = None


# =========================================================
# SUPABASE INITIALIZATION
# =========================================================

if SUPABASE_URL and SUPABASE_KEY and create_client:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception as exc:
        SUPABASE_INIT_ERROR = str(exc)
        print(
            "Feature Supabase initialization failed:",
            repr(exc)
        )
        supabase = None


# =========================================================
# HELPERS
# =========================================================

def _json():
    return request.get_json(silent=True) or {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# FEATURE HEALTH
# =========================================================

@feature_bp.get("/api/feature-health")
def feature_health():
    return jsonify({
        "success": True,
        "features": [
            "authentication",
            "role_based_access",
            "vet_verification",
            "smart_alerts",
            "vaccination_tracking",
            "outbreak_prediction",
            "dashboard_kpis"
        ],
        "supabase": bool(supabase),
        "supabase_init_error": SUPABASE_INIT_ERROR
    })


# =========================================================
# VET CASE VERIFICATION
# =========================================================

@feature_bp.post("/api/cases/<case_id>/verify")
def verify_case(case_id):

    data = _json()

    status = str(
        data.get(
            "case_status",
            "VERIFIED"
        )
    ).strip().upper()

    allowed = {
        "UNDER_REVIEW",
        "VERIFIED",
        "TREATMENT",
        "ISOLATED",
        "CLOSED",
        "REJECTED"
    }

    if status not in allowed:
        return jsonify({
            "success": False,
            "error": "Invalid case status"
        }), 400

    payload = {
        "case_status": status,

        "vet_verified": status in {
            "VERIFIED",
            "TREATMENT",
            "ISOLATED",
            "CLOSED"
        },

        "vet_notes": str(
            data.get(
                "vet_notes",
                ""
            )
        )[:4000],

        "diagnosis": str(
            data.get(
                "diagnosis",
                ""
            )
        )[:2000],

        "treatment": str(
            data.get(
                "treatment",
                ""
            )
        )[:4000],

        "verified_at": _now()
    }

    try:

        if not supabase:
            return jsonify({
                "success": True,
                "demo": True,
                "supabase": False,
                "report": {
                    "id": case_id,
                    **payload
                }
            })

        result = (
            supabase
            .table("reports")
            .update(payload)
            .eq("id", case_id)
            .execute()
        )

        return jsonify({
            "success": True,
            "report": (
                result.data[0]
                if result.data
                else {
                    "id": case_id,
                    **payload
                }
            )
        })

    except Exception as exc:

        print(
            "Case verification failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# =========================================================
# ADD VACCINATION
# =========================================================

@feature_bp.post("/api/vaccinations")
def add_vaccination():

    data = _json()

    required = [
        "species",
        "vaccine_name",
        "vaccination_date"
    ]

    missing = [
        field
        for field in required
        if not data.get(field)
    ]

    if missing:
        return jsonify({
            "success": False,
            "error": "Missing: " + ", ".join(missing)
        }), 400

    payload = {
        "animal_id": data.get("animal_id"),
        "species": data.get("species"),
        "vaccine_name": data.get("vaccine_name"),
        "vaccination_date": data.get(
            "vaccination_date"
        ),
        "next_due_date": data.get(
            "next_due_date"
        ),
        "batch_number": data.get(
            "batch_number"
        ),
        "administered_by": data.get(
            "administered_by"
        ),
        "notes": data.get(
            "notes",
            ""
        )
    }

    try:

        if not supabase:
            return jsonify({
                "success": True,
                "demo": True,
                "record": payload
            })

        result = (
            supabase
            .table("vaccination_records")
            .insert(payload)
            .execute()
        )

        return jsonify({
            "success": True,
            "record": (
                result.data[0]
                if result.data
                else payload
            )
        })

    except Exception as exc:

        print(
            "Vaccination insert failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# =========================================================
# GET VACCINATIONS
# =========================================================

@feature_bp.get("/api/vaccinations")
def get_vaccinations():

    try:

        if not supabase:
            return jsonify({
                "success": True,
                "records": [],
                "demo": True
            })

        result = (
            supabase
            .table(
                "vaccination_records"
            )
            .select("*")
            .order(
                "vaccination_date",
                desc=True
            )
            .limit(1000)
            .execute()
        )

        return jsonify({
            "success": True,
            "records": result.data or []
        })

    except Exception as exc:

        print(
            "Vaccination fetch failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# =========================================================
# OUTBREAK RISK / CLUSTER DETECTION
# =========================================================

@feature_bp.get("/api/outbreak-risk")
def outbreak_risk():

    try:

        if not supabase:
            return jsonify({
                "success": True,
                "clusters": [],
                "demo": True,
                "disclaimer":
                    "Early-warning aid only; "
                    "not epidemiological confirmation."
            })

        result = (
            supabase
            .table("reports")
            .select(
                "id,"
                "village,"
                "block,"
                "district,"
                "risk_level,"
                "affected_count,"
                "created_at,"
                "latitude,"
                "longitude,"
                "case_status,"
                "symptoms"
            )
            .order(
                "created_at",
                desc=True
            )
            .limit(1000)
            .execute()
        )

        groups = {}

        for row in result.data or []:

            area = (
                row.get("village")
                or row.get("block")
                or "Unknown"
            )

            if area not in groups:

                groups[area] = {
                    "area": area,
                    "village": row.get(
                        "village"
                    ),
                    "block": row.get(
                        "block"
                    ),
                    "district": row.get(
                        "district"
                    ),
                    "reports": 0,
                    "affected": 0,
                    "high": 0,
                    "moderate": 0,
                    "low": 0,
                    "active_cases": 0,
                    "deaths": 0,
                    "latitude": row.get(
                        "latitude"
                    ),
                    "longitude": row.get(
                        "longitude"
                    )
                }

            group = groups[area]

            group["reports"] += 1

            affected = max(
                _int(
                    row.get(
                        "affected_count"
                    ),
                    1
                ),
                1
            )

            group["affected"] += affected

            level = str(
                row.get(
                    "risk_level",
                    ""
                )
            ).upper()

            if level == "HIGH":

                group["high"] += 1

            elif level in {
                "MODERATE",
                "MEDIUM"
            }:

                group["moderate"] += 1

            else:

                group["low"] += 1

            status = str(
                row.get(
                    "case_status",
                    "OPEN"
                )
            ).upper()

            if status not in {
                "CLOSED",
                "REJECTED",
                "RESOLVED"
            }:

                group["active_cases"] += 1

            symptoms = str(
                row.get(
                    "symptoms",
                    ""
                )
            ).lower()

            if (
                "death" in symptoms
                or "deaths" in symptoms
                or status == "DEATH"
            ):

                group["deaths"] += affected

        clusters = []

        for group in groups.values():

            score = min(
                100,
                group["high"] * 20
                + group["moderate"] * 8
                + group["active_cases"] * 5
                + min(
                    group["affected"],
                    20
                ) * 2
            )

            if score >= 60:

                outbreak_level = "HIGH"

            elif score >= 30:

                outbreak_level = "WATCH"

            else:

                outbreak_level = "LOW"

            clusters.append({
                **group,
                "outbreak_score": score,
                "outbreak_level": outbreak_level
            })

        clusters.sort(
            key=lambda x:
                x["outbreak_score"],
            reverse=True
        )

        return jsonify({
            "success": True,
            "clusters": clusters,
            "disclaimer":
                "Early-warning aid only; "
                "not epidemiological confirmation."
        })

    except Exception as exc:

        print(
            "Outbreak risk failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# =========================================================
# DASHBOARD KPIs
# =========================================================

@feature_bp.get("/api/dashboard-kpis")
def dashboard_kpis():

    try:

        if not supabase:

            return jsonify({
                "success": True,
                "total_cases": 0,
                "active_cases": 0,
                "high_risk_cases": 0,
                "moderate_cases": 0,
                "animals_affected": 0,
                "verified_cases": 0,
                "suspected_outbreaks": 0,
                "deaths": 0,
                "vaccinated_animals": 0
            })

        result = (
            supabase
            .table("reports")
            .select(
                "risk_level,"
                "affected_count,"
                "case_status,"
                "symptoms,"
                "village"
            )
            .limit(5000)
            .execute()
        )

        rows = result.data or []

        total = len(rows)

        active = 0
        high = 0
        moderate = 0
        affected_total = 0
        verified = 0
        deaths = 0

        outbreak_groups = {}

        for row in rows:

            status = str(
                row.get(
                    "case_status",
                    "OPEN"
                )
            ).upper()

            risk = str(
                row.get(
                    "risk_level",
                    ""
                )
            ).upper()

            affected = max(
                _int(
                    row.get(
                        "affected_count"
                    ),
                    1
                ),
                1
            )

            affected_total += affected

            if status not in {
                "CLOSED",
                "REJECTED",
                "RESOLVED"
            }:

                active += 1

            if risk == "HIGH":

                high += 1

            elif risk in {
                "MODERATE",
                "MEDIUM"
            }:

                moderate += 1

            if status in {
                "VERIFIED",
                "TREATMENT",
                "ISOLATED",
                "CLOSED"
            }:

                verified += 1

            symptoms = str(
                row.get(
                    "symptoms",
                    ""
                )
            ).lower()

            if (
                "death" in symptoms
                or "deaths" in symptoms
                or status == "DEATH"
            ):

                deaths += affected

            village = (
                row.get("village")
                or "Unknown"
            )

            if village not in outbreak_groups:

                outbreak_groups[village] = {
                    "high": 0,
                    "affected": 0
                }

            if risk == "HIGH":

                outbreak_groups[
                    village
                ]["high"] += 1

            outbreak_groups[
                village
            ]["affected"] += affected

        suspected_outbreaks = 0

        for group in outbreak_groups.values():

            if (
                group["high"] >= 3
                or group["affected"] >= 10
            ):

                suspected_outbreaks += 1

        vaccinated_animals = 0

        try:

            vaccination_result = (
                supabase
                .table(
                    "vaccination_records"
                )
                .select("animal_id")
                .limit(5000)
                .execute()
            )

            unique_animals = set()

            for row in (
                vaccination_result.data
                or []
            ):

                animal_id = row.get(
                    "animal_id"
                )

                if animal_id:

                    unique_animals.add(
                        str(animal_id)
                    )

            vaccinated_animals = len(
                unique_animals
            )

        except Exception as exc:

            print(
                "Vaccination KPI failed:",
                repr(exc)
            )

        return jsonify({
            "success": True,
            "total_cases": total,
            "active_cases": active,
            "high_risk_cases": high,
            "moderate_cases": moderate,
            "animals_affected": affected_total,
            "verified_cases": verified,
            "suspected_outbreaks":
                suspected_outbreaks,
            "deaths": deaths,
            "vaccinated_animals":
                vaccinated_animals
        })

    except Exception as exc:

        print(
            "Dashboard KPI failed:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500
```
