import { canonicalIntake } from "./intake-filter.js";
import { getApplicationStatus } from "./status.js";
import { deadlineDaysRemaining } from "./deadline-semantics.js";
import { recordProvenance } from "./window-provenance.js";

const fields = {
  search: ["q", ""],
  selectedUniversityId: ["university", ""],
  ranking: ["ranking", "qs"],
  region: ["region", "all"],
  intake: ["intake", "all"],
  applicantCategory: ["applicant", "all"],
  deadlineRange: ["deadline", "all"],
  dateType: ["dates", "official"],
  status: ["status", "open"],
  sort: ["sort", "rank"],
  rankLimit: ["rank", "200"],
};
const allowed = {
  ranking: ["qs", "the", "arwu"],
  deadlineRange: ["all", "30", "90", "180"],
  dateType: ["all", "official", "estimated", "recurring", "review"],
  status: [
    "all",
    "open",
    "upcoming",
    "future",
    "closed",
    "exception",
    "unknown",
  ],
  sort: ["rank", "opens", "deadline"],
  rankLimit: ["30", "50", "100", "150", "200"],
};

export function readViewFilters(search) {
  const params = new URLSearchParams(search);
  const result = {};
  for (const [field, [key, fallback]] of Object.entries(fields)) {
    const value = params.get(key) ?? fallback;
    result[field] =
      !allowed[field] || allowed[field].includes(value) ? value : fallback;
  }
  result.favoritesOnly = params.get("saved") === "1";
  return result;
}

export function writeViewFilters(filters) {
  const params = new URLSearchParams();
  for (const [field, [key, fallback]] of Object.entries(fields)) {
    const value = filters[field] ?? fallback;
    if (value !== fallback) params.set(key, String(value));
  }
  if (filters.favoritesOnly) params.set("saved", "1");
  return params;
}

export function matchesDateAndScope(record, filters, today = new Date()) {
  const day = new Date(
    Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()),
  );
  const remaining = deadlineDaysRemaining(
    record,
    Math.ceil((new Date(`${record.closesAt}T00:00:00Z`) - day) / 86400000),
  );
  const provenance = recordProvenance(record);
  const type = filters.dateType || "official";
  return (
    (filters.region === "all" || record.region === filters.region) &&
    (filters.intake === "all" ||
      canonicalIntake(record).key === filters.intake) &&
    (filters.applicantCategory === "all" ||
      record.applicantCategories?.includes(filters.applicantCategory)) &&
    (filters.deadlineRange === "all" ||
      (remaining >= 0 && remaining <= Number(filters.deadlineRange))) &&
    (type === "all" ||
      provenance === (type === "estimated" ? "predicted" : type))
  );
}

export function matchesTimeStatus(record, status, today) {
  return status === "all" || getApplicationStatus(record, today) === status;
}
