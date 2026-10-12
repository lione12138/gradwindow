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

### IOE identity review, 2026-10-11

The official [IOE graduate course list](https://www.ucl.ac.uk/ioe/courses/graduate-taught)
explicitly identifies former names for nine pending candidates: Citizenship
Education, Educational Assessment, Geography Education, History Education,
Science Education, Educational Leadership (formerly In-service), Education,
Conflict, Emergencies and Peace, Social Policy and Evidence Synthesis, and
Social Policy and Research Methods. These retain their existing public IDs.
Current names and official course links are updated without adding programmes
or dates. The duplicate new-programme candidates are rejected with the source
recorded in review notes. `REVIEWED_IOE_IDENTITIES` takes precedence over IDs
from unreviewed discovery snapshots, preventing recurrence on later refreshes.
The other 84 candidates still require identity/publication review.

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

### Further course identity review (2026-10-12)

Three current course names retain their existing public IDs:

- Energy Systems and Data Analytics MSc retains the ESDA ID. The
  [official departmental article](https://www.ucl.ac.uk/bartlett/news/2022/mar/energy-systems-and-data-analytics-msc-students-come-second-energy-idea-challenge)
  uses both names for the same course.
- Public Health MPH retains the Master of Public Health MPH ID. The
  [current page](https://www.ucl.ac.uk/study/prospective-students/graduate/courses/public-health-mph)
  still identifies its video as Master of Public Health MPH; its online mode,
  department and curriculum agree with the
  [2026 page](https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/master-public-health-mph-2026).
- Manufacturing with Innovation and Entrepreneurship MSc retains the Enterprise
  ID. The [current page](https://www.ucl.ac.uk/study/prospective-students/graduate/courses/manufacturing-innovation-and-entrepreneurship-msc)
  still names Enterprise in its application guidance; the department, location
  and curriculum agree with the
  [2026 page](https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/manufacturing-innovation-and-enterprise-msc-2026).

The old pages' generic 2027-entry links lead to the course directory, so those
links alone are not identity evidence. Exact reviewed names override earlier
unreviewed snapshot IDs. `scripts/review_ucl_course_renames.py` updates only public
names and URLs and rejects the three duplicate candidates, preserving existing
IDs and references. It adds no programmes or windows. Current pages describe
application dates as to be confirmed; previous-cycle dates are not reused.

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

## Mixed directory snapshots (2026-10-10 UTC)

Run [38087082403](https://github.com/lione12138/gradwindow/actions/runs/38087082403)
saved two successful HTTP 200 browser responses: the first page advertised 695
courses, while page 2 advertised 694. Inspecting its saved checkpoint confirmed
20 cards on each page and the expected first titles/pagination links; this was
not a 429 or a count parsed from an access-denied page.

A fresh run [38088577107](https://github.com/lione12138/gradwindow/actions/runs/38088577107)
reproduced the mismatch at page 7 (`?page=6`): 694 versus the first page's 695.
The interactive browser returned 695 for that same URL. This establishes that
retrievals can receive different directory versions; upstream cache/update
propagation is the likely cause, but the responsible cache layer is unconfirmed.

The adapter continues to reject mixed totals, duplicate cards and incomplete
pagination. These consistency failures now invalidate only the browser page
keys visited in that snapshot, so a later job fetches fresh pages instead of
replaying the known-inconsistent six-hour checkpoint. Other schools' cache
entries and account cooldowns remain intact. There is no immediate retry loop,
no relaxed minimum/count check and no overwrite of published or operational
data on failure. Error messages include the page URL, actual count, first-page
count and minimum to distinguish this case from a genuinely small catalogue.
