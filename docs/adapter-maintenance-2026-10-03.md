# Caltech adapter maintenance: 2026-10-03

The existing parser failed on the official application notice because it only
accepted a future early-October opening and a December 1–15 deadline range.
Direct retrieval on 2026-10-03 returned an already-open 2026–2027 admissions
notice and a December 1–January 15 range instead.

Source: <https://gradoffice.caltech.edu/admissions/applyonline>.

The parser accepts both observed notice formats, validates consecutive academic
years, and sets the adapter intake from the source rather than its old Fall 2027
default. Programme notes no longer claim that every notice says early October.
The central date range is guidance only, never a shared programme deadline.

Live CLI dry run fetched all four official pages successfully and recovered
three direct-entry master's programmes, matching the previous catalogue. Two
Aerospace deadline records remain incomplete because the exact opening date is
missing. The returned source cycle is Fall 2026; it is not advanced to Fall 2027
based on today's date. No exact windows are eligible for publication.

Completion: catalogue parsing recovered; incomplete deadline discovery verified.
Operational candidates are pending review. The official cycle needs review
before any new public application window can be approved.
