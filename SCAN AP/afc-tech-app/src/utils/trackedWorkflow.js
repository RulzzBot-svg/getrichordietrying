const TRACKED_FIELDS_KEY = "trackedWorkflowFields";
const TRACKED_ENTRIES_KEY = "trackedWorkflowEntries";

const DEFAULT_FIELDS = ["Technician Name", "Work Order", "Site Notes"];

function parseStoredValue(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function saveValue(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function getTrackedFields() {
  const fields = parseStoredValue(TRACKED_FIELDS_KEY, DEFAULT_FIELDS);
  return Array.isArray(fields) && fields.length > 0 ? fields : DEFAULT_FIELDS;
}

export function saveTrackedFields(fields) {
  const cleanedFields = fields
    .map((field) => String(field || "").trim())
    .filter(Boolean);

  saveValue(
    TRACKED_FIELDS_KEY,
    cleanedFields.length > 0 ? cleanedFields : DEFAULT_FIELDS
  );
}

export function getTrackedEntries() {
  const entries = parseStoredValue(TRACKED_ENTRIES_KEY, []);
  return Array.isArray(entries) ? entries : [];
}

export function addTrackedEntry(entry) {
  const nextEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    values: {},
    ...entry,
  };

  const entries = getTrackedEntries();
  const updatedEntries = [nextEntry, ...entries];
  saveValue(TRACKED_ENTRIES_KEY, updatedEntries);
  return nextEntry;
}

export function getTrackedSummary(entries = getTrackedEntries()) {
  const totalEntries = entries.length;
  const latestEntry = entries[0] || null;
  const lastUpdated = latestEntry?.createdAt || null;

  return {
    totalEntries,
    latestEntry,
    lastUpdated,
  };
}

export function createEmptyTrackedValues(fields = getTrackedFields()) {
  return fields.reduce((accumulator, field) => {
    accumulator[field] = "";
    return accumulator;
  }, {});
}