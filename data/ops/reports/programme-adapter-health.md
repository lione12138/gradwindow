# Dedicated adapter health

- Checked adapters: 144
- Healthy: 120
- Schools needing maintenance: 24
- Schools monitoring without exact windows: 92
- Schools that gained exact windows: None

## Maintenance required

| University | Catalogue | Windows | Reason | Last success |
|---|---|---|---|---|
| Aalto University | error | unknown | Adapter failed 5 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-30T03:56:36.366815+00:00 |
| Brown University | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T04:39:30.200455+00:00 |
| California Institute of Technology (Caltech) | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T22:44:38.493805+00:00 |
| Harvard University | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-07T15:44:51.145053+00:00 |
| McGill University | ok | exact | Exact window count fell from baseline 304 to 302. | 2026-08-04T07:06:08.198315+00:00 |
| Nanyang Technological University, Singapore (NTU Singapore) | error | exact | Adapter failed 2 consecutive checks: NTU live application table contained programmes missing from the official coursework catalogue: chinese, managerial economics chinese No successful adapter check has completed in the last 48 hours. | 2026-08-02T07:09:20.266931+00:00 |
| National University of Singapore (NUS) | ok | monitoring | Exact window count fell from baseline 52 to 0. | 2026-08-04T07:08:54.742592+00:00 |
| Northwestern University | error | exact | Adapter failed 5 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-29T07:08:13.273947+00:00 |
| Princeton University | error | needs-opening-date | Adapter failed 5 consecutive checks: Princeton official page was unavailable: https://gradschool.princeton.edu/academics/degrees-requirements/fields-study No successful adapter check has completed in the last 48 hours. | 2026-07-29T07:10:30.551856+00:00 |
| The Chinese University of Hong Kong (CUHK) | ok | needs-opening-date | Exact window count fell from baseline 231 to 0. | 2026-08-04T06:52:12.528345+00:00 |
| The University of Queensland | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-06T13:50:25.975297+00:00 |
| The University of Western Australia | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | 2026-08-04T07:22:40.878103+00:00 |
| University of British Columbia | ok | partial | Exact window count fell from baseline 146 to 140. | 2026-08-04T07:16:49.942527+00:00 |
| University of California, Berkeley (UCB) | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T11:22:56.672814+00:00 |
| University of Cambridge | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-01T16:13:46.525518+00:00 |
| University of Chicago | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T02:51:15.361384+00:00 |
| The University of Edinburgh | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T18:21:45.060199+00:00 |
| University of Helsinki | error | unknown | Adapter failed 5 consecutive checks: [Errno 101] Network is unreachable No successful adapter check has completed in the last 48 hours. | 2026-07-30T03:46:13.194655+00:00 |
| University of Oxford | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-14T03:14:35.526337+00:00 |
| University of Pennsylvania | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-15T00:47:37.357985+00:00 |
| The University of Technology Sydney (UTS) | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | 2026-08-04T07:22:31.121927+00:00 |
| University of Texas at Austin | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-26T04:39:38.035209+00:00 |
| University of Toronto | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T15:17:30.251008+00:00 |
| Yale University | error | unknown | Adapter failed 10 consecutive checks: HTTP 403 No successful adapter check has completed in the last 48 hours. | 2026-07-23T10:52:23.116027+00:00 |

Expected `monitoring` status is not an error. Notifications are emitted only
when the active school-level alert set changes.
