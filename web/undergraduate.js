import { makeCalendarMenu } from "./calendar-export.js";
import { makeElement, makeLink, parseDate } from "./dom.js";
import { translate } from "./i18n.js";
import { countryLabel, regionLabel, schoolLabels } from "./localization.js";
import { countUniversitiesByStatus, getApplicationStatus } from "./status.js";
import {
  createSchoolPagination,
  createTrackerTable,
  formatRank,
  makeCell,
  makeSchoolDisplay,
  makeSchoolGroupSummary,
  paginateSchools,
} from "./tracker-table.js";
import { groupWindowRecordsForDisplay } from "./window-grouping.js";

const search = document.getElementById("undergraduate-search");
const statusFilter = document.getElementById("undergraduate-status");
const regionFilter = document.getElementById("undergraduate-region");
const intakeFilter = document.getElementById("undergraduate-intake");
const sortFilter = document.getElementById("undergraduate-sort");
const count = document.getElementById("undergraduate-count");
const results = document.getElementById("undergraduate-results");
const empty = document.getElementById("undergraduate-empty");
const groupActions = document.getElementById("undergraduate-group-actions");
const expand = document.getElementById("undergraduate-expand");
const collapse = document.getElementById("undergraduate-collapse");
const languageToggle = document.getElementById("language-toggle");
const themeToggle = document.getElementById("theme-toggle");
const statusLabels = {
  all: "statusAll",
  open: "statusOpen",
  upcoming: "statusUpcoming",
  future: "statusFuture",
  closed: "undergraduateDeadlinePassed",
};
const expandedGroups = new Set();
const statusButtons = new Map();
let selectedStatus = "all";
let language =
  localStorage.getItem("gradwindow:language") === "zh" ? "zh" : "en";
let records = null;
let loadFailed = false;
let currentPage = 1;
let visibleGroups = [];

function t(key) {
  return translate(language, key);
}

function populateFilter(select, options) {
  const selected = select.value;
  select.replaceChildren(
    select.options[0],
    ...options.map(([value, label]) => new Option(label, value)),
  );
  select.value = selected;
}

function refreshFilterOptions() {
  if (!records) return;
  const regions = [
    ...new Set(records.map(({ region }) => region).filter(Boolean)),
  ];
  const intakes = new Map(
    records.map(({ intake, intakeZh }) => [
      intake,
      language === "zh" ? intakeZh : intake,
    ]),
  );
  populateFilter(
    regionFilter,
    regions.sort().map((region) => [region, regionLabel(region, language)]),
  );
  populateFilter(intakeFilter, [...intakes].sort());
}

function applyLanguage() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = `${t("undergraduateTitle")} | GradWindow`;
  languageToggle.textContent = language === "zh" ? "EN" : "中文";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  search.placeholder = t("searchPlaceholder");
  refreshFilterOptions();
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "☀" : "◐";
}

function dateStack(value, label, formatter) {
  const stack = document.createDocumentFragment();
  const date = makeElement("time", {
    className: "date-primary",
    text: formatter.format(parseDate(value)),
  });
  date.dateTime = value;
  stack.append(date);
  if (label)
    stack.append(
      makeElement("span", { className: "date-secondary", text: label }),
    );
  return stack;
}

function admissionsStatus(record) {
  const status = getApplicationStatus(record);
  return t(
    status === "closed" && record.round === "equal-consideration"
      ? "undergraduateEqualConsiderationPassed"
      : statusLabels[status],
  );
}

function programmeContent(record, { scope, intake, round }) {
  const content = document.createDocumentFragment();
  content.append(
    makeElement("span", {
      className: "application-action-summary",
      text: admissionsStatus(record),
    }),
    makeLink(scope, record.sourceUrl, "program-link date-primary"),
    makeElement("span", {
      className: "date-secondary",
      text: `${intake} · ${round}`,
    }),
  );
  return content;
}

function sourceLinks(record) {
  const links = document.createDocumentFragment();
  links.append(
    makeLink(t("undergraduateDeadlineSource"), record.sourceUrl, "source-link"),
  );
  if (record.openingSourceUrl !== record.sourceUrl) {
    links.append(
      makeLink(
        t("undergraduateOpeningSource"),
        record.openingSourceUrl,
        "source-link",
      ),
    );
  }
  if (record.eligibilitySourceUrl !== record.sourceUrl) {
    links.append(
      makeLink(
        t("undergraduateEligibilitySource"),
        record.eligibilitySourceUrl,
        "source-link",
      ),
    );
  }
  return links;
}

function applicationRow(
  record,
  { programme, opening, deadline, action, source },
) {
  const row = makeElement("tr", { className: "window-card-row" });
  const rankDisplay = record.rankDisplay ?? record.qsRank;
  const sourceCell = makeCell(t("dataSource"), source);
  sourceCell.className = "application-source-cell";
  row.append(
    makeCell(
      t("undergraduateQsRank"),
      makeElement("span", {
        className: "rank-cell",
        text: rankDisplay == null ? "—" : formatRank(rankDisplay),
      }),
    ),
    makeCell(t("universityEntry"), makeSchoolDisplay(record, language)),
    makeCell(t("programmeIntake"), programme),
    makeCell(
      t("applicantGroup"),
      makeElement("span", {
        className: "applicant-category",
        text: t("undergraduateInternational"),
      }),
    ),
    makeCell(t("undergraduateOpens"), opening),
    makeCell(t("undergraduateCloses"), deadline),
    makeCell(t("graduateApplication"), action),
    sourceCell,
  );
  return row;
}

function renderWindow(record, formatter) {
  const scope = language === "zh" ? record.scopeZh : record.scope;
  const intake = language === "zh" ? record.intakeZh : record.intake;
  const round = t(`undergraduateRound-${record.round}`);
  const equalConsideration = record.round === "equal-consideration";
  const deadlineLabel = t(
    equalConsideration
      ? "undergraduateEqualConsiderationCloses"
      : "undergraduateCloses",
  );
  const school = schoolLabels(record, language).primary;
  const action = makeElement("div", {
    className: "undergraduate-window-actions",
  });
  action.append(
    makeLink(
      t("undergraduateApply"),
      record.applicationUrl,
      "undergraduate-apply",
    ),
    makeCalendarMenu(record, {
      translate: t,
      title: `${school} · ${scope} · ${deadlineLabel}`,
      notes: [`${intake} · ${round}`, t("undergraduateCalendarTimeNote")],
    }),
  );
  const row = applicationRow(record, {
    programme: programmeContent(record, { scope, intake, round }),
    opening: dateStack(record.opensAt, t("undergraduateOpens"), formatter),
    deadline: dateStack(
      record.closesAt,
      equalConsideration ? deadlineLabel : "",
      formatter,
    ),
    action,
    source: sourceLinks(record),
  });
  row.classList.add("undergraduate-window-row");
  return row;
}

function renderUniversity(tbody, group, formatter) {
  const windows = group.records;
  if (!group.collapsible) {
    tbody.append(renderWindow(windows[0], formatter));
    return;
  }
  const expanded = expandedGroups.has(group.key);
  const { summary, toggle } = makeSchoolGroupSummary(
    new Set(windows.map(({ scope }) => scope)).size,
    windows.length,
    expanded,
    t,
  );
  const active = windows.filter(
    (record) => getApplicationStatus(record) !== "closed",
  );
  const dateWindows = active.length ? active : windows;
  const opening = dateWindows.map(({ opensAt }) => opensAt).sort()[0];
  const deadlines = dateWindows.map(({ closesAt }) => closesAt).sort();
  const deadline = active.length ? deadlines[0] : deadlines.at(-1);
  const row = applicationRow(windows[0], {
    programme: summary,
    opening: dateStack(opening, t("earliestOpening"), formatter),
    deadline: dateStack(
      deadline,
      t(active.length ? "nextDeadlineLabel" : "undergraduateDeadlinePassed"),
      formatter,
    ),
    action: makeElement("span", { text: "—" }),
    source: makeElement("span", {
      className: "source-badge discovered school-group-source",
      text: t("verifiedDates"),
    }),
  });
  row.classList.add(
    "university-group-parent",
    `university-group-parent--${expanded ? "expanded" : "collapsed"}`,
  );
  row.dataset.groupKey = group.key;
  row.dataset.groupState = expanded ? "expanded" : "collapsed";
  toggle.addEventListener("click", () => {
    if (expanded) expandedGroups.delete(group.key);
    else expandedGroups.add(group.key);
    render();
    results
      .querySelector(
        `[data-group-key="${CSS.escape(group.key)}"] .university-group-toggle`,
      )
      ?.focus({ preventScroll: true });
  });
  row.addEventListener("click", (event) => {
    if (!event.target.closest("a, button")) toggle.click();
  });
  tbody.append(row);
  if (expanded) {
    const children = windows.map((record) => renderWindow(record, formatter));
    children.forEach((child) => {
      child.classList.add("university-group-child");
      child.dataset.universityGroup = group.universityId;
    });
    children[0].classList.add("university-group-child--first");
    children.at(-1).classList.add("university-group-child--last");
    tbody.append(...children);
  }
}

function filteredWindows() {
  const query = search.value.trim().toLowerCase();
  return records.filter((record) => {
    if (regionFilter.value !== "all" && regionFilter.value !== record.region)
      return false;
    if (intakeFilter.value !== "all" && intakeFilter.value !== record.intake)
      return false;
    return [
      record.school,
      record.schoolZh,
      record.scope,
      record.scopeZh,
      record.country,
      countryLabel(record.country, "zh"),
    ].some((value) => value.toLowerCase().includes(query));
  });
}

function updateStatusButtons(windows) {
  const counts = countUniversitiesByStatus(windows);
  counts.all = new Set(windows.map(({ universityId }) => universityId)).size;
  for (const [status, button] of statusButtons) {
    const active = status === selectedStatus;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    button.firstChild.textContent = t(statusLabels[status]);
    button.lastChild.textContent = counts[status];
  }
}

function compareWindows(a, b) {
  const dateField = { opens: "opensAt", deadline: "closesAt" }[
    sortFilter.value
  ];
  const dateOrder = dateField ? a[dateField].localeCompare(b[dateField]) : 0;
  return (
    dateOrder ||
    (a.qsRank ?? Infinity) - (b.qsRank ?? Infinity) ||
    a.school.localeCompare(b.school) ||
    a.scope.localeCompare(b.scope) ||
    b.closesAt.localeCompare(a.closesAt)
  );
}

function renderFirstPage() {
  currentPage = 1;
  render();
}

function changePage(page) {
  currentPage = page;
  render();
  const heading = results.querySelector(".group-heading h3");
  heading.tabIndex = -1;
  heading.focus({ preventScroll: true });
  heading.scrollIntoView({ block: "start" });
}

function render() {
  if (records === null) {
    updateStatusButtons([]);
    count.textContent = t(
      loadFailed ? "undergraduateLoadError" : "undergraduateLoading",
    );
    return;
  }
  const windows = filteredWindows();
  updateStatusButtons(windows);
  const matches = windows
    .filter(
      (record) =>
        selectedStatus === "all" ||
        getApplicationStatus(record) === selectedStatus,
    )
    .sort(compareWindows);
  const groups = groupWindowRecordsForDisplay(matches);
  const pagination = paginateSchools(groups, currentPage);
  currentPage = pagination.page;
  visibleGroups = pagination.items.filter(({ collapsible }) => collapsible);
  groupActions.hidden = visibleGroups.length === 0;
  expand.disabled = visibleGroups.every(({ key }) => expandedGroups.has(key));
  collapse.disabled = visibleGroups.every(
    ({ key }) => !expandedGroups.has(key),
  );
  const windowCount = `${matches.length} ${t("windows")}`;
  count.replaceChildren(
    makeElement("strong", { text: `${groups.length} ${t("universities")}` }),
    makeElement("span", { text: "·" }),
    makeElement("span", { text: windowCount }),
  );
  empty.hidden = matches.length > 0;
  results.replaceChildren();
  if (!matches.length) return;

  const formatter = new Intl.DateTimeFormat(document.documentElement.lang, {
    dateStyle: "long",
    timeZone: "UTC",
  });
  const { section, tbody } = createTrackerTable({
    status: selectedStatus,
    heading: {
      title: `${t("verifiedDates")} · ${t(statusLabels[selectedStatus])}`,
      description: t("undergraduateInternational"),
    },
    countLabel: windowCount,
    columns: [
      { label: t("undergraduateQsRank"), sort: "rank" },
      t("universityEntry"),
      t("programmeIntake"),
      t("applicantGroup"),
      { label: t("undergraduateOpens"), sort: "opens" },
      { label: t("undergraduateCloses"), sort: "deadline" },
      t("graduateApplication"),
      t("dataSource"),
    ],
    tableClass: "undergraduate-table",
    sort: sortFilter.value,
    onSort(sort) {
      sortFilter.value = sort;
      renderFirstPage();
      results
        .querySelector(`[data-sort="${sort}"]`)
        ?.focus({ preventScroll: true });
    },
  });
  pagination.items.forEach((group) =>
    renderUniversity(tbody, group, formatter),
  );
  section.append(createSchoolPagination(pagination, t, changePage));
  results.append(section);
}

async function loadWindows() {
  try {
    const response = await fetch("./data/undergraduate-applications.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    records = await response.json();
    refreshFilterOptions();
  } catch {
    loadFailed = true;
  }
  render();
}

Object.keys(statusLabels).forEach((status) => {
  const button = makeElement("button", { className: "status-tab" });
  button.type = "button";
  button.dataset.status = status;
  button.append(makeElement("span"), makeElement("span"));
  button.addEventListener("click", () => {
    selectedStatus = status;
    renderFirstPage();
  });
  statusButtons.set(status, button);
  statusFilter.append(button);
});
languageToggle.addEventListener("click", () => {
  language = language === "zh" ? "en" : "zh";
  localStorage.setItem("gradwindow:language", language);
  applyLanguage();
  render();
});
themeToggle.addEventListener("click", () => {
  const theme =
    document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("gradwindow:theme", theme);
  applyTheme(theme);
});
expand.addEventListener("click", () => {
  visibleGroups.forEach(({ key }) => expandedGroups.add(key));
  render();
  collapse.focus();
});
collapse.addEventListener("click", () => {
  visibleGroups.forEach(({ key }) => expandedGroups.delete(key));
  render();
  expand.focus();
});
search.addEventListener("input", renderFirstPage);
[regionFilter, intakeFilter, sortFilter].forEach((filter) =>
  filter.addEventListener("change", renderFirstPage),
);
applyLanguage();
applyTheme(
  localStorage.getItem("gradwindow:theme") === "dark" ? "dark" : "light",
);
render();
loadWindows();
