function valueAt(values, index, fallback = null) {
  return index >= 0 ? values[index] : fallback;
}

export function decodeRecordBundle(bundle, universities) {
  const dictionaries = bundle?.dictionaries || {};
  const scopes = dictionaries.scopes || [];
  const intakes = dictionaries.intakes || [];
  const rounds = dictionaries.rounds || [];
  const categorySets = dictionaries.categorySets || [];
  const urls = dictionaries.urls || [];
  const statuses = dictionaries.statuses || [];
  const sourceCycles = dictionaries.sourceCycles || [];
  const confidences = dictionaries.confidences || [];
  const monitors = dictionaries.monitors || [];
  const deadlineSemantics = dictionaries.deadlineSemantics || [];
  const trustStatuses = dictionaries.trustStatuses || [];

  return (bundle?.rows || []).map((row) => {
    const university = universities[row[1]] || {};
    const [scopeId = "", scopeType = "institution", program = scopeId] =
      scopes[row[2]] || [];
    const [intake = "", intakeDetails = {}] = intakes[row[3]] || [];
    return {
      id: row[0],
      universityId: university.id || "",
      scopeId,
      scopeType,
      program,
      intake,
      intakeDetails,
      round: valueAt(rounds, row[4], ""),
      applicantCategories: valueAt(categorySets, row[5], []),
      opensAt: row[6],
      closesAt: row[7],
      applicationUrl: valueAt(urls, row[8], ""),
      sourceUrl: valueAt(urls, row[9], ""),
      verifiedAt: row[10] || undefined,
      policyCheckedAt: row[11] || undefined,
      dataStatus: valueAt(statuses, row[12], "official"),
      sourceCycle: valueAt(sourceCycles, row[13], ""),
      confidence: valueAt(confidences, row[14], ""),
      evidenceCycleCount: row[15] ?? undefined,
      sourceMonitor: valueAt(monitors, row[16], {}),
      deadlineSemantics: valueAt(deadlineSemantics, row[17], "on"),
      trustStatus: valueAt(trustStatuses, row[18], "current"),
      school: university.school || "",
      schoolZh: university.schoolZh || "",
      schoolAliasesZh: university.schoolAliasesZh || [],
      qsRank: university.qsRank || 999,
      country: university.country || "",
      region: university.region || "",
    };
  });
}
