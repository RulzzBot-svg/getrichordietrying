import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTenant } from "../context/TenantContext";
import {
  getTrackedEntries,
  getTrackedFields,
  getTrackedSummary,
  saveTrackedFields,
} from "../utils/trackedWorkflow";

function formatTimestamp(value) {
  if (!value) return "No tracked activity yet";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return "No tracked activity yet";
  }
}

export default function TrackingDashboard() {
  const navigate = useNavigate();
  const { config } = useTenant();
  const [activeTab, setActiveTab] = useState("overview");
  const [fieldInput, setFieldInput] = useState("");
  const [fields, setFields] = useState(() => getTrackedFields());
  const [entries, setEntries] = useState(() => getTrackedEntries());

  const summary = useMemo(() => getTrackedSummary(entries), [entries]);

  const persistFields = (nextFields) => {
    saveTrackedFields(nextFields);
    setFields(getTrackedFields());
  };

  const handleAddField = (event) => {
    event.preventDefault();
    const nextField = fieldInput.trim();
    if (!nextField) return;
    if (fields.some((field) => field.toLowerCase() === nextField.toLowerCase())) {
      setFieldInput("");
      return;
    }

    persistFields([...fields, nextField]);
    setFieldInput("");
  };

  const handleRemoveField = (fieldToRemove) => {
    persistFields(fields.filter((field) => field !== fieldToRemove));
  };

  return (
    <div data-theme="corporate" className="min-h-screen bg-base-200">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col md:flex-row">
        <aside className="border-b border-base-300 bg-base-100 px-4 py-5 md:min-h-screen md:w-72 md:border-b-0 md:border-r">
          <div className="space-y-3">
            <button className="btn btn-ghost btn-sm justify-start px-0" onClick={() => navigate("/")}>
              ← Back to Home
            </button>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/50">
                Tracking
              </p>
              <h1 className="text-2xl font-semibold">Workflow Dashboard</h1>
              <p className="mt-2 text-sm text-base-content/70">
                Review tracked activity and control which labels appear in manual mode.
              </p>
            </div>
          </div>

          <nav className="mt-6 space-y-2">
            <button
              className={`btn btn-block justify-start ${
                activeTab === "overview" ? "btn-primary" : "btn-ghost"
              }`}
              onClick={() => setActiveTab("overview")}
            >
              Overview
            </button>
            <button
              className={`btn btn-block justify-start ${
                activeTab === "edit-views" ? "btn-primary" : "btn-ghost"
              }`}
              onClick={() => setActiveTab("edit-views")}
            >
              Edit Views
            </button>
            <button className="btn btn-outline btn-block justify-start" onClick={() => navigate("/manual-mode")}>
              Open Manual Mode
            </button>
          </nav>

          <div className="mt-8 rounded-2xl border border-base-300 bg-base-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/50">
              Tenant
            </p>
            <p className="mt-2 font-medium">{config.tenantName}</p>
            <p className="text-sm text-base-content/60">{config.industry || "General"}</p>
          </div>
        </aside>

        <main className="flex-1 px-4 py-5 md:px-8 md:py-8">
          {activeTab === "overview" ? (
            <div className="space-y-6">
              <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <article className="card border border-base-300 bg-base-100 shadow-sm">
                  <div className="card-body">
                    <p className="text-sm text-base-content/60">Tracked submissions</p>
                    <p className="text-4xl font-semibold text-primary">{summary.totalEntries}</p>
                  </div>
                </article>

                <article className="card border border-base-300 bg-base-100 shadow-sm">
                  <div className="card-body">
                    <p className="text-sm text-base-content/60">Configured labels</p>
                    <p className="text-4xl font-semibold text-secondary">{fields.length}</p>
                  </div>
                </article>

                <article className="card border border-base-300 bg-base-100 shadow-sm">
                  <div className="card-body">
                    <p className="text-sm text-base-content/60">Last updated</p>
                    <p className="text-lg font-semibold">{formatTimestamp(summary.lastUpdated)}</p>
                  </div>
                </article>
              </section>

              <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.25fr_0.95fr]">
                <article className="card border border-base-300 bg-base-100 shadow-sm">
                  <div className="card-body">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h2 className="card-title">Recent activity</h2>
                        <p className="text-sm text-base-content/60">
                          New manual submissions appear here after techs click Add.
                        </p>
                      </div>
                      <button className="btn btn-sm btn-outline" onClick={() => setEntries(getTrackedEntries())}>
                        Refresh
                      </button>
                    </div>

                    {entries.length === 0 ? (
                      <div className="mt-4 rounded-2xl border border-dashed border-base-300 p-6 text-sm text-base-content/60">
                        No tracked submissions yet. Use manual mode to start recording entries.
                      </div>
                    ) : (
                      <div className="mt-4 space-y-3">
                        {entries.slice(0, 5).map((entry) => (
                          <div key={entry.id} className="rounded-2xl border border-base-300 p-4">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="font-medium">Tracked entry</p>
                              <span className="text-xs text-base-content/50">
                                {formatTimestamp(entry.createdAt)}
                              </span>
                            </div>
                            <div className="mt-3 grid gap-2 sm:grid-cols-2">
                              {fields.map((field) => (
                                <div key={`${entry.id}-${field}`} className="rounded-xl bg-base-200 px-3 py-2">
                                  <p className="text-xs uppercase tracking-wide text-base-content/50">
                                    {field}
                                  </p>
                                  <p className="text-sm font-medium">
                                    {entry.values?.[field] || "-"}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </article>

                <article className="card border border-base-300 bg-base-100 shadow-sm">
                  <div className="card-body">
                    <h2 className="card-title">Manual mode preview</h2>
                    <p className="text-sm text-base-content/60">
                      These labels appear in the rectangle that technicians fill out.
                    </p>
                    <div className="mt-4 rounded-3xl border-2 border-base-300 bg-base-200 p-5">
                      <div className="space-y-3">
                        {fields.map((field) => (
                          <div key={field} className="rounded-2xl border border-base-300 bg-base-100 px-4 py-3">
                            <p className="text-sm font-medium">{field}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </article>
              </section>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <section className="card border border-base-300 bg-base-100 shadow-sm">
                <div className="card-body">
                  <div>
                    <h2 className="card-title">Edit Views</h2>
                    <p className="text-sm text-base-content/60">
                      Add the labels you want technicians to complete in manual mode.
                    </p>
                  </div>

                  <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={handleAddField}>
                    <input
                      type="text"
                      className="input input-bordered flex-1"
                      value={fieldInput}
                      onChange={(event) => setFieldInput(event.target.value)}
                      placeholder="Add a new tracked label"
                    />
                    <button type="submit" className="btn btn-primary">
                      Add Label
                    </button>
                  </form>

                  <div className="mt-5 space-y-3">
                    {fields.map((field) => (
                      <div
                        key={field}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-base-300 p-4"
                      >
                        <div>
                          <p className="font-medium">{field}</p>
                          <p className="text-sm text-base-content/50">Shown to technicians in manual mode</p>
                        </div>
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost text-error"
                          onClick={() => handleRemoveField(field)}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="card border border-base-300 bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title">Rectangle Preview</h2>
                  <p className="text-sm text-base-content/60">
                    This is the block users see when they click Manual Mode.
                  </p>
                  <div className="mt-4 rounded-3xl border-2 border-dashed border-primary/40 bg-base-200 p-5">
                    <div className="space-y-3">
                      {fields.map((field) => (
                        <div key={field} className="rounded-2xl border border-base-300 bg-base-100 px-4 py-3">
                          <p className="text-sm font-medium">{field}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-5 grid grid-cols-2 gap-3">
                      <button type="button" className="btn btn-primary" disabled>
                        Add
                      </button>
                      <button type="button" className="btn btn-outline" disabled>
                        Go Back
                      </button>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}