# Washington directory migration — 2026-10-05

The former `/SharedUIComponents/ProgramSearch/getPrograms` endpoint returns an
HTTP 500 database error. The official graduate directory now loads the
`SharedElementsPublic/Scripts/dist/main.js` bundle, which calls:

https://webapps.grad.uw.edu/SharedElementsPublic/ProgramSearch/GetPrograms

The complete non-paginated response contains 532 records: 249 master's, 131
doctoral, 116 non-matriculated, 34 certificate, and two educational specialist
records. Of the master's records, 16 are explicitly named Visiting Grad/Graduate
and have Slate degree codes ending in VG. Excluding them leaves 233 degree
programme entries. The parser now uses the Slate fields and rejects malformed
master's records and unknown response schemas instead of silently omitting them.
Legacy-format fixtures remain supported.

The completeness floor changes from 250 to 225 because the new official directory
has only 233 qualifying entries, not because a partial response was accepted.
The full 532-record response and the degree-level breakdown were checked before
changing the floor. Any further reduction needs review.

Live dry run: 233 programmes versus 261 in the old state, with 75 candidate IDs
not in curated programmes. Names and groupings changed substantially in the new
source; additions and disappearances must be reviewed as possible renames, not
automatically published or interpreted as closures. No operational state,
candidate records, or public programme/window records were written in this repair.

This is catalogue recovery only. The directory does not provide exact opening
and closing dates. Programme/faculty deadline discovery and intake scope review
remain pending; no new exact windows were generated.

QUT was also rechecked: both its online catalogue and application guide returned
HTTP 200, and its unmodified adapter recovered the same ten online master's
programmes. Its previous HTTP 404 was not reproducible; no QUT code was changed.
