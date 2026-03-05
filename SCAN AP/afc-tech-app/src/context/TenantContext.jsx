/**
 * TenantContext.jsx
 *
 * Phase 3 — React "Theme & Config" Engine
 *
 * Provides every component in the tree with:
 *   - config.terminology  — industry-specific label dictionary
 *   - config.brandColor   — hex colour string (e.g. "#0ea5e9")
 *   - config.logoUrl      — URL of the client's logo
 *   - config.industry     — industry slug ("hvac", "plumbing", …)
 *   - config.tenantName   — display name of the client
 *   - config.loading      — true while the config is being fetched
 *
 * The tenant is resolved in priority order:
 *   1. `tenant_id` stored in the logged-in tech's localStorage entry
 *   2. `X-Tenant-ID` / `tenantSlug` in sessionStorage (e.g. set by QR redirect)
 *   3. A `?tenant=<slug>` query param in the current URL
 *   4. Hard-coded default (HVAC industry, original AFC colours)
 *
 * Dynamic CSS variable injection
 * --------------------------------
 * The brand colour is injected into the document root as the CSS
 * variable `--brand-primary`.  DaisyUI's `primary` colour is also
 * overridden so that every `btn-primary`, `text-primary`, etc. uses
 * the client's brand colour automatically.
 *
 * Terminology usage
 * -----------------
 * Inside any component:
 *
 *   import { useTenant } from "../context/TenantContext";
 *   const { config } = useTenant();
 *   // Render:  <h1>Scan the {config.terminology.asset_name}</h1>
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

// ---------------------------------------------------------------------------
// Industry presets (mirror of backend INDUSTRY_PRESETS)
// The frontend uses these as an instant fallback while the network request
// resolves, and as defaults when no tenant is configured.
// ---------------------------------------------------------------------------
const INDUSTRY_PRESETS = {
  hvac: {
    location_name: "Hospital",
    asset_name: "AHU",
    service_item_name: "Filter",
    service_action: "Replace",
    location_plural: "Hospitals",
    asset_plural: "AHUs",
    service_item_plural: "Filters",
  },
  plumbing: {
    location_name: "Property",
    asset_name: "Fixture",
    service_item_name: "Component",
    service_action: "Service",
    location_plural: "Properties",
    asset_plural: "Fixtures",
    service_item_plural: "Components",
  },
  "fire-safety": {
    location_name: "Building",
    asset_name: "Extinguisher",
    service_item_name: "Inspection Item",
    service_action: "Inspect",
    location_plural: "Buildings",
    asset_plural: "Extinguishers",
    service_item_plural: "Inspection Items",
  },
  "property-management": {
    location_name: "Office Park",
    asset_name: "Unit",
    service_item_name: "Task",
    service_action: "Complete",
    location_plural: "Office Parks",
    asset_plural: "Units",
    service_item_plural: "Tasks",
  },
  general: {
    location_name: "Location",
    asset_name: "Asset",
    service_item_name: "Service Item",
    service_action: "Service",
    location_plural: "Locations",
    asset_plural: "Assets",
    service_item_plural: "Service Items",
  },
};

// Default / fallback config (original HVAC / AFC branding)
const DEFAULT_CONFIG = {
  tenantName: "AFC Technician",
  industry: "hvac",
  brandColor: "#0ea5e9",
  logoUrl: null,
  terminology: INDUSTRY_PRESETS.hvac,
  loading: false,
};

// ---------------------------------------------------------------------------
// Context + hook
// ---------------------------------------------------------------------------
const TenantContext = createContext(DEFAULT_CONFIG);

export function useTenant() {
  return useContext(TenantContext);
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function TenantProvider({ children }) {
  const [config, setConfig] = useState({ ...DEFAULT_CONFIG, loading: true });

  // Determine the tenant slug / id to look up
  const tenantKey = useMemo(() => {
    // 1. From logged-in tech
    try {
      const raw = localStorage.getItem("tech");
      if (raw) {
        const tech = JSON.parse(raw);
        if (tech?.tenant_id) return String(tech.tenant_id);
      }
    } catch (_) {}

    // 2. From sessionStorage (set before QR redirect)
    try {
      const slug = sessionStorage.getItem("tenantSlug");
      if (slug) return slug;
    } catch (_) {}

    // 3. From URL query param (?tenant=<slug>)
    try {
      const params = new URLSearchParams(window.location.search);
      const t = params.get("tenant");
      if (t) return t;
    } catch (_) {}

    return null;
  }, []);

  useEffect(() => {
    if (!tenantKey) {
      setConfig({ ...DEFAULT_CONFIG, loading: false });
      return;
    }

    let cancelled = false;

    axios
      .get(`${API_BASE}/api/tenants/${encodeURIComponent(tenantKey)}`)
      .then(({ data }) => {
        if (cancelled) return;
        const industry = data.industry || "general";
        const terminology = {
          ...INDUSTRY_PRESETS[industry],   // preset as base
          ...(data.terminology || {}),      // server overrides
        };
        const nextConfig = {
          tenantName: data.name || DEFAULT_CONFIG.tenantName,
          industry,
          brandColor: data.brand_color || DEFAULT_CONFIG.brandColor,
          logoUrl: data.logo_url || null,
          terminology,
          loading: false,
        };
        setConfig(nextConfig);
        _applyBrandColor(nextConfig.brandColor);
      })
      .catch(() => {
        if (!cancelled) {
          setConfig({ ...DEFAULT_CONFIG, loading: false });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tenantKey]);

  // Apply brand colour on initial mount for the default config too
  useEffect(() => {
    _applyBrandColor(config.brandColor);
  }, [config.brandColor]);

  return (
    <TenantContext.Provider value={{ config, INDUSTRY_PRESETS }}>
      {children}
    </TenantContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// CSS variable injection
// ---------------------------------------------------------------------------
/**
 * Injects `--brand-primary` into :root and monkey-patches DaisyUI's
 * `--color-primary` so that every `btn-primary` / `text-primary` uses
 * the client brand colour automatically.
 */
function _applyBrandColor(hex) {
  if (!hex) return;
  const root = document.documentElement;
  root.style.setProperty("--brand-primary", hex);
  // DaisyUI v4 uses oklch; we inject a CSS override as a fallback
  root.style.setProperty("--color-primary", hex);
}

export default TenantContext;
