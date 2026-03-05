from flask import Blueprint, jsonify, request
from models import Location as Hospital, Asset as AHU, Job, Technician, SupervisorSignoff, Notification
from db import db
from sqlalchemy.orm import joinedload
from datetime import datetime
from middleware.auth import require_admin
import subprocess
import time
import os
import platform
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/supervisor-signoff", methods=["POST"])
@require_admin
def create_supervisor_signoff():
    try:
        data = request.get_json()
        hospital_id = data.get("hospital_id")
        date_str = data.get("date")
        supervisor_name = data.get("supervisor_name")
        summary = data.get("summary")
        signature_data = data.get("signature_data")
        job_ids = data.get("job_ids")

        if not (hospital_id and date_str and supervisor_name and signature_data and job_ids):
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
            location_id=hospital_id,
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
        hospital_id = request.args.get("hospital_id")
        date_str = request.args.get("date")
        query = SupervisorSignoff.query
        if hospital_id:
            query = query.filter_by(location_id=hospital_id)
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
                "hospital_id": s.location_id,
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


@admin_bp.route("/hospitals", methods=["GET"])
@require_admin
def get_hospitals():
    try:
        hospitals = Hospital.query.all()
        return jsonify([
            {"id": h.id, "name": h.name, "active": getattr(h, "active", True)}
            for h in hospitals
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/overview", methods=["GET"])
@require_admin
def admin_overview():
    hospitals = Hospital.query.all()
    return jsonify({
        "hospitals": len(hospitals),
        "total_ahus": 0,
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
                "hospital_id": n.location_id,
                "hospital_name": n.location.name if n.location else None,
                "ahu_id": n.asset_id,
                "ahu_name": n.asset.name if n.asset else None,
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
            "ahu_id": job.asset_id,
            "ahu_name": job.asset.name if job.asset else "Unknown",
            "technician": job.technician.name if job.technician else "Unknown",
            "completed_at": job.completed_at.isoformat() + "Z",
            "overall_notes": job.overall_notes,
            "gps_lat": job.gps_lat,
            "gps_long": job.gps_long,
            "filters": [
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


@admin_bp.route("/ahu", methods=["POST"])
@require_admin
def create_ahu():
    try:
        data = request.get_json()
        hospital_id = data.get("hospital_id")
        ahu_name_input = data.get("ahu_name")
        location = data.get("location")
        notes = data.get("notes")

        if not hospital_id:
            return jsonify({"error": "Missing hospital_id"}), 400

        hospital = Hospital.query.get(hospital_id)
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        note_bits = []
        if ahu_name_input:
            note_bits.append(f"Manual label: {ahu_name_input}")
        if notes:
            note_bits.append(str(notes))
        final_notes = " | ".join(note_bits) if note_bits else None

        new_ahu = AHU(
            tenant_id=hospital.tenant_id,
            location_id=hospital_id,
            name=ahu_name_input or None,
            location_label=location,
            notes=final_notes,
        )
        db.session.add(new_ahu)
        db.session.commit()

        if not new_ahu.name:
            new_ahu.name = f"AHU-{new_ahu.id:03d}"
        if hasattr(new_ahu, "excel_order") and not new_ahu.excel_order:
            new_ahu.excel_order = int(new_ahu.id)
        db.session.commit()

        return jsonify({
            "id": new_ahu.id,
            "hospital_id": new_ahu.location_id,
            "name": new_ahu.name,
            "location": new_ahu.location_label,
            "notes": new_ahu.notes,
            "excel_order": new_ahu.excel_order,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/launch-qb-macro", methods=["POST"])
@require_admin
def launch_qb_macro():
    try:
        if platform.system() != "Windows":
            return jsonify({
                "error": "QB macros only work on Windows systems",
                "current_system": platform.system(),
                "tip": "Run QB operations on your local Windows machine.",
            }), 400

        data = request.get_json() or {}
        action = data.get("action")
        delete_old = data.get("delete_old", False)

        if not action:
            return jsonify({"error": "Missing 'action' parameter"}), 400

        if action not in ["generate_packing_slip"]:
            return jsonify({"error": f"Invalid action: {action}"}), 400

        macro_dir = Path(__file__).parent.parent

        if delete_old:
            qb_delete_script = macro_dir / "qb_sections.au3"
            if not qb_delete_script.exists():
                return jsonify({"error": "qb_sections.au3 not found"}), 404
            subprocess.Popen(str(qb_delete_script))
            time.sleep(2.5)

        special_paste_exe = macro_dir / "SpecialPaste.exe"
        if not special_paste_exe.exists():
            return jsonify({"error": "SpecialPaste.exe not found"}), 404

        subprocess.Popen(str(special_paste_exe))
        return jsonify({"status": "started", "message": "QB macros launched"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
