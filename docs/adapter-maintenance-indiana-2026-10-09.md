# Indiana Bloomington catalogue review — 2026-10-09

The official public degrees API returns 363 records with pagination reporting
one complete page (total and thisPage both 363). Of these, 362 are Bloomington
master's records; 35 repeat an existing URL and one record is doctoral. The
complete deduplicated master's catalogue is therefore 327, below the old 330
floor. No eligible record has a missing name, degree or URL.

Compared with the saved 336-record catalogue, 11 IDs are absent and two new
International and Regional Studies degrees appear. Their official pages were
reviewed:

- https://academics.iu.edu/degrees/bloomington/master-of-arts/international-and-regional-studies.html
- https://academics.iu.edu/degrees/bloomington/master-of-science/international-and-regional-studies.html

The MA describes regional tracks including Central Eurasian, East Asian,
European, Latin American/Caribbean and Middle Eastern studies. This supports
catalogue restructuring, but does not establish that every absent programme
has closed. Missing IDs remain subject to the existing lifecycle review.

Set the minimum to the verified current count of 327 (no additional tolerance),
and retain the maximum of 370. Require successful status and consistent complete
single-page metadata before accepting data. Fail incomplete master's records
and conflicting duplicate identities instead of silently discarding them.
Do not automatically follow unreviewed pagination links or publish dates.

This is catalogue recovery. Department-level window discovery remains pending;
the adapter continues verifying the official department-specific deadline
policy. No operational state or published records are changed by this repair.
