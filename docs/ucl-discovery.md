# UCL directory migration — 2026-10-10

## Official source and scope

The current 2027/28 directory is
<https://www.ucl.ac.uk/study/prospective-students/graduate/courses>.
The old `/prospective-students/graduate/taught-degrees` source belongs to the
previous entry cycle and is no longer the default catalogue.

Browser inspection followed all 35 official pagination links on 2026-10-10:
694 cards in total, including non-master degrees. There were 498 master's
main cards: 486 linked courses and 12 explicitly labelled Coming soon. The
linked cards included 55 additional study-option routes, giving 541 linked
master's routes and 553 records including Coming soon courses. These are
catalogue observations, not counts of open applications or verified deadlines.

The adapter checks the advertised count on every page and requires the final
card count to match. Existing minimum counts remain 550 total cards and 500
master's records. Unexpected pagination, missing course fields and unreviewed
degree labels fail discovery rather than silently producing a partial snapshot.
The official directory contains a same-title PG Cert / PG Dip pair; duplicate
card detection therefore includes the degree label.

Study-option query parameters are retained. Unique previous names retain their
programme IDs, including changes limited to punctuation, `&` versus `and`, and
moving the degree abbreviation from the end to the beginning. Ambiguous matches
are rejected and semantic renames are not fuzzy-matched. The first live refresh
revealed 15 such typographical changes that otherwise became duplicate candidates.
The existing curated overrides remain a fallback. Renamed or
removed courses still require review. Coming soon records use the official
directory as evidence; no detail URL, intake or application date is invented.

## Application-window status

**Catalogue parser implemented; systematic detail/window discovery pending.**
The current Advanced Materials Science MSc and Computer Science MSc pages
were inspected and explicitly say application dates are to be confirmed:

- <https://www.ucl.ac.uk/study/prospective-students/graduate/courses/advanced-materials-science-msc>
- <https://www.ucl.ac.uk/study/prospective-students/graduate/courses/computer-science-msc>

These examples do not establish a university-wide no-deadline policy. All
other detail routes, including option-specific and applicant-category rules,
still need systematic checking. Directory intake months are metadata, not
exact opening dates. No 2026 dates are reused for 2027 entry. Existing public
windows are not changed by this migration.

A further one-course-per-faculty check on the same date covered all 11 faculty
groups present in the master's directory. Each sampled page explicitly said
the course application dates are to be confirmed. Relative to the current
directory URL, the inspected course slugs were:

- Brain Sciences: `advanced-audiology-msc`
- Medical Sciences: `advanced-biomedical-imaging-msc`
- Mathematical and Physical Sciences: `advanced-materials-science-data-driven-innovation-msc`
- Population Health Sciences: `advanced-musculoskeletal-physiotherapy-clinical-practice-msc`
- Life Sciences: `advanced-pharmacy-practice-msc`
- Social and Historical Sciences: `ancient-history-ma`
- Institute of Education: `applied-linguistics-ma`
- Built Environment: `architectural-computation-msc`
- Arts and Humanities: `archives-and-records-management-ma`
- Engineering Sciences: `artificial-intelligence-and-data-engineering-msc`
- Laws: `law-and-finance-msc`

This bounded sampling supports a shared detail-page parser as the next step;
it does not establish the status of every programme or study option.

## Transport and integration limits

Local HTTP and curl requests returned HTTP 403 while the interactive browser
could read the directory. The shared discovery transport supports the existing
Cloudflare browser fallback; this adapter allows up to 40 fallback pages to
cover pagination. Local Cloudflare credentials were unavailable. GitHub Actions
run [38032372262](https://github.com/lione12138/gradwindow/actions/runs/38032372262)
subsequently completed a full unattended discovery on 2026-10-10: all 35 direct
requests were blocked, and all 35 browser fallbacks succeeded, producing 553
records. Validation and 972 tests passed. This confirms catalogue transport;
it does not validate programme-specific application dates.

Operational candidate/state refresh and translation review should follow a
successful unattended run. This change does not publish programmes or dates.
