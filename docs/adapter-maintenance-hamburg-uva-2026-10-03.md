# Hamburg and UvA maintenance: 2026-10-03

## Hamburg

The English catalogue shell at
<https://www.uni-hamburg.de/en/campuscenter/studienangebot> references
`studiengaenge/indexDE.js`. The official `indexEN.js` endpoint still works.
Requiring the English filename in the shell caused repeated refresh failures.

Accept either observed shell language while continuing to parse the English
asset, preserving programme names and IDs. The existing catalogue-size and
admissions-policy checks remain in force.

Live dry run: three successful requests, 109 deduplicated programmes (173 raw
master's rows), matching the previous catalogue with no removed IDs. No exact
application windows were discovered. Programme-level window discovery remains
pending; this is a catalogue refresh recovery.

## University of Amsterdam

The official programme JSON endpoint remains available, but the central guide at
<https://www.uva.nl/en/education/admissions/masters/applying-for-a-degree-programme.html>
returns HTTP 404 from the local retrieval path. Search-index copies still show
the guide, so no unverified replacement URL is configured.

Parse and validate the catalogue independently. If the guide cannot be retrieved
or recognised, retain an `APPLICATION_GUIDE_UNAVAILABLE` warning and use each
official programme page as its application-information link. Do not claim that
the guide was verified and do not infer dates. Catalogue transport failures,
invalid JSON and insufficient programme counts still fail the run.

Live dry run: 269 programmes versus 271 previously, one new candidate, zero exact
windows; the guide's HTTP 404 is explicitly recorded. Changes in programme IDs
remain available in the discovery diff for review. No public programmes or dates
were removed or promoted. Application-window discovery remains pending.
