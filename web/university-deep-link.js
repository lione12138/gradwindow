export function universityDeepLink(search, knownUniversityIds = null) {
  const params = new URLSearchParams(search || "");
  const universityId = (params.get("university") || "").trim();
  const known =
    !knownUniversityIds ||
    (typeof knownUniversityIds.has === "function" &&
      knownUniversityIds.has(universityId));
  return {
    universityId: universityId && known ? universityId : "",
    action:
      universityId && known && params.get("action") === "save" ? "save" : "",
  };
}

export function searchWithoutDeepLinkAction(search) {
  const params = new URLSearchParams(search || "");
  params.delete("action");
  return params.size ? `?${params}` : "";
}
