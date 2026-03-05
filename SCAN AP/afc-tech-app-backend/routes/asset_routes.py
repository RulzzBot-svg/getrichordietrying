"""
Asset routes — generic, tenant-scoped replacement for ahu_routes.py.

API surface:
  GET  /api/assets                              – list all assets for a tenant
  GET  /api/assets/<id>                         – get asset by id (QR scan target)
  POST /api/assets                              – create asset (admin)
  GET  /api/assets/<id>/service-items           – list service items (admin)
  POST /api/assets/<id>/service-items           – add service item (admin)
  PATCH /api/assets/service-items/<id>/deactivate  – soft-delete service item
  PUT  /api/assets/service-items/<id>           – update service item
  DELETE /api/assets/service-items/<id>         – hard-delete service item
"""
import traceback
from flask import Blueprint, jsonify, request
from models import Asset, ServiceItem, Technician
from db import db
from middleware.auth import require_admin
from sqlalchemy.orm import joinedload, selectinload
from utility.status import compute_filter_status as compute_service_item_status

asset_bp = Blueprint("assets", __name__)


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------
def _require_tenant_id():
    raw = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id")
    if not raw:
        return None, (jsonify({"error": "X-Tenant-ID header or tenant_id query param required"}), 400)
    try:
        return int(raw), None
    except ValueError:
        return None, (jsonify({"error": "tenant_id must be numeric"}), 400)


def safe_service_item_status(si):
    try:
        st = compute_service_item_status(si) or {}
    except Exception:
        traceback.print_exc()
        st = {}
    return {
        "status": st.get("status"),
        "next_due_date": st.get("next_due_date"),
        "days_until_due": st.get("days_until_due"),
        "days_overdue": st.get("days_overdue"),
    }


def compute_asset_status(service_items):
    if not service_items:
        return {"status": "Pending", "next_due_date": None, "days_until_due": None, "days_overdue": None}

    next_dues, days_until_list, overdue_days = [], [], []
    for si in service_items:
        st = safe_service_item_status(si)
        if st["next_due_date"]:
            next_dues.append(st["next_due_date"])
        if st["days_until_due"] is not None:
            days_until_list.append(st["days_until_due"])
        if st["days_overdue"]:
            overdue_days.append(st["days_overdue"])

    if not next_dues:
        return {"status": "Pending", "next_due_date": None, "days_until_due": None, "days_overdue": None}

    if overdue_days:
        return {"status": "Overdue", "next_due_date": min(next_dues),
                "days_until_due": 0, "days_overdue": max(overdue_days)}
    if any(d <= 7 for d in days_until_list):
        return {"status": "Due Soon", "next_due_date": min(next_dues),
                "days_until_due": min(days_until_list) if days_until_list else None, "days_overdue": 0}
    return {"status": "Completed", "next_due_date": min(next_dues),
            "days_until_due": min(days_until_list) if days_until_list else None, "days_overdue": 0}


# ---------------------------------------------------
# GET /api/assets  (list, tenant-scoped)
# ---------------------------------------------------
@asset_bp.route("/assets", methods=["GET"])
def get_all_assets():
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        assets = (
            db.session.query(Asset)
            .filter(Asset.tenant_id == tenant_id)
            .options(joinedload(Asset.location), joinedload(Asset.building), selectinload(Asset.service_items))
            .order_by(Asset.location_id.asc(), Asset.excel_order.asc(), Asset.id.asc())
            .all()
        )
        payload = []
        for a in assets:
            active_items = [si for si in a.service_items if getattr(si, "is_active", True)]
            status_data = compute_asset_status(active_items)
            overdue_count = sum(1 for si in active_items if safe_service_item_status(si).get("status") == "Overdue")
            due_soon_count = sum(1 for si in active_items if safe_service_item_status(si).get("status") == "Due Soon")
            last_serviced_dates = [si.last_service_date for si in active_items if si.last_service_date]

            payload.append({
                "id": a.id,
                "tenant_id": a.tenant_id,
                "location_id": a.location_id,
                "location": a.location.name if a.location else None,
                "name": a.name,
                "asset_type": a.asset_type,
                "location_label": a.location_label,
                "notes": a.notes,
                "overdue_count": overdue_count,
                "due_soon_count": due_soon_count,
                "last_serviced": max(last_serviced_dates).isoformat() if last_serviced_dates else None,
                "status": status_data["status"],
                "next_due_date": status_data["next_due_date"],
                "days_until_due": status_data["days_until_due"],
                "days_overdue": status_data["days_overdue"],
                "service_items_count": len(active_items),
                "building_id": a.building_id,
                "building": a.building.name if a.building else None,
            })
        return jsonify(payload), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# GET /api/assets/<asset_id>  (QR scan lookup — public within tenant)
# ---------------------------------------------------
@asset_bp.route("/assets/<string:asset_id>", methods=["GET"])
def get_asset_by_id(asset_id):
    try:
        asset_obj = None
        try:
            aid = int(asset_id)
            asset_obj = db.session.get(Asset, aid)
        except Exception:
            asset_obj = Asset.query.filter_by(name=asset_id).first()

        if not asset_obj:
            return jsonify({"error": "Asset not found"}), 404

        active_items = (
            db.session.query(ServiceItem)
            .filter(ServiceItem.asset_id == asset_obj.id, ServiceItem.is_active.is_(True))
            .order_by(ServiceItem.excel_order.asc(), ServiceItem.id.asc())
            .all()
        )

        items_payload = []
        for si in active_items:
            st = safe_service_item_status(si)
            items_payload.append({
                "id": si.id,
                "phase": si.phase,
                "part_number": si.part_number,
                "size": si.size,
                "quantity": si.quantity,
                "frequency_days": si.frequency_days,
                "last_service_date": si.last_service_date.isoformat() if si.last_service_date else None,
                **{k: v for k, v in st.items() if v is not None},
            })

        asset_status = compute_asset_status(active_items)

        return jsonify({
            "asset_id": asset_obj.id,
            "tenant_id": asset_obj.tenant_id,
            "location_id": asset_obj.location_id,
            "location_name": asset_obj.location.name if asset_obj.location else None,
            "name": asset_obj.name,
            "asset_type": asset_obj.asset_type,
            "location_label": asset_obj.location_label,
            "notes": asset_obj.notes,
            **asset_status,
            "service_items": items_payload,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# POST /api/assets  (admin: create)
# ---------------------------------------------------
@asset_bp.route("/assets", methods=["POST"])
@require_admin
def create_asset():
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        data = request.json or {}
        location_id = data.get("location_id")
        if not location_id:
            return jsonify({"error": "location_id is required"}), 400

        a = Asset(
            tenant_id=tenant_id,
            location_id=int(location_id),
            building_id=data.get("building_id"),
            name=data.get("name") or f"Asset-{tenant_id}",
            asset_type=data.get("asset_type"),
            location_label=data.get("location_label"),
            notes=data.get("notes"),
            excel_order=data.get("excel_order"),
        )
        db.session.add(a)
        db.session.commit()
        return jsonify({
            "id": a.id,
            "tenant_id": a.tenant_id,
            "location_id": a.location_id,
            "name": a.name,
            "asset_type": a.asset_type,
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# GET /api/assets/<asset_id>/service-items  (admin)
# ---------------------------------------------------
@asset_bp.route("/assets/<int:asset_id>/service-items", methods=["GET"])
@require_admin
def get_service_items(asset_id):
    try:
        items = (
            db.session.query(ServiceItem)
            .filter(ServiceItem.asset_id == asset_id)
            .order_by(ServiceItem.excel_order.asc(), ServiceItem.id.asc())
            .all()
        )
        return jsonify([
            {
                "id": si.id,
                "phase": si.phase,
                "part_number": si.part_number,
                "size": si.size,
                "quantity": si.quantity,
                "frequency_days": si.frequency_days,
                "last_service_date": si.last_service_date.isoformat() if si.last_service_date else None,
                "is_active": si.is_active,
            }
            for si in items
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# POST /api/assets/<asset_id>/service-items  (admin)
# ---------------------------------------------------
@asset_bp.route("/assets/<int:asset_id>/service-items", methods=["POST"])
@require_admin
def add_service_item(asset_id):
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        data = request.json or {}
        si = ServiceItem(
            tenant_id=tenant_id,
            asset_id=asset_id,
            phase=data.get("phase", ""),
            part_number=data.get("part_number", ""),
            size=data.get("size", ""),
            quantity=int(data.get("quantity", 1)),
            frequency_days=int(data.get("frequency_days", 90)),
            is_active=True,
        )
        db.session.add(si)
        db.session.commit()
        return jsonify({"message": "Service item added", "id": si.id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# PATCH /api/assets/service-items/<id>/deactivate  (admin)
# ---------------------------------------------------
@asset_bp.route("/assets/service-items/<int:item_id>/deactivate", methods=["PATCH"])
@require_admin
def deactivate_service_item(item_id):
    try:
        si = db.session.get(ServiceItem, item_id)
        if not si:
            return jsonify({"error": "Service item not found"}), 404
        si.is_active = False
        db.session.commit()
        return jsonify({"message": "Deactivated", "id": si.id}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# PUT /api/assets/service-items/<id>  (admin)
# ---------------------------------------------------
@asset_bp.route("/assets/service-items/<int:item_id>", methods=["PUT"])
@require_admin
def update_service_item(item_id):
    try:
        si = db.session.get(ServiceItem, item_id)
        if not si:
            return jsonify({"error": "Service item not found"}), 404
        data = request.json or {}
        si.phase = data.get("phase", si.phase)
        si.part_number = data.get("part_number", si.part_number)
        si.size = data.get("size", si.size)
        si.quantity = int(data.get("quantity", si.quantity))
        si.frequency_days = int(data.get("frequency_days", si.frequency_days))
        db.session.commit()
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# DELETE /api/assets/service-items/<id>  (admin)
# ---------------------------------------------------
@asset_bp.route("/assets/service-items/<int:item_id>", methods=["DELETE"])
@require_admin
def delete_service_item(item_id):
    try:
        si = db.session.get(ServiceItem, item_id)
        if not si:
            return jsonify({"error": "Service item not found"}), 404
        db.session.delete(si)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
