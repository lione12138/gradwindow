import { translate } from "./i18n.js";
import {
  matchesDateAndScope,
  matchesTimeStatus,
  readViewFilters,
  writeViewFilters,
} from "./view-filters.js";
import { createRankingIndex } from "./ranking-filter.js";
import { canonicalIntake, intakeLabel } from "./intake-filter.js";
import { acronym, makeElement, makeLink, parseDate } from "./dom.js";
import { recordProvenance } from "./window-provenance.js";
import { universityDeepLink } from "./university-deep-link.js";
import {
  countryLabel,
  regionLabel,
  programmeLabel,
  programmeSearchTerms,
  roundLabel,
  schoolLabels,
  setProgrammeTranslations,
} from "./localization.js";
import { decodeRecordBundle } from "./frontend-data.js";
import { formatDeadlineDate } from "./deadline-semantics.js";

const state = {
  records: [],
  ...readViewFilters(location.search),
  universities: [],
  rankings: {},
  applicantLabels: {},
  favorites: new Set(),
  month: null,
  language: "en",
  theme: "light",
  selectedDay: "",
  limit: 50,
  view: window.matchMedia("(max-width: 720px)").matches ? "agenda" : "month",
};
let programmeTranslationsPromise = null;

function t(key) {
  return translate(state.language, key);
}

function todayUtc() {
  const now = new Date();
  return new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
}

function monthStart(date = todayUtc()) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
}

function addMonths(date, offset) {
  return new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1),
  );
}

function formatDate(value) {
  return new Intl.DateTimeFormat(state.language === "zh" ? "zh-CN" : "en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parseDate(value));
}

function formatEventDate(event) {
  const formatted = formatDate(event.date);
  return event.type === "deadline"
    ? formatDeadlineDate(event.record, formatted, state.language)
    : formatted;
}

function formatMonth(value) {
  return new Intl.DateTimeFormat(state.language === "zh" ? "zh-CN" : "en-GB", {
    year: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(value);
}

function weekdayFormatter() {
  return new Intl.DateTimeFormat(state.language === "zh" ? "zh-CN" : "en-GB", {
    weekday: "short",
    timeZone: "UTC",
  });
}

function calendarEvents(records) {
  return records
    .flatMap((record) => [
      { type: "open", date: record.opensAt, record },
      { type: "deadline", date: record.closesAt, record },
    ])
    .filter((event) => event.date);
}

function rankingIndex() {
  const rows =
    state.ranking === "qs"
      ? state.universities
          .filter((item) => item.qsPosition != null)
          .map((item) => ({
            universityId: item.id,
            rankPosition: item.qsPosition,
            rankDisplay: item.rankDisplay,
          }))
      : state.rankings.rankings?.[state.ranking]?.rows || [];
  return createRankingIndex(rows).byUniversityId;
}

function filteredRecords() {
  const query = state.search.trim().toLocaleLowerCase("zh-CN");
  const ranks = rankingIndex();
  return state.records.filter((record) => {
    const searchable = [
      record.school,
      record.schoolZh,
      acronym(record.school),
      record.program,
      ...programmeSearchTerms(record.scopeId, record.program),
      record.universityId,
      record.scopeId,
      record.country,
      record.region,
    ]
      .join(" ")
      .toLocaleLowerCase("zh-CN");
    return (
      (!state.selectedUniversityId ||
        record.universityId === state.selectedUniversityId) &&
      (state.selectedUniversityId ||
        (ranks.get(record.universityId)?.rankPosition ?? Infinity) <=
          Number(state.rankLimit)) &&
      matchesDateAndScope(record, state) &&
      matchesTimeStatus(record, state.status) &&
      (!state.favoritesOnly ||
        state.favorites.has(`window:${record.id}`) ||
        state.favorites.has(`university:${record.universityId}`)) &&
      (!query || searchable.includes(query))
    );
  });
}

function ensureCalendarMonth(records) {
  if (state.month) return;
  const nextEvent = calendarEvents(records)
    .filter((event) => parseDate(event.date) >= todayUtc())
    .sort((a, b) => a.date.localeCompare(b.date))[0];
  state.month = nextEvent
    ? monthStart(parseDate(nextEvent.date))
    : monthStart();
}

function eventLabel(event) {
  const school = schoolLabels(event.record, state.language).primary;
  const provenance = ` · ${t({ official: "officialOnly", predicted: "estimatedOnly", recurring: "recurringPolicyShort", review: "statusNeedsCheck" }[recordProvenance(event.record)])}`;
  return `${event.type === "open" ? t("calendarEventOpen") : t("calendarEventDeadline")} · ${school}${provenance}`;
}

function makeCalendarEvent(event) {
  const params = writeViewFilters(state);
  params.set("window", event.record.id);
  const link = makeLink(
    eventLabel(event),
    `./?${params}#application-board`,
    `calendar-event ${event.type}`,
  );
  link.removeAttribute("target");
  link.title = [
    schoolLabels(event.record, state.language).primary,
    programmeLabel(event.record.scopeId, event.record.program, state.language),
  ].join(" · ");
  return link;
}

function selectDay(key) {
  state.selectedDay = key;
  state.limit = 50;
  render();
  document.getElementById("calendar-list-title").focus({ preventScroll: true });
  document
    .getElementById("calendar-list-title")
    .scrollIntoView({ block: "start" });
}

function renderCalendar(records) {
  const ranks = rankingIndex();
  ensureCalendarMonth(records);
  document.getElementById("calendar-month-label").textContent = formatMonth(
    state.month,
  );

  const weekdays = document.getElementById("calendar-weekdays");
  const formatter = weekdayFormatter();
  const weekStart = new Date(Date.UTC(2026, 5, 15));
  weekdays.replaceChildren(
    ...Array.from({ length: 7 }, (_, index) =>
      makeElement("span", {
        text: formatter.format(
          new Date(weekStart.getTime() + index * 86_400_000),
        ),
      }),
    ),
  );

  const monthIndex = state.month.getUTCMonth();
  const firstOffset = (state.month.getUTCDay() + 6) % 7;
  const firstCell = new Date(
    Date.UTC(state.month.getUTCFullYear(), monthIndex, 1 - firstOffset),
  );
  const eventsByDate = new Map();
  calendarEvents(records).forEach((event) => {
    if (monthStart(parseDate(event.date)).getTime() !== state.month.getTime())
      return;
    const events = eventsByDate.get(event.date) || [];
    events.push(event);
    eventsByDate.set(event.date, events);
  });

  const todayKey = todayUtc().toISOString().slice(0, 10);
  const cells = Array.from({ length: 42 }, (_, index) => {
    const date = new Date(firstCell.getTime() + index * 86_400_000);
    const key = date.toISOString().slice(0, 10);
    const cell = makeElement("div", {
      className: `calendar-cell${date.getUTCMonth() === monthIndex ? "" : " muted"}${key === todayKey ? " today" : ""}`,
    });
    const dayButton = makeElement("button", {
      className: "calendar-day",
      text: date.getUTCDate(),
    });
    dayButton.type = "button";
    dayButton.setAttribute("aria-label", formatDate(key));
    dayButton.setAttribute("aria-pressed", String(state.selectedDay === key));
    dayButton.addEventListener("click", () => {
      state.month = monthStart(date);
      selectDay(key);
    });
    cell.appendChild(dayButton);
    const events = (eventsByDate.get(key) || []).sort((a, b) => {
      if (a.type !== b.type) return a.type === "deadline" ? -1 : 1;
      return (
        (ranks.get(a.record.universityId)?.rankPosition ?? Infinity) -
        (ranks.get(b.record.universityId)?.rankPosition ?? Infinity)
      );
    });
    events
      .slice(0, 4)
      .forEach((event) => cell.appendChild(makeCalendarEvent(event)));
    if (events.length) {
      const more = makeElement("button", {
        className: "calendar-more",
        text: t("calendarDayEvents").replace("{count}", events.length),
      });
      more.type = "button";
      more.addEventListener("click", () => {
        state.month = monthStart(date);
        selectDay(key);
      });
      cell.appendChild(more);
    }
    return cell;
  });
  document.getElementById("calendar-grid").replaceChildren(...cells);
}

function renderList(records) {
  const ranks = rankingIndex();
  const events = calendarEvents(records)
    .filter(
      (event) =>
        monthStart(parseDate(event.date)).getTime() === state.month.getTime() &&
        (!state.selectedDay || event.date === state.selectedDay),
    )
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) ||
        (ranks.get(a.record.universityId)?.rankPosition ?? Infinity) -
          (ranks.get(b.record.universityId)?.rankPosition ?? Infinity),
    );
  document.getElementById("calendar-result-count").textContent =
    `${events.length} ${t("calendarEventsUnit")}`;
  const list = document.getElementById("calendar-list");
  document.getElementById("calendar-list-title").textContent = state.selectedDay
    ? formatDate(state.selectedDay)
    : t("calendarMonthEvents");
  document.getElementById("calendar-load-more").hidden =
    events.length <= state.limit;
  if (!events.length) {
    list.replaceChildren(
      makeElement("div", {
        className: "empty-state compact",
        text: t("calendarNoEvents"),
      }),
    );
    return;
  }
  const daySections = new Map();
  events.slice(0, state.limit).forEach((event) => {
    if (!daySections.has(event.date)) {
      const section = makeElement("section", {
        className: "calendar-day-section",
      });
      section.appendChild(makeElement("h3", { text: formatDate(event.date) }));
      daySections.set(event.date, section);
    }
    const card = makeElement("article", {
      className: `calendar-list-item ${event.type}`,
    });
    const school = schoolLabels(event.record, state.language);
    const intake = intakeLabel(canonicalIntake(event.record), state.language);
    const round = roundLabel(event.record.round, state.language);
    card.append(
      makeElement("span", {
        className: "date-secondary",
        text: `${formatEventDate(event)} · ${state.ranking.toUpperCase()} ${ranks.get(event.record.universityId)?.rankDisplay || "—"}`,
      }),
      makeCalendarEvent(event),
      makeElement("span", {
        className: "school-meta",
        text: [
          programmeLabel(
            event.record.scopeId,
            event.record.program,
            state.language,
          ),
          intake,
          round,
          countryLabel(event.record.country, state.language),
          school.secondary,
        ]
          .filter(Boolean)
          .join(" · "),
      }),
    );
    card.appendChild(
      makeElement("p", {
        text: (event.record.applicantCategories || [])
          .map((id) => state.applicantLabels[id]?.[state.language] || id)
          .join(" · "),
      }),
    );
    card.appendChild(
      makeLink(t("applyOfficial"), event.record.applicationUrl, "apply-link"),
    );
    if (event.record.sourceUrl)
      card.appendChild(
        makeLink(t("dataSource"), event.record.sourceUrl, "source-link"),
      );
    daySections.get(event.date).appendChild(card);
  });
  list.replaceChildren(...daySections.values());
}

function render() {
  for (const option of document.getElementById("calendar-qs").options) {
    option.textContent = `${state.ranking.toUpperCase()} Top ${option.value}`;
  }
  const records = filteredRecords();
  ensureCalendarMonth(records);
  renderCalendar(records);
  renderList(records);
  document.getElementById("calendar-month-grid").hidden =
    state.view !== "month";
  document
    .getElementById("calendar-agenda-view")
    .setAttribute("aria-pressed", String(state.view === "agenda"));
  document
    .getElementById("calendar-month-view")
    .setAttribute("aria-pressed", String(state.view === "month"));
  document.getElementById("calendar-clear-day").hidden = !state.selectedDay;
  document.getElementById("calendar-month-picker").value = state.month
    .toISOString()
    .slice(0, 7);
  const params = writeViewFilters(state);
  const trackerUrl = `./${params.size ? `?${params}` : ""}#application-board`;
  document
    .querySelectorAll('.calendar-back-link, a[href="./#application-board"]')
    .forEach((link) => (link.href = trackerUrl));
  document.getElementById("calendar-filter-context").textContent =
    `${t("calendarFilterNote")} ${filterDescription()}`;
  params.set("month", state.month.toISOString().slice(0, 7));
  params.set("view", state.view);
  if (state.selectedDay) params.set("day", state.selectedDay);
  history.replaceState(null, "", `${location.pathname}?${params}`);
}

function filterDescription() {
  const labels = [
    t(
      {
        official: "officialOnly",
        all: "allDateTypes",
        estimated: "estimatedOnly",
        recurring: "recurringOnly",
        review: "statusNeedsCheck",
      }[state.dateType],
    ),
  ];
  if (state.region !== "all")
    labels.push(regionLabel(state.region, state.language));
  if (state.intake !== "all") {
    const [term, year] = state.intake.split(":");
    labels.push(intakeLabel({ term, year: Number(year) }, state.language));
  }
  if (state.applicantCategory !== "all")
    labels.push(
      state.applicantLabels[state.applicantCategory]?.[state.language] ||
        state.applicantCategory,
    );
  if (state.deadlineRange !== "all")
    labels.push(t(`deadlineNext${state.deadlineRange}`));
  if (state.favoritesOnly) labels.push(t("favoritesOnly"));
  return labels.join(" · ");
}

function applyStaticTranslations() {
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const translated = t(node.dataset.i18n);
    if (translated !== node.dataset.i18n) node.textContent = translated;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    const translated = t(node.dataset.i18nPlaceholder);
    if (translated !== node.dataset.i18nPlaceholder)
      node.placeholder = translated;
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    const translated = t(node.dataset.i18nAriaLabel);
    if (translated !== node.dataset.i18nAriaLabel) {
      node.setAttribute("aria-label", translated);
    }
  });
  document.getElementById("language-toggle").textContent =
    state.language === "en" ? "中文" : "EN";
  document.getElementById("theme-toggle").textContent =
    state.theme === "dark" ? "☀" : "☾";
  document.title =
    state.language === "zh"
      ? "GradWindow · 申请日历"
      : "GradWindow · Application Calendar";
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  localStorage.setItem("gradwindow:theme", state.theme);
  const button = document.getElementById("theme-toggle");
  if (button) button.textContent = state.theme === "dark" ? "☀" : "☾";
}

function bindEvents() {
  for (const view of ["agenda", "month"]) {
    document
      .getElementById(`calendar-${view}-view`)
      .addEventListener("click", () => {
        state.view = view;
        render();
      });
  }
  document
    .getElementById("calendar-load-more")
    .addEventListener("click", () => {
      state.limit += 50;
      render();
    });
  document
    .getElementById("calendar-clear-day")
    .addEventListener("click", () => {
      state.selectedDay = "";
      state.limit = 50;
      render();
    });
  document
    .getElementById("calendar-month-picker")
    .addEventListener("change", (event) => {
      if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(event.target.value)) return;
      state.month = new Date(`${event.target.value}-01T00:00:00Z`);
      state.selectedDay = "";
      state.limit = 50;
      render();
    });
  document
    .getElementById("calendar-ranking")
    .addEventListener("change", (event) => {
      state.ranking = event.target.value;
      state.selectedUniversityId = "";
      state.selectedDay = "";
      state.limit = 50;
      render();
    });
  document
    .getElementById("language-toggle")
    .addEventListener("click", async () => {
      state.language = state.language === "en" ? "zh" : "en";
      if (state.language === "zh") await ensureProgrammeTranslations();
      localStorage.setItem("gradwindow:language", state.language);
      applyStaticTranslations();
      render();
    });
  document.getElementById("theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    applyTheme();
  });
  document
    .getElementById("calendar-search")
    .addEventListener("input", (event) => {
      state.selectedUniversityId = "";
      state.search = event.target.value;
      state.month = null;
      state.selectedDay = "";
      state.limit = 50;
      render();
    });
  document.getElementById("calendar-qs").addEventListener("change", (event) => {
    state.rankLimit = event.target.value;
    state.month = null;
    state.selectedDay = "";
    state.limit = 50;
    render();
  });
  document
    .getElementById("calendar-status")
    .addEventListener("change", (event) => {
      state.status = event.target.value;
      state.month = null;
      state.selectedDay = "";
      state.limit = 50;
      render();
    });
  document.getElementById("calendar-prev").addEventListener("click", () => {
    state.month = addMonths(state.month || monthStart(), -1);
    state.selectedDay = "";
    state.limit = 50;
    render();
  });
  document.getElementById("calendar-next").addEventListener("click", () => {
    state.month = addMonths(state.month || monthStart(), 1);
    state.selectedDay = "";
    state.limit = 50;
    render();
  });
  document.getElementById("calendar-today").addEventListener("click", () => {
    state.month = monthStart();
    state.selectedDay = "";
    state.limit = 50;
    render();
  });
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function fetchOptionalJson(path, fallback) {
  try {
    return await fetchJson(path);
  } catch (error) {
    console.warn(`Optional data unavailable: ${path}`, error);
    return fallback;
  }
}

async function ensureProgrammeTranslations() {
  if (!programmeTranslationsPromise) {
    programmeTranslationsPromise = fetchOptionalJson(
      "./data/programme-translations.json",
      { translations: {} },
    ).then((payload) => setProgrammeTranslations(payload));
  }
  await programmeTranslationsPromise;
}

async function init() {
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

  const [frontend, closed] = await Promise.all([
    fetchJson("./data/frontend-index.json"),
    fetchJson("./data/frontend-closed.json"),
  ]);
  if (state.language === "zh") await ensureProgrammeTranslations();
  const universityById = new Map(
    frontend.universities.map((item) => [item.id, item]),
  );
  state.universities = frontend.universities;
  state.rankings = frontend.rankings || { rankings: {} };
  state.applicantLabels = frontend.applicantCategoryLabels || {};
  try {
    state.favorites = new Set(
      JSON.parse(
        sessionStorage.getItem("gradwindow:calendar-favorites") ||
          localStorage.getItem("gradwindow:favorites") ||
          "[]",
      ),
    );
  } catch {
    state.favorites = new Set();
  }
  const deepLink = universityDeepLink(
    window.location.search,
    new Set(universityById.keys()),
  );
  state.selectedUniversityId = deepLink.universityId;
  if (state.selectedUniversityId) {
    state.search = universityById.get(state.selectedUniversityId).school;
  }
  document.getElementById("calendar-search").value = state.search;
  document.getElementById("calendar-ranking").value = state.ranking;
  document.getElementById("calendar-qs").value = state.rankLimit;
  document.getElementById("calendar-status").value = state.status;
  const urlParams = new URLSearchParams(location.search);
  const month = urlParams.get("month");
  if (/^\d{4}-(0[1-9]|1[0-2])$/.test(month || ""))
    state.month = new Date(`${month}-01T00:00:00Z`);
  const day = urlParams.get("day");
  if (
    state.month &&
    /^\d{4}-\d{2}-\d{2}$/.test(day || "") &&
    day.startsWith(month) &&
    !Number.isNaN(Date.parse(day)) &&
    new Date(day).toISOString().slice(0, 10) === day
  )
    state.selectedDay = day;
  if (["month", "agenda"].includes(urlParams.get("view")))
    state.view = urlParams.get("view");
  state.records = [
    ...decodeRecordBundle(frontend.records, frontend.universities),
    ...decodeRecordBundle(closed.records, frontend.universities),
  ];
  bindEvents();
  render();
}

init().catch((error) => {
  document
    .getElementById("calendar-list")
    .replaceChildren(
      makeElement("div", { className: "empty-state", text: t("loadFailed") }),
    );
  console.error(error);
});
