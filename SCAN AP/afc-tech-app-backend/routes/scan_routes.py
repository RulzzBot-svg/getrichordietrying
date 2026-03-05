"""
Universal scan route — Phase 5 of the white-label roadmap.

When a QR code is scanned, it opens:
    app.com/scan?asset_id=<id>

The frontend calls this endpoint to:
1. Resolve the asset and its service items.
2. Return asset_type + required form fields so the React app can
   dynamically render the correct checklist (no hardcoded logic).

API surface:
  GET  /api/scan?asset_id=<id>   – resolve asset + service items
  POST /api/scan/submit           – submit a completed scan job
"""
import traceback
from flask import Blueprint, jsonify, request
from models import Asset, ServiceItem, Job, JobServiceItem, Technician
from db import db
from datetime import datetime, timezone
from dateutil.parser import isoparse
from utility.status import compute_filter_status as compute_service_item_status

scan_bp = Blueprint("scan", __name__)


# -------------------------------------------------------
# Field schema per asset_type
# Different industries get different form fields, but the
# frontend renders them generically from this config.
# -------------------------------------------------------
ASSET_TYPE_FIELDS = {
    "default": [
        {"key": "is_completed", "label": "Mark as completed", "type": "checkbox"},
        {"key": "is_inspected", "label": "Inspected", "type": "checkbox"},
        {"key": "note", "label": "Notes", "type": "textarea"},
    ],
    "AHU": [
        {"key": "is_completed", "label": "Filter replaced", "type": "checkbox"},
        {"key": "is_inspected", "label": "Inspected", "type": "checkbox"},
        {"key": "initial_resistance", "label": "Initial resistance (in. w.g.)", "type": "number"},
        {"key": "final_resistance", "label": "Final resistance (in. w.g.)", "type": "number"},
        {"key": "note", "label": "Notes", "type": "textarea"},
    ],
    "Boiler": [
        {"key": "is_completed", "label": "Service completed", "type": "checkbox"},
        {"key": "is_inspected", "label": "Inspected", "type": "checkbox"},
        {"key": "initial_resistance", "label": "Water pressure (psi)", "type": "number"},
        {"key": "note", "label": "Notes", "type": "textarea"},
    ],
    "Fire Extinguisher": [
        {"key": "is_inspected", "label": "Inspected", "type": "checkbox"},
        {"key": "is_completed", "label": "Recharged / replaced", "type": "checkbox"},
        {"key": "note", "label": "Condition notes", "type": "textarea"},
    ],
    "Plumbing Fixture": [
        {"key": "is_inspected", "label": "Inspected", "type": "checkbox"},
        {"key": "is_completed", "label": "Repaired / serviced", "type": "checkbox"},
        {"key": "note", "label": "Notes", "type": "textarea"},
    ],
}


def _get_fields_for_asset_type(asset_type: str) -> list:
    return ASSET_TYPE_FIELDS.get(asset_type, ASSET_TYPE_FIELDS["default"])


def _safe_status(si):
    try:
        return compute_service_item_status(si) or {}
    except Exception:
        return {}


# -------------------------------------------------------
# GET /api/scan?asset_id=<id>
# -------------------------------------------------------
@scan_bp.route("/scan", methods=["GET"])
def resolve_scan():
    """
    Resolve a scanned QR code into asset + service item data.

    The React app passes asset_id (the integer database ID embedded in the QR).
    Returns:
      - asset details
      - list of active service items with their current status
      - form_fields config so the frontend knows what inputs to render
    """
    asset_id_raw = request.args.get("asset_id")
    if not asset_id_raw:
        return jsonify({"error": "asset_id query parameter is required"}), 400

    try:
        asset_id = int(asset_id_raw)
    except ValueError:
        return jsonify({"error": "asset_id must be numeric"}), 400

    try:
        asset = db.session.get(Asset, asset_id)
        if not asset:
            return jsonify({"error": "Asset not found"}), 404

        active_items = (
            db.session.query(ServiceItem)
            .filter(ServiceItem.asset_id == asset_id, ServiceItem.is_active.is_(True))
            .order_by(ServiceItem.excel_order.asc(), ServiceItem.id.asc())
            .all()
        )

        items_payload = []
        for si in active_items:
            st = _safe_status(si)
            items_payload.append({
                "id": si.id,
                "phase": si.phase,
                "part_number": si.part_number,
                "size": si.size,
                "quantity": si.quantity,
                "frequency_days": si.frequency_days,
                "last_service_date": si.last_service_date.isoformat() if si.last_service_date else None,
                "status": st.get("status", "Pending"),
                "next_due_date": st.get("next_due_date"),
                "days_until_due": st.get("days_until_due"),
                "days_overdue": st.get("days_overdue"),
            })

        return jsonify({
            "asset_id": asset.id,
            "tenant_id": asset.tenant_id,
            "location_id": asset.location_id,
            "location_name": asset.location.name if asset.location else None,
            "name": asset.name,
            "asset_type": asset.asset_type or "default",
            "location_label": asset.location_label,
            "notes": asset.notes,
            # Dynamic form fields based on asset type — the React app
            # renders these without any hardcoded knowledge of the industry.
            "form_fields": _get_fields_for_asset_type(asset.asset_type or "default"),
            "service_items": items_payload,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------
# POST /api/scan/submit
# -------------------------------------------------------
@scan_bp.route("/scan/submit", methods=["POST"])
def submit_scan():
    """
    Submit a completed scan job.

    Accepts the same payload as POST /api/jobs but is the canonical
    endpoint for QR-driven submissions.

    Body:
      asset_id, tech_id, completed_at (ISO), overall_notes,
      gps_lat, gps_long,
      service_items: [
        { service_item_id, is_completed, is_inspected, note,
          initial_resistance, final_resistance }
      ]
    """
    try:
        data = request.json or {}

        asset_id_raw = data.get("asset_id")
        if asset_id_raw is None:
            return jsonify({"error": "asset_id is required"}), 400
        try:
            asset_id = int(asset_id_raw)
        except Exception:
            return jsonify({"error": "asset_id must be numeric"}), 400

        tech_id = data.get("tech_id")
        if not tech_id:
            return jsonify({"error": "tech_id is required"}), 400

        asset = db.session.get(Asset, asset_id)
        if not asset:
            return jsonify({"error": "Asset not found"}), 400

        tech = db.session.get(Technician, tech_id)
        if not tech:
            return jsonify({"error": "Technician not found"}), 400

        # Honour client-provided timestamp or fall back to server UTC
        incoming_completed = data.get("completed_at")
        if incoming_completed:
            try:
                dt = isoparse(incoming_completed)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                completed_at_val = dt.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                completed_at_val = datetime.utcnow()
        else:
            completed_at_val = datetime.utcnow()

        job = Job(
            tenant_id=asset.tenant_id,
            asset_id=asset_id,
            tech_id=tech_id,
            overall_notes=data.get("overall_notes"),
            gps_lat=data.get("gps_lat"),
            gps_long=data.get("gps_long"),
            completed_at=completed_at_val,
        )
        db.session.add(job)
        db.session.flush()

        for item_data in data.get("service_items", []):
            si_id = item_data.get("service_item_id")
            si = db.session.get(ServiceItem, si_id)
            if not si:
                db.session.rollback()
                return jsonify({"error": f"Service item not found: {si_id}"}), 400

            jsi = JobServiceItem(
                job_id=job.id,
                service_item_id=si_id,
                is_completed=item_data.get("is_completed", False),
                is_inspected=item_data.get("is_inspected", False),
                note=item_data.get("note", ""),
                initial_resistance=item_data.get("initial_resistance"),
                final_resistance=item_data.get("final_resistance"),
            )
            db.session.add(jsi)

            if jsi.is_completed:
                si.last_service_date = datetime.utcnow().date()

        db.session.commit()
        return jsonify({"message": "Scan job recorded", "job_id": job.id}), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
