# Browser fetch scheduling and checkpoints

The direct HTTP path remains the default. Cloudflare rendering is a bounded
fallback, not the primary crawler for every school. This change does not
approve programmes, dates or incomplete discovery results.

## Scheduling

Daily updates, manual programme discovery, and each post-merge adapter smoke
job share the `application-data-state-writes` GitHub concurrency group.
`queue: max` permits up to 100 pending runs/jobs instead of replacing the
previous pending run. It is not an unlimited queue or a guaranteed priority
order. Unrelated repositories, dashboard requests and local machines are not
coordinated by this repository's queue.

Within a Python process, environment-created browser clients with the same
configuration are reused so adapters share their request lock and pacing.
Production workflows use a 12-second minimum interval. Retry-After supports
seconds and HTTP dates; missing delays use exponential backoff. Waiting more
than 60 seconds defers the request instead of keeping a worker asleep. A known
daily browser-time exhaustion blocks further uncached requests until the next
UTC day. Exhausted transient 429 retries impose at least a 60-second cooldown.
These changes reduce avoidable contention; they cannot guarantee access to a
university or remove a provider's quota.

## Page checkpoints

Set `CLOUDFLARE_BROWSER_CACHE_DIR` to enable a SQLite public-page checkpoint
store. The three workflows restore and save it with the local
`browser-checkpoint` action, including when discovery fails. Every successful
non-empty, non-obvious-challenge response is committed immediately. Cache keys
include the account, endpoint and complete rendering request (URL, option,
selector and script). Tokens are not stored. The cache must only be used for
the existing public university-page discovery flows, not authenticated pages.

On a retry, the parser runs again and reuses successful pages, requesting only
missing/expired ones. This is page-level recovery, not a saved parser cursor.
Existing catalogue completeness, duplicate and evidence checks still apply.
Partial candidates/state are not published merely because some pages were saved.

Pages expire after six hours or at the next UTC date boundary, whichever comes
first. No stale-on-error fallback is allowed. Resume after that boundary must
fetch fresh pages. Cache restore follows GitHub's branch visibility rules;
main can share with main, but a feature-branch cache is not a promise of reuse
on main. Hard runner loss or failed cache upload may lose that run's checkpoint.
For a forced fresh investigation, use an empty cache directory (or unset the
variable); changing this does not bypass service limits. SQLite data is ignored
by Git and is not a public dataset.

## Usage

Each workflow summary reports real browser milliseconds from
`X-Browser-Ms-Used`, request/status counts, cache hits, and requests where the
usage header was missing. Missing usage is unknown, never zero. Counts are
cumulative for the workflow run/attempt represented in the restored store,
not the complete Cloudflare account bill. No estimate equates wall-clock job
duration to browser time. Run `python -m gradwindow.browser_cache` to print the
current run's counters with the cache environment variable set.

Official references checked 2026-10-10:

- https://developers.cloudflare.com/browser-run/limits/
- https://developers.cloudflare.com/browser-run/pricing/
- https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency

Future scope: incremental HTTP fetching, a distributed account-wide queue
across repositories, and adaptive per-school refresh schedules are separate
from this bounded browser-fallback implementation.
