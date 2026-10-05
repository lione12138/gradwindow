# TU Wien language-directory migration — 2026-10-05

The official master's landing page now links to language/subject directories
instead of listing every programme with a `Master Programme` label. The old
parser returned zero entries. The complete language lists expose 14 German-taught
and 26 English-taught entries (including two double-degree routes):

- https://www.tuwien.at/en/studies/studies/master-programmes/deutschsprachige-masterstudien
- https://www.tuwien.at/en/studies/studies/master-programmes/english-taught-masters-programmes

Follow both lists from the official landing page. Accept programme detail paths
with a subject and programme segment, excluding category navigation. The two
double-degree links use the official faculty host `informatics.tuwien.ac.at`,
which differs from `tuwien.at`; allow that exact host and master's double-degree
path. Retain legacy prefixed labels and deduplicate homepage featured programmes.
Require both language lists and non-empty parsed results from each.

Live dry run: 40 programmes versus 37 previously, with eight candidate IDs not
in curated data. Names and offerings changed and require review. The minimum
stays 30. Regression coverage includes both language pages, featured duplicates,
double degrees, category/external-link exclusion and a missing-language failure.

This completes catalogue recovery only. Programme-specific application-window
and applicant-scope discovery remain pending. No exact windows were generated;
no operational candidate/state or public data files were written.
