# LSE catalogue recovery: 2026-10-04

The previous catalogue source was the available-programmes page. It currently
announces the closed admissions cycle and retains only a small executive and
visiting-research list. It is not a stable source for programme existence.

The official navigation links to <https://www.lse.ac.uk/programmes/search-courses>.
Its server-rendered directory exposes 258 results, twelve per page, and its
application bundle confirms one-based `pageIndex` query navigation.

Read every directory page and retain master's entries through the existing
degree filter. Validate consecutive result ranges and an unchanged total, cap
pagination at 50 pages, and keep the existing 130-programme minimum. Missing,
repeated or changing pagination fails rather than accepting a partial list.
No application status or dates are inferred from directory membership.

Live dry run: all 22 requests succeeded; 142 master's programmes were parsed,
compared with 155 in the previous snapshot. Renames and removed IDs remain
review items. No public records were changed or candidates approved.
Catalogue discovery recovered; application-window discovery remains pending.

UCL was also probed and returned HTTP 403 locally. Its parser and completeness
thresholds were not changed without a reliable full-source reproduction.
