import { translate } from "./i18n.js";
import { getApplicationStatus } from "./status.js";
import { canonicalIntake, intakeLabel } from "./intake-filter.js";
import { acronym, makeElement, makeLink, parseDate } from "./dom.js";
import { isRecurringPolicyRecord } from "./window-provenance.js";
import { universityDeepLink } from "./university-deep-link.js";
import {
  countryLabel,
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
  search: "",
  universityId: "",
  qsLimit: 200,
  status: "all",
  month: null,
  language: "en",
  theme: "light",
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
  return records.flatMap((record) => [
    { type: "open", date: record.opensAt, record },
    { type: "deadline", date: record.closesAt, record },
  ]);
}

function filteredRecords() {
  const query = state.search.trim().toLocaleLowerCase("zh-CN");
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
      (!state.universityId || record.universityId === state.universityId) &&
      (state.universityId || record.qsRank <= state.qsLimit) &&
      (state.status === "all" ||
        getApplicationStatus(record) === state.status) &&
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
  const provenance = isRecurringPolicyRecord(event.record)
    ? ` · ${t("recurringPolicyShort")}`
    : "";
  return `${event.type === "open" ? t("calendarEventOpen") : t("calendarEventDeadline")} · ${school}${provenance}`;
}

function makeCalendarEvent(event) {
  const link = makeLink(
    eventLabel(event),
    event.record.applicationUrl,
    `calendar-event ${event.type}`,
  );
  link.title = [
    schoolLabels(event.record, state.language).primary,
    programmeLabel(event.record.scopeId, event.record.program, state.language),
  ].join(" · ");
  return link;
}

function renderCalendar(records) {
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
    cell.appendChild(
      makeElement("span", {
        className: "calendar-day",
        text: date.getUTCDate(),
      }),
    );
    const events = (eventsByDate.get(key) || []).sort((a, b) => {
      if (a.type !== b.type) return a.type === "deadline" ? -1 : 1;
      return a.record.qsRank - b.record.qsRank;
    });
    events
      .slice(0, 4)
      .forEach((event) => cell.appendChild(makeCalendarEvent(event)));
    if (events.length > 4) {
      cell.appendChild(
        makeElement("span", {
          className: "calendar-more",
          text: `+${events.length - 4} ${t("calendarMore")}`,
        }),
      );
    }
    return cell;
  });
  document.getElementById("calendar-grid").replaceChildren(...cells);
}

function renderList(records) {
  const events = calendarEvents(records)
    .filter(
      (event) =>
        monthStart(parseDate(event.date)).getTime() === state.month.getTime(),
    )
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) || a.record.qsRank - b.record.qsRank,
    );
  document.getElementById("calendar-result-count").textContent =
    `${events.length} ${t("calendarEventsUnit")}`;
  const list = document.getElementById("calendar-list");
  if (!events.length) {
    list.replaceChildren(
      makeElement("div", {
        className: "empty-state compact",
        text: t("calendarNoEvents"),
      }),
    );
    return;
  }
  list.replaceChildren(
    ...events.map((event) => {
      const card = makeElement("article", {
        className: `calendar-list-item ${event.type}`,
      });
      const school = schoolLabels(event.record, state.language);
      const intake = intakeLabel(canonicalIntake(event.record), state.language);
      const round = roundLabel(event.record.round, state.language);
      card.append(
        makeElement("span", {
          className: "date-secondary",
          text: `${formatEventDate(event)} · QS #${event.record.qsRank}`,
        }),
        makeLink(eventLabel(event), event.record.applicationUrl, "school-link"),
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
      return card;
    }),
  );
}

function render() {
  const records = filteredRecords();
  ensureCalendarMonth(records);
  renderCalendar(records);
  renderList(records);
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
      state.universityId = "";
      state.search = event.target.value;
      state.month = null;
      render();
    });
  document.getElementById("calendar-qs").addEventListener("change", (event) => {
    state.qsLimit = Number(event.target.value);
    state.month = null;
    render();
  });
  document
    .getElementById("calendar-status")
    .addEventListener("change", (event) => {
      state.status = event.target.value;
      state.month = null;
      render();
    });
  document.getElementById("calendar-prev").addEventListener("click", () => {
    state.month = addMonths(state.month || monthStart(), -1);
    render();
  });
  document.getElementById("calendar-next").addEventListener("click", () => {
    state.month = addMonths(state.month || monthStart(), 1);
    render();
  });
  document.getElementById("calendar-today").addEventListener("click", () => {
    state.month = monthStart();
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
  const deepLink = universityDeepLink(
    window.location.search,
    new Set(universityById.keys()),
  );
  state.universityId = deepLink.universityId;
  if (state.universityId) {
    state.search = universityById.get(state.universityId).school;
    document.getElementById("calendar-search").value = state.search;
  }
  state.records = [
    ...decodeRecordBundle(frontend.records, frontend.universities),
    ...decodeRecordBundle(closed.records, frontend.universities),
  ];
  bindEvents();
  render();
}

init().catch((error) => {
  document
    .getElementById("calendar-grid")
    .replaceChildren(
      makeElement("div", { className: "empty-state", text: t("loadFailed") }),
    );
  console.error(error);
});
