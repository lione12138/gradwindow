export function isPredictedRecord(record) {
  return record?.dataStatus === "predicted";
}

export function isRecurringPolicyRecord(record) {
  return record?.dataStatus === "recurring";
}

export function calendarTitlePrefix(record) {
  if (isPredictedRecord(record)) return "[ESTIMATE] ";
  if (isRecurringPolicyRecord(record)) return "[RECURRING POLICY] ";
  return "";
}

export function calendarWarning(record) {
  if (isPredictedRecord(record)) {
    return "Unofficial calendar-date estimate. Confirm on the official website before applying.";
  }
  if (isRecurringPolicyRecord(record)) {
    return (
      "Official recurring day/month policy; GradWindow mapped the cycle year. " +
      "Confirm the year on the official website before applying."
    );
  }
  return "";
}
