# Western University directory recovery — 2026-10-09

## Official evidence

The previous directory, https://grad.uwo.ca/admissions/programs/index.cfm,
now redirects to the graduate-school homepage. That page links the replacement
https://grad.uwo.ca/admissions/explore-our-programs.cfm. The replacement returns
HTTP 200 and retains the programme table: 161 total offerings/specializations,
including 87 master's degree rows. The existing minimum of 80 remains unchanged.

Relative detail links now resolve under `/admissions/program.cfm`, not the old
`/admissions/programs/` directory. The live Anatomy and Cell Biology MSc detail
at https://grad.uwo.ca/admissions/program.cfm?p=5 was checked successfully.
The new official application guide is
https://grad.uwo.ca/admissions/apply-for-admission/index.cfm.

## Change and verification

Update both entry points and therefore the base used for relative detail links.
Keep existing programme identities, including the curated Computer Science ID.
Reject malformed master's rows instead of silently dropping them. Continue to
exclude doctoral/diploma rows and reject a homepage as an incomplete catalogue.

Live discovery dry run: 87 current and 87 previous programmes, no added, changed
or disappeared programme IDs, no new candidates, no adapter warnings, two direct
successful requests. Focused tests cover relative links, degree distinctions,
stable identity, incomplete rows and homepage redirects. Validation includes
full pytest, Ruff, public-data validation, temporary build and frontend checks.

## Remaining window-discovery work

Catalogue recovery is complete; systematic programme deadline discovery is not.
The application guide explicitly says deadlines differ by programme and domestic
versus international applicant category. The sampled Anatomy and Cell Biology
page provides recurring month/day deadlines by curriculum/term, without a
complete year-specific opening/closing pair. Do not infer an exact window from
those dates. Further programme/faculty review is still required.

No operational candidate/state files or published dates were changed.
During triage, Queen's Belfast returned HTTP 403; its minimum count was not
lowered without evidence. Icahn's heartbeat returned only a client-rendered
shell; no speculative changes were made to that adapter.
