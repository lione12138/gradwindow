# Stanford departmental date review — 17 October 2026

This review covers two existing master's programmes, not the full Stanford
catalogue. No adapter-wide opening date has been configured.

## Computer Science MS: full official window

The [CS departmental deadline table](https://www.cs.stanford.edu/admissions-graduate-application-deadlines)
gives the regular master's Autumn application an opening date of 15 September
2026 and a closing date of 8 December 2026. The
[central application page](https://gradadmissions.stanford.edu/apply) identifies
the current application as 2027 entry. The published intake is Autumn 2027.

The [master's admissions page](https://www.cs.stanford.edu/admissions/masters-admissions)
accepts applicants with US or equivalent overseas bachelor's degrees. The
deadline table gives one regular master's deadline without a nationality split.
The record uses the existing `all` applicant category for that regular route.
It does not represent coterminal admission, the additional applications required
for joint degrees, Knight-Hennessy scholarships, or suggested language-test dates.

The window was entered as a pending manual-review candidate and promoted through
`approve_window`; the approval stores a review evidence snapshot. Future source
monitoring uses the departmental source URL. Departmental discovery automation
is still pending; the central catalogue adapter alone does not supply this opening.

The existing catalogue snapshot was captured on 5 October 2026, before this
official review. The publication audit now ignores snapshot reconciliation when
the snapshot predates `verifiedAt`; it still enforces intake consistency and
source-availability checks. Same-day/newer snapshots and unknown timestamps keep
the existing conservative reconciliation behaviour. A later incompatible scrape
may therefore request another review; this is not a permanent exemption.

## Design MS: verified deadline only

The [d.school admissions timeline](https://dschool.stanford.edu/study/graduate-degree/admissions)
explicitly identifies Autumn 2027 entry and a completed-application deadline of
1 December 2026, 11:59pm Pacific Time. Supporting materials must arrive by that
deadline. Opening is described only as mid-September 2026.

The approved deadline-only record keeps `opensAt: null`. It must not borrow the
CS opening date or become an open application window, calendar event or predicted
cycle. Users can follow the official link for the submission time and requirements.

## Remaining work

Other Stanford departments still require their own official-source review.
The 47-programme catalogue is not evidence that all application dates have been
verified. Reusable departmental extraction rules should follow verified examples;
no dates should be propagated from these two programmes to the rest of the school.
