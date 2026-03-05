"""
Authentication and authorization middleware for Flask routes.
"""
from flask import request, jsonify
from functools import wraps
from models import Technician
from db import db


def require_admin(f):
    """
    Decorator to require admin role for a route.

    Checks for tech_id in:
    1. X-Tech-ID request header
    2. tech_id query parameter

    Returns:
        401: If no tech_id provided or technician not found
        403: If technician exists but doesn't have admin role

    Usage:
        @admin_bp.route("/some-admin-route")
        @require_admin
        def my_admin_route():
            # This code only runs if user is an admin
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tech_id = request.headers.get("X-Tech-ID") or request.args.get("tech_id")

        if not tech_id:
            return jsonify({"error": "Authentication required"}), 401

        try:
            tech = db.session.get(Technician, int(tech_id))
            if not tech:
                return jsonify({"error": "Invalid technician"}), 401

            if getattr(tech, "role", "technician") != "admin":
                return jsonify({"error": "Admin access required"}), 403

        except ValueError:
            return jsonify({"error": "Invalid tech_id format"}), 400
        except Exception:
            return jsonify({"error": "Authentication failed"}), 401

        return f(*args, **kwargs)
    return decorated_function
