import { t } from "./strings.js";
import { makeElement, makeLink, parseDate } from "./dom.js";
import { calendarTitlePrefix, calendarWarning } from "./window-provenance.js";

// Build "add to calendar" links and downloads for a single application window.
// Pure with respect to page state: everything derives from the record. The
// URL builders and icsFileBody are exported for the frontend contract tests.

function calendarText(record, { title, notes = [] } = {}) {
  const eventTitle =
    title ?? `${record.school} ${record.program} application deadline`;
  return {
    title: `${calendarTitlePrefix(record)}${eventTitle}`,
    details: [
      calendarWarning(record),
      ...notes,
      `Application: ${record.applicationUrl}`,
      `Source: ${record.sourceUrl}`,
    ]
      .filter(Boolean)
      .join("\n"),
  };
}

export function googleCalendarUrl(record, content) {
  const start = record.closesAt.replaceAll("-", "");
  const endDate = parseDate(record.closesAt);
  endDate.setUTCDate(endDate.getUTCDate() + 1);
  const end = endDate.toISOString().slice(0, 10).replaceAll("-", "");
  const { title, details } = calendarText(record, content);
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: title,
    dates: `${start}/${end}`,
    details,
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export function outlookCalendarUrl(record, content) {
  const start = `${record.closesAt}T00:00:00Z`;
  const endDate = parseDate(record.closesAt);
  endDate.setUTCDate(endDate.getUTCDate() + 1);
  const end = `${endDate.toISOString().slice(0, 10)}T00:00:00Z`;
  const { title, details } = calendarText(record, content);
  const params = new URLSearchParams({
    path: "/calendar/action/compose",
    rru: "addevent",
    startdt: start,
    enddt: end,
    subject: title,
    body: details,
    allday: "true",
  });
  return `https://outlook.live.com/calendar/0/deeplink/compose?${params.toString()}`;
}

export function icsFileBody(record, now = new Date(), content) {
  const start = record.closesAt.replaceAll("-", "");
  const endDate = parseDate(record.closesAt);
  endDate.setUTCDate(endDate.getUTCDate() + 1);
  const end = endDate.toISOString().slice(0, 10).replaceAll("-", "");
  const { title, details } = calendarText(record, content);
  const escapeIcs = (value) =>
    value
      .replaceAll("\\", "\\\\")
      .replaceAll("\n", "\\n")
      .replaceAll(",", "\\,")
      .replaceAll(";", "\\;");
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//GradWindow//Application Deadline//CN",
    "BEGIN:VEVENT",
    `UID:${record.id}@gradwindow`,
    `DTSTAMP:${now.toISOString().replaceAll(/[-:]/g, "").split(".")[0]}Z`,
    `DTSTART;VALUE=DATE:${start}`,
    `DTEND;VALUE=DATE:${end}`,
    `SUMMARY:${escapeIcs(title)}`,
    `DESCRIPTION:${escapeIcs(details)}`,
    `URL:${record.applicationUrl}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
}

function downloadIcs(record, content) {
  const body = icsFileBody(record, new Date(), content);
  const blob = new Blob([body], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${record.id}-deadline.ics`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function makeCalendarMenu(record, { translate = t, ...content } = {}) {
  const menu = makeElement("details", { className: "calendar-menu" });
  const summary = makeElement("summary", {
    className: "calendar-menu-trigger",
    title: translate("calendarOptions"),
  });
  summary.setAttribute("aria-label", translate("addCalendar"));
  summary.append(
    makeElement("span", { className: "calendar-menu-icon" }),
    makeElement("span", {
      className: "calendar-menu-label",
      text: translate("addCalendar"),
    }),
  );
  const options = makeElement("div", { className: "calendar-menu-options" });
  const makeDownloadOption = (label) => {
    const button = makeElement("button", {
      className: "calendar-menu-item",
      text: label,
      title: translate("downloadIcs"),
    });
    button.type = "button";
    button.addEventListener("click", () => {
      downloadIcs(record, content);
      menu.open = false;
      summary.focus();
    });
    return button;
  };
  options.append(
    makeLink(
      translate("googleCalendar"),
      googleCalendarUrl(record, content),
      "calendar-menu-item",
    ),
    makeLink(
      translate("outlookCalendar"),
      outlookCalendarUrl(record, content),
      "calendar-menu-item",
    ),
    makeDownloadOption(translate("appleCalendar")),
    makeDownloadOption(translate("androidCalendar")),
    makeDownloadOption(translate("downloadIcs")),
  );
  menu.append(summary, options);
  return menu;
}
