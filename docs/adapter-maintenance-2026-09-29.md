# Adapter maintenance: 2026-09-29

The health report identified failures caused by fixed application-cycle wording,
as well as separate transport failures and catalogue-count changes. This patch
addresses two reproducible wording failures; it does not declare all adapters
healthy or lower catalogue completeness thresholds.

## Dartmouth

- Official sources: <https://graduate.dartmouth.edu/admissions/programs> and
  <https://graduate.dartmouth.edu/admissions/applying-dartmouth>.
- The application guide now contains general application requirements rather
  than the old Fall 2027 September announcement. Requiring that announcement
  stopped an otherwise valid catalogue refresh.
- Accept the identifiable general guide, retain the catalogue minimum, reject
  unrelated/error pages, and resolve relative programme links to absolute URLs.
- Live dry run: 14 programmes, matching the previous 14; zero disappeared
  programmes and zero exact windows. Catalogue remains partial because the
  Guarini directory does not cover all independently offered professional degrees.
- Catalogue refresh recovered; programme-level window discovery remains pending.

## Princeton

- Official source:
  <https://gradschool.princeton.edu/admission-onboarding/prepare/application-deadlines>.
- The current Fall 2027 notice says applications are now open; the old parser
  only accepted a future opening notice containing an exact date.
- Preserve officially stated closing dates when the opening date is missing.
  Mark such windows incomplete with `opens_at_basis=missing`; do not manufacture
  an opening date from the crawl date or the month-only notice.
- The current notice explicitly excludes Computer Science M.S.E. from Fall 2027
  admissions. Preserve the catalogue programme with paused admission status and
  no new window, rather than assigning another degree's deadline.
- Parser regressions covered by fixtures. Live CLI dry run remains blocked by
  HTTP 403 from the catalogue on this host. Transport recovery and a successful
  complete live run remain pending. No candidates or public dates were promoted.

Caltech was also checked: its public application text still matches the existing
parser, while direct retrieval returned HTTP 403 locally. There was insufficient
evidence to justify changing its cycle parser in this patch.
