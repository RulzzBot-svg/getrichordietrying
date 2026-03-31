# Field Service Platform

A white-label, multi-tenant field service management application.  
Technicians scan QR codes to look up assets, complete service checklists, and record jobs — all from a mobile browser.

---

## Features

- **Multi-tenant** — each client (tenant) has its own branding, logo, and terminology
- **Industry-agnostic** — built-in presets for HVAC, Plumbing, Fire Safety, Property Management, and General
- **QR-code driven** — every asset gets a scannable label; technicians never type IDs
- **Offline-capable** — service records queue locally and sync when connectivity is restored
- **Role-based access** — technician and admin roles with PIN-based login
- **Dynamic checklists** — form fields are driven by asset type, requiring no frontend changes to support new asset categories

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask · SQLAlchemy |
| Frontend | React · Vite · DaisyUI / Tailwind |
| Database | PostgreSQL |
| Auth | PIN-based + role header middleware |

---

## White-Label Setup

### 1. Create a Tenant

`POST /api/tenants` (requires admin auth via `X-Tech-ID` header)

```json
{
  "name": "Acme HVAC",
  "slug": "acme-hvac",
  "industry": "hvac",
  "brand_color": "#1d4ed8",
  "logo_url": "https://cdn.acme.com/logo.png"
}
```

`industry` controls the default terminology preset.  Available values:

| Industry slug | Location | Asset | Service Item |
|---|---|---|---|
| `hvac` | Hospital | AHU | Filter |
| `plumbing` | Property | Fixture | Component |
| `fire-safety` | Building | Extinguisher | Inspection Item |
| `property-management` | Office Park | Unit | Task |
| `general` | Location | Asset | Service Item |

You can override individual labels by passing a `terminology` object:

```json
{
  "terminology": {
    "location_name": "Warehouse",
    "asset_name": "Conveyor",
    "service_item_name": "Belt"
  }
}
```

### 2. Add Technicians

`POST /api/technicians/login` authenticates by name + PIN.  
Create technician records directly in the database or via seed script.

### 3. Import Assets

Use `seed_from_excel.py` to bulk-import locations and assets from an Excel spreadsheet:

```bash
python seed_from_excel.py --tenant-slug acme-hvac --file assets.xlsx
```

### 4. Generate QR Labels

```bash
python generate_qr_labels.py --tenant-slug acme-hvac
```

Outputs printable PDF/PNG QR labels for every asset.  
Each label encodes a URL in the form `https://app.yourdomain.com/scan?asset_id=<id>`.

---

## Backend Deployment

```bash
cd "SCAN AP/afc-tech-app-backend"
cp .env.example .env        # fill in DATABASE_URL and ALLOWED_ORIGINS
pip install -r requirements.txt
python init_db.py           # create tables
gunicorn app:app
```

Key environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (required) |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend URLs |
| `SECRET_KEY` | Flask session secret (use a long random string in production) |

---

## Frontend Deployment

```bash
cd "SCAN AP/afc-tech-app"
cp .env.example .env        # set VITE_API_BASE_URL
npm install
npm run build               # outputs to dist/
```

Set `VITE_API_BASE_URL` to the backend's base URL (e.g. `https://api.yourdomain.com`).

---

## API Overview

### Tenant

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tenants/presets` | List industry presets |
| GET | `/api/tenants` | List all tenants (admin) |
| POST | `/api/tenants` | Create tenant (admin) |
| GET | `/api/tenants/<slug_or_id>` | Get tenant config (public) |
| PUT | `/api/tenants/<slug_or_id>` | Update tenant (admin) |

### Locations & Assets

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/locations` | List locations |
| POST | `/api/locations` | Create location (admin) |
| GET | `/api/assets` | List assets |
| GET | `/api/scan?asset_id=<id>` | Resolve QR scan |
| POST | `/api/scan/submit` | Submit completed job |

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs` | Record a job (legacy) |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/<id>` | Get job details |

---

## License

MIT — see [LICENSE](LICENSE)
