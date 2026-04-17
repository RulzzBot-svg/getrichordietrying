import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTenant } from "../context/TenantContext";
import {
  addTrackedEntry,
  createEmptyTrackedValues,
  getVisibleTrackedFields,
} from "../utils/trackedWorkflow";

export default function ManualModePage() {
  const navigate = useNavigate();
  const { config } = useTenant();
  const terms = config.terminology;
  const [fields, setFields] = useState(() => getVisibleTrackedFields());
  const [values, setValues] = useState(() => createEmptyTrackedValues(getVisibleTrackedFields()));
  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    const nextFields = getVisibleTrackedFields();
    setFields(nextFields);
    setValues(createEmptyTrackedValues(nextFields));
  }, []);

  const handleChange = (field, value) => {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    addTrackedEntry({ values });
    setSavedMessage("Entry added to the dashboard.");
    setValues(createEmptyTrackedValues(fields));
  };

  return (
    <div data-theme="corporate" className="min-h-screen bg-base-200 px-4 py-6">
      <div className="mx-auto max-w-3xl">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/50">
              Manual Mode
            </p>
            <h1 className="text-2xl font-semibold">Tracked {terms.service_action.toLowerCase()} entry</h1>
            <p className="mt-2 text-sm text-base-content/60">
              Fill out the admin-defined labels below, then click Add to record the entry.
            </p>
          </div>

          <button className="btn btn-outline" onClick={() => navigate("/dashboard")}>
            Open Dashboard
          </button>
        </div>

        <form onSubmit={handleSubmit} className="rounded-[2rem] border-2 border-base-300 bg-base-100 p-5 shadow-sm sm:p-8">
          <div className="space-y-4">
            {fields.map((field) => (
              <label key={field} className="block rounded-2xl border border-base-300 bg-base-200 px-4 py-4">
                <span className="mb-2 block text-sm font-medium">{field}</span>
                <input
                  type="text"
                  className="input input-bordered w-full bg-base-100"
                  value={values[field] || ""}
                  onChange={(event) => handleChange(field, event.target.value)}
                  placeholder={`Enter ${field.toLowerCase()}`}
                />
              </label>
            ))}
          </div>

          {savedMessage ? (
            <div className="alert alert-success mt-5">
              <span>{savedMessage}</span>
            </div>
          ) : null}

          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button type="submit" className="btn btn-primary">
              Add
            </button>
            <button type="button" className="btn btn-outline" onClick={() => navigate(-1)}>
              Go Back
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}