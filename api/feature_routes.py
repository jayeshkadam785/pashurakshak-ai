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
if SUPABASE_URL and SUPABASE_KEY and create_client:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None


def _json():
    return request.get_json(silent=True) or {}


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


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
            "outbreak_prediction"
        ]
    })


@feature_bp.post("/api/cases/<case_id>/verify")
def verify_case(case_id):
    data = _json()
    status = str(data.get("case_status", "VERIFIED")).upper()

    allowed = {
        "UNDER_REVIEW", "VERIFIED", "TREATMENT",
        "ISOLATED", "CLOSED", "REJECTED"
    }

    if status not in allowed:
        return jsonify({"success": False, "error": "Invalid case status"}), 400

    payload = {
        "case_status": status,
        "vet_verified": status in {"VERIFIED", "TREATMENT", "ISOLATED", "CLOSED"},
        "vet_notes": str(data.get("vet_notes", ""))[:4000],
        "diagnosis": str(data.get("diagnosis", ""))[:1000],
        "treatment": str(data.get("treatment", ""))[:4000],
        "verified_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        if not supabase:
            return jsonify({
                "success": True,
                "demo": True,
                "report": {"id": case_id, **payload}
            })

        result = (
            supabase.table("reports")
            .update(payload)
            .eq("id", case_id)
            .execute()
        )

        return jsonify({
            "success": True,
            "report": result.data[0] if result.data else payload
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@feature_bp.post("/api/vaccinations")
def add_vaccination():
    data = _json()
    required = ["species", "vaccine_name", "vaccination_date"]
    missing = [x for x in required if not data.get(x)]

    if missing:
        return jsonify({
            "success": False,
            "error": "Missing: " + ", ".join(missing)
        }), 400

    payload = {
        "animal_id": data.get("animal_id"),
        "species": data.get("species"),
        "vaccine_name": data.get("vaccine_name"),
        "vaccination_date": data.get("vaccination_date"),
        "next_due_date": data.get("next_due_date"),
        "batch_number": data.get("batch_number"),
        "administered_by": data.get("administered_by"),
        "notes": data.get("notes", "")
    }

    try:
        if not supabase:
            return jsonify({"success": True, "demo": True, "record": payload})

        result = supabase.table("vaccination_records").insert(payload).execute()

        return jsonify({
            "success": True,
            "record": result.data[0] if result.data else payload
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@feature_bp.get("/api/vaccinations")
def get_vaccinations():
    try:
        if not supabase:
            return jsonify({"success": True, "records": []})

        result = (
            supabase.table("vaccination_records")
            .select("*")
            .order("vaccination_date", desc=True)
            .limit(500)
            .execute()
        )

        return jsonify({"success": True, "records": result.data or []})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@feature_bp.get("/api/outbreak-risk")
def outbreak_risk():
    try:
        if not supabase:
            return jsonify({
                "success": True,
                "clusters": [],
                "disclaimer": "Early-warning aid only; not epidemiological confirmation."
            })

        result = (
            supabase.table("reports")
            .select("village,block,risk_level,affected_count,created_at,lat,lng")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )

        groups = {}
        for row in result.data or []:
            area = row.get("village") or row.get("block") or "Unknown"
            g = groups.setdefault(area, {
                "area": area,
                "reports": 0,
                "affected": 0,
                "high": 0,
                "moderate": 0,
                "lat": row.get("lat"),
                "lng": row.get("lng")
            })

            g["reports"] += 1
            g["affected"] += max(_safe_int(row.get("affected_count"), 1), 1)

            level = str(row.get("risk_level", "")).upper()
            if level == "HIGH":
                g["high"] += 1
            elif level == "MODERATE":
                g["moderate"] += 1

        clusters = []
        for g in groups.values():
            score = min(
                100,
                g["high"] * 20 +
                g["moderate"] * 8 +
                min(g["affected"], 20) * 2
            )

            level = (
                "HIGH" if score >= 60
                else "WATCH" if score >= 30
                else "LOW"
            )

            clusters.append({
                **g,
                "outbreak_score": score,
                "outbreak_level": level
            })

        clusters.sort(
            key=lambda x: x["outbreak_score"],
            reverse=True
        )

        return jsonify({
            "success": True,
            "clusters": clusters,
            "disclaimer": "Early-warning aid only; not epidemiological confirmation."
        })

    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@feature_bp.get("/api/dashboard-kpis")
def dashboard_kpis():
    try:
        if not supabase:
            return jsonify({
                "success": True,
                "total_cases": 0,
                "high_risk_cases": 0,
                "moderate_cases": 0,
                "animals_affected": 0,
                "verified_cases": 0
            })

        result = (
            supabase.table("reports")
            .select("risk_level,affected_count,case_status")
            .limit(2000)
            .execute()
        )

        rows = result.data or []

        total = len(rows)
        high = sum(
            1 for r in rows
            if str(r.get("risk_level", "")).upper() == "HIGH"
        )
        moderate = sum(
            1 for r in rows
            if str(r.get("risk_level", "")).upper() == "MODERATE"
        )
        affected = sum(
            max(_safe_int(r.get("affected_count"), 1), 1)
            for r in rows
        )
        verified = sum(
            1 for r in rows
            if r.get("case_status") in {
                "VERIFIED", "TREATMENT", "CLOSED"
            }
        )

        return jsonify({
            "success": True,
            "total_cases": total,
            "high_risk_cases": high,
            "moderate_cases": moderate,
            "animals_affected": affected,
            "verified_cases": verified
        })

    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
