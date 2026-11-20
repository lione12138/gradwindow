import { makeElement, makeLink, parseDate } from "./dom.js";
import { translate } from "./i18n.js";
import { countryLabel } from "./localization.js";
import { getApplicationStatus } from "./status.js";

const search = document.getElementById("undergraduate-search");
const statusFilter = document.getElementById("undergraduate-status");
const count = document.getElementById("undergraduate-count");
const results = document.getElementById("undergraduate-results");
const languageToggle = document.getElementById("language-toggle");
const themeToggle = document.getElementById("theme-toggle");
const statusLabels = {
  open: "statusOpen",
  upcoming: "statusUpcoming",
  future: "statusFuture",
  closed: "undergraduateDeadlinePassed",
};

let language =
  localStorage.getItem("gradwindow:language") === "zh" ? "zh" : "en";
let records = null;
let loadFailed = false;

function t(key) {
  return translate(language, key);
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
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "☀" : "◐";
}

function datePair(label, value, formatter) {
  const pair = makeElement("div");
  const time = makeElement("time", {
    text: formatter.format(parseDate(value)),
  });
  time.dateTime = value;
  const date = makeElement("dd");
  date.append(time);
  pair.append(makeElement("dt", { text: t(label) }), date);
  return pair;
}

function renderWindow(record, status, formatter) {
  const localized = language === "zh";
  const item = makeElement("li", { className: "undergraduate-window" });
  const school = localized ? record.schoolZh : record.school;
  const heading = makeElement("p", {
    className: "undergraduate-school",
    text: [record.rankDisplay, school, countryLabel(record.country, language)]
      .filter(Boolean)
      .join(" · "),
  });
  const title = makeElement("h2", {
    text: localized ? record.scopeZh : record.scope,
  });
  const labels = makeElement("p", {
    className: "undergraduate-round",
    text: `${localized ? record.intakeZh : record.intake} · ${t(`undergraduateRound-${record.round}`)}`,
  });
  const statusLabel =
    status === "closed" && record.round === "equal-consideration"
      ? "undergraduateEqualConsiderationPassed"
      : statusLabels[status];
  const badges = makeElement("div", { className: "undergraduate-badges" });
  badges.append(
    makeElement("span", { text: t("undergraduateInternational") }),
    makeElement("span", { text: t(statusLabel) }),
  );
  badges.dataset.status = status;
  const dates = makeElement("dl", { className: "undergraduate-dates" });
  dates.append(
    datePair("undergraduateOpens", record.opensAt, formatter),
    datePair("undergraduateCloses", record.closesAt, formatter),
  );
  const links = makeElement("div", { className: "undergraduate-links" });
  links.append(
    makeLink(
      t("undergraduateApply"),
      record.applicationUrl,
      "undergraduate-apply",
    ),
    makeLink(t("undergraduateDeadlineSource"), record.sourceUrl),
  );
  if (record.openingSourceUrl !== record.sourceUrl) {
    links.append(
      makeLink(t("undergraduateOpeningSource"), record.openingSourceUrl),
    );
  }
  if (record.eligibilitySourceUrl !== record.sourceUrl) {
    links.append(
      makeLink(
        t("undergraduateEligibilitySource"),
        record.eligibilitySourceUrl,
      ),
    );
  }
  item.append(heading, title, labels, badges, dates, links);
  return item;
}

function render() {
  if (records === null) {
    count.textContent = t(
      loadFailed ? "undergraduateLoadError" : "undergraduateLoading",
    );
    return;
  }
  const query = search.value.trim().toLowerCase();
  const matches = records
    .map((record) => ({ record, status: getApplicationStatus(record) }))
    .filter(({ record, status }) => {
      if (statusFilter.value !== "all" && statusFilter.value !== status)
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
  const schools = new Set(matches.map(({ record }) => record.universityId));
  count.textContent = matches.length
    ? t("undergraduateCount")
        .replace("{schools}", schools.size)
        .replace("{windows}", matches.length)
    : t("undergraduateEmpty");
  const formatter = new Intl.DateTimeFormat(document.documentElement.lang, {
    dateStyle: "long",
    timeZone: "UTC",
  });
  results.replaceChildren(
    ...matches.map(({ record, status }) =>
      renderWindow(record, status, formatter),
    ),
  );
}

async function loadWindows() {
  try {
    const response = await fetch("./data/undergraduate-applications.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    records = data.sort(
      (a, b) =>
        (a.qsRank ?? Infinity) - (b.qsRank ?? Infinity) ||
        a.scope.localeCompare(b.scope) ||
        b.closesAt.localeCompare(a.closesAt),
    );
  } catch {
    loadFailed = true;
  }
  render();
}

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
search.addEventListener("input", render);
statusFilter.addEventListener("change", render);
applyLanguage();
applyTheme(
  localStorage.getItem("gradwindow:theme") === "dark" ? "dark" : "light",
);
loadWindows();
