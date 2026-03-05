from flask import Flask
from db import db
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Legacy HVAC-specific blueprints (kept for backward compatibility)
from routes.hospital_routes import hospital_bp
from routes.ahu_routes import ahu_bp
from routes.tech_routes import tech_bp
from routes.job_routes import job_bp
from routes.admin import admin_bp
from routes.signature import signature_bp

# New generic / white-label blueprints
from routes.tenant_routes import tenant_bp
from routes.location_routes import location_bp
from routes.asset_routes import asset_bp
from routes.scan_routes import scan_bp

load_dotenv()


def create_app():
    app = Flask(__name__)

    # -----------------------------
    # DATABASE CONFIG
    # -----------------------------
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Check .env")

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Allow CORS for API routes from our frontends and localhost (for dev).
    # In production, restrict origins to your deployed frontend domains.
    CORS(app, resources={r"/api/*": {"origins": [
        "https://qrscan-lyart.vercel.app",
        "https://qrscan-8ql2.onrender.com",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://192.168.1.131:5173"
    ]}}, supports_credentials=True)

    db.init_app(app)

    # -----------------------------------------
    # Register legacy HVAC blueprints (backward compat)
    # -----------------------------------------
    app.register_blueprint(ahu_bp, url_prefix="/api")
    app.register_blueprint(job_bp, url_prefix="/api")
    app.register_blueprint(tech_bp, url_prefix="/api")
    app.register_blueprint(hospital_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(signature_bp, url_prefix="/api")

    # -----------------------------------------
    # Register generic white-label blueprints
    # -----------------------------------------
    app.register_blueprint(tenant_bp, url_prefix="/api")
    app.register_blueprint(location_bp, url_prefix="/api")
    app.register_blueprint(asset_bp, url_prefix="/api")
    app.register_blueprint(scan_bp, url_prefix="/api")

    @app.route("/")
    def home():
        return {"message": "Field Service Platform API Running"}

    return app


# Gunicorn entry point
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
