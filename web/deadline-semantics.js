export function formatDeadlineDate(record, formattedDate, language = "en") {
  if (record?.deadlineSemantics !== "before") return formattedDate;
  return language === "zh" ? `${formattedDate}前` : `Before ${formattedDate}`;
}

export function formatDeadlineRange(
  record,
  formattedOpenDate,
  formattedCloseDate,
  language = "en",
) {
  return `${formattedOpenDate} – ${formatDeadlineDate(
    record,
    formattedCloseDate,
    language,
  )}`;
}

export function deadlineDaysRemaining(record, calendarDaysUntilDate) {
  return record?.deadlineSemantics === "before"
    ? calendarDaysUntilDate - 1
    : calendarDaysUntilDate;
}
