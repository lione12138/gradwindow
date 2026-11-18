# Directory retrieval checks

On 2026-11-18 the Edinburgh official taught A–Z directory returned 240 course
links, including certificates and doctorates. The existing master's filter
selected 224 unique programmes. The previous minimum of 250 master's programmes
could not be met by that directory. The default floor is now 200; explicit
caller overrides remain supported. When the page declares a numeric result
count, it must match the number of course links before any details are fetched.
The directory checkpoint version changed so older checkpoints are revalidated.
This is a catalogue check, not completed application-window discovery.

Toronto's direct public API returned valid JSON locally. Its earlier hosted
smoke failed JSON decoding after browser fallback; the exact returned document
was not retained, so its cause is not conclusively established. The parser now
also accepts a single browser-rendered `pre` JSON document, preserving escaped
entities and rejecting forms, scripts, multiple JSON blocks and extra body text.
An invalid document still fails directory discovery and cannot erase candidates.
The decoder is reusable by other public API adapters.

Live directory-only checks on 2026-11-18 accepted Edinburgh's 224 programmes
without fetching details. Toronto's two real API pages, wrapped in the browser
document format, produced 126 programme rows. These checks generated no public
data or operational candidates. Hosted smoke remains necessary to distinguish
rendered JSON from access challenges or other unexpected responses.
