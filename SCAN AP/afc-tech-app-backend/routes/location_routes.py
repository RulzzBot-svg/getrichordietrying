"""
Location routes — generic, tenant-scoped replacement for hospital_routes.py.

All endpoints filter by tenant_id so data from one client is never
visible to another.

API surface:
  GET  /api/locations                       – list locations for a tenant
  GET  /api/locations/<id>                  – single location detail
  POST /api/locations                       – create location
  GET  /api/locations/<id>/assets           – list assets at a location
  GET  /api/locations/<id>/buildings        – list buildings at a location
  GET  /api/locations/<id>/offline-bundle   – full offline data bundle
"""
import traceback
from flask import Blueprint, jsonify, request
from models import Location, Asset, Building, ServiceItem
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from db import db
from datetime import date, timedelta
from middleware.auth import require_admin

location_bp = Blueprint("locations", __name__)


def _require_tenant_id():
    """Extract tenant_id from header or query param. Returns (tenant_id, error_response)."""
    raw = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id")
    if not raw:
        return None, (jsonify({"error": "X-Tenant-ID header or tenant_id query param required"}), 400)
    try:
        return int(raw), None
    except ValueError:
        return None, (jsonify({"error": "tenant_id must be numeric"}), 400)


# --------------------------------------------------
# GET /api/locations
# --------------------------------------------------
@location_bp.route("/locations", methods=["GET"])
def get_locations():
    """List all locations for a tenant."""
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        locations = Location.query.filter_by(tenant_id=tenant_id, active=True).all()
        return jsonify([
            {
                "id": loc.id,
                "name": loc.name,
                "address": loc.address,
                "city": loc.city,
                "active": loc.active,
                "asset_count": len(loc.assets),
            }
            for loc in locations
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# GET /api/locations/<location_id>
# --------------------------------------------------
@location_bp.route("/locations/<int:location_id>", methods=["GET"])
def get_location(location_id):
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        loc = Location.query.filter_by(id=location_id, tenant_id=tenant_id).first()
        if not loc:
            return jsonify({"error": "Location not found"}), 404
        return jsonify({
            "id": loc.id,
            "name": loc.name,
            "address": loc.address,
            "city": loc.city,
            "active": loc.active,
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# POST /api/locations
# --------------------------------------------------
@location_bp.route("/locations", methods=["POST"])
@require_admin
def create_location():
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        data = request.json or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        loc = Location(
            tenant_id=tenant_id,
            name=name,
            address=data.get("address"),
            city=data.get("city"),
            active=True,
        )
        db.session.add(loc)
        db.session.commit()
        return jsonify({"id": loc.id, "name": loc.name}), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# GET /api/locations/<location_id>/assets
# --------------------------------------------------
@location_bp.route("/locations/<int:location_id>/assets", methods=["GET"])
def get_assets_for_location(location_id):
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        assets = (
            Asset.query
            .filter_by(location_id=location_id, tenant_id=tenant_id)
            .all()
        )
        result = []
        for a in assets:
            overdue_count = 0
            due_soon_count = 0
            filters_count = 0
            latest_service = None
            next_due_dates = []

            for si in (a.service_items or []):
                filters_count += 1
                last = getattr(si, "last_service_date", None)
                freq = getattr(si, "frequency_days", None)
                if last and (latest_service is None or last > latest_service):
                    latest_service = last
                if last and freq:
                    try:
                        next_due = last + timedelta(days=int(freq))
                        next_due_dates.append(next_due)
                        delta = (next_due - date.today()).days
                        if delta < 0:
                            overdue_count += 1
                        elif delta <= 7:
                            due_soon_count += 1
                    except Exception:
                        pass

            if overdue_count > 0:
                status = "Overdue"
            elif due_soon_count > 0:
                status = "Due Soon"
            elif filters_count > 0:
                status = "Completed"
            else:
                status = "Pending"

            next_due_date = min(next_due_dates).isoformat() if next_due_dates else None

            result.append({
                "id": a.id,
                "building_id": a.building_id,
                "name": a.name,
                "asset_type": a.asset_type,
                "location_label": a.location_label,
                "service_items_count": filters_count,
                "overdue_count": overdue_count,
                "due_soon_count": due_soon_count,
                "last_serviced": latest_service.isoformat() if latest_service else None,
                "next_due_date": next_due_date,
                "status": status,
            })
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# GET /api/locations/<location_id>/buildings
# --------------------------------------------------
@location_bp.route("/locations/<int:location_id>/buildings", methods=["GET"])
def get_buildings_for_location(location_id):
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        rows = (
            db.session.query(Building, func.count(Asset.id).label("asset_count"))
            .outerjoin(Asset, Asset.building_id == Building.id)
            .filter(
                Building.location_id == location_id,
                Building.tenant_id == tenant_id,
                Building.active.is_(True),
            )
            .group_by(Building.id)
            .all()
        )
        return jsonify([
            {
                "id": b.id,
                "name": b.name,
                "floor_area": b.floor_area,
                "active": b.active,
                "asset_count": asset_count,
            }
            for b, asset_count in rows
        ]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# GET /api/locations/<location_id>/offline-bundle
# --------------------------------------------------
@location_bp.route("/locations/<int:location_id>/offline-bundle", methods=["GET"])
def location_offline_bundle(location_id):
    tenant_id, err = _require_tenant_id()
    if err:
        return err
    try:
        loc = (
            db.session.query(Location)
            .filter(Location.id == location_id, Location.tenant_id == tenant_id)
            .options(
                selectinload(Location.assets).selectinload(Asset.service_items)
            )
            .first()
        )
        if not loc:
            return jsonify({"error": "Location not found"}), 404

        payload = {
            "location": {
                "id": loc.id,
                "name": loc.name,
                "address": loc.address,
                "city": loc.city,
                "active": loc.active,
            },
            "assets": [],
        }

        for a in loc.assets:
            payload["assets"].append({
                "id": a.id,
                "location_id": a.location_id,
                "name": a.name,
                "asset_type": a.asset_type,
                "location_label": a.location_label,
                "notes": a.notes,
                "service_items": [
                    {
                        "id": si.id,
                        "asset_id": si.asset_id,
                        "phase": si.phase,
                        "part_number": si.part_number,
                        "size": si.size,
                        "quantity": si.quantity,
                        "frequency_days": si.frequency_days,
                        "last_service_date": (
                            si.last_service_date.isoformat()
                            if si.last_service_date else None
                        ),
                    }
                    for si in (a.service_items or [])
                ],
            })

        return jsonify(payload), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
