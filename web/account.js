import { state } from "./state.js";
import { openAuthPanel, persistFavorites } from "./auth.js";
import { makeElement, makeLink } from "./dom.js";
import { programmeLabel, schoolLabels } from "./localization.js";
import { recordProvenance } from "./window-provenance.js";
import { makeCalendarMenu } from "./calendar-export.js";
import { canonicalIntake, intakeLabel } from "./intake-filter.js";
import { formatDeadlineDate } from "./deadline-semantics.js";

const copy = {
  en: {
    title: "My application space",
    greeting: "Welcome back",
    subtitle: "Your shortlist and the dates that matter, in one place.",
    browse: "Explore universities",
    settings: "Account settings",
    schools: "Saved universities",
    projects: "Saved programmes / windows",
    calendar: "My calendar",
    upcoming: "Next 30 days",
    empty:
      "Nothing saved yet. Explore the tracker and save a university or programme to start your shortlist.",
    calendarHelp:
      "Official opening dates and deadlines from your saved universities and programmes. Select a day to see its events.",
    noEvents: "No application events for this selection.",
    allMonth: "Whole month",
    previous: "Previous month",
    next: "Next month",
    today: "Today",
    open: "Opens",
    deadline: "Deadline",
    remove: "Remove",
    source: "Official source",
    profile: "Your plan",
    intake: "Target intake",
    country: "Country / region",
    notSet: "Not set yet",
    signedOut: "Sign in to see your personal homepage",
    signIn: "Sign in / create account",
    loading: "Loading your saved applications…",
    loadError: "Some saved applications could not load. Please retry.",
    retry: "Retry",
    missing: "This saved item is no longer in the published catalogue.",
    official: "Verified official dates",
    predicted: "Unofficial estimate",
    recurring: "Recurring policy",
    review: "Needs review",
    sync: "Saved items sync across your devices.",
    syncError:
      "Cloud sync failed. Your changes are kept on this device. Try again.",
    syncing: "Syncing your saved items…",
    showMore: "Show more",
  },
  zh: {
    title: "我的申请主页",
    greeting: "欢迎回来",
    subtitle: "把心仪学校、收藏项目和重要日期，放在一起。",
    browse: "继续找学校",
    settings: "账号设置",
    schools: "收藏的学校",
    projects: "收藏的项目 / 申请窗口",
    calendar: "我的小日历",
    upcoming: "未来 30 天",
    empty:
      "还没有收藏。去申请看板找找心仪的学校和项目，点一下收藏，就会出现在这里。",
    calendarHelp:
      "显示收藏学校及项目已核验的正式开放、截止日期。点击日期查看当天事项。",
    noEvents: "这段时间没有申请事项。",
    allMonth: "整月事项",
    previous: "上个月",
    next: "下个月",
    today: "今天",
    open: "开放申请",
    deadline: "截止申请",
    remove: "取消收藏",
    source: "查看官网",
    profile: "我的申请计划",
    intake: "目标入学季",
    country: "国家 / 地区",
    notSet: "尚未设置",
    signedOut: "登录后查看你的个人主页",
    signIn: "登录 / 注册",
    loading: "正在加载你的收藏…",
    loadError: "部分收藏暂时加载失败，请重试。",
    retry: "重新加载",
    missing: "这条收藏目前不在已发布目录中。",
    official: "已核验精确日期",
    predicted: "非官方预测",
    recurring: "周期性政策",
    review: "待核验",
    sync: "收藏会在你的设备之间同步。",
    syncError: "云端同步失败，修改已保存在当前设备，请重试。",
    syncing: "正在同步收藏…",
    showMore: "显示更多",
  },
};
const text = (key) => copy[state.language]?.[key] || copy.en[key];
const el = (tag, label, className = "") =>
  makeElement(tag, { text: label, className });
const isoToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};
let month = isoToday().slice(0, 7);
let selectedDay = "";
let visibleProjects = 12;
let loadClosed = async () => {};
let loading = false;
let loadError = false;

export function personalEvents(records, favorites) {
  return records
    .filter(
      (record) =>
        recordProvenance(record) === "official" &&
        (favorites.has(`window:${record.id}`) ||
          favorites.has(`university:${record.universityId}`)),
    )
    .flatMap((record) => [
      { type: "open", date: record.opensAt, record },
      { type: "deadline", date: record.closesAt, record },
    ])
    .filter((event) => /^\d{4}-\d{2}-\d{2}$/.test(event.date || ""))
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) || a.record.id.localeCompare(b.record.id),
    );
}

function button(label, action, className = "toolbar-button") {
  const node = el("button", label, className);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}

function remove(key) {
  state.favorites.delete(key);
  persistFavorites();
  renderAccount();
}

function schoolName(school) {
  return schoolLabels(school, state.language).primary;
}

function programmeName(record) {
  return programmeLabel(record.scopeId, record.program, state.language);
}

function schoolLink(school) {
  const link = el("a", schoolName(school));
  link.href = `./?university=${encodeURIComponent(school.id || school.universityId)}&status=all`;
  return link;
}

function card(title, className = "") {
  const section = el("section", undefined, `account-card ${className}`);
  section.append(el("h2", title));
  return section;
}

function eventList(events, limit = 20) {
  const list = el("div", undefined, "account-event-list");
  if (!events.length) list.append(el("p", text("noEvents"), "muted"));
  events.slice(0, limit).forEach((event) => {
    const item = el("article", undefined, "account-event");
    const date = el(
      "time",
      event.type === "deadline"
        ? formatDeadlineDate(event.record, event.date, state.language)
        : event.date,
    );
    date.dateTime = event.date;
    const details = el("div");
    details.append(
      el("span", text(event.type), `account-event-type ${event.type}`),
      el("strong", programmeName(event.record)),
      el("small", schoolName(event.record)),
      makeLink(text("source"), event.record.sourceUrl),
    );
    item.append(date, details);
    list.append(item);
  });
  if (events.length > limit)
    list.append(
      button(`${text("showMore")} (${events.length - limit})`, () =>
        list.replaceWith(eventList(events, limit + 30)),
      ),
    );
  return list;
}

function renderCalendar(events) {
  const section = card(text("calendar"), "account-calendar");
  section.append(el("p", text("calendarHelp"), "muted"));
  const toolbar = el("div", undefined, "account-calendar-toolbar");
  const changeMonth = (offset) => {
    const date = new Date(`${month}-01T00:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() + offset);
    month = date.toISOString().slice(0, 7);
    selectedDay = "";
    renderAccount();
  };
  const prev = button("‹", () => changeMonth(-1));
  prev.setAttribute("aria-label", text("previous"));
  const next = button("›", () => changeMonth(1));
  next.setAttribute("aria-label", text("next"));
  toolbar.append(
    prev,
    el(
      "h3",
      new Intl.DateTimeFormat(state.language === "zh" ? "zh-CN" : "en", {
        year: "numeric",
        month: "long",
        timeZone: "UTC",
      }).format(new Date(`${month}-01T00:00:00Z`)),
    ),
    next,
    button(text("today"), () => {
      month = isoToday().slice(0, 7);
      selectedDay = isoToday();
      renderAccount();
    }),
  );
  section.append(toolbar);
  const grid = el("div", undefined, "account-calendar-grid");
  (state.language === "zh"
    ? ["一", "二", "三", "四", "五", "六", "日"]
    : ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
  ).forEach((day) => grid.append(el("span", day, "account-weekday")));
  const date = new Date(`${month}-01T00:00:00Z`);
  const offset = (date.getUTCDay() + 6) % 7;
  for (let index = 0; index < offset; index++) grid.append(el("span"));
  while (date.toISOString().startsWith(month)) {
    const iso = date.toISOString().slice(0, 10);
    const daily = events.filter((event) => event.date === iso);
    const day = button(
      String(date.getUTCDate()),
      () => {
        selectedDay = iso;
        renderAccount();
      },
      "account-day",
    );
    day.setAttribute("aria-label", `${iso} · ${daily.length}`);
    day.setAttribute("aria-pressed", String(selectedDay === iso));
    if (iso === isoToday()) day.setAttribute("aria-current", "date");
    if (daily.length)
      day.append(el("small", `${daily.length}`, "account-day-count"));
    grid.append(day);
    date.setUTCDate(date.getUTCDate() + 1);
  }
  section.append(
    grid,
    button(
      text("allMonth"),
      () => {
        selectedDay = "";
        renderAccount();
      },
      "text-button",
    ),
    el("h3", selectedDay || month),
    eventList(
      events.filter((event) =>
        selectedDay ? event.date === selectedDay : event.date.startsWith(month),
      ),
    ),
  );
  return section;
}

export function renderAccount() {
  const root = document.getElementById("my-account");
  if (!root || root.hidden) return;
  root.replaceChildren();
  if (!state.user) {
    root.append(
      el("h1", text("signedOut")),
      button(text("signIn"), () => openAuthPanel()),
      button(text("browse"), () => {
        location.hash = "application-board";
      }),
    );
    return;
  }
  const hero = el("header", undefined, "account-hero");
  const welcome = el("div");
  welcome.append(
    el(
      "span",
      `${text("greeting")}${state.user.displayName ? `，${state.user.displayName}` : ""}`,
      "section-kicker",
    ),
    el("h1", text("title")),
    el("p", text("subtitle")),
  );
  const actions = el("div", undefined, "account-tabs");
  actions.append(
    button(
      text("browse"),
      () => {
        location.hash = "application-board";
      },
      "primary-button",
    ),
    button(text("settings"), () => openAuthPanel("", true)),
  );
  hero.append(welcome, actions);
  root.append(hero);
  const sync = el(
    "p",
    text(
      state.favoriteSyncStatus === "error"
        ? "syncError"
        : ["pending", "syncing"].includes(state.favoriteSyncStatus)
          ? "syncing"
          : "sync",
    ),
    "muted",
  );
  sync.id = "account-sync-status";
  sync.setAttribute("role", "status");
  root.append(sync);
  if (state.favoriteSyncStatus === "error")
    root.append(button(text("retry"), persistFavorites));
  if (loading) root.append(el("p", text("loading"), "muted"));
  if (loadError)
    root.append(
      el("p", text("loadError")),
      button(text("retry"), loadAccountRecords),
    );
  const savedSchools = [...state.favorites].filter((key) =>
    key.startsWith("university:"),
  );
  const savedProjects = [...state.favorites].filter((key) =>
    key.startsWith("window:"),
  );
  const events = personalEvents(state.data, state.favorites);
  const today = isoToday();
  const end = new Date(`${today}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 30);
  const upcoming = events.filter(
    (event) =>
      event.date >= today && event.date <= end.toISOString().slice(0, 10),
  );
  const stats = el("div", undefined, "account-stats");
  [
    [savedSchools.length, "schools"],
    [savedProjects.length, "projects"],
    [upcoming.length, "upcoming"],
  ].forEach(([count, label]) => {
    const stat = el("div");
    stat.append(el("strong", count), el("span", text(label)));
    stats.append(stat);
  });
  root.append(stats);
  const columns = el("div", undefined, "account-columns");
  const left = el("div", undefined, "account-main-column");
  const right = el("div", undefined, "account-side-column");
  const schools = card(text("schools"));
  if (!savedSchools.length) schools.append(el("p", text("empty"), "muted"));
  savedSchools.forEach((key) => {
    const school = state.universityById.get(key.slice(11));
    const item = el("div", undefined, "account-saved-school");
    item.append(
      school ? schoolLink(school) : el("span", text("missing")),
      button(text("remove"), () => remove(key), "text-button"),
    );
    schools.append(item);
  });
  left.append(schools);
  const projects = card(text("projects"));
  if (!savedProjects.length) projects.append(el("p", text("empty"), "muted"));
  const recordMap = new Map(state.data.map((record) => [record.id, record]));
  savedProjects.slice(0, visibleProjects).forEach((key) => {
    const record = recordMap.get(key.slice(7));
    const item = el("article", undefined, "account-saved-project");
    if (record) {
      item.append(
        el("span", text(recordProvenance(record)), "account-provenance"),
        makeLink(
          programmeName(record),
          record.applicationUrl,
          "account-programme-title",
        ),
        schoolLink(record),
        el("p", intakeLabel(canonicalIntake(record), state.language), "muted"),
        el(
          "p",
          `${text("open")}: ${record.opensAt || "—"} · ${text("deadline")}: ${formatDeadlineDate(record, record.closesAt || "—", state.language)}`,
        ),
      );
      const controls = el("div", undefined, "account-tabs");
      if (recordProvenance(record) === "official")
        controls.append(makeCalendarMenu(record));
      controls.append(
        makeLink(text("source"), record.sourceUrl),
        button(text("remove"), () => remove(key), "text-button"),
      );
      item.append(controls);
    } else {
      item.append(
        el("p", text(loading ? "loading" : "missing")),
        button(text("remove"), () => remove(key), "text-button"),
      );
    }
    projects.append(item);
  });
  if (savedProjects.length > visibleProjects)
    projects.append(
      button(text("showMore"), () => {
        visibleProjects += 20;
        renderAccount();
      }),
    );
  left.append(projects);
  const next = card(text("upcoming"));
  next.append(eventList(upcoming, 8));
  left.append(next);
  right.append(renderCalendar(events));
  const plan = card(text("profile"));
  plan.append(
    el("p", `${text("intake")}: ${state.user.targetIntake || text("notSet")}`),
    el("p", `${text("country")}: ${state.user.country || text("notSet")}`),
    button(text("settings"), () => openAuthPanel("", true)),
  );
  right.append(plan);
  columns.append(left, right);
  root.append(columns);
}

async function loadAccountRecords() {
  if (loading || !state.user) return;
  loading = true;
  loadError = false;
  renderAccount();
  try {
    await loadClosed();
  } catch {
    loadError = true;
  } finally {
    loading = false;
    renderAccount();
  }
}

export function openAccountHome() {
  location.hash = "my-account";
  updateView();
}

function updateView() {
  const active = location.hash === "#my-account";
  document.body.classList.toggle("account-view", active);
  document.getElementById("my-account").hidden = !active;
  if (active) {
    renderAccount();
    loadAccountRecords();
  }
}

export function setupAccount(ensureClosedRecords) {
  loadClosed = ensureClosedRecords;
  const section = el("section", undefined, "account-home");
  section.id = "my-account";
  section.hidden = true;
  document.querySelector("main").prepend(section);
  window.addEventListener("hashchange", updateView);
  window.addEventListener("accountchange", () => {
    renderAccount();
    if (location.hash === "#my-account" && !state.closedLoaded && !loadError)
      loadAccountRecords();
  });
  updateView();
}
