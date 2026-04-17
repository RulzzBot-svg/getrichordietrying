const TRACKED_FIELDS_KEY = "trackedWorkflowFields";
const TRACKED_ENTRIES_KEY = "trackedWorkflowEntries";
const TRACKED_FIELD_VISIBILITY_KEY = "trackedWorkflowFieldVisibility";

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

export function getTrackedFieldVisibility(fields = getTrackedFields()) {
  const visibility = parseStoredValue(TRACKED_FIELD_VISIBILITY_KEY, {});
  const cleaned = {};

  fields.forEach((field) => {
    cleaned[field] = visibility[field] !== false;
  });

  return cleaned;
}

export function saveTrackedFieldVisibility(visibility) {
  const fields = getTrackedFields();
  const next = {};

  fields.forEach((field) => {
    next[field] = visibility[field] !== false;
  });

  saveValue(TRACKED_FIELD_VISIBILITY_KEY, next);
}

export function getVisibleTrackedFields() {
  const fields = getTrackedFields();
  const visibility = getTrackedFieldVisibility(fields);
  const visible = fields.filter((field) => visibility[field] !== false);

  return visible.length > 0 ? visible : fields;
}

export function saveTrackedFields(fields) {
  const cleanedFields = fields
    .map((field) => String(field || "").trim())
    .filter(Boolean);

  const nextFields = cleanedFields.length > 0 ? cleanedFields : DEFAULT_FIELDS;

  saveValue(TRACKED_FIELDS_KEY, nextFields);

  const currentVisibility = parseStoredValue(TRACKED_FIELD_VISIBILITY_KEY, {});
  const nextVisibility = {};
  nextFields.forEach((field) => {
    nextVisibility[field] = currentVisibility[field] !== false;
  });
  saveValue(TRACKED_FIELD_VISIBILITY_KEY, nextVisibility);
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