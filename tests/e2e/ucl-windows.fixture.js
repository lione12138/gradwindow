// Fixed UI scenarios, never publication data. Four reviewed 2027 examples and
// two synthetic historical rows keep behavior tests independent of daily feeds.
export function uclWindowRows(schoolIndex, dictionaries) {
  const indexOf = (key, value) => {
    const values = (dictionaries[key] ||= []);
    let index = values.findIndex(
      (item) => JSON.stringify(item) === JSON.stringify(value),
    );
    if (index === -1) index = values.push(value) - 1;
    return index;
  };
  const rows = [];
  for (const [slug, name] of [
    ["advanced-materials-science-msc", "Advanced Materials Science MSc"],
    ["law-and-finance-msc", "Law and Finance MSc"],
  ]) {
    for (const category of [
      "requires-uk-study-visa",
      "does-not-require-uk-study-visa",
    ]) {
      const url = `https://www.ucl.ac.uk/study/prospective-students/graduate/courses/${slug}`;
      rows.push([
        `ucl-${slug}-2027-application-period-${category}`,
        schoolIndex,
        indexOf("scopes", [`ucl-${slug}`, "programme", name]),
        indexOf("intakes", [
          "September 2027",
          {
            label: "September 2027",
            cycleYear: 2027,
            academicYearEnd: null,
            term: "fall",
            startMonth: 9,
          },
        ]),
        indexOf("rounds", "Application period"),
        indexOf("categorySets", [category]),
        "2026-10-19",
        category === "requires-uk-study-visa" ? "2027-06-25" : "2027-08-27",
        indexOf("urls", `${url}#apply`),
        indexOf("urls", url),
        "2026-10-25",
        null,
        indexOf("statuses", "official"),
        -1,
        -1,
        null,
        -1,
        indexOf("deadlineSemantics", "on"),
        indexOf("trustStatuses", "source-unavailable"),
      ]);
    }
  }
  for (let i = 0; i < 2; i += 1) {
    const row = [...rows[i]];
    row[0] = `fixture-ucl-history-${i}`;
    row[3] = indexOf("intakes", [
      "September 2026",
      {
        label: "September 2026",
        cycleYear: 2026,
        academicYearEnd: null,
        term: "fall",
        startMonth: 9,
      },
    ]);
    row[6] = "2025-10-20";
    row[7] = "2026-06-30";
    row[10] = "2026-01-01";
    rows.push(row);
  }
  return rows;
}
