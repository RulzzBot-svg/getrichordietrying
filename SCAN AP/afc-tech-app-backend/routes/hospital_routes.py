"""
Legacy hospital routes — kept for backward compatibility.
New code should use /api/locations/* instead.

These routes delegate to the Location model (formerly Hospital).
"""
from flask import Blueprint, jsonify
from models import Location as Hospital, Asset as AHU, Building, ServiceItem as Filter
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from db import db
from datetime import date, timedelta

hospital_bp = Blueprint("hospital", __name__)


@hospital_bp.route("/hospitals", methods=["GET"])
def get_hospitals():
    """Get all locations (hospitals). Accessible by all users."""
    hospitals = Hospital.query.all()
    return jsonify([
        {
            "id": h.id,
            "name": h.name,
            "active": getattr(h, "active", True),
        }
        for h in hospitals
    ]), 200


@hospital_bp.route("/hospital/all", methods=["GET"])
def get_all_hospitals():
    hospitals = Hospital.query.all()
    return jsonify([
        {
            "id": h.id,
            "name": h.name,
            "city": h.city,
            "active": h.active,
            "ahu_count": len(h.assets),
        }
        for h in hospitals
    ])


@hospital_bp.route("/hospital/<int:hospital_id>/ahus", methods=["GET"])
def get_ahus_for_hospital(hospital_id):
    ahus = AHU.query.filter_by(location_id=hospital_id).all()

    result = []
    for a in ahus:
        overdue_count = 0
        due_soon_count = 0
        filters_count = 0
        latest_service = None
        next_due_dates = []

        for f in (a.service_items or []):
            filters_count += 1
            last = getattr(f, "last_service_date", None)
            freq = getattr(f, "frequency_days", None)

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
            "building_id": getattr(a, "building_id", None),
            "name": a.name,
            "location": a.location_label,
            "filters_count": filters_count,
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count,
            "last_serviced": latest_service.isoformat() if latest_service else None,
            "next_due_date": next_due_date,
            "status": status,
        })

    return jsonify(result), 200


@hospital_bp.route("/hospital/<int:hospital_id>/buildings", methods=["GET"])
def get_buildings_for_hospital(hospital_id):
    rows = (
        db.session.query(Building, func.count(AHU.id).label("ahu_count"))
        .outerjoin(AHU, AHU.building_id == Building.id)
        .filter(Building.location_id == hospital_id, Building.active.is_(True))
        .group_by(Building.id)
        .all()
    )
    return jsonify([
        {
            "id": b.id,
            "name": b.name,
            "floor_area": b.floor_area,
            "active": b.active,
            "ahu_count": ahu_count,
        }
        for b, ahu_count in rows
    ]), 200


@hospital_bp.route("/hospitals/<int:hospital_id>/offline-bundle", methods=["GET"])
def hospital_offline_bundle(hospital_id):
    hospital = (
        db.session.query(Hospital)
        .filter(Hospital.id == hospital_id)
        .options(
            selectinload(Hospital.assets).selectinload(AHU.service_items)
        )
        .first()
    )

    if not hospital:
        return jsonify({"error": "Hospital not found"}), 404

    payload = {
        "hospital": {
            "id": hospital.id,
            "name": hospital.name,
            "address": hospital.address,
            "city": hospital.city,
            "active": hospital.active,
        },
        "ahus": [],
    }

    for a in hospital.assets:
        payload["ahus"].append({
            "id": a.id,
            "hospital_id": a.location_id,
            "name": a.name,
            "location": a.location_label,
            "notes": a.notes,
            "filters": [
                {
                    "id": f.id,
                    "ahu_id": f.asset_id,
                    "phase": f.phase,
                    "part_number": f.part_number,
                    "size": f.size,
                    "quantity": f.quantity,
                    "frequency_days": f.frequency_days,
                    "last_service_date": (
                        f.last_service_date.isoformat()
                        if f.last_service_date else None
                    ),
                }
                for f in (a.service_items or [])
            ],
        })

    return jsonify(payload), 200
