# Deakin missing version notes — 2026-10-05

The handbook index returned 83 current master's names under the existing rule,
below its 85-name minimum. Some rows have no commencement note even though the
linked course version explicitly states an ongoing commencement range. For
example, Dietetics H718 version 2 states “For students who commenced from 2025
onwards” on its official detail page:

https://handbook.deakin.edu.au/current-students-courses/course.php?course=H718&version=2

The adapter keeps the index's explicit ongoing records and checks only remaining
master's rows without commencement notes. A detail must match both the requested
course code and version and explicitly state a year followed by “onwards” in its
Course information field. Ended, mismatched and unverified versions are excluded.
Existing current entries retain their selected source URLs; names are deduplicated.
The completeness minimum remains 85. A failed detail fetch fails discovery rather
than silently accepting an incomplete result.

The live dry run returned 89 programmes after 19 successful official requests,
recovering six names omitted by the index-only rule. The previous saved catalogue
contained 87 names; the newly observed IDs are Dietetics and Social Work. All
differences remain review work. No operational candidate/state files or public
data were written. This is catalogue recovery; exact-window discovery is pending.

Purdue was also checked: 122 matching cards collapse to 118 distinct programme
names. Four duplicated cards share both names and admissions URLs. The existing
minimum of 120 still fails; it was not lowered or padded with duplicate records.
The saved 120-entry catalogue differs only by Art and Design, Art, and Performance;
their current master's availability needs a separate review. Directory absence
alone is not treated as proof that admissions have closed.
