# Discovery reliability and failure recovery

The October 2026 reliability changes protect programme discovery progress without
changing the approval requirements for official application windows.

## Generic catalogue and detail checks

The generic adapter retains every eligible programme found on the configured seed
pages. `maxDetailPages` limits detail requests, not the number of catalogue rows.
Detail requests rotate across runs using `adapterState.detailMonitor`, ordered by
the last attempt time with unvisited URLs first. A new configured intake resets
the scheduling baseline. `--dry-run` does not persist that baseline.

The discovery report and saved state expose:

- `adapterDiagnostics.catalogueComplete`: all configured seeds were read; this
  does **not** certify that those seeds cover every programme at the university.
- `detailSucceededProgrammeIds`: details successfully inspected this run.
- `detailFailedProgrammeIds`: detail retrieval or parsing failed.
- `detailUnvisitedProgrammeIds`: detail checks deferred by this run's budget.
- `detailMonitor`: request counts and the number of URLs never attempted.

Failed or deferred rows have no new date evidence. Existing candidates retain
their dates and original timestamps; newly discovered rows remain catalogue-only
candidates. Current snapshot dates are only from the current successful detail
checks. Published-data auditing and reconciliation exclude deferred or failed
programme details, so an unvisited page cannot trigger retirement of a published
window. A successful recheck that finds no dates can still update a candidate and
trigger the existing review process.

## Safe candidate replacement

`discover-generic-batch --replace-existing` stages each school's programme
candidates in a temporary sibling file. Failed, blocked, and no-result runs do
not replace the original candidates. A successful bounded run merges observed
updates while retaining unfinished candidates. Pruning of matching pending
new-programme candidates requires complete configured catalogue/detail coverage.
Reviewed records and unrelated schools are retained.

This protects the programme-candidate replacement step. It is not a transaction
across catalogue state, window candidates, approvals, or public data. Those
collections retain their existing validation and write paths.

## Daily pipeline diagnostics

Dedicated discovery writes `.cache/pipeline-run/dedicated-discovery.json` before
each adapter and after each result. It records the active adapter, completed and
failed counts, and per-school reports. If execution is interrupted, `running`
means that completion was not recorded; it does not assert that a partial result
is safe to publish. A new invocation starts a new report. Dry runs do not write
the default report.

The scheduled/manual data workflow captures the pipeline exit status with
`pipefail`, and attempts diagnostic collection/upload even when the pipeline
fails. Artifacts named `daily-pipeline-diagnostics-<run>-<attempt>` are retained
for 14 days. They contain a sanitized log tail, the progress report, and an
allowlist of operational candidate/state/report files including university
shards. The collector excludes credentials, browser cache, and public exports,
redacts the configured provider credential values, and records missing or
size-limited files in `inventory.json`. Limits are 2 MiB for the log tail,
32 MiB per operational file, and 256 MiB total retained content. Abrupt runner
termination or an artifact-service failure can still prevent upload.

To investigate a failed run, inspect the log and progress report, then use the
inventory to determine which snapshots were retained. Some files can be unchanged
checkout data. Review and validate any recovered changes against the current
branch before applying them. Failed-run artifacts are **not automatically
restored, approved, or published**; automatic multi-stage resume remains future
work.
