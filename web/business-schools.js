import { translate } from "./i18n.js";

const search = document.getElementById("business-search");
const region = document.getElementById("business-region");
const level = document.getElementById("business-level");
const count = document.getElementById("business-count");
const empty = document.getElementById("business-empty");
const languageToggle = document.getElementById("language-toggle");
const themeToggle = document.getElementById("theme-toggle");
let language =
  localStorage.getItem("gradwindow:language") === "zh" ? "zh" : "en";

function t(key) {
  return translate(language, key);
}

function searchText(value) {
  return value
    .normalize("NFD")
    .replace(/\p{Mark}/gu, "")
    .toLocaleLowerCase();
}

function bilingualText(node) {
  return searchText(`${node.dataset.en} ${node.dataset.zh}`);
}

const schools = [...document.querySelectorAll(".business-school")].map(
  (element) => ({
    element,
    location: element.dataset.region,
    keywords: [
      bilingualText(element.querySelector("h2 a")),
      bilingualText(element.querySelector(".business-school-location")),
      element.dataset.region === "paris" ? "paris 巴黎" : "",
    ].join(" "),
    programmes: [...element.querySelectorAll("[data-level]")].map((row) => ({
      row,
      level: row.dataset.level,
      keywords: bilingualText(row.querySelector("a")),
    })),
  }),
);

function render() {
  const terms = searchText(search.value).trim().split(/\s+/);
  let visible = 0;
  for (const school of schools) {
    const regionMatches =
      region.value === "all" ||
      region.value === school.location ||
      (region.value === "france" && school.location === "paris");
    let hasProgramme = false;
    for (const programme of school.programmes) {
      const keywords = `${school.keywords} ${programme.keywords}`;
      const matches =
        (level.value === "all" || programme.level === level.value) &&
        terms.every((term) => keywords.includes(term));
      programme.row.hidden = !matches;
      hasProgramme ||= matches;
    }
    school.element.hidden = !regionMatches || !hasProgramme;
    visible += Number(!school.element.hidden);
  }
  count.textContent = t(
    visible === 1 ? "businessCountOne" : "businessCount",
  ).replace("{count}", visible);
  empty.hidden = visible > 0;
}

function applyLanguage() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = `${t("businessTitle")} | GradWindow`;
  languageToggle.textContent = language === "zh" ? "EN" : "中文";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-en][data-zh]").forEach((node) => {
    node.textContent = node.dataset[language];
  });
  search.placeholder = t("businessSearch");
  render();
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "☀" : "◐";
}

search.addEventListener("input", render);
region.addEventListener("change", render);
level.addEventListener("change", render);
languageToggle.addEventListener("click", () => {
  language = language === "zh" ? "en" : "zh";
  localStorage.setItem("gradwindow:language", language);
  applyLanguage();
});
themeToggle.addEventListener("click", () => {
  const theme =
    document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("gradwindow:theme", theme);
  applyTheme(theme);
});

applyTheme(
  localStorage.getItem("gradwindow:theme") === "dark" ? "dark" : "light",
);
applyLanguage();
document.getElementById("business-filters").hidden = false;
