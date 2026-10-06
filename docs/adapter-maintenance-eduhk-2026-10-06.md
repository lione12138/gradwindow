# EdUHK directory and 2027/28 schedule migration

The former acadprog postgraduate directory now links to the Graduate School
programme-information page instead of embedding programme links:
https://gs.eduhk.hk/pg-programmes/programme-information.html

Both administering sections are required. Read the English label before the
Chinese line break, preserve medium-of-instruction variants, and extract the
administering unit. Exclude external hosts, certificates, doctorates and entries
marked `*` (subject to University approval). The source has 60 linked, non-provisional
master's entries including language variants. Keep the minimum at 48 and expand
the old maximum of 55 to 65 for the verified new scope.

The current official HTML schedule replaces the old 2026/27 PDF:
https://www.eduhk.hk/acadprog/postgrad/schedule_index.html

It explicitly states September 2027 intake, opening on 5 October 2026, a
10 May 2027 non-local deadline and 31 May 2027 local deadline. Validate these
date statements and the exclusion list before producing two general admissions
group windows. Preserve exceptions: programmes can close earlier when places
fill; the schedule excludes PhD, MPhil, EdD, EdD(Chinese), MSocSc(EP) and PGDE.
Do not copy these dates onto individual programmes. Early/main-round deadlines
also appear in the source but are not added by this repair.

The legacy schedule parser remains covered by its existing test: month-only
opening wording must never become an exact opening date. New tests cover
bilingual names, provisional exclusions, administering sections, exact general
dates and rejection of changed dates/intake/scope.

Catalogue recovery and general-schedule window discovery are implemented;
programme-specific exceptions still need review. This change runs discovery in
dry-run mode only. Candidate/state and public programme/window data are not
written, and the new dates are not approved for publication.
