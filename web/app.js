import { countUniversitiesByStatus, getApplicationStatus } from "./status.js";
import { state } from "./state.js";
import { t } from "./strings.js";
import { makeCalendarMenu } from "./calendar-export.js";
import {
  initAuth,
  openAuthPanel,
  scheduleFavoriteSync,
  setupAuthPanel,
  updateAuthUi,
} from "./auth.js";
import {
  makeReviewButton,
  setupReviewPanel,
  updateReviewAuthState,
} from "./review.js";
import {
  acronym,
  formatDateRange,
  makeElement,
  makeLink,
  parseDate,
  safeUrl,
} from "./dom.js";
import {
  canonicalIntake,
  compareIntakes,
  intakeLabel,
} from "./intake-filter.js";
import {
  countryLabel,
  programmeLabel,
  programmeSearchTerms,
  regionLabel,
  roundLabel,
  schoolLabels,
  setProgrammeTranslations,
} from "./localization.js";
import { needsManualCheck } from "./exception-status.js";
import {
  createRankingIndex,
  filterRecordsToRanking,
} from "./ranking-filter.js";
import { groupWindowRecordsForDisplay } from "./window-grouping.js";

const PAGE_SIZE = 20;
const dateFormatters = new Map();
const deadlineDatePartsFormatters = new Map();
const recordSearchTextCache = new WeakMap();
const recordIntakeCache = new WeakMap();
let selectedRankingCache = null;

function statusLabels() {
  return {
    open: { title: t("openTitle"), description: t("openDescription") },
    upcoming: {
      title: t("upcomingTitle"),
      description: t("upcomingDescription"),
    },
    future: { title: t("futureTitle"), description: t("futureDescription") },
    closed: { title: t("closedTitle"), description: t("closedDescription") },
    exception: {
      title: t("exceptionTitle"),
      description: t("exceptionDescription"),
    },
    unknown: {
      title: t("directoryTitle"),
      description: t("directoryDescription"),
    },
  };
}

function dateFormatter() {
  const locale = state.language === "zh" ? "zh-CN" : "en-GB";
  if (!dateFormatters.has(locale)) {
    dateFormatters.set(
      locale,
      new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }),
    );
  }
  return dateFormatters.get(locale);
}

function deadlineDatePartsFormatter() {
  const locale = state.language === "zh" ? "zh-CN" : "en-GB";
  if (!deadlineDatePartsFormatters.has(locale)) {
    deadlineDatePartsFormatters.set(
      locale,
      new Intl.DateTimeFormat(locale, {
        day: "2-digit",
        month: "short",
        timeZone: "UTC",
      }),
    );
  }
  return deadlineDatePartsFormatters.get(locale);
}

function makeCell(label, ...children) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  children.filter(Boolean).forEach((child) => cell.appendChild(child));
  return cell;
}

function resetPages() {
  state.pages = {};
  state.expandedWindowGroups.clear();
  state.expandedUniversityGroups.clear();
}

function makeTextStack(primary, secondary, primaryClass = "date-primary") {
  const wrapper = document.createDocumentFragment();
  wrapper.appendChild(
    makeElement("span", { className: primaryClass, text: primary }),
  );
  if (secondary) {
    wrapper.appendChild(
      makeElement("span", { className: "date-secondary", text: secondary }),
    );
  }
  return wrapper;
}

function makeLinkedTextStack(
  primary,
  url,
  secondary,
  primaryClass = "date-primary",
) {
  const wrapper = document.createDocumentFragment();
  wrapper.appendChild(makeLink(primary, url, primaryClass));
  if (secondary) {
    wrapper.appendChild(
      makeElement("span", { className: "date-secondary", text: secondary }),
    );
  }
  return wrapper;
}

function favoriteKey(type, id) {
  return `${type}:${id}`;
}

function saveFavorites() {
  localStorage.setItem(
    "gradwindow:favorites",
    JSON.stringify([...state.favorites]),
  );
  updateFavoriteControls();
  scheduleFavoriteSync();
}

function toggleFavorite(key) {
  if (state.favorites.has(key)) state.favorites.delete(key);
  else state.favorites.add(key);
  saveFavorites();
  render();
}

function makeFavoriteButton(key) {
  const active = state.favorites.has(key);
  const button = makeElement("button", {
    className: `icon-button favorite-button${active ? " active" : ""}`,
    text: active ? t("favorited") : t("favorite"),
    title: active ? t("removeFavorite") : t("favorite"),
  });
  button.type = "button";
  button.dataset.favoriteKey = key;
  button.setAttribute("aria-pressed", String(active));
  button.addEventListener("click", () => toggleFavorite(key));
  return button;
}

function todayUtc() {
  const now = new Date();
  return new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
}

function getStatus(record, today = todayUtc()) {
  return getApplicationStatus(record, today);
}

function daysUntil(dateValue) {
  return Math.ceil((parseDate(dateValue) - todayUtc()) / 86_400_000);
}

function formatDate(value) {
  return dateFormatter().format(parseDate(value));
}

function makeSchoolDisplay(record) {
  const school = document.createDocumentFragment();
  const schoolText = schoolLabels(record, state.language);
  const country = countryLabel(record.country, state.language);
  school.appendChild(
    makeLink(schoolText.primary, record.applicationUrl, "school-link"),
  );
  if (country) {
    school.appendChild(
      makeElement("span", {
        className: "school-country-inline",
        text: `(${country})`,
      }),
    );
  }
  school.appendChild(
    makeElement("span", {
      className: "school-meta",
      text: [schoolText.secondary, country].filter(Boolean).join(" · "),
    }),
  );
  return school;
}

function makeResponsiveDeadline(
  opensAt,
  closesAt,
  secondary,
  primaryClass = "date-primary",
) {
  const deadline = document.createDocumentFragment();
  const desktop = makeElement("span", {
    className: "desktop-deadline-stack",
  });
  desktop.appendChild(
    makeTextStack(formatDate(closesAt), secondary, primaryClass),
  );
  deadline.append(
    desktop,
    makeElement("span", {
      className: `mobile-date-range ${primaryClass}`,
      text: formatDateRange(opensAt, closesAt),
    }),
  );
  return deadline;
}

function recordIntake(record) {
  if (!recordIntakeCache.has(record)) {
    recordIntakeCache.set(record, canonicalIntake(record));
  }
  return recordIntakeCache.get(record);
}

function deadlineNote(record, status) {
  if (record.dataStatus === "predicted") {
    return `${t("calendarShift")} · ${t("basedOn")} ${record.sourceCycle}`;
  }
  const days = daysUntil(record.closesAt);
  if (status === "closed") return `${Math.abs(days)} ${t("daysAgo")}`;
  if (days === 0) return t("dueToday");
  if (days === 1) return t("dueTomorrow");
  if (days > 1 && days <= 30) return `${days} ${t("daysLeft")}`;
  return intakeLabel(recordIntake(record), state.language);
}

const APPLICANT_CATEGORY_LABELS = {
  all: { en: "All applicants", zh: "所有申请人" },
  "international-bachelors": {
    en: "International bachelor's degree",
    zh: "境外本科申请人",
  },
  esop: { en: "ESOP scholarship applicants", zh: "ESOP 奖学金申请人" },
  "direct-doctorate": { en: "Direct doctorate applicants", zh: "直博申请人" },
  "swiss-bachelors": {
    en: "Swiss bachelor's degree",
    zh: "瑞士高校本科申请人",
  },
  "requires-uk-study-visa": {
    en: "UK Student visa required",
    zh: "需要英国学生签证",
  },
  "does-not-require-uk-study-visa": {
    en: "No UK Student visa required",
    zh: "无需英国学生签证",
  },
};

function applicantCategoryText(categories = []) {
  return categories
    .map(
      (category) =>
        state.applicantCategoryLabels[category]?.[state.language] ||
        APPLICANT_CATEGORY_LABELS[category]?.[state.language] ||
        category,
    )
    .join("、");
}

function sourceMonitorDescription(record) {
  const monitor = record.sourceMonitor || {};
  if (monitor.changed) return [t("sourceChanged"), "candidate"];
  if (monitor.status === "ok") return [t("sourceOk"), "verified"];
  if (monitor.status === "blocked") return [t("sourceBlocked"), "candidate"];
  if (monitor.status === "error" || monitor.status === "http-error") {
    return [t("sourceError"), "homepage"];
  }
  return [t("sourceUnchecked"), "homepage"];
}

function closeWindowDetail() {
  const panel = document.getElementById("window-detail-panel");
  if (panel) panel.hidden = true;
  document.body.classList.remove("window-detail-open");
}

function detailField(label, value) {
  const row = makeElement("div", { className: "window-detail-field" });
  row.append(
    makeElement("span", { text: label }),
    makeElement("strong", { text: value }),
  );
  return row;
}

function openWindowDetail(record, status = getStatus(record)) {
  const panel = document.getElementById("window-detail-panel");
  const body = document.getElementById("window-detail-body");
  const actions = document.getElementById("window-detail-header-actions");
  const university = state.universityById.get(record.universityId);
  if (!panel || !body || !actions) return;

  const schoolText = schoolLabels(record, state.language);
  const intake = intakeLabel(recordIntake(record), state.language);
  const localizedRound = roundLabel(record.round, state.language);
  const programmeName = programmeLabel(
    record.scopeId,
    record.program,
    state.language,
  );
  const [sourceStatus, sourceClass] =
    record.dataStatus === "predicted"
      ? [t("estimateBadge"), "predicted"]
      : sourceMonitorDescription(record);

  const heading = makeElement("section", {
    className: "window-detail-heading",
  });
  const schoolRow = makeElement("div", {
    className: "window-detail-school-row",
  });
  schoolRow.append(
    makeElement("h2", { text: schoolText.primary }),
    makeElement("span", {
      className: "rank-cell",
      text: formatRank(
        selectedRankForUniversity(record.universityId)?.rankDisplay ||
          record.qsRank,
      ),
    }),
  );
  heading.append(
    schoolRow,
    makeElement("p", {
      className: "school-meta",
      text: [schoolText.secondary, countryLabel(record.country, state.language)]
        .filter(Boolean)
        .join(" · "),
    }),
    makeLink(
      programmeName,
      record.applicationUrl,
      "program-link window-detail-programme",
    ),
  );

  const deadline = makeElement("section", {
    className: "window-detail-deadline",
  });
  deadline.append(
    makeElement("span", { text: t("deadline") }),
    makeElement("strong", { text: formatDate(record.closesAt) }),
    makeElement("small", { text: deadlineNote(record, status) }),
  );

  const info = makeElement("section", { className: "window-detail-section" });
  info.append(
    makeElement("h3", { text: t("mobileWindowDetails") }),
    detailField(t("opens"), formatDate(record.opensAt)),
    detailField(
      t("programmeIntake"),
      `${intake}${localizedRound ? ` · ${localizedRound}` : ""}`,
    ),
    detailField(
      t("applicantGroup"),
      applicantCategoryText(record.applicantCategories),
    ),
    detailField(t("statusTabsLabel"), statusLabels()[status]?.title || status),
  );

  const source = makeElement("section", {
    className: "window-detail-section window-detail-source",
  });
  const sourceHeader = makeElement("div", {
    className: "window-detail-source-header",
  });
  sourceHeader.append(
    makeElement("h3", { text: t("dataSource") }),
    makeElement("span", {
      className: `source-badge ${sourceClass}`,
      text: sourceStatus,
    }),
  );
  source.append(
    sourceHeader,
    makeElement("p", {
      text:
        record.dataStatus === "predicted"
          ? `${t("reference")} ${record.sourceCycle} · ${predictionConfidenceText(record)}`
          : `${t("verifiedOn")} ${record.verifiedAt}`,
    }),
    makeLink(
      record.dataStatus === "predicted"
        ? t("viewReference")
        : t("viewOfficial"),
      record.sourceUrl,
      "primary-button window-detail-source-link",
    ),
  );

  if (university) {
    const reviews = makeElement("section", {
      className: "window-detail-section window-detail-reviews",
    });
    reviews.append(
      makeElement("h3", { text: t("schoolReviewsTitle") }),
      makeElement("p", { text: t("reviewPublicNote") }),
      makeReviewButton(university),
    );
    body.replaceChildren(heading, deadline, info, source, reviews);
  } else {
    body.replaceChildren(heading, deadline, info, source);
  }

  actions.replaceChildren(
    makeCalendarMenu(record),
    makeFavoriteButton(favoriteKey("window", record.id)),
  );
  panel.hidden = false;
  document.body.classList.add("window-detail-open");
  panel.querySelector("[data-window-detail-close]")?.focus();
}

function setupWindowDetailPanel() {
  document.querySelectorAll("[data-window-detail-close]").forEach((button) => {
    button.addEventListener("click", closeWindowDetail);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeWindowDetail();
  });
}

function downloadFavoriteCalendars() {
  const records = state.data.filter((record) =>
    state.favorites.has(favoriteKey("window", record.id)),
  );
  if (!records.length) return;
  const events = records.flatMap((record) => {
    const start = record.closesAt.replaceAll("-", "");
    const endDate = parseDate(record.closesAt);
    endDate.setUTCDate(endDate.getUTCDate() + 1);
    const end = endDate.toISOString().slice(0, 10).replaceAll("-", "");
    return [
      "BEGIN:VEVENT",
      `UID:${record.id}@gradwindow`,
      `DTSTART;VALUE=DATE:${start}`,
      `DTEND;VALUE=DATE:${end}`,
      `SUMMARY:${record.dataStatus === "predicted" ? "[ESTIMATE] " : ""}${record.school} ${record.program} application deadline`,
      `URL:${record.applicationUrl}`,
      "END:VEVENT",
    ];
  });
  const body = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//GradWindow//Favorite Deadlines//CN",
    ...events,
    "END:VCALENDAR",
  ].join("\r\n");
  const blob = new Blob([body], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "gradwindow-favorite-deadlines.ics";
  anchor.click();
  URL.revokeObjectURL(url);
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b, "zh-CN"));
}

function populateSelect(elementId, values, labeler = (value) => value) {
  const select = document.getElementById(elementId);
  const selected = select.value;
  [...select.options].slice(1).forEach((option) => option.remove());
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labeler(value);
    select.appendChild(option);
  });
  select.value = [...select.options].some((option) => option.value === selected)
    ? selected
    : "all";
}

function populateIntakeSelect() {
  const select = document.getElementById("intake-filter");
  const selected = state.intake;
  select.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = t("allIntakes");
  select.appendChild(allOption);

  const intakes = new Map();
  recordsInSelectedRanking().forEach((record) => {
    const intake = recordIntake(record);
    if (intake.term === "academic") return;
    intakes.set(intake.key, intake);
  });
  [...intakes.values()].sort(compareIntakes).forEach((intake) => {
    const option = document.createElement("option");
    option.value = intake.key;
    option.textContent = intakeLabel(intake, state.language);
    select.appendChild(option);
  });
  select.value = [...select.options].some((option) => option.value === selected)
    ? selected
    : "all";
}

function buildSelectedRankingDefinition() {
  if (state.ranking === "qs") {
    return {
      id: "qs",
      shortLabel: "QS",
      available: true,
      rows: state.universities.map((university) => ({
        id: university.id,
        universityId: university.id,
        school: university.school,
        schoolZh: university.schoolZh,
        schoolAliasesZh: university.schoolAliasesZh || [],
        country: university.country,
        region: university.region,
        rankPosition: university.qsPosition,
        rankDisplay: university.rankDisplay,
        rankingOnly: false,
      })),
    };
  }
  const ranking = state.rankingPayload.rankings?.[state.ranking];
  if (!ranking) {
    return { id: state.ranking, available: false, rows: [] };
  }
  return { id: state.ranking, available: true, rows: [], ...ranking };
}

function selectedRankingContext() {
  if (
    selectedRankingCache?.ranking === state.ranking &&
    selectedRankingCache.universities === state.universities &&
    selectedRankingCache.rankingPayload === state.rankingPayload
  ) {
    return selectedRankingCache;
  }
  const definition = buildSelectedRankingDefinition();
  const rows = definition.available === false ? [] : definition.rows || [];
  selectedRankingCache = {
    ranking: state.ranking,
    universities: state.universities,
    rankingPayload: state.rankingPayload,
    definition,
    index: createRankingIndex(rows),
  };
  return selectedRankingCache;
}

function selectedRankingDefinition() {
  return selectedRankingContext().definition;
}

function selectedRankingRows() {
  return selectedRankingContext().index.rows;
}

function selectedRankByUniversityId() {
  return selectedRankingContext().index.byUniversityId;
}

function selectedRankForUniversity(universityId) {
  return selectedRankByUniversityId().get(universityId) || null;
}

function recordsInSelectedRanking() {
  const context = selectedRankingContext();
  if (context.recordsSource !== state.data) {
    context.recordsSource = state.data;
    context.records = filterRecordsToRanking(
      state.data,
      context.index.rows,
      context.index.universityIds,
    );
  }
  return context.records;
}

function selectedDirectoryUniversities() {
  return selectedRankingRows().map((rankingRow) => {
    const university = rankingRow.universityId
      ? state.universityById.get(rankingRow.universityId)
      : null;
    if (university) {
      return {
        ...university,
        rankPosition: rankingRow.rankPosition,
        rankDisplay: rankingRow.rankDisplay,
        rankingSourceUrl: rankingRow.sourceUrl || "",
        rankingOnly: false,
      };
    }
    return {
      id: `${state.ranking}:${rankingRow.id}`,
      school: rankingRow.school,
      schoolZh: rankingRow.schoolZh || "",
      schoolAliasesZh: rankingRow.schoolAliasesZh || [],
      country: rankingRow.country,
      region: rankingRow.region,
      rankPosition: rankingRow.rankPosition,
      rankDisplay: rankingRow.rankDisplay,
      rankingSourceUrl: rankingRow.sourceUrl || "",
      rankingOnly: true,
      admissionsDiscovery: "ranking-only",
      admissionsUrl: "",
      homepageUrl: "",
      monitor: {},
      windowPolicy: null,
      coverage: null,
    };
  });
}

function rankingShortLabel() {
  return selectedRankingDefinition().shortLabel || "QS";
}

function rankColumnLabel() {
  return `${rankingShortLabel()} ${t("rank")}`;
}

function rankRangeLabel(limit) {
  return t("rankRangeTop")
    .replace("{ranking}", rankingShortLabel())
    .replace("{limit}", limit);
}

function formatRank(rankDisplay) {
  return String(rankDisplay).startsWith("=") ? rankDisplay : `#${rankDisplay}`;
}

function refreshFilterOptions() {
  populateSelect(
    "region-filter",
    uniqueSorted(
      [...recordsInSelectedRanking(), ...selectedDirectoryUniversities()]
        .map((record) => record.region)
        .filter(Boolean),
    ),
    (region) => regionLabel(region, state.language),
  );
  populateIntakeSelect();
}

function updateRankingAvailability() {
  const select = document.getElementById("ranking-filter");
  [...select.options].forEach((option) => {
    if (option.value === "qs") return;
    const ranking = state.…9236 tokens truncated…ment.querySelector("script[data-gradwindow-turnstile]")) {
    return;
  }
  const container = document.getElementById("turnstile-container");
  if (!container) return;
  const widget = makeElement("div", { className: "cf-turnstile" });
  widget.dataset.sitekey = siteKey;
  widget.dataset.action = "turnstile-spin-v1";
  widget.dataset.theme = state.theme === "dark" ? "dark" : "light";
  container.appendChild(widget);
  const script = document.createElement("script");
  script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
  script.async = true;
  script.defer = true;
  script.dataset.gradwindowTurnstile = "true";
  document.head.appendChild(script);
}

function setupSubscription() {
  const form = document.getElementById("subscribe-form");
  const button = document.getElementById("subscribe-button");
  const status = document.getElementById("subscribe-status");
  if (!form || !button || !status) return;
  const config = window.GRADWINDOW_CONFIG || {};
  const endpoint = String(config.subscribeUrl || "").replace(/\/$/, "");
  if (!endpoint) {
    button.disabled = true;
    status.textContent = t("subscribeUnavailable");
    return;
  }
  const subscriptionState = new URLSearchParams(window.location.search).get(
    "subscription",
  );
  if (subscriptionState === "confirmed") {
    status.className = "subscribe-status success";
    status.textContent = t("subscriptionConfirmed");
  } else if (subscriptionState === "invalid") {
    status.className = "subscribe-status error";
    status.textContent = t("subscriptionInvalid");
  }
  button.disabled = false;
  if (!subscriptionState) status.textContent = "";
  loadTurnstile(config.turnstileSiteKey || "");
  if (form.dataset.bound === "true") return;
  form.dataset.bound = "true";
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("subscribe-email").value.trim();
    const turnstileToken =
      form.querySelector('[name="cf-turnstile-response"]')?.value || "";
    button.disabled = true;
    status.className = "subscribe-status";
    status.textContent = t("subscribeSending");
    try {
      const response = await fetch(`${endpoint}/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          language: state.language,
          consent: true,
          turnstileToken,
        }),
      });
      if (!response.ok) throw new Error("subscribe failed");
      form.reset();
      status.className = "subscribe-status success";
      status.textContent = t("subscribeSuccess");
      if (window.turnstile) window.turnstile.reset();
    } catch {
      status.className = "subscribe-status error";
      status.textContent = t("subscribeError");
    } finally {
      button.disabled = false;
    }
  });
}

function updateDataNotes() {
  const checkedAt = state.monitorPayload?.meta?.checkedAt;
  document.getElementById("updated-at").textContent = checkedAt
    ? `${t("checkedAt")} ${formatDate(checkedAt.slice(0, 10))}`
    : `${t("dataUpdatedAt")} ${formatDate(state.meta.updatedAt.slice(0, 10))}`;
  const monitorSummary = state.monitorPayload?.meta?.summary;
  document.getElementById("monitor-summary").textContent = monitorSummary
    ? ` ${monitorSummary.ok}/${monitorSummary.total} ${t("pagesAccessible")}, ${monitorSummary.blocked} ${t("pagesBlocked")}.`
    : ` ${t("monitorUnavailable")}`;
  if (state.optionalFailureCount) {
    document.getElementById("monitor-summary").textContent +=
      ` ${state.optionalFailureCount} ${t("optionalUnavailable")}.`;
  }
}

function refreshLanguage() {
  localStorage.setItem("gradwindow:language", state.language);
  applyStaticTranslations();
  refreshFilterOptions();
  updateDataNotes();
  renderCoverage();
  setupHero();
  setupSubscription();
  render();
}

function setupHero() {
  const futureDeadline = state.data
    .filter(
      (record) =>
        record.dataStatus === "official" && getStatus(record) !== "closed",
    )
    .sort((a, b) => a.closesAt.localeCompare(b.closesAt))[0];
  if (!futureDeadline) {
    document.getElementById("hero-deadline-day").textContent = "200";
    document.getElementById("hero-deadline-month").textContent =
      state.language === "zh" ? "所学校" : "SCHOOLS";
    document.getElementById("hero-deadline-school").textContent =
      state.language === "zh"
        ? "官方申请目录"
        : "Official admissions directory";
    const mobileLink = document.getElementById("mobile-deadline-link");
    if (mobileLink) mobileLink.removeAttribute("target");
    const mobileSchool = document.getElementById("mobile-deadline-school");
    const mobileDate = document.getElementById("mobile-deadline-date");
    const mobileNote = document.getElementById("mobile-deadline-note");
    if (mobileSchool)
      mobileSchool.textContent =
        state.language === "zh"
          ? "官方申请目录"
          : "Official admissions directory";
    if (mobileDate) mobileDate.textContent = "TOP 200";
    if (mobileNote) mobileNote.textContent = "";
    return;
  }
  const dateParts = deadlineDatePartsFormatter()
    .formatToParts(parseDate(futureDeadline.closesAt))
    .reduce((result, part) => ({ ...result, [part.type]: part.value }), {});
  document.getElementById("hero-deadline-day").textContent = dateParts.day;
  document.getElementById("hero-deadline-month").textContent =
    dateParts.month.toUpperCase();
  document.getElementById("hero-deadline-school").textContent = schoolLabels(
    futureDeadline,
    state.language,
  ).primary;
  const mobileLink = document.getElementById("mobile-deadline-link");
  const mobileSchool = document.getElementById("mobile-deadline-school");
  const mobileDate = document.getElementById("mobile-deadline-date");
  const mobileNote = document.getElementById("mobile-deadline-note");
  if (mobileLink) {
    mobileLink.href =
      safeUrl(futureDeadline.applicationUrl) || "#application-groups";
    mobileLink.target = safeUrl(futureDeadline.applicationUrl) ? "_blank" : "";
    mobileLink.rel = "noreferrer";
  }
  if (mobileSchool)
    mobileSchool.textContent = schoolLabels(
      futureDeadline,
      state.language,
    ).primary;
  if (mobileDate) mobileDate.textContent = formatDate(futureDeadline.closesAt);
  if (mobileNote)
    mobileNote.textContent = deadlineNote(
      futureDeadline,
      getStatus(futureDeadline),
    );
}

function setMobileNavActive(name) {
  document.querySelectorAll("[data-mobile-nav]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mobileNav === name);
  });
}

function updateMobileFilterToggle() {
  const toolbar = document.querySelector(".quick-filter-panel .toolbar");
  const button = document.getElementById("mobile-filter-toggle");
  const label = document.getElementById("mobile-filter-toggle-label");
  if (!toolbar || !button || !label) return;
  const expanded = toolbar.classList.contains("mobile-filters-open");
  const hasAdvancedFilters =
    state.ranking !== "qs" ||
    state.region !== "all" ||
    state.intake !== "all" ||
    state.rankLimit !== "200";
  button.setAttribute("aria-expanded", String(expanded));
  button.classList.toggle("active", expanded || hasAdvancedFilters);
  label.textContent = t(expanded ? "hideFilters" : "showFilters");
}

function bindEvents() {
  document.getElementById("language-toggle").addEventListener("click", () => {
    state.language = state.language === "en" ? "zh" : "en";
    refreshLanguage();
  });
  document.getElementById("theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    applyTheme();
  });
  document
    .getElementById("mobile-filter-toggle")
    .addEventListener("click", () => {
      document
        .querySelector(".quick-filter-panel .toolbar")
        .classList.toggle("mobile-filters-open");
      updateMobileFilterToggle();
    });
  document.getElementById("search-input").addEventListener("input", (event) => {
    state.search = event.target.value;
    resetPages();
    syncUrl();
    render();
  });
  document
    .getElementById("ranking-filter")
    .addEventListener("change", (event) => {
      state.ranking = event.target.value;
      state.region = "all";
      state.intake = "all";
      if (state.ranking !== "qs") state.sort = "rank";
      resetPages();
      refreshFilterOptions();
      updateRankRangeOptions();
      syncUrl();
      updateStatusTabs();
      render();
    });
  document
    .getElementById("region-filter")
    .addEventListener("change", (event) => {
      state.region = event.target.value;
      resetPages();
      syncUrl();
      render();
    });
  document
    .getElementById("intake-filter")
    .addEventListener("change", (event) => {
      state.intake = event.target.value;
      resetPages();
      syncUrl();
      render();
    });
  document
    .getElementById("rank-range-filter")
    .addEventListener("change", (event) => {
      state.rankLimit = event.target.value;
      resetPages();
      syncUrl();
      render();
    });
  document.querySelectorAll(".status-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.status = button.dataset.status;
      resetPages();
      syncUrl();
      updateStatusTabs();
      render();
    });
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
        return;
      }
      event.preventDefault();
      const tabs = [...document.querySelectorAll(".status-tab")];
      const currentIndex = tabs.indexOf(button);
      const nextIndex =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? tabs.length - 1
            : (currentIndex +
                (event.key === "ArrowRight" ? 1 : -1) +
                tabs.length) %
              tabs.length;
      state.status = tabs[nextIndex].dataset.status;
      resetPages();
      syncUrl();
      render();
      updateStatusTabs(state.status);
    });
  });
  document
    .getElementById("expand-visible-groups")
    .addEventListener("click", () => setVisibleUniversityGroups(true));
  document
    .getElementById("collapse-visible-groups")
    .addEventListener("click", () => setVisibleUniversityGroups(false));
  document.getElementById("favorites-toggle").addEventListener("click", () => {
    state.favoritesOnly = !state.favoritesOnly;
    resetPages();
    render();
  });
  document
    .getElementById("export-favorites")
    .addEventListener("click", downloadFavoriteCalendars);

  document.querySelectorAll("[data-mobile-sort]").forEach((button) => {
    button.addEventListener("click", () => {
      state.sort = button.dataset.mobileSort;
      resetPages();
      syncUrl();
      render();
    });
  });

  document.querySelectorAll("[data-mobile-nav]").forEach((button) => {
    button.addEventListener("click", () => {
      const destination = button.dataset.mobileNav;
      setMobileNavActive(destination);
      if (destination === "home") {
        state.search = "";
        state.favoritesOnly = false;
        state.status = "open";
        document.getElementById("search-input").value = "";
        updateStatusTabs();
        resetPages();
        syncUrl();
        render();
        document
          .getElementById("application-board")
          .scrollIntoView({ behavior: "smooth" });
      } else if (destination === "favorites") {
        state.favoritesOnly = true;
        resetPages();
        syncUrl();
        render();
        document
          .getElementById("application-groups")
          .scrollIntoView({ behavior: "smooth" });
      } else if (destination === "profile") {
        openAuthPanel();
      }
    });
  });
}

async function init() {
  try {
    state.language =
      localStorage.getItem("gradwindow:language") === "zh" ? "zh" : "en";
    const savedTheme = localStorage.getItem("gradwindow:theme");
    state.theme = ["light", "dark"].includes(savedTheme)
      ? savedTheme
      : window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    applyTheme();
    applyStaticTranslations();
    const fetchRequiredJson = async (path) => {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
      return response.json();
    };
    const optionalFailures = [];
    const fetchOptionalJson = async (path, fallback) => {
      try {
        return await fetchRequiredJson(path);
      } catch (error) {
        optionalFailures.push(path);
        console.warn(`Optional data unavailable: ${path}`, error);
        return fallback;
      }
    };

    const [
      payload,
      universityPayload,
      programsPayload,
      predictionsPayload,
      monitorPayload,
      policiesPayload,
      coveragePayload,
      sourceMonitorPayload,
      programmeGroupsPayload,
      applicantCategoriesPayload,
      rankingsPayload,
      programmeTranslationsPayload,
    ] = await Promise.all([
      fetchRequiredJson("./data/applications.json"),
      fetchRequiredJson("./data/universities.json"),
      fetchRequiredJson("./data/programs.json"),
      fetchRequiredJson("./data/predictions.json"),
      fetchOptionalJson("./data/monitor-state.json", null),
      fetchOptionalJson("./data/window-policies.json", { policies: [] }),
      fetchOptionalJson("./data/coverage.json", null),
      fetchOptionalJson("./data/application-source-state.json", {
        applications: {},
      }),
      fetchOptionalJson("./data/programme-groups.json", { groups: [] }),
      fetchOptionalJson("./data/applicant-categories.json", {
        categories: [],
      }),
      fetchOptionalJson("./data/global-rankings.json", { rankings: {} }),
      fetchOptionalJson("./data/programme-translations.json", {
        translations: {},
      }),
    ]);
    setProgrammeTranslations(programmeTranslationsPayload);
    state.coverage = coveragePayload;
    state.monitorPayload = monitorPayload;
    state.optionalFailureCount = optionalFailures.length;
    state.sourceMonitor = sourceMonitorPayload.applications || {};
    state.universities = universityPayload.universities;
    state.universityById = new Map(
      state.universities.map((university) => [university.id, university]),
    );
    state.rankingPayload = rankingsPayload;
    state.programs = programsPayload.programs;
    state.programmeGroups = programmeGroupsPayload.groups || [];
    state.applicantCategoryLabels = Object.fromEntries(
      (applicantCategoriesPayload.categories || []).map((category) => [
        category.id,
        {
          en: category.labelEn || category.id,
          zh: category.labelZh || category.labelEn || category.id,
        },
      ]),
    );
    state.policies = policiesPayload.policies || [];
    const universityById = state.universityById;
    const programById = new Map(
      state.programs.map((program) => [program.id, program]),
    );
    const groupById = new Map(
      state.programmeGroups.map((group) => [group.id, group]),
    );
    const enrichRecord = (record) => {
      const university = universityById.get(record.universityId) || {};
      const program =
        record.scopeType === "programme"
          ? programById.get(record.scopeId) || {}
          : {};
      const programmeGroup =
        record.scopeType === "programme-group"
          ? groupById.get(record.scopeId) || {}
          : {};
      return {
        ...record,
        sourceMonitor:
          state.sourceMonitor[record.basedOnRecordId || record.id] || {},
        school: university.school || record.school || "",
        schoolZh: university.schoolZh || record.schoolZh || "",
        schoolAliasesZh:
          university.schoolAliasesZh || record.schoolAliasesZh || [],
        qsRank: university.qsRank || record.qsRank || 999,
        country: university.country || record.country || "",
        region: university.region || record.region || "",
        program:
          program.name ||
          programmeGroup.name ||
          record.program ||
          (record.scopeType === "institution"
            ? t("institutionWindow")
            : record.scopeId),
      };
    };
    const officialRecords = payload.applications.map((record) =>
      enrichRecord({ ...record, dataStatus: "official" }),
    );
    const predictedRecords = predictionsPayload.predictions.map((record) =>
      enrichRecord({ ...record, dataStatus: "predicted" }),
    );
    state.officialCount = officialRecords.length;
    state.predictionCount = predictedRecords.length;
    state.data = [...officialRecords, ...predictedRecords];
    state.universities.forEach((university) => {
      university.monitor = monitorPayload?.universities?.[university.id] || {};
    });
    const policyByUniversity = new Map(
      state.policies.map((policy) => [policy.universityId, policy]),
    );
    const coverageByUniversity = new Map(
      (state.coverage?.universities || []).map((item) => [
        item.universityId,
        item,
      ]),
    );
    state.universities.forEach((university) => {
      university.windowPolicy = policyByUniversity.get(university.id) || null;
      university.coverage = coverageByUniversity.get(university.id) || null;
    });
    state.meta = { ...payload.meta, ...universityPayload.meta };
    try {
      state.favorites = new Set(
        JSON.parse(localStorage.getItem("gradwindow:favorites") || "[]"),
      );
    } catch {
      state.favorites = new Set();
    }
    loadUrlState();
    if (selectedRankingDefinition().available === false) state.ranking = "qs";
    updateRankingAvailability();

    refreshFilterOptions();
    const legacyIntake = state.intake;
    const matchingLegacyRecord = state.data.find(
      (record) => record.intake === legacyIntake,
    );
    if (matchingLegacyRecord) {
      state.intake = recordIntake(matchingLegacyRecord).key;
    }
    populateIntakeSelect();
    const allowedStatuses = new Set([
      "open",
      "upcoming",
      "future",
      "closed",
      "exception",
      "unknown",
    ]);
    if (!allowedStatuses.has(state.status)) state.status = "open";
    if (
      state.region !== "all" &&
      ![...document.getElementById("region-filter").options].some(
        (option) => option.value === state.region,
      )
    ) {
      state.region = "all";
    }
    if (
      state.intake !== "all" &&
      ![...document.getElementById("intake-filter").options].some(
        (option) => option.value === state.intake,
      )
    ) {
      state.intake = "all";
    }
    document.getElementById("search-input").value = state.search;
    document.getElementById("region-filter").value = state.region;
    document.getElementById("intake-filter").value = state.intake;
    document.getElementById("ranking-filter").value = state.ranking;
    updateRankRangeOptions();
    updateStatusTabs();
    const schoolCount = state.universities.length;
    document.getElementById("total-schools").textContent = schoolCount;
    document.getElementById("total-records").textContent = state.officialCount;
    document.getElementById("total-predictions").textContent =
      state.predictionCount;
    updateDataNotes();
    document.getElementById("demo-banner").hidden = false;
    renderCoverage();
    setupHero();
    setupSubscription();
    bindEvents();
    initAuth({ render, updateFavoriteControls, updateReviewAuthState });
    setupAuthPanel();
    setupReviewPanel();
    setupWindowDetailPanel();
    render();
  } catch (error) {
    const errorState = makeElement("div", { className: "empty-state" });
    errorState.append(
      makeElement("strong", { text: t("loadFailed") }),
      makeElement("span", {
        text: t("useServer"),
      }),
    );
    document.getElementById("application-groups").replaceChildren(errorState);
    console.error(error);
  }
}

init();
