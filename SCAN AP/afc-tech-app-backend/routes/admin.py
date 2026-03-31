from flask import Blueprint, jsonify, request
from models import Location, Asset, Job, Technician, SupervisorSignoff, Notification
from db import db
from sqlalchemy.orm import joinedload
from datetime import datetime
from middleware.auth import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/supervisor-signoff", methods=["POST"])
@require_admin
def create_supervisor_signoff():
    try:
        data = request.get_json()
        location_id = data.get("location_id") or data.get("hospital_id")
        date_str = data.get("date")
        supervisor_name = data.get("supervisor_name")
        summary = data.get("summary")
        signature_data = data.get("signature_data")
        job_ids = data.get("job_ids")

        if not (location_id and date_str and supervisor_name and signature_data and job_ids):
            return jsonify({"error": "Missing required fields"}), 400

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"error": "Invalid date format, should be YYYY-MM-DD"}), 400

        if isinstance(job_ids, list):
            job_ids_str = ",".join(str(j) for j in job_ids)
        else:
            job_ids_str = str(job_ids)

        new_signoff = SupervisorSignoff(
            location_id=location_id,
            date=date,
            supervisor_name=supervisor_name,
            summary=summary,
            signature_data=signature_data,
            job_ids=job_ids_str,
        )
        db.session.add(new_signoff)
        db.session.commit()
        return jsonify({"id": new_signoff.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/supervisor-signoff", methods=["GET"])
@require_admin
def get_supervisor_signoffs():
    try:
        location_id = request.args.get("location_id") or request.args.get("hospital_id")
        date_str = request.args.get("date")
        query = SupervisorSignoff.query
        if location_id:
            query = query.filter_by(location_id=location_id)
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter_by(date=date)
            except Exception:
                return jsonify({"error": "Invalid date format"}), 400
        signoffs = query.order_by(SupervisorSignoff.date.desc()).all()
        result = [
            {
                "id": s.id,
                "location_id": s.location_id,
                "date": s.date.isoformat(),
                "supervisor_name": s.supervisor_name,
                "summary": s.summary,
                "signature_data": s.signature_data,
                "job_ids": s.job_ids,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signoffs
        ]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/locations", methods=["GET"])
@require_admin
def get_locations():
    try:
        locations = Location.query.all()
        return jsonify([
            {"id": h.id, "name": h.name, "active": getattr(h, "active", True)}
            for h in locations
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/overview", methods=["GET"])
@require_admin
def admin_overview():
    locations = Location.query.all()
    return jsonify({
        "locations": len(locations),
        "total_assets": 0,
        "overdue": 0,
        "due_soon": 0,
        "completed": 0,
        "pending": 0,
    }), 200


@admin_bp.route("/notifications", methods=["GET"])
@require_admin
def list_notifications():
    try:
        notifs = Notification.query.order_by(Notification.created_at.desc()).all()
        result = [
            {
                "id": n.id,
                "location_id": n.location_id,
                "location_name": n.location.name if n.location else None,
                "asset_id": n.asset_id,
                "asset_name": n.asset.name if n.asset else None,
                "job_id": n.job_id,
                "technician_id": n.technician_id,
                "technician_name": n.technician.name if n.technician else None,
                "comment_text": n.comment_text,
                "status": n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "resolved_at": n.resolved_at.isoformat() if n.resolved_at else None,
                "resolved_by": n.resolved_by,
            }
            for n in notifs
        ]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/notifications/<int:notif_id>/status", methods=["POST"])
@require_admin
def update_notification_status(notif_id):
    try:
        data = request.get_json() or {}
        status = data.get("status")
        resolved_by = data.get("resolved_by")

        notif = Notification.query.get(notif_id)
        if not notif:
            return jsonify({"error": "Notification not found"}), 404

        if status == "completed":
            notif.status = "completed"
            notif.resolved_at = datetime.utcnow()
            notif.resolved_by = resolved_by
        else:
            notif.status = "pending"
            notif.resolved_at = None
            notif.resolved_by = None

        db.session.commit()
        return jsonify({"message": "Notification updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/jobs", methods=["GET"])
@require_admin
def get_all_jobs():
    from models import JobServiceItem
    jobs = db.session.query(Job).options(
        joinedload(Job.technician),
        joinedload(Job.asset),
        joinedload(Job.job_service_items).joinedload(JobServiceItem.service_item),
    ).all()

    result = [
        {
            "id": job.id,
            "asset_id": job.asset_id,
            "asset_name": job.asset.name if job.asset else "Unknown",
            "technician": job.technician.name if job.technician else "Unknown",
            "completed_at": job.completed_at.isoformat() + "Z",
            "overall_notes": job.overall_notes,
            "gps_lat": job.gps_lat,
            "gps_long": job.gps_long,
            "service_items": [
                {
                    "phase": jf.service_item.phase,
                    "part_number": jf.service_item.part_number,
                    "size": jf.service_item.size,
                    "is_completed": jf.is_completed,
                    "is_inspected": jf.is_inspected,
                    "note": jf.note,
                }
                for jf in job.job_service_items
            ],
        }
        for job in jobs
    ]
    return jsonify(result), 200


@admin_bp.route("/assets", methods=["POST"])
@require_admin
def create_asset():
    try:
        data = request.get_json()
        location_id = data.get("location_id") or data.get("hospital_id")
        asset_name_input = data.get("asset_name") or data.get("ahu_name")
        location_label = data.get("location")
        notes = data.get("notes")

        if not location_id:
            return jsonify({"error": "Missing location_id"}), 400

        location = Location.query.get(location_id)
        if not location:
            return jsonify({"error": "Location not found"}), 404

        note_bits = []
        if asset_name_input:
            note_bits.append(f"Manual label: {asset_name_input}")
        if notes:
            note_bits.append(str(notes))
        final_notes = " | ".join(note_bits) if note_bits else None

        new_asset = Asset(
            tenant_id=location.tenant_id,
            location_id=location_id,
            name=asset_name_input or None,
            location_label=location_label,
            notes=final_notes,
        )
        db.session.add(new_asset)
        db.session.commit()

        if not new_asset.name:
            new_asset.name = f"Asset-{new_asset.id:03d}"
        if hasattr(new_asset, "excel_order") and not new_asset.excel_order:
            new_asset.excel_order = int(new_asset.id)
        db.session.commit()

        return jsonify({
            "id": new_asset.id,
            "location_id": new_asset.location_id,
            "name": new_asset.name,
            "location": new_asset.location_label,
            "notes": new_asset.notes,
            "excel_order": new_asset.excel_order,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
