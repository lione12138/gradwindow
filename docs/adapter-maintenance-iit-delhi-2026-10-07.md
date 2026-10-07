# IIT Delhi admissions-route recovery — 2026-10-07

## Official evidence

https://home.iitd.ac.in/pg-admissions.php returns HTTP 200. Its heading changed
from PG ADMISSIONS to ADMISSIONS, and the current content describes the second
semester of 2026–27. Old first-semester notices remain inside HTML comments.

The international Ph.D./M.S.(R) notice says applications are open and gives a
2026-10-29 closing date, but no exact opening date. The national-candidate notice
gives 2026-10-09 at noon as the opening, but no closing date. These dates belong
to different applicant categories and must not be combined. The new information
brochure is explicitly awaiting upload. The linked academic directory at
https://academics.iitd.ac.in/ returned HTTP 403 during this review; TLS validation
was not disabled.

## Change and completion scope

Recognise visible, cycle-labelled research-master admissions notices and official
HTTPS application links. Exclude comments, scripts, styles and navigation; reject
navigation-only pages, missing cycles and lookalike application hosts. Keep
legacy brochure recognition without hard-coding 2026–27. Preserve each visible
applicant notice as separate guidance, generating no exact windows. Replace the
stale claim about broken TLS with an explicit description of the monitor's scope.
Report admissions-route-level granularity instead of programme-level.

Live dry run recovered the single existing admissions-route record, with no
new exact-window candidates or adapter warnings. This completes route-monitor
recovery only. Programme catalogue discovery and systematic programme/faculty
deadline discovery remain pending; a placeholder is not a completed school
adapter. No operational state, candidates or published application dates changed.

Validation includes current/legacy notices, academic-year rollover, applicant
separation, comment/navigation exclusion, official-host checks, full pytest,
Ruff, public-data validation, temporary site build and frontend checks.
