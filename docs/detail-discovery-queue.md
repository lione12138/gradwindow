# Shared programme detail queue

Implemented for UCL, Edinburgh and Toronto on 2026-11-02. This is a shared
scheduling layer around their existing official-source parsers, not a universal
date parser or a claim of complete school-level application-window coverage.

## Catalogue and detail work

UCL and Edinburgh save a metadata-only `catalogueCheckpoint` after their directory
checks succeed. The checkpoint has a versioned key, content hash and original
fetch timestamp. Normal runs reuse it for seven days; expiry, a changed parser
key, a changed minimum count or corruption requires a complete directory refresh.
Failed/incomplete refreshes never replace the last complete checkpoint. Detail
enrichment cannot mutate its metadata. The checkpoint cannot contain dates.
An intake change not yet seen by the directory still fails UCL's detail identity
and intake checks; the old directory cannot justify publishing a new cycle.

Toronto continues checking its small public API directory each run: the API's
modified timestamp, degree list and configured intake year invalidate detail
tasks when their source identity changes.

| Adapter | Detail request budget per run | Normal minimum recheck interval |
| --- | --- | --- |
| UCL | 5 on directory-refresh runs, 24 with a reused directory | 1 day |
| Edinburgh | 24, including newly discovered courses | 1 day |
| Toronto | 24, including newly discovered courses | 14 days |

These are upper bounds, not throughput promises: transport errors pause a batch,
and school selection still follows the existing pipeline scheduler. UCL allows
up to 45 browser fallbacks on a refresh run (up to 40 directory pages plus five
details). Reused-directory runs need no directory requests. A smaller explicit
transport budget remains authoritative.

## Durable progress and errors

`detailQueue` maps each official detail URL, including option query parameters,
to its identity fingerprint, attempt time, last successful check, last outcome,
failure count and next eligible time. New tasks precede previously attempted
tasks; older attempts precede more recent ones. Changed identities or intakes
start a new task. Both successful and failed attempts advance the rotation.

The common executor isolates expected parser errors per page. A transport error
pauses further requests in that school batch. Failures back off from two hours
to a maximum of 48 hours. Local fallback-budget exhaustion, upstream rate limits,
blocks and page-review errors are separate outcomes. Unexpected programming
errors still fail the adapter instead of being silently labelled missing dates.
Edinburgh and Toronto use the shared sequential, paced executor; their old
worker-count constructor arguments remain accepted for caller compatibility.
UCL shares scheduling/state but retains its scoped application-evidence parser.

The central `discover_programmes` transaction persists queue and catalogue state
alongside review candidates, through the existing manifest-aware IO layer. No
extra state files or alternate publication path are introduced. A dry run does
not advance the queue. A manual discovery PR must be merged before another main
checkout can resume from that state; daily refreshes use the existing validated
data-PR merge flow. Failed CI/PR publication does not advance main's checkpoint.

## Trust and coverage

Cached and deferred detail dates are excluded from current-run observations.
Existing candidates, verification times and confirmation counts are retained.
The separate `windowBaseline` survives skipped runs, so a later successful
check can still detect an actual removed or changed window. Directory reuse
retains the previous watched-source fingerprint without inventing a new fetch.

`adapterDiagnostics.detailQueue` reports eligible tasks, attempted, checked,
failed, deferred, never successfully checked and last-outcome counts. A programme
waiting for its first check is `catalogue-only`, not an assertion that its
official page has no deadline. The older `programmesWithoutDeadlines` field still
describes this run's output; use the queue diagnostics to distinguish unchecked
courses from checked pages without exact dates. Date candidates still require
the normal official-evidence validation and review/promotion process.

## Adding another adapter

1. Keep the school's directory completeness and official identity guards. Use
   `CatalogueCheckpoint` only around a metadata-only directory loader. Include
   parser version and relevant configuration in its key; bump the version when
   directory interpretation changes. Set `catalogue_max_age_days=0` on UCL or
   Edinburgh when explicitly investigating a directory change.
2. Supply `DetailQueue` with URL-to-identity inputs covering programme/option,
   intake and source revision where available. Keep date interpretation in the
   school's parser. Include a parser version in the task identity when a parser
   update must bypass the current cooldown.
3. Save the queue through `catalog.adapter_state` and call `queue.attach` so
   failed/unvisited IDs reach shared candidate-preservation logic. Never label a
   cached page a fresh check. Set `uses_shared_detail_queue = True` so changes to
   the common module automatically select this adapter for post-merge smoke.
4. Test cold-start bounds, persisted continuation, parser/transport failure,
   identity changes, dry-run non-mutation and original verification timestamps.

The three-school fixture integration suite exercises the same contract against
UCL cards, Edinburgh HTML links and Toronto API rows. Future work includes
migrating additional adapters and prioritizing approaching deadlines within the
queue; neither is implied by this initial integration.
