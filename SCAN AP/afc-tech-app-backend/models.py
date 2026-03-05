from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Text, Float, Date, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from db import db


# -------------------------
# TENANT  (multi-tenancy root)
# -------------------------
class Tenant(db.Model):
    """
    Represents a white-label client organisation.
    Every other model references this via tenant_id.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)       # url-safe key, e.g. "acme-hvac"
    industry = Column(String(100), default="general")             # hvac, plumbing, general …

    # Branding
    brand_color = Column(String(20), default="#0ea5e9")           # hex, e.g. "#1d4ed8"
    logo_url = Column(String(500))

    # Terminology dictionary stored as JSON, e.g.:
    # {"location_name": "Hospital", "asset_name": "AHU", "service_item_name": "Filter"}
    terminology = Column(JSON, default=lambda: {})

    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    locations = relationship("Location", back_populates="tenant", cascade="all, delete-orphan")
    technicians = relationship("Technician", back_populates="tenant", cascade="all, delete-orphan")


# -------------------------
# LOCATION  (formerly Hospital)
# -------------------------
class Location(db.Model):
    """
    Generic top-level site/location for a tenant.
    Replaces the HVAC-specific 'Hospital' concept.
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(String(300))
    city = Column(String(200))
    active = Column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="locations")
    assets = relationship("Asset", back_populates="location", cascade="all, delete-orphan")
    buildings = relationship("Building", back_populates="location", cascade="all, delete-orphan")


# Backward-compatible alias so existing code using "Hospital" still works
Hospital = Location


# -------------------------
# BUILDING
# -------------------------
class Building(db.Model):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    floor_area = Column(String(200))
    active = Column(Boolean, default=True)

    location = relationship("Location", back_populates="buildings")
    assets = relationship("Asset", back_populates="building", cascade="all, delete-orphan")


# -------------------------
# ASSET  (formerly AHU)
# -------------------------
class Asset(db.Model):
    """
    Generic trackable asset/equipment at a location.
    Replaces the HVAC-specific 'AHU' concept.
    """
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True)          # QR CODE = ID
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)

    name = Column(String(150), nullable=False)
    asset_type = Column(String(100))                # e.g. "AHU", "Fire Extinguisher", "Boiler"
    location_label = Column(String(200))            # physical location description
    notes = Column(Text)
    excel_order = Column(Integer, nullable=True)

    location = relationship("Location", back_populates="assets")
    building = relationship("Building", back_populates="assets")
    service_items = relationship("ServiceItem", back_populates="asset", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="asset", cascade="all, delete-orphan")


# Backward-compatible aliases
AHU = Asset


# -------------------------
# NOTIFICATIONS
# -------------------------
class Notification(db.Model):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)

    comment_text = Column(Text)
    status = Column(String(20), default="pending")  # pending, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(150), nullable=True)

    location = relationship("Location")
    asset = relationship("Asset")
    job = relationship("Job")
    technician = relationship("Technician")


# -------------------------
# SERVICE ITEM  (formerly Filter)
# -------------------------
class ServiceItem(db.Model):
    """
    A required service task on an asset.
    Replaces the HVAC-specific 'Filter' concept.
    """
    __tablename__ = "service_items"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    # Generic service fields
    phase = Column(String(50))                      # stage / category
    part_number = Column(String(100))
    size = Column(String(50))
    quantity = Column(Integer)
    is_active = Column(Boolean, default=True, nullable=False)

    # Service scheduling
    frequency_days = Column(Integer, nullable=False)
    last_service_date = Column(Date)

    excel_order = Column(Integer, nullable=True)

    asset = relationship("Asset", back_populates="service_items")
    job_service_items = relationship(
        "JobServiceItem",
        back_populates="service_item",
        cascade="all, delete-orphan"
    )


# Backward-compatible alias
Filter = ServiceItem


# -------------------------
# TECHNICIAN
# -------------------------
class Technician(db.Model):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(150), nullable=False)
    pin = Column(String(20), nullable=False)
    active = Column(Boolean, default=True)
    role = Column(String(20), default="technician", nullable=False)  # 'technician' or 'admin'

    tenant = relationship("Tenant", back_populates="technicians")
    jobs = relationship("Job", back_populates="technician", cascade="all, delete-orphan")


# -------------------------
# JOB
# -------------------------
class Job(db.Model):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    tech_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)

    completed_at = Column(DateTime, default=datetime.utcnow)
    overall_notes = Column(Text)
    gps_lat = Column(Float)
    gps_long = Column(Float)

    asset = relationship("Asset", back_populates="jobs")
    technician = relationship("Technician", back_populates="jobs")
    job_service_items = relationship("JobServiceItem", back_populates="job", cascade="all, delete-orphan")
    signature = relationship(
        "JobSignature",
        uselist=False,
        back_populates="job",
        cascade="all, delete-orphan"
    )


# Backward-compatible property aliases on Job so old code using .ahu still works
Job.ahu = Job.asset
Job.job_filters = Job.job_service_items


# -------------------------
# JOB SERVICE ITEMS  (formerly JobFilter)
# -------------------------
class JobServiceItem(db.Model):
    __tablename__ = "job_service_items"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    service_item_id = Column(Integer, ForeignKey("service_items.id"), nullable=False)
    is_inspected = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False)
    note = Column(Text)
    initial_resistance = Column(Float, nullable=True)
    final_resistance = Column(Float, nullable=True)

    job = relationship("Job", back_populates="job_service_items")
    service_item = relationship("ServiceItem", back_populates="job_service_items")


# Backward-compatible alias and property
JobFilter = JobServiceItem
JobServiceItem.filter = JobServiceItem.service_item
JobServiceItem.filter_id = JobServiceItem.service_item_id


# -------------------------
# JOB SIGNATURE
# -------------------------
class JobSignature(db.Model):
    __tablename__ = "job_signatures"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    signer_name = Column(String(150))
    signer_role = Column(String(100))
    signature_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="signature")


# -------------------------
# SUPERVISOR SIGNOFF
# -------------------------
class SupervisorSignoff(db.Model):
    __tablename__ = "supervisor_signoffs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    date = Column(Date, nullable=False)
    supervisor_name = Column(String(150), nullable=False)
    summary = Column(Text)
    signature_data = Column(Text, nullable=False)   # base64 PNG
    job_ids = Column(Text)                          # Comma-separated job IDs
    created_at = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location")
