# Dedicated adapter health

- Checked adapters: 302
- Healthy: 282
- Schools needing maintenance: 20
- Schools monitoring without exact windows: 213
- Schools that gained exact windows: University of British Columbia, University of Helsinki
- Published-data risks: 3
- Unavailable adapters: 18
- Non-blocking catalogue count warnings: 1

## Maintenance required

| University | Priority | Catalogue | Windows | Reason | Next action | Last success |
|---|---|---|---|---|---|---|
| California Institute of Technology (Caltech) | availability | error | unknown | Adapter failed 36 consecutive checks: Caltech application page lacked its target academic year | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T22:44:38.493805+00:00 |
| King Abdulaziz University (KAU) | data integrity | ok | monitoring | 1 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-08-30T10:41:07.925652+00:00 |
| Michigan State University | data integrity | partial | monitoring | 181 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-08-30T10:47:09.076888+00:00 |
| Northwestern University | data integrity | error | monitoring | Adapter failed 2 consecutive checks: Northwestern Bienen's official timeline source did not contain MM/DMA application timeline content Exact window count fell from baseline 11 to 0. Observed window count fell from baseline 11 to 0. | Compare the official cycle with parsed windows before publication. | 2026-08-28T00:47:01.617158+00:00 |
| Princeton University | availability | error | needs-opening-date | Adapter failed 31 consecutive checks: Princeton's official next application cycle was not found | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:10:30.551856+00:00 |
| Purdue University | availability | error | monitoring | Adapter failed 2 consecutive checks: purdue-university catalogue contained 118 master's programmes; expected at least 120 | Check source access; update the endpoint or official-domain fallback. | 2026-08-28T00:52:02.095112+00:00 |
| South China University of Technology | availability | error | unknown | Adapter failed 18 consecutive checks: SCUT catalogue did not expose its programme selector | Check source access; update the endpoint or official-domain fallback. | 2026-08-13T04:33:21.464199+00:00 |
| Stockholm University | availability | error | monitoring | Adapter failed 2 consecutive checks: [Errno 101] Network is unreachable | Check source access; update the endpoint or official-domain fallback. | 2026-08-28T00:55:27.033091+00:00 |
| University of Nottingham | availability | error | monitoring | Adapter failed 4 consecutive checks: Nottingham's official course search contained 139 master's courses; expected at least 140 | Check source access; update the endpoint or official-domain fallback. | 2026-08-26T05:42:19.184925+00:00 |
| The University of Queensland | availability | error | unknown | Adapter failed 36 consecutive checks: UQ detail retrieval failed for 87/87 programmes | Check source access; update the endpoint or official-domain fallback. | 2026-07-06T13:50:25.975297+00:00 |
| Tufts University | availability | error | unknown | Adapter failed 20 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T02:06:38.353496+00:00 |
| University of California, San Francisco | availability | error | monitoring | Adapter failed 5 consecutive checks: UCSF portal contained 4 master's routes; expected at least 12 | Check source access; update the endpoint or official-domain fallback. | 2026-08-25T05:59:19.009415+00:00 |
| The University of Edinburgh | availability | error | unknown | Adapter failed 36 consecutive checks: University of Edinburgh detail refresh failed for 19 of 24 programme pages (79.2%); previous exact windows were preserved | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T18:21:45.060199+00:00 |
| University of Hamburg | availability | error | monitoring | Adapter failed 4 consecutive checks: Hamburg's official catalogue asset is missing | Check source access; update the endpoint or official-domain fallback. | 2026-08-26T05:26:46.263233+00:00 |
| University of Leicester | availability | error | monitoring | Adapter failed 19 consecutive checks: Leicester's official postgraduate application guide is missing | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T08:04:44.041800+00:00 |
| University of Oxford | availability | error | unknown | Adapter failed 36 consecutive checks: Direct retrieval and browser fallback failed: direct=HTTP 403; browser=The read operation timed out | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T03:14:35.526337+00:00 |
| University of Southern California | availability | error | unknown | Adapter failed 21 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-09T20:33:52.659548+00:00 |
| University of Toronto | availability | error | unknown | Adapter failed 36 consecutive checks: Expecting value: line 1 column 1 (char 0) | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T15:17:30.251008+00:00 |
| University of Washington | availability | error | monitoring | Adapter failed 6 consecutive checks: Expecting value: line 1 column 1 (char 0) | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:26:39.832871+00:00 |
| Technische Universität Wien | availability | error | monitoring | Adapter failed 6 consecutive checks: vienna-university-of-technology catalogue contained 0 master's programmes; expected at least 30 | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:11:04.801811+00:00 |

## Warnings

- Michigan State University: catalogue count changed from 181 to 172; the adapter remains healthy while the cumulative change is monitored.

Expected `monitoring` status is not an error. The issue body is refreshed after
every full run, while consolidated reminder comments are limited to once every
seven days until all alerts clear.
