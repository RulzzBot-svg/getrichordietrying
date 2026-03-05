from flask import Blueprint, request, jsonify
from models import Technician
from db import db

tech_bp = Blueprint("technicians", __name__)


@tech_bp.route("/technicians", methods=["GET"])
def get_all_tech():
    techs = Technician.query.all()
    return jsonify([
        {"id": t.id, "name": t.name, "active": t.active}
        for t in techs
    ]), 200


@tech_bp.route("/technicians/login", methods=["POST"])
def login_technicians():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        pin = data.get("pin")

        if not name or not pin:
            return jsonify({"error": "Missing name or pin"}), 400

        tech = Technician.query.filter_by(name=name, pin=pin, active=True).first()
        if not tech:
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({
            "id": tech.id,
            "name": tech.name,
            "active": tech.active,
            "role": getattr(tech, "role", "technician"),
            "tenant_id": tech.tenant_id,
        }), 200
    except Exception as e:
        print(f"Error in login_technicians: {e}")
        return jsonify({"error": "Internal server error"}), 500


@tech_bp.route("/technicians/<int:tech_id>", methods=["GET"])
def get_technician(tech_id):
    tech = db.session.get(Technician, tech_id)
    if not tech:
        return jsonify({"error": "Technician not found"}), 404
    return jsonify({"id": tech.id, "name": tech.name, "active": tech.active, "tenant_id": tech.tenant_id}), 200
