"""
seed_from_excel.py — Universal data seeder for white-label platform.

Phase 4 of the white-label roadmap: generalise onboarding so ANY industry
client can seed their database from a simple CSV/Excel template.

UNIVERSAL TEMPLATE COLUMNS
---------------------------
Required:
  Location_Name      - Name of the site / location (e.g. "Main Campus", "Foothill Hospital")
  Asset_ID           - Human-readable asset identifier (e.g. "AHU-01", "Boiler-B", "FE-042")
  Asset_Description  - Brief description / location label for the asset
  Required_Service   - Name/description of the service item / task (used as `size` column)

Optional:
  Asset_Type         - Category for dynamic form rendering (e.g. "AHU", "Fire Extinguisher")
  Building           - Sub-location / building name
  Floor_Area         - Floor/area label
  Part_Number        - Part number for the service item
  Phase              - Stage or phase label
  Quantity           - Number of service items (default 1)
  Frequency          - Service interval, e.g. "90 days", "3 months", "1 year" (default 90 days)
  Last_Service_Date  - Date of most recent service (YYYY-MM-DD or Excel date)

LEGACY HVAC COLUMNS (also recognised for backward compat)
-----------------------------------------------------------
  AHU NO., LOCATION, STAGE, FILTER SIZE, FREQUENCY, QUANTITY,
  BUILDING, FLOOR/AREA, PART NUMBER, FILTER TYPE, DATE OF REPLACEMENT

Usage
-----
  python seed_from_excel.py --tenant-slug acme-hvac --file data.xlsx [--sheet "Sheet1"]
  python seed_from_excel.py --tenant-slug acme-hvac --file data.csv
  python seed_from_excel.py --tenant-slug acme-hvac --file filter-datasheet.xlsm --sheet all
  python seed_from_excel.py --help
"""
import argparse
import os
import re
import sys
from datetime import datetime, date

import pandas as pd

from app import app
from db import db
from models import Tenant, Location, Asset, ServiceItem, Building


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        description="Seed a tenant's database from a CSV or Excel template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file", "-f",
        default=os.path.join("excel_data_raw", "data.xlsx"),
        help="Path to the CSV or Excel/xlsm file (default: excel_data_raw/data.xlsx)",
    )
    parser.add_argument(
        "--sheet", "-s",
        default=None,
        help='Sheet name to import, or "all" to import every sheet (Excel only).',
    )
    parser.add_argument(
        "--tenant-slug", "-t",
        required=True,
        help="Slug of the Tenant record this data belongs to.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print stats without writing to the database.",
    )
    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_str(x):
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    s = str(x).strip()
    if not s:
        return None
    if s.lower() in ("nan", "none", "null", "n/a", "na", "-", "empty"):
        return None
    return s


def is_placeholder(s):
    if not s:
        return True
    return str(s).strip().lower() in ["empty", "nan", "n/a", "na", "-", "none", "null"]


def to_date(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def parse_quantity(val, default=1):
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else default


def parse_frequency_to_days(raw, default=90):
    """Convert human-readable frequency string to integer days."""
    if raw is None:
        return default
    s = str(raw).strip()
    if not s or s.lower() == "removed":
        return None

    m = re.search(r"(\d+)\s*day", s, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*month", s, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*year", s, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 365
    # bare number → treat as days
    m = re.match(r"^(\d+)$", s)
    if m:
        return int(m.group(1))
    return default


def normalize_asset_key(display_name: str, building: str = None, location_name: str = None) -> str:
    parts = filter(None, [location_name, building, display_name])
    raw = "::".join(p.strip().lower() for p in parts)
    return re.sub(r"\s+", " ", raw).strip() or "unnamed"


# ---------------------------------------------------------------------------
# Column resolver — handles both universal template + legacy HVAC columns
# ---------------------------------------------------------------------------
class ColumnMap:
    """Resolve a DataFrame's columns to the canonical field names."""

    UNIVERSAL = {
        "location_name": ["location_name"],
        "asset_id": ["asset_id"],
        "asset_description": ["asset_description"],
        "required_service": ["required_service"],
        "asset_type": ["asset_type"],
        "building": ["building"],
        "floor_area": ["floor_area", "floor/area"],
        "part_number": ["part_number", "part number"],
        "phase": ["phase", "stage"],
        "quantity": ["quantity", "qty"],
        "frequency": ["frequency"],
        "last_service_date": ["last_service_date", "date_of_replacement", "date of replacement"],
    }

    HVAC_LEGACY = {
        "asset_id": ["ahu no.", "ahu no", "ahuno"],
        "asset_description": ["location"],
        "required_service": ["filter size"],
        "building": ["building"],
        "floor_area": ["floor/area"],
        "part_number": ["part number"],
        "phase": ["stage"],
        "quantity": ["quantity", "qty"],
        "frequency": ["frequency"],
        "last_service_date": ["date of replacement"],
    }

    def __init__(self, df_columns):
        normalized = {re.sub(r"\s+", " ", str(c)).strip().lower(): c for c in df_columns}
        self._map = {}
        # Try universal first, fall back to HVAC legacy aliases
        for field, aliases in self.UNIVERSAL.items():
            for alias in aliases:
                if alias in normalized:
                    self._map[field] = normalized[alias]
                    break
        for field, aliases in self.HVAC_LEGACY.items():
            if field not in self._map:
                for alias in aliases:
                    if alias in normalized:
                        self._map[field] = normalized[alias]
                        break

    def get(self, field, row):
        col = self._map.get(field)
        if col is None:
            return None
        return row.get(col)

    def has(self, field):
        return field in self._map

    def missing_required(self):
        required = ["asset_id", "required_service"]
        return [f for f in required if not self.has(f)]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------
def upsert_location(tenant_id: int, name: str):
    obj = Location.query.filter_by(tenant_id=tenant_id, name=name).first()
    if obj:
        return obj
    obj = Location(tenant_id=tenant_id, name=name, active=True)
    db.session.add(obj)
    db.session.flush()
    return obj


def upsert_building(tenant_id: int, location_id: int, name: str, floor_area: str = None):
    name = clean_str(name)
    if not name:
        return None
    obj = Building.query.filter_by(tenant_id=tenant_id, location_id=location_id, name=name).first()
    if obj:
        return obj
    obj = Building(
        tenant_id=tenant_id,
        location_id=location_id,
        name=name,
        floor_area=floor_area,
        active=True,
    )
    db.session.add(obj)
    db.session.flush()
    return obj


def upsert_asset(tenant_id, location_id, building_id, name, asset_type, location_label, excel_order):
    obj = Asset.query.filter_by(tenant_id=tenant_id, location_id=location_id, name=name).first()
    if obj:
        if building_id and not obj.building_id:
            obj.building_id = building_id
        if location_label and not obj.location_label:
            obj.location_label = location_label
        if asset_type and not obj.asset_type:
            obj.asset_type = asset_type
        return obj, False
    obj = Asset(
        tenant_id=tenant_id,
        location_id=location_id,
        building_id=building_id,
        name=name,
        asset_type=asset_type,
        location_label=location_label,
        excel_order=excel_order,
    )
    db.session.add(obj)
    db.session.flush()
    return obj, True


def upsert_service_item(tenant_id, asset_id, phase, part_number, size, quantity, frequency_days, last_service_date, is_active, excel_order):
    size = clean_str(size)
    if not size:
        return None
    phase = clean_str(phase)
    part_number = clean_str(part_number) or ""
    existing = ServiceItem.query.filter_by(asset_id=asset_id, phase=phase, part_number=part_number, size=size).first()
    if existing:
        existing.quantity = parse_quantity(quantity, default=existing.quantity or 1)
        if frequency_days is not None:
            existing.frequency_days = int(frequency_days)
        if last_service_date:
            existing.last_service_date = last_service_date
        existing.is_active = bool(is_active)
        if excel_order is not None:
            existing.excel_order = int(excel_order)
        return existing

    si = ServiceItem(
        tenant_id=tenant_id,
        asset_id=asset_id,
        phase=phase,
        part_number=part_number,
        size=size,
        quantity=parse_quantity(quantity),
        frequency_days=int(frequency_days) if frequency_days else 90,
        last_service_date=last_service_date,
        is_active=bool(is_active),
        excel_order=excel_order,
    )
    db.session.add(si)
    return si


# ---------------------------------------------------------------------------
# Per-sheet seeder
# ---------------------------------------------------------------------------
def seed_sheet(df, tenant_id: int, location_name_override: str | None, stats: dict, dry_run: bool):
    df.columns = [str(c).strip() for c in df.columns]
    cm = ColumnMap(df.columns)

    missing = cm.missing_required()
    if missing:
        print(f"  ⚠ Skipping — missing required columns: {missing}. Found: {list(df.columns)}")
        return

    asset_key_to_id: dict[str, int] = {}
    next_seq = 1
    service_item_order: dict[int, int] = {}

    for _, row in df.iterrows():
        # ----- location -----
        loc_name = clean_str(cm.get("location_name", row)) or location_name_override
        if not loc_name:
            loc_name = "Default Location"

        # ----- asset identifier -----
        asset_raw = clean_str(cm.get("asset_id", row))
        if not asset_raw or is_placeholder(asset_raw):
            stats["service_items_skipped"] += 1
            continue

        # ----- building -----
        building_name = clean_str(cm.get("building", row))
        floor_area = clean_str(cm.get("floor_area", row))
        asset_type = clean_str(cm.get("asset_type", row))
        asset_description = clean_str(cm.get("asset_description", row))

        # ----- service item fields -----
        required_service = clean_str(cm.get("required_service", row))
        if not required_service:
            stats["service_items_skipped"] += 1
            continue

        phase = clean_str(cm.get("phase", row))
        part_number = clean_str(cm.get("part_number", row))
        quantity = cm.get("quantity", row)
        freq_raw = cm.get("frequency", row)
        freq_days = parse_frequency_to_days(freq_raw)
        last_service_date = to_date(cm.get("last_service_date", row))
        is_active = not (isinstance(freq_raw, str) and freq_raw.strip().lower() == "removed")

        if dry_run:
            stats["service_items_upserted"] += 1
            stats["locations"].add(loc_name)
            continue

        # ----- DB writes -----
        location = upsert_location(tenant_id, loc_name)
        stats["locations"].add(location.id)

        building_obj = None
        if building_name:
            building_obj = upsert_building(tenant_id, location.id, building_name, floor_area)

        asset_key = normalize_asset_key(asset_raw, building=building_name, location_name=loc_name)
        if asset_key not in asset_key_to_id:
            asset_obj, _ = upsert_asset(
                tenant_id=tenant_id,
                location_id=location.id,
                building_id=building_obj.id if building_obj else None,
                name=asset_raw,
                asset_type=asset_type,
                location_label=asset_description,
                excel_order=next_seq,
            )
            asset_key_to_id[asset_key] = asset_obj.id
            stats["assets"].add(asset_obj.id)
            next_seq += 1
        else:
            a_id = asset_key_to_id[asset_key]
            stats["assets"].add(a_id)

        a_id = asset_key_to_id[asset_key]
        service_item_order.setdefault(a_id, 1)
        si_order = service_item_order[a_id]
        service_item_order[a_id] += 1

        upsert_service_item(
            tenant_id=tenant_id,
            asset_id=a_id,
            phase=phase,
            part_number=part_number,
            size=required_service,
            quantity=quantity,
            frequency_days=freq_days,
            last_service_date=last_service_date,
            is_active=is_active,
            excel_order=si_order,
        )
        stats["service_items_upserted"] += 1


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------
def seed(file_path: str, tenant_slug: str, sheet_name=None, dry_run: bool = False):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with app.app_context():
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            raise ValueError(
                f"Tenant with slug '{tenant_slug}' not found. "
                "Create it first via POST /api/tenants."
            )
        tenant_id = tenant.id

        stats = {
            "file": file_path,
            "tenant": tenant.name,
            "locations": set(),
            "assets": set(),
            "service_items_upserted": 0,
            "service_items_skipped": 0,
            "sheets_processed": 0,
        }

        is_csv = file_path.lower().endswith(".csv")

        if is_csv:
            df = pd.read_csv(file_path)
            location_name_override = tenant.name
            print(f"\n→ Seeding CSV: {file_path}")
            seed_sheet(df, tenant_id, location_name_override, stats, dry_run)
            stats["sheets_processed"] = 1
        else:
            xls = pd.ExcelFile(file_path)
            all_sheets = [s for s in xls.sheet_names if s.strip().lower() != "filter"]

            if sheet_name and str(sheet_name).strip().lower() != "all":
                if sheet_name not in xls.sheet_names:
                    raise ValueError(f"Sheet '{sheet_name}' not found. Available: {xls.sheet_names}")
                sheets_to_process = [sheet_name]
            else:
                sheets_to_process = all_sheets if (sheet_name is None or sheet_name.lower() == "all") else [sheet_name]

            for sheet in sheets_to_process:
                print(f"\n→ Seeding sheet: {sheet}")
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet, header=4)
                except Exception:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                location_name_override = sheet.upper().replace("_", " ")
                seed_sheet(df, tenant_id, location_name_override, stats, dry_run)
                stats["sheets_processed"] += 1

        if not dry_run:
            db.session.commit()

        _print_stats(stats, dry_run)


def _print_stats(stats, dry_run):
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}✅ Seed complete")
    print(f"  Tenant     : {stats['tenant']}")
    print(f"  File       : {stats['file']}")
    print(f"  Sheets     : {stats['sheets_processed']}")
    print(f"  Locations  : {len(stats['locations'])}")
    print(f"  Assets     : {len(stats['assets'])}")
    print(f"  Service items upserted : {stats['service_items_upserted']}")
    print(f"  Service items skipped  : {stats['service_items_skipped']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    try:
        seed(
            file_path=args.file,
            tenant_slug=args.tenant_slug,
            sheet_name=args.sheet,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
