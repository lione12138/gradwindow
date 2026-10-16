# Reviewed deadline-only facts

`data/reviewed-deadlines.json` holds manually reviewed deadline facts, separate
from `applications.json`. An exact closing date does not establish an opening
date or prove the programme is currently accepting applications. These facts
must not feed open-status counts, predictions, notifications or calendar exports.

Review the full official programme page, degree, intake/cycle, applicant scope,
round and deadline semantics. Record supporting excerpts and official source URLs,
including a separate cycle source when necessary. Never fill an unknown opening
with the first of a month, a shared default or the day the page was checked.
Search snippets and unreviewed programme candidates are insufficient.

Prepare a JSON draft matching `reviewed-deadline.schema.json`, omitting
`reviewedBy`, then explicitly approve it:

```
gradwindow approve-deadline path/to/draft.json --reviewer reviewer-name
gradwindow validate
gradwindow build-site
```

The command requires a known programme, official-domain evidence, reviewer and
exact closing date. It refuses duplicate IDs and does not alter application
windows. Semantic evidence review remains the reviewer's responsibility; domain
validation alone cannot prove that a quotation supports a particular intake.
Adapters must never invoke this approval automatically.

The first reviewed example is Harvard's SM Data Science: its programme page
lists December 1, 2026, and the GSAS application page identifies the 2027–2028
academic year. Reviewed on October 15, 2026. The application page says September
without an exact opening day, so `opensAt` stays null. The public UI displays the
verification date and links to the official page; it does not assert current
availability. At this stage these facts are manually maintained and shown in
the All universities programme catalogue, not included in window-only filters.

Follow-up work: systematic rechecking of these sources, extension to more
reviewed Stanford/Harvard programmes, and programme-specific full-window
discovery where faculty pages supply exact opening dates.
