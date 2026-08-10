# Dedicated adapter health

- Checked adapters: 200
- Healthy: 174
- Schools needing maintenance: 26
- Schools monitoring without exact windows: 139
- Schools that gained exact windows: The University of Manchester
- Published-data risks: 4
- Unavailable adapters: 22

## Maintenance required

| University | Priority | Catalogue | Windows | Reason | Next action | Last success |
|---|---|---|---|---|---|---|
| Aalto University | availability | error | unknown | Adapter failed 11 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-30T03:56:36.366815+00:00 |
| Brown University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T04:39:30.200455+00:00 |
| California Institute of Technology (Caltech) | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T22:44:38.493805+00:00 |
| Harvard University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-07T15:44:51.145053+00:00 |
| KAIST | availability | error | exact | Adapter failed 3 consecutive checks: timed out | Check source access; update the endpoint or official-domain fallback. | 2026-08-07T06:11:04.478993+00:00 |
| McGill University | data integrity | ok | exact | Exact window count fell from baseline 304 to 302. | Compare the official cycle with parsed windows before publication. | 2026-08-10T06:15:18.004535+00:00 |
| Nanyang Technological University, Singapore (NTU Singapore) | availability | error | exact | Adapter failed 8 consecutive checks: NTU live application table contained programmes missing from the official coursework catalogue: chinese, managerial economics chinese | Check source access; update the endpoint or official-domain fallback. | 2026-08-02T07:09:20.266931+00:00 |
| National University of Singapore (NUS) | data integrity | ok | monitoring | Exact window count fell from baseline 52 to 0. | Compare the official cycle with parsed windows before publication. | 2026-08-10T06:18:20.328682+00:00 |
| New York University (NYU) | availability | error | unknown | Adapter failed 4 consecutive checks: HTTP 405 | Check source access; update the endpoint or official-domain fallback. | 2026-08-06T15:03:23.536563+00:00 |
| Northwestern University | availability | error | exact | Adapter failed 11 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:08:13.273947+00:00 |
| Princeton University | availability | error | needs-opening-date | Adapter failed 11 consecutive checks: Princeton official page was unavailable: https://gradschool.princeton.edu/academics/degrees-requirements/fields-study | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:10:30.551856+00:00 |
| Stockholm University | availability | error | unknown | Adapter failed 7 consecutive checks: [Errno 101] Network is unreachable | Check source access; update the endpoint or official-domain fallback. | 2026-08-03T14:22:33.202618+00:00 |
| The Chinese University of Hong Kong (CUHK) | data integrity | ok | needs-opening-date | Exact window count fell from baseline 231 to 0. | Compare the official cycle with parsed windows before publication. | 2026-08-10T05:57:09.429854+00:00 |
| The University of Queensland | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-06T13:50:25.975297+00:00 |
| University of British Columbia | data integrity | ok | partial | Exact window count fell from baseline 146 to 141. | Compare the official cycle with parsed windows before publication. | 2026-08-10T06:27:25.894945+00:00 |
| University of California, Berkeley (UCB) | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T11:22:56.672814+00:00 |
| University of Cambridge | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-01T16:13:46.525518+00:00 |
| University of Chicago | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T02:51:15.361384+00:00 |
| The University of Edinburgh | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T18:21:45.060199+00:00 |
| University of Helsinki | availability | error | unknown | Adapter failed 11 consecutive checks: [Errno 101] Network is unreachable | Check source access; update the endpoint or official-domain fallback. | 2026-07-30T03:46:13.194655+00:00 |
| University of North Carolina at Chapel Hill | availability | error | unknown | Adapter failed 7 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-04T05:09:52.235528+00:00 |
| University of Oxford | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T03:14:35.526337+00:00 |
| University of Pennsylvania | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-15T00:47:37.357985+00:00 |
| University of Texas at Austin | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T04:39:38.035209+00:00 |
| University of Toronto | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T15:17:30.251008+00:00 |
| Yale University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T10:52:23.116027+00:00 |

Expected `monitoring` status is not an error. The issue body is refreshed after
every full run, while consolidated reminder comments are limited to once every
seven days until all alerts clear.
