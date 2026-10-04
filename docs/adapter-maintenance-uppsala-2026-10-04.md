# Uppsala catalogue recovery — 2026-10-04

## Source change and scope

The old search URL's `internationalMastersProgrammes` category no longer selects
the international master's catalogue. Its initial state now identifies the
general `educationCoursesAndProgrammes` search, which includes standalone courses.
The official master's landing page links to a dedicated catalogue:
https://www.uu.se/en/study/masters-studies/masters-programmes

That page exposes the `educationInternationalMastersProgrammes` search category
through the existing Sitevision search API. Live inspection reported 116 records;
the adapter's minimum of 105 is unchanged. Only this dedicated category is used.

The adapter now checks a stable total across pages, rejects empty/truncated pages,
duplicate or missing programme URLs, and non-programme hits. It fails rather than
silently accepting general courses or a partial response.

## Validation and remaining work

The live dry run recovered 116 programmes versus 112 previously, with no missing
old programme IDs and four additions. It produced no exact-window candidates.
Focused tests cover the new category, multiple pages, interrupted pagination,
changing totals, duplicate records, and accidental course-search responses.

This completes catalogue recovery only. Application-window discovery is pending:
the official application page and its application guide explicitly state an
international application round from 16 October 2026 to 15 January 2027:

- https://www.uu.se/en/study/masters-studies/application
- https://www.uu.se/en/study/masters-studies/application/application-guide

Before generating programme-specific windows, check intake and programme scope,
including joint-degree exceptions, against programme detail pages. The central
round alone has not been copied onto every programme. Existing public data and
operational candidate/state files were not changed by this dry-run repair.
