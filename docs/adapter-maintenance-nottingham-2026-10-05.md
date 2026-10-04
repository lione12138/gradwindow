# Nottingham course-card awards — 2026-10-05

The existing parser reproduced the monitoring failure: 139 master's courses,
below the unchanged minimum of 140. The official A–Z directory has taught
master's courses whose URL no longer ends with a recognised award. Their empty
links sit inside `.courseDescription` cards with explicit award-bearing `h3`
headings. Examples include Cyber Security MSc, Architecture (ARB RIBA Part 2)
MArch and Medical Education MMedSci/PGDip/PGCert.

Use those official card headings when the existing URL rule does not match,
only for taught-course paths on www.nottingham.ac.uk. Certificate-only and
doctoral records remain excluded. Preserve URL-based IDs and deduplicate repeated
cards. Existing URL-based parsing remains supported; the minimum stays 140.

Live verification fetched 22 A–Z pages. The repaired adapter finds 150 master's
entries, recovering 11 missed by the old parser. The Cyber Security detail page
returned HTTP 200 and confirmed its MSc heading:
https://www.nottingham.ac.uk/pgstudy/course/taught/cybersecurity

This is catalogue recovery, not completed application-window discovery. No new
exact windows were generated. Candidate and operational state writes were not
run, and public data was not edited. Programme-name/URL changes in the directory
still require review before publication.

Other probes: Leeds returned HTTP 403; no parser change was made based on that
blocked response. Toronto's full dry run succeeded with 155 programmes, unchanged
from its previous catalogue, and 130 successful requests (two API pages and 128
detail pages). Its two observed deadlines still lack exact opening dates. No
Toronto code was changed because the old failure was not reproducible.
