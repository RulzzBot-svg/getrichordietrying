import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTenant } from "../context/TenantContext";
import {
  getTrackedEntries,
  getTrackedFields,
  getTrackedSummary,
  getTrackedFieldVisibility,
  saveTrackedFields,
  saveTrackedFieldVisibility,
} from "../utils/trackedWorkflow";
import "./TrackingDashboard.css";

function formatTimestamp(value) {
  if (!value) return "No tracked activity yet";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return "No tracked activity yet";
  }
}

function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2 12C3.8 7.8 7.5 5 12 5C16.5 5 20.2 7.8 22 12C20.2 16.2 16.5 19 12 19C7.5 19 3.8 16.2 2 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function EyeSlashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2 12C3.8 7.8 7.5 5 12 5C16.5 5 20.2 7.8 22 12C20.2 16.2 16.5 19 12 19C7.5 19 3.8 16.2 2 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 4L20 20" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function Sparkline() {
  return (
    <svg viewBox="0 0 180 56" className="sparkline" preserveAspectRatio="none" aria-hidden="true">
      <polyline
        fill="none"
        stroke="#16a34a"
        strokeWidth="3"
        points="0,44 20,39 40,42 60,31 80,34 100,26 120,29 140,18 160,21 180,13"
      />
    </svg>
  );
}

export default function TrackingDashboard() {
  const navigate = useNavigate();
  const { config } = useTenant();

  const [fields, setFields] = useState(() => getTrackedFields());
  const [entries, setEntries] = useState(() => getTrackedEntries());
  const [fieldInput, setFieldInput] = useState("");
  const [yearFilter, setYearFilter] = useState("2026");
  const [statusFilter, setStatusFilter] = useState("Active");
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [fieldVisibility, setFieldVisibility] = useState(() => {
    const visibility = getTrackedFieldVisibility(getTrackedFields());
    return visibility;
  });

  const summary = useMemo(() => getTrackedSummary(entries), [entries]);

  const priorityFeed = useMemo(
    () => [
      {
        id: "feed-1",
        color: "#dc2626",
        title: "Delivery delayed - Route B",
        time: "10 mins ago",
      },
      {
        id: "feed-2",
        color: "#f59e0b",
        title: "Queue nearing capacity - Logistics",
        time: "18 mins ago",
      },
      {
        id: "feed-3",
        color: "#16a34a",
        title: "High priority work order closed",
        time: "28 mins ago",
      },
      {
        id: "feed-4",
        color: "#2563eb",
        title: "Supervisor approval submitted",
        time: "42 mins ago",
      },
    ],
    []
  );

  const flowRows = useMemo(
    () => [
      {
        label: "Pending Assignment",
        value: 45,
        color: "#64748b",
        tooltip: "View all 45 items",
      },
      {
        label: "In Progress / On-Site",
        value: 82,
        color: "#f59e0b",
        tooltip: "View all 82 items",
      },
      {
        label: "Awaiting QA/Approval",
        value: 15,
        color: "#7c3aed",
        tooltip: "View all 15 items",
      },
      {
        label: "Completed (Today)",
        value: 128,
        color: "#16a34a",
        tooltip: "View all 128 items",
      },
    ],
    []
  );

  const flowMax = useMemo(() => Math.max(...flowRows.map((row) => row.value), 1), [flowRows]);

  const syncVisibilityForFields = (nextFields) => {
    const nextVisibility = getTrackedFieldVisibility(nextFields);
    saveTrackedFieldVisibility(nextVisibility);
    setFieldVisibility(nextVisibility);
  };

  const handleAddField = (event) => {
    event.preventDefault();
    const nextField = fieldInput.trim();

    if (!nextField) return;
    if (fields.some((field) => field.toLowerCase() === nextField.toLowerCase())) {
      setFieldInput("");
      return;
    }

    const nextFields = [...fields, nextField];
    saveTrackedFields(nextFields);
    setFields(nextFields);
    syncVisibilityForFields(nextFields);
    setFieldInput("");
  };

  const handleRemoveField = (fieldToRemove) => {
    const nextFields = fields.filter((field) => field !== fieldToRemove);
    saveTrackedFields(nextFields);
    setFields(nextFields);
    syncVisibilityForFields(nextFields);
  };

  const handleToggleFieldVisibility = (field) => {
    const nextVisibility = {
      ...fieldVisibility,
      [field]: !(fieldVisibility[field] !== false),
    };
    saveTrackedFieldVisibility(nextVisibility);
    setFieldVisibility(nextVisibility);
  };

  return (
    <div data-theme="corporate" className="dashboard-shell">
      <div className="dashboard-wrap">
        <header className="dashboard-header">
          <div>
            <h1 className="dashboard-title">Workflow Dashboard</h1>
            <p className="card-subtitle">Fast view for supervisors with clear action status.</p>
          </div>

          <div className="header-actions">
            <button type="button" className="nav-btn" onClick={() => navigate("/")}>
              Back Home
            </button>
            <button type="button" className="nav-btn" onClick={() => navigate("/manual-mode")}>
              Open Manual Mode
            </button>
            <button type="button" className="nav-btn" onClick={() => setEntries(getTrackedEntries())}>
              Refresh
            </button>
          </div>

          <div className="filters-row">
            <select
              className="filter-pill"
              value={yearFilter}
              onChange={(event) => setYearFilter(event.target.value)}
            >
              <option value="2026">Year 2026</option>
              <option value="2025">Year 2025</option>
              <option value="2024">Year 2024</option>
            </select>
            <select
              className="filter-pill"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="Active">Active</option>
              <option value="All">All</option>
              <option value="Closed">Closed</option>
            </select>
            <select
              className="filter-pill"
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value)}
            >
              <option value="All">Priority All</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
            </select>
          </div>
        </header>

        <section className="top-grid">
          <article className="card">
            <p className="kpi-label">Total Inventory Scanned</p>
            <p className="kpi-value" style={{ color: "#166534" }}>1,248</p>
            <span className="kpi-badge">+5% today</span>
            <Sparkline />
          </article>

          <article className="card">
            <p className="kpi-label">Active Logistics Queues</p>
            <p className="kpi-value" style={{ color: "#0f172a" }}>24</p>
            <div className="capacity-track">
              <div className="capacity-fill" />
            </div>
            <p className="capacity-caption">65% Capacity</p>
          </article>

          <article className="card">
            <p className="kpi-label">Overdue Deliveries / Alerts</p>
            <p className="kpi-value" style={{ color: "#dc2626" }}>6</p>
            <div className="alert-line">
              <span aria-hidden="true">⚠</span>
              <span>Action required</span>
            </div>
          </article>
        </section>

        <section className="middle-grid">
          <article className="card">
            <h2 className="card-title">Active Workflow Status</h2>
            <p className="card-subtitle">Real-time volume of scanned items across operational stages.</p>

            {flowRows.map((row) => (
              <div className="pipeline-row" key={row.label}>
                <div className="pipeline-label">
                  <span>{row.label}</span>
                  <span>{row.value}</span>
                </div>
                <div className="pipeline-track">
                  <div
                    className="pipeline-fill"
                    style={{ width: `${Math.max(8, (row.value / flowMax) * 100)}%`, background: row.color }}
                  />
                  <span className="pipeline-tooltip">{row.tooltip}</span>
                </div>
              </div>
            ))}
          </article>

          <article className="card">
            <h2 className="card-title">Priority Action Feed</h2>
            <p className="card-subtitle">Items that need supervisor attention.</p>
            <div className="feed-list">
              {priorityFeed.map((item) => (
                <div className="feed-item" key={item.id}>
                  <span className="feed-dot" style={{ background: item.color }} />
                  <div>
                    <p className="feed-title">{item.title}</p>
                    <p className="feed-time">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="card admin-card">
          <h2 className="card-title">Active Custom Fields (Admin View)</h2>
          <p className="card-subtitle">Toggle which fields are visible to technicians on the entry form.</p>

          <form className="add-field-row" onSubmit={handleAddField}>
            <input
              type="text"
              className="add-field-input"
              value={fieldInput}
              onChange={(event) => setFieldInput(event.target.value)}
              placeholder="Add a custom field"
            />
            <button type="submit" className="add-field-btn">
              Add Field
            </button>
          </form>

          <div className="admin-grid">
            {fields.map((field) => {
              const isVisible = fieldVisibility[field] !== false;

              return (
                <div className={`admin-row ${isVisible ? "" : "hidden"}`} key={field}>
                  <p className="field-name">{field}</p>
                  <div className="field-controls">
                    <button
                      type="button"
                      className="eye-toggle"
                      aria-label={isVisible ? `Hide ${field}` : `Show ${field}`}
                      title={isVisible ? "Visible to technicians" : "Hidden from technicians"}
                      onClick={() => handleToggleFieldVisibility(field)}
                    >
                      {isVisible ? <EyeIcon /> : <EyeSlashIcon />}
                    </button>
                    <button
                      type="button"
                      className="remove-btn"
                      onClick={() => handleRemoveField(field)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="card-subtitle" style={{ marginTop: "10px" }}>
            Latest update: {formatTimestamp(summary.lastUpdated)} | Tenant: {config.tenantName}
          </p>
        </section>
      </div>
    </div>
  );
}
