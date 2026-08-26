# Dedicated adapter health

- Checked adapters: 302
- Healthy: 262
- Schools needing maintenance: 40
- Schools monitoring without exact windows: 206
- Schools that gained exact windows: None
- Published-data risks: 10
- Unavailable adapters: 33

## Maintenance required

| University | Priority | Catalogue | Windows | Reason | Next action | Last success |
|---|---|---|---|---|---|---|
| Aalto University | availability | error | unknown | Adapter failed 27 consecutive checks: The read operation timed out | Check source access; update the endpoint or official-domain fallback. | 2026-07-30T03:56:36.366815+00:00 |
| Brown University | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T04:39:30.200455+00:00 |
| California Institute of Technology (Caltech) | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T22:44:38.493805+00:00 |
| Case Western Reserve University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-10T11:23:27.696335+00:00 |
| Curtin University | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:23:07.118985+00:00 |
| Harvard University | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-07T15:44:51.145053+00:00 |
| Khalifa University | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:34:00.796948+00:00 |
| King's College London | data integrity | error | needs-opening-date | Adapter failed 6 consecutive checks: 146 of 173 KCL programme requirements pages failed during discovery, exceeding the 10% critical-detail threshold. Observed window count fell from baseline 48 to 13. | Check source access; update the endpoint or official-domain fallback. | 2026-08-20T05:32:50.207443+00:00 |
| Macquarie University (Sydney, Australia) | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:39:48.632069+00:00 |
| Medical University of Vienna | data integrity | ok | partial | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:40:28.862677+00:00 |
| Michigan State University | data integrity | error | monitoring | Michigan State's official graduate catalogue exposed unclassified degree codes; those routes were not ingested. Adapter failed 3 consecutive checks: Michigan State's Registrar catalogue returned an access challenge through Browser Rendering | Check source access; update the endpoint or official-domain fallback. | 2026-08-23T05:46:03.167479+00:00 |
| Nanyang Technological University, Singapore (NTU Singapore) | data integrity | error | monitoring | Adapter failed 6 consecutive checks: NTU official application page produced zero windows without an explicit no-programmes-open notice. Exact window count fell from baseline 29 to 0. Observed window count fell from baseline 29 to 0. | Compare the official cycle with parsed windows before publication. | 2026-08-20T05:40:59.538298+00:00 |
| Northwestern University | availability | error | exact | Adapter failed 27 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:08:13.273947+00:00 |
| The Ohio State University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-10T08:57:55.675038+00:00 |
| Princeton University | availability | error | needs-opening-date | Adapter failed 27 consecutive checks: Princeton official page was unavailable: https://gradschool.princeton.edu/academics/degrees-requirements/fields-study | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:10:30.551856+00:00 |
| Queen's University Belfast | availability | error | unknown | Adapter failed 17 consecutive checks: QUB catalogue no longer returned its known AWS WAF page | Check source access; update the endpoint or official-domain fallback. | 2026-08-09T20:57:15.156115+00:00 |
| South China University of Technology | availability | error | unknown | Adapter failed 14 consecutive checks: SCUT catalogue did not expose its programme selector | Check source access; update the endpoint or official-domain fallback. | 2026-08-13T04:33:21.464199+00:00 |
| Sungkyunkwan University (SKKU) | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:48:17.586138+00:00 |
| The University of Queensland | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-06T13:50:25.975297+00:00 |
| Tufts University | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T02:06:38.353496+00:00 |
| University of California, Berkeley (UCB) | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T11:22:56.672814+00:00 |
| University of California, Santa Barbara (UCSB) | availability | error | monitoring | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-10T06:31:49.645065+00:00 |
| University of Chicago | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T02:51:15.361384+00:00 |
| University of Cologne | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T03:04:14.643209+00:00 |
| The University of Edinburgh | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T18:21:45.060199+00:00 |
| University of Gothenburg | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:26:20.867991+00:00 |
| University of Helsinki | availability | error | unknown | Adapter failed 27 consecutive checks: [Errno 101] Network is unreachable | Check source access; update the endpoint or official-domain fallback. | 2026-07-30T03:46:13.194655+00:00 |
| University of Leicester | availability | error | monitoring | Adapter failed 15 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T08:04:44.041800+00:00 |
| University of Maryland, College Park | availability | error | unknown | Adapter failed 16 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-10T08:00:20.005163+00:00 |
| University of North Carolina at Chapel Hill | availability | error | unknown | Adapter failed 23 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-04T05:09:52.235528+00:00 |
| University of Oxford | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T03:14:35.526337+00:00 |
| University of Pennsylvania | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-15T00:47:37.357985+00:00 |
| University of Southern California | availability | error | unknown | Adapter failed 17 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-09T20:33:52.659548+00:00 |
| University of Texas at Austin | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-26T04:39:38.035209+00:00 |
| University of Toronto | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T15:17:30.251008+00:00 |
| University of Twente | data integrity | ok | recurring-policy-partial | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-08-26T05:54:43.463072+00:00 |
| University of Virginia | availability | error | unknown | Adapter failed 14 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-13T06:05:47.789675+00:00 |
| University of Washington | availability | error | monitoring | Adapter failed 2 consecutive checks: HTTP 500 | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:26:39.832871+00:00 |
| Technische Universität Wien | availability | error | monitoring | Adapter failed 2 consecutive checks: vienna-university-of-technology catalogue contained 0 master's programmes; expected at least 30 | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:11:04.801811+00:00 |
| Yale University | availability | error | unknown | Adapter failed 32 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T10:52:23.116027+00:00 |

Expected `monitoring` status is not an error. The issue body is refreshed after
every full run, while consolidated reminder comments are limited to once every
seven days until all alerts clear.
