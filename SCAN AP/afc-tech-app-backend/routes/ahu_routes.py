"""
Legacy AHU routes — kept for backward compatibility.
New code should use /api/assets/* instead.
"""
import traceback
from flask import Blueprint, jsonify, request
from models import Asset as AHU, ServiceItem as Filter, Technician
from db import db
from middleware.auth import require_admin
from sqlalchemy.orm import joinedload, selectinload
from utility.status import compute_filter_status

ahu_bp = Blueprint("ahu", __name__)


def safe_filter_status(f):
    try:
        st = compute_filter_status(f) or {}
    except Exception:
        traceback.print_exc()
        st = {}
    return {
        "status": st.get("status"),
        "next_due_date": st.get("next_due_date"),
        "days_until_due": st.get("days_until_due"),
        "days_overdue": st.get("days_overdue"),
    }


def compute_ahu_status_from_filters(filters):
    if not filters:
        return {"status": "Pending", "next_due_date": None, "days_until_due": None, "days_overdue": None}
    next_dues, days_until_list, overdue_days = [], [], []
    for f in filters:
        st = safe_filter_status(f)
        if st["next_due_date"]:
            next_dues.append(st["next_due_date"])
        if st["days_until_due"] is not None:
            days_until_list.append(st["days_until_due"])
        if st["days_overdue"]:
            overdue_days.append(st["days_overdue"])
    if not next_dues:
        return {"status": "Pending", "next_due_date": None, "days_until_due": None, "days_overdue": None}
    if overdue_days:
        return {"status": "Overdue", "next_due_date": min(next_dues), "days_until_due": 0, "days_overdue": max(overdue_days)}
    if any(d <= 7 for d in days_until_list):
        return {"status": "Due Soon", "next_due_date": min(next_dues), "days_until_due": min(days_until_list) if days_until_list else None, "days_overdue": 0}
    return {"status": "Completed", "next_due_date": min(next_dues), "days_until_due": min(days_until_list) if days_until_list else None, "days_overdue": 0}


@ahu_bp.route("/qr/<string:ahu_id>", methods=["GET"])
def get_ahu_by_qr(ahu_id):
    try:
        ahu_obj = None
        try:
            aid = int(ahu_id)
            ahu_obj = db.session.get(AHU, aid)
        except Exception:
            ahu_obj = AHU.query.filter_by(name=ahu_id).first()

        if not ahu_obj:
            return jsonify({"error": "AHU not found"}), 404

        active_filters = (
            db.session.query(Filter)
            .filter(Filter.asset_id == ahu_obj.id, Filter.is_active.is_(True))
            .order_by(Filter.excel_order.asc(), Filter.id.asc())
            .all()
        )

        filters_payload = [
            {
                "id": f.id,
                "phase": f.phase,
                "part_number": f.part_number,
                "size": f.size,
                "quantity": f.quantity,
                "frequency_days": f.frequency_days,
                "last_service_date": f.last_service_date.isoformat() if f.last_service_date else None,
                **{k: v for k, v in safe_filter_status(f).items() if v is not None},
            }
            for f in active_filters
        ]

        ahu_status = compute_ahu_status_from_filters(active_filters)

        return jsonify({
            "ahu_id": ahu_obj.id,
            "hospital_id": ahu_obj.location_id,
            "hospital_name": ahu_obj.location.name if ahu_obj.location else None,
            "name": ahu_obj.name,
            "location": ahu_obj.location_label,
            "notes": ahu_obj.notes,
            **ahu_status,
            "filters": filters_payload,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/debug/ahu-ids", methods=["GET"])
def debug_ahu_ids():
    ahus = db.session.query(AHU.id).order_by(AHU.id.asc()).limit(150).all()
    return jsonify([a[0] for a in ahus]), 200


@ahu_bp.route("/admin/ahus/<string:ahu_id>/filters", methods=["GET"])
@require_admin
def get_filters_for_admin(ahu_id):
    try:
        ahu = None
        try:
            aid = int(ahu_id)
            ahu = db.session.get(AHU, aid)
        except Exception:
            ahu = AHU.query.filter_by(name=ahu_id).first()
        if not ahu:
            return jsonify({"error": "AHU not found"}), 404

        active_only = request.args.get("active_only", "0") == "1"
        q = db.session.query(Filter).filter(Filter.asset_id == ahu.id)
        filters = q.order_by(Filter.excel_order.asc(), Filter.id.asc()).all()
        if active_only:
            filters = [f for f in filters if getattr(f, "is_active", True)]

        return jsonify([
            {
                "id": f.id,
                "phase": f.phase,
                "part_number": f.part_number,
                "size": f.size,
                "quantity": f.quantity,
                "frequency_days": f.frequency_days,
                "last_service_date": f.last_service_date.isoformat() if f.last_service_date else None,
                "is_active": f.is_active,
            }
            for f in filters
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/admin/ahus/<string:ahu_id>/filters", methods=["POST"])
@require_admin
def add_filter(ahu_id):
    try:
        data = request.json or {}
        try:
            aid = int(ahu_id)
        except Exception:
            ahu_obj = AHU.query.filter_by(name=ahu_id).first()
            if not ahu_obj:
                return jsonify({"error": "AHU not found"}), 404
            aid = ahu_obj.id

        f = Filter(
            tenant_id=db.session.get(AHU, aid).tenant_id,
            asset_id=aid,
            phase=data.get("phase", ""),
            part_number=data.get("part_number", ""),
            size=data.get("size", ""),
            quantity=int(data.get("quantity", 1)),
            frequency_days=int(data.get("frequency_days", 90)),
            is_active=True,
        )
        db.session.add(f)
        db.session.commit()
        return jsonify({"message": "Filter added", "id": f.id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/admin/filters/<int:filter_id>/deactivate", methods=["PATCH"])
@require_admin
def deactivate_filter(filter_id):
    try:
        f = db.session.get(Filter, filter_id)
        if not f:
            return jsonify({"error": "Filter not found"}), 404
        f.is_active = False
        db.session.commit()
        return jsonify({"message": "Filter deactivated", "id": f.id}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/admin/filters/<int:filter_id>", methods=["PUT"])
@require_admin
def update_filter(filter_id):
    try:
        f = db.session.get(Filter, filter_id)
        if not f:
            return jsonify({"error": "Filter not found"}), 404
        data = request.json or {}
        f.phase = data.get("phase", f.phase)
        f.part_number = data.get("part_number", f.part_number)
        f.size = data.get("size", f.size)
        f.quantity = int(data.get("quantity", f.quantity))
        f.frequency_days = int(data.get("frequency_days", f.frequency_days))
        db.session.commit()
        return jsonify({"message": "Filter updated"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/admin/filters/<int:filter_id>", methods=["DELETE"])
@require_admin
def delete_filter(filter_id):
    try:
        f = db.session.get(Filter, filter_id)
        if not f:
            return jsonify({"error": "Filter not found"}), 404
        db.session.delete(f)
        db.session.commit()
        return jsonify({"message": "Filter removed"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/ahus", methods=["GET"])
def get_all_ahus():
    try:
        ahus = (
            db.session.query(AHU)
            .options(joinedload(AHU.location), joinedload(AHU.building), selectinload(AHU.service_items))
            .order_by(AHU.location_id.asc(), AHU.excel_order.asc(), AHU.id.asc())
            .all()
        )
        payload = []
        for a in ahus:
            active_filters = [f for f in a.service_items if getattr(f, "is_active", True)]
            status_data = compute_ahu_status_from_filters(active_filters)
            overdue_count = sum(1 for f in active_filters if safe_filter_status(f).get("status") == "Overdue")
            due_soon_count = sum(1 for f in active_filters if safe_filter_status(f).get("status") == "Due Soon")
            last_serviced_dates = [f.last_service_date for f in active_filters if f.last_service_date]

            payload.append({
                "id": a.id,
                "hospital_id": a.location_id,
                "hospital": a.location.name if a.location else None,
                "name": a.name,
                "location": a.location_label,
                "notes": a.notes,
                "overdue_count": overdue_count,
                "due_soon_count": due_soon_count,
                "last_serviced": max(last_serviced_dates).isoformat() if last_serviced_dates else None,
                "status": status_data["status"],
                "next_due_date": status_data["next_due_date"],
                "days_until_due": status_data["days_until_due"],
                "days_overdue": status_data["days_overdue"],
                "filters_count": len(active_filters),
                "building_id": a.building_id,
                "building": a.building.name if a.building else None,
            })
        return jsonify(payload), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@ahu_bp.route("/admin/ahus", methods=["GET"])
@require_admin
def admin_get_all_ahus():
    return get_all_ahus()


@ahu_bp.route("/admin/filters/<int:filter_id>/reactivate", methods=["PATCH"])
@require_admin
def reactivate_filter(filter_id):
    f = db.session.get(Filter, filter_id)
    if not f:
        return jsonify({"error": "Filter not found"}), 404
    f.is_active = True
    db.session.commit()
    return jsonify({"message": "Filter reactivated", "id": f.id}), 200


@ahu_bp.route("/admin/ahus", methods=["POST"])
@require_admin
def admin_create_ahu():
    try:
        data = request.json or {}
        hospital_id = data.get("hospital_id")
        if hospital_id is None:
            return jsonify({"error": "hospital_id is required"}), 400
        try:
            hospital_id = int(hospital_id)
        except Exception:
            return jsonify({"error": "hospital_id must be numeric"}), 400

        # Determine tenant_id from location
        from models import Location
        loc = db.session.get(Location, hospital_id)
        tenant_id = loc.tenant_id if loc else None

        a = AHU(
            tenant_id=tenant_id,
            location_id=hospital_id,
            building_id=data.get("building_id"),
            name=data.get("name") or f"AHU-{hospital_id}",
            location_label=data.get("location"),
            notes=data.get("notes"),
            excel_order=data.get("excel_order"),
        )
        db.session.add(a)
        db.session.commit()

        return jsonify({
            "id": a.id,
            "hospital_id": a.location_id,
            "building_id": a.building_id,
            "name": a.name,
            "location": a.location_label,
            "notes": a.notes,
            "excel_order": a.excel_order,
        }), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
