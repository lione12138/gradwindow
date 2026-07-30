# Dedicated adapter health

- Checked adapters: 104
- Healthy: 88
- Schools needing maintenance: 16
- Schools monitoring without exact windows: 56
- Schools that gained exact windows: University of British Columbia

## Maintenance required

| University | Catalogue | Windows | Reason | Last success |
|---|---|---|---|---|
| Brown University | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T04:39:30.200455+00:00 |
| California Institute of Technology (Caltech) | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T22:44:38.493805+00:00 |
| Harvard University | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-07T15:44:51.145053+00:00 |
| KAIST | error | exact | Adapter failed 2 consecutive checks: timed out No successful adapter check has completed in the last 48 hours. | 2026-07-28T06:57:40.186890+00:00 |
| McGill University | error | exact | Adapter failed 2 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-28T07:00:29.202007+00:00 |
| National University of Singapore (NUS) | ok | monitoring | Exact window count fell from baseline 52 to 0. | 2026-07-30T07:07:44.382642+00:00 |
| The University of Queensland | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-06T13:50:25.975297+00:00 |
| University of California, Berkeley (UCB) | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T11:22:56.672814+00:00 |
| University of Cambridge | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-01T16:13:46.525518+00:00 |
| University of Chicago | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T02:51:15.361384+00:00 |
| The University of Edinburgh | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T18:21:45.060199+00:00 |
| University of Oxford | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T03:14:35.526337+00:00 |
| University of Pennsylvania | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-15T00:47:37.357985+00:00 |
| University of Texas at Austin | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T04:39:38.035209+00:00 |
| University of Toronto | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T15:17:30.251008+00:00 |
| Yale University | error | unknown | Adapter failed 6 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T10:52:23.116027+00:00 |

Expected `monitoring` status is not an error. Notifications are emitted only
when the active school-level alert set changes.
