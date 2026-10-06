# IIT Bombay catalogue recovery — 2026-10-06

## Official evidence and scope

- Catalogue: https://acad.iitb.ac.in/admissions/masters/divisions
- Admissions overview: https://acad.iitb.ac.in/admissions/masters
- Both returned HTTP 200 during review. The catalogue now contains paragraphs
  instead of tables; programme codes, degree headings and department text remain,
  but departmental links are absent. The previous table-only parser returned zero.
- The ten reviewed degree sections contain 57 catalogue entries, matching the
  previous successful catalogue. The minimum count remains 40.

## Change

Keep legacy table parsing. For the flattened Drupal body, identify sections by
their explicit heading and column-label markers, not degree position. Require
all ten distinct sections. Coded programmes use their official codes to separate
them from department labels. Uncoded rows use a strictly checked, reviewed row
grammar: a shared department can follow multiple programmes, and Chemistry and
Physics repeat as both programme and department. Changed uncoded rows fail for
review rather than producing a guessed catalogue. Retain the MBA/EMBA distinction.

Use the official central catalogue as source where the department links have
disappeared; do not reconstruct URLs. Reordered sections retain their degree types.

## Validation and completion phase

Live discovery dry run: 57 programmes, previous 57, no disappeared programmes,
zero new programme or exact-window candidates, no adapter warnings. Fixtures
cover coded and uncoded records, shared departments, duplicate labels, executive
MBA, reordered sections and incomplete/changed content; legacy tests remain.

Catalogue recovery is complete. Application-window discovery remains pending:
the admissions overview describes programme families and admission categories,
but supplies no complete dated cycle applicable to these 57 entries. This repair
does not systematically inspect each programme-family brochure or deadline page.
No operational candidate/state files or published application dates were changed.
