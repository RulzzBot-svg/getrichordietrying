"""
Tenant management routes.

Provides CRUD for Tenant records (white-label client organisations).
Each tenant can configure their own:
 - brand_color  (hex string)
 - logo_url
 - terminology  (JSON dict mapping generic terms to industry-specific ones)
 - industry     (e.g. "hvac", "plumbing", "fire-safety", "general")

Terminology dict example:
    {
        "location_name": "Hospital",
        "asset_name": "AHU",
        "service_item_name": "Filter",
        "service_action": "Replace"
    }
"""
import traceback
from flask import Blueprint, jsonify, request
from models import Tenant
from db import db
from middleware.auth import require_admin

tenant_bp = Blueprint("tenants", __name__)

# ------------------------------------
# Industry terminology presets
# ------------------------------------
INDUSTRY_PRESETS = {
    "hvac": {
        "location_name": "Hospital",
        "asset_name": "AHU",
        "service_item_name": "Filter",
        "service_action": "Replace",
        "location_plural": "Hospitals",
        "asset_plural": "AHUs",
        "service_item_plural": "Filters",
    },
    "plumbing": {
        "location_name": "Property",
        "asset_name": "Fixture",
        "service_item_name": "Component",
        "service_action": "Service",
        "location_plural": "Properties",
        "asset_plural": "Fixtures",
        "service_item_plural": "Components",
    },
    "fire-safety": {
        "location_name": "Building",
        "asset_name": "Extinguisher",
        "service_item_name": "Inspection Item",
        "service_action": "Inspect",
        "location_plural": "Buildings",
        "asset_plural": "Extinguishers",
        "service_item_plural": "Inspection Items",
    },
    "property-management": {
        "location_name": "Office Park",
        "asset_name": "Unit",
        "service_item_name": "Task",
        "service_action": "Complete",
        "location_plural": "Office Parks",
        "asset_plural": "Units",
        "service_item_plural": "Tasks",
    },
    "general": {
        "location_name": "Location",
        "asset_name": "Asset",
        "service_item_name": "Service Item",
        "service_action": "Service",
        "location_plural": "Locations",
        "asset_plural": "Assets",
        "service_item_plural": "Service Items",
    },
}


def get_preset_terminology(industry: str) -> dict:
    return INDUSTRY_PRESETS.get(industry, INDUSTRY_PRESETS["general"]).copy()


# ------------------------------------
# GET /api/tenants/presets
# ------------------------------------
@tenant_bp.route("/tenants/presets", methods=["GET"])
def list_presets():
    """Return available industry presets."""
    return jsonify(INDUSTRY_PRESETS), 200


# ------------------------------------
# GET /api/tenants
# ------------------------------------
@tenant_bp.route("/tenants", methods=["GET"])
@require_admin
def list_tenants():
    """List all tenants."""
    try:
        tenants = Tenant.query.order_by(Tenant.name).all()
        return jsonify([_tenant_to_dict(t) for t in tenants]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ------------------------------------
# POST /api/tenants
# ------------------------------------
@tenant_bp.route("/tenants", methods=["POST"])
@require_admin
def create_tenant():
    """Create a new tenant."""
    try:
        data = request.json or {}
        name = data.get("name")
        slug = data.get("slug")
        industry = data.get("industry", "general")

        if not name or not slug:
            return jsonify({"error": "name and slug are required"}), 400

        if Tenant.query.filter_by(slug=slug).first():
            return jsonify({"error": f"Slug '{slug}' already in use"}), 409

        # Start with industry preset and allow override
        base_terminology = get_preset_terminology(industry)
        custom_terminology = data.get("terminology", {})
        merged_terminology = {**base_terminology, **custom_terminology}

        t = Tenant(
            name=name,
            slug=slug,
            industry=industry,
            brand_color=data.get("brand_color", "#0ea5e9"),
            logo_url=data.get("logo_url"),
            terminology=merged_terminology,
            active=True,
        )
        db.session.add(t)
        db.session.commit()
        return jsonify(_tenant_to_dict(t)), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ------------------------------------
# GET /api/tenants/<slug_or_id>
# ------------------------------------
@tenant_bp.route("/tenants/<slug_or_id>", methods=["GET"])
def get_tenant(slug_or_id):
    """
    Get a single tenant by slug (string) or numeric id.
    This endpoint is public so the frontend can load branding/terminology
    before the user is authenticated.
    """
    try:
        t = _resolve_tenant(slug_or_id)
        if not t:
            return jsonify({"error": "Tenant not found"}), 404
        return jsonify(_tenant_to_dict(t)), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ------------------------------------
# PUT /api/tenants/<slug_or_id>
# ------------------------------------
@tenant_bp.route("/tenants/<slug_or_id>", methods=["PUT"])
@require_admin
def update_tenant(slug_or_id):
    """Update tenant branding / terminology."""
    try:
        t = _resolve_tenant(slug_or_id)
        if not t:
            return jsonify({"error": "Tenant not found"}), 404

        data = request.json or {}

        if "name" in data:
            t.name = data["name"]
        if "industry" in data:
            t.industry = data["industry"]
        if "brand_color" in data:
            t.brand_color = data["brand_color"]
        if "logo_url" in data:
            t.logo_url = data["logo_url"]
        if "active" in data:
            t.active = bool(data["active"])
        if "terminology" in data:
            existing = t.terminology or {}
            existing.update(data["terminology"])
            t.terminology = existing

        db.session.commit()
        return jsonify(_tenant_to_dict(t)), 200

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ------------------------------------
# Helpers
# ------------------------------------
def _resolve_tenant(slug_or_id) -> Tenant | None:
    try:
        return db.session.get(Tenant, int(slug_or_id))
    except (ValueError, TypeError):
        return Tenant.query.filter_by(slug=str(slug_or_id)).first()


def _tenant_to_dict(t: Tenant) -> dict:
    terminology = t.terminology or {}
    if not terminology:
        terminology = get_preset_terminology(t.industry or "general")
    return {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "industry": t.industry,
        "brand_color": t.brand_color,
        "logo_url": t.logo_url,
        "terminology": terminology,
        "active": t.active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
