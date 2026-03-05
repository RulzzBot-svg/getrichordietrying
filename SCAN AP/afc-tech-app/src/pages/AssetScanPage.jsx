/**
 * AssetScanPage.jsx
 *
 * Phase 5 — QR Code & Scanner Agnosticism
 *
 * Opened when the user scans a QR code that points to:
 *   app.com/scan?asset_id=<id>
 *
 * The page:
 *  1. Reads `asset_id` from the URL query string.
 *  2. Fetches GET /api/scan?asset_id=<id> from the backend.
 *  3. Receives asset metadata + `form_fields` config.
 *  4. Dynamically renders the correct checklist — no hardcoded logic.
 *  5. On submit, posts to POST /api/scan/submit.
 *
 * The form_fields array from the backend looks like:
 *  [
 *    { key: "is_completed",       label: "Filter replaced", type: "checkbox" },
 *    { key: "initial_resistance", label: "Initial resistance (in. w.g.)", type: "number" },
 *    { key: "note",               label: "Notes", type: "textarea" },
 *  ]
 *
 * This means the frontend has zero industry-specific knowledge.
 * Adding a new asset type (e.g. "Chemical Tank") only requires a backend change.
 */

import React, { useEffect, useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { useTenant } from "../context/TenantContext";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export default function AssetScanPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { config } = useTenant();
  const terms = config.terminology;

  const assetId = searchParams.get("asset_id");

  const [assetData, setAssetData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Per-service-item form state: { [serviceItemId]: { [fieldKey]: value } }
  const [fieldValues, setFieldValues] = useState({});
  const [overallNotes, setOverallNotes] = useState("");

  const tech = useMemo(() => {
    try {
      const raw = localStorage.getItem("tech");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!tech) {
      // Save intended destination so login can redirect back
      try {
        sessionStorage.setItem("post_login_path", `/asset-scan?asset_id=${assetId}`);
      } catch (_) {}
      navigate("/");
      return;
    }
    if (!assetId) {
      setError("No asset_id provided in URL.");
      setLoading(false);
      return;
    }

    axios
      .get(`${API_BASE}/api/scan?asset_id=${encodeURIComponent(assetId)}`)
      .then(({ data }) => {
        setAssetData(data);
        // Initialize field state for each service item
        const initial = {};
        (data.service_items || []).forEach((si) => {
          initial[si.id] = {};
          (data.form_fields || []).forEach((field) => {
            initial[si.id][field.key] =
              field.type === "checkbox" ? false : "";
          });
        });
        setFieldValues(initial);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.error || "Failed to load asset data.");
        setLoading(false);
      });
  }, [assetId, tech, navigate]);

  const handleFieldChange = (serviceItemId, fieldKey, value) => {
    setFieldValues((prev) => ({
      ...prev,
      [serviceItemId]: {
        ...prev[serviceItemId],
        [fieldKey]: value,
      },
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!assetData || !tech) return;
    setSubmitting(true);

    const serviceItemsPayload = assetData.service_items.map((si) => {
      const vals = fieldValues[si.id] || {};
      return {
        service_item_id: si.id,
        is_completed: vals.is_completed ?? false,
        is_inspected: vals.is_inspected ?? false,
        note: vals.note ?? "",
        initial_resistance: vals.initial_resistance ? parseFloat(vals.initial_resistance) : null,
        final_resistance: vals.final_resistance ? parseFloat(vals.final_resistance) : null,
      };
    });

    try {
      await axios.post(`${API_BASE}/api/scan/submit`, {
        asset_id: assetData.asset_id,
        tech_id: tech.id,
        overall_notes: overallNotes,
        completed_at: new Date().toISOString(),
        service_items: serviceItemsPayload,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.error || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------
  const renderField = (field, serviceItemId) => {
    const val = fieldValues[serviceItemId]?.[field.key];
    const onChange = (e) =>
      handleFieldChange(
        serviceItemId,
        field.key,
        field.type === "checkbox" ? e.target.checked : e.target.value
      );

    switch (field.type) {
      case "checkbox":
        return (
          <label key={field.key} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="checkbox checkbox-primary"
              checked={!!val}
              onChange={onChange}
            />
            <span className="text-sm">{field.label}</span>
          </label>
        );
      case "number":
        return (
          <div key={field.key} className="form-control">
            <label className="label py-0">
              <span className="label-text text-xs">{field.label}</span>
            </label>
            <input
              type="number"
              step="0.01"
              className="input input-bordered input-sm w-full"
              value={val ?? ""}
              onChange={onChange}
              placeholder={field.label}
            />
          </div>
        );
      case "textarea":
      default:
        return (
          <div key={field.key} className="form-control">
            <label className="label py-0">
              <span className="label-text text-xs">{field.label}</span>
            </label>
            <textarea
              className="textarea textarea-bordered textarea-sm w-full"
              rows={2}
              value={val ?? ""}
              onChange={onChange}
              placeholder={field.label}
            />
          </div>
        );
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="loading loading-spinner loading-lg text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="alert alert-error max-w-sm">
          <span>❌ {error}</span>
          <button className="btn btn-sm" onClick={() => navigate(-1)}>
            Back
          </button>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card bg-base-100 shadow-lg max-w-sm w-full p-6 text-center space-y-4">
          <div className="text-5xl">✅</div>
          <h2 className="text-xl font-bold text-success">Job Recorded!</h2>
          <p className="text-sm text-base-content/70">
            {terms.service_action} completed for{" "}
            <strong>{assetData.name}</strong> at{" "}
            <strong>{assetData.location_name}</strong>.
          </p>
          <button className="btn btn-primary w-full" onClick={() => navigate("/Home")}>
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div data-theme="corporate" className="min-h-screen bg-base-200 p-4">
      <div className="max-w-lg mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)}>
            ← Back
          </button>
          <h1 className="text-lg font-bold flex-1 text-center">
            {terms.service_action} {terms.service_item_name}
          </h1>
        </div>

        {/* Asset info card */}
        <div className="card bg-base-100 shadow-sm border border-base-300">
          <div className="card-body p-4 space-y-1">
            <div className="flex items-center justify-between">
              <h2 className="card-title text-base">{assetData.name}</h2>
              {assetData.asset_type && (
                <span className="badge badge-outline badge-sm">{assetData.asset_type}</span>
              )}
            </div>
            {assetData.location_name && (
              <p className="text-sm text-base-content/70">
                {terms.location_name}: <strong>{assetData.location_name}</strong>
              </p>
            )}
            {assetData.location_label && (
              <p className="text-sm text-base-content/70">{assetData.location_label}</p>
            )}
            {assetData.notes && (
              <p className="text-xs text-base-content/50 mt-1">{assetData.notes}</p>
            )}
          </div>
        </div>

        {/* Dynamic service item checklist */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {assetData.service_items?.map((si, idx) => (
            <div
              key={si.id}
              className="card bg-base-100 shadow-sm border border-base-300"
            >
              <div className="card-body p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-sm">
                      {si.phase ? `${si.phase} — ` : ""}{si.size}
                    </p>
                    {si.part_number && (
                      <p className="text-xs text-base-content/50">PN: {si.part_number}</p>
                    )}
                    {si.quantity > 1 && (
                      <p className="text-xs text-base-content/50">Qty: {si.quantity}</p>
                    )}
                  </div>
                  <StatusBadge status={si.status} />
                </div>

                {/* Dynamically rendered fields from backend config */}
                <div className="space-y-2">
                  {assetData.form_fields?.map((field) =>
                    renderField(field, si.id)
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Overall notes */}
          <div className="card bg-base-100 shadow-sm border border-base-300">
            <div className="card-body p-4">
              <label className="label py-0">
                <span className="label-text font-medium">Overall Notes</span>
              </label>
              <textarea
                className="textarea textarea-bordered w-full"
                rows={3}
                placeholder="Any general notes for this job…"
                value={overallNotes}
                onChange={(e) => setOverallNotes(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            className={`btn btn-primary w-full ${submitting ? "loading" : ""}`}
            disabled={submitting}
          >
            {submitting ? "Submitting…" : `Submit ${terms.service_action}`}
          </button>
        </form>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    Overdue: "badge-error",
    "Due Soon": "badge-warning",
    Completed: "badge-success",
    Pending: "badge-ghost",
  };
  return (
    <span className={`badge badge-sm ${map[status] || "badge-ghost"}`}>
      {status || "Pending"}
    </span>
  );
}
