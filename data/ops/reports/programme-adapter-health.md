# Dedicated adapter health

- Checked adapters: 302
- Healthy: 259
- Schools needing maintenance: 43
- Schools monitoring without exact windows: 213
- Schools that gained exact windows: None
- Published-data risks: 19
- Unavailable adapters: 25
- Non-blocking catalogue count warnings: 15

## Maintenance required

| University | Priority | Catalogue | Windows | Reason | Next action | Last success |
|---|---|---|---|---|---|---|
| Beijing Institute of Technology | availability | error | partial | Adapter failed 2 consecutive checks: [Errno 101] Network is unreachable | Check source access; update the endpoint or official-domain fallback. | 2026-09-03T09:06:42.760461+00:00 |
| California Institute of Technology (Caltech) | availability | error | unknown | Adapter failed 42 consecutive checks: Caltech application page lacked its target academic year | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T22:44:38.493805+00:00 |
| Case Western Reserve University | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T08:47:19.718870+00:00 |
| Indian Institute of Technology Bombay (IITB) | availability | error | monitoring | Adapter failed 6 consecutive checks: indian-institute-of-technology-bombay-iitb catalogue contained 0 master's programmes; expected at least 40 | Check source access; update the endpoint or official-domain fallback. | 2026-08-30T10:33:48.781119+00:00 |
| Johannes Gutenberg University Mainz | availability | error | partial | Adapter failed 3 consecutive checks: HTTP 404 | Check source access; update the endpoint or official-domain fallback. | 2026-09-02T09:35:59.099966+00:00 |
| Khalifa University | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:01:09.650550+00:00 |
| KTH Royal Institute of Technology | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:01:42.922808+00:00 |
| Macquarie University (Sydney, Australia) | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:06:02.043996+00:00 |
| Medical University of Vienna | data integrity | ok | exact | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:06:34.159419+00:00 |
| Nanyang Technological University, Singapore (NTU Singapore) | data integrity | ok | partial | NTU's official application table contains 10 rows that could not be matched to the official coursework catalogue. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:10:19.754528+00:00 |
| Northwestern University | data integrity | error | monitoring | Adapter failed 8 consecutive checks: Northwestern Bienen's official timeline source did not contain MM/DMA application timeline content Exact window count fell from baseline 11 to 0. Observed window count fell from baseline 11 to 0. | Compare the official cycle with parsed windows before publication. | 2026-08-28T00:47:01.617158+00:00 |
| Pohang University of Science And Technology (POSTECH) | data integrity | ok | exact | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:14:42.103937+00:00 |
| Princeton University | availability | error | needs-opening-date | Adapter failed 37 consecutive checks: Princeton's official next application cycle was not found | Check source access; update the endpoint or official-domain fallback. | 2026-07-29T07:10:30.551856+00:00 |
| Purdue University | availability | error | monitoring | Adapter failed 8 consecutive checks: purdue-university catalogue contained 118 master's programmes; expected at least 120 | Check source access; update the endpoint or official-domain fallback. | 2026-08-28T00:52:02.095112+00:00 |
| Queen Mary University of London | data integrity | ok | monitoring | 1 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:15:35.518249+00:00 |
| Queen's University Belfast | availability | error | monitoring | Adapter failed 4 consecutive checks: QUB's January programme list did not match the main catalogue: [('people analytics', 'msc')] | Check source access; update the endpoint or official-domain fallback. | 2026-09-01T10:18:26.336806+00:00 |
| Soochow University (China) | availability | error | partial | Adapter failed 5 consecutive checks: Direct retrieval and browser fallback failed: direct=[Errno 101] Network is unreachable; browser=Cloudflare Browser Rendering returned HTTP 422: [{'code': 6002, 'message': 'A timeout was reached. Check gotoOptions/waitForSelector/waitForTimeout/actionTimeout options.', 'detail | Check source access; update the endpoint or official-domain fallback. | 2026-08-31T11:55:26.337843+00:00 |
| South China University of Technology | availability | error | unknown | Adapter failed 24 consecutive checks: SCUT catalogue did not expose its programme selector | Check source access; update the endpoint or official-domain fallback. | 2026-08-13T04:33:21.464199+00:00 |
| The University of Manchester | data integrity | ok | partial | Exact window count fell from baseline 72 to 68. Observed window count fell from baseline 427 to 279. | Compare the official cycle with parsed windows before publication. | 2026-09-05T09:05:18.779711+00:00 |
| University of Nottingham | availability | error | monitoring | Adapter failed 10 consecutive checks: Nottingham's official course search contained 139 master's courses; expected at least 140 | Check source access; update the endpoint or official-domain fallback. | 2026-08-26T05:42:19.184925+00:00 |
| The University of Queensland | availability | error | unknown | Adapter failed 42 consecutive checks: UQ detail retrieval failed for 87/87 programmes | Check source access; update the endpoint or official-domain fallback. | 2026-07-06T13:50:25.975297+00:00 |
| The University of Sydney | data integrity | ok | needs-opening-date | Observed window count fell from baseline 696 to 676. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:28:52.685118+00:00 |
| The University of Western Australia | data integrity | ok | monitoring | 2 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:47:28.574434+00:00 |
| Tufts University | availability | error | unknown | Adapter failed 26 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T02:06:38.353496+00:00 |
| UCL | availability | error | monitoring | Adapter failed 3 consecutive checks: UCL official catalogue only contained 0 taught courses; expected at least 550 | Check source access; update the endpoint or official-domain fallback. | 2026-09-02T10:02:53.885349+00:00 |
| Universiti Kebangsaan Malaysia (UKM) | data integrity | ok | monitoring | 1 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:37:35.554098+00:00 |
| University of California, Irvine | data integrity | ok | needs-opening-date | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:37:08.114483+00:00 |
| University of California, San Francisco | availability | error | monitoring | Adapter failed 11 consecutive checks: UCSF portal contained 4 master's routes; expected at least 12 | Check source access; update the endpoint or official-domain fallback. | 2026-08-25T05:59:19.009415+00:00 |
| The University of Edinburgh | availability | error | unknown | Adapter failed 42 consecutive checks: University of Edinburgh detail refresh failed for 19 of 24 programme pages (79.2%); previous exact windows were preserved | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T18:21:45.060199+00:00 |
| University of Glasgow | data integrity | ok | monitoring | Exact window count fell from baseline 1 to 0. Observed window count fell from baseline 185 to 0. | Compare the official cycle with parsed windows before publication. | 2026-09-05T08:54:02.321289+00:00 |
| University of Gothenburg | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T08:54:53.122067+00:00 |
| University of Hamburg | availability | error | monitoring | Adapter failed 10 consecutive checks: Hamburg's official catalogue asset is missing | Check source access; update the endpoint or official-domain fallback. | 2026-08-26T05:26:46.263233+00:00 |
| University of Leicester | availability | error | monitoring | Adapter failed 25 consecutive checks: Leicester's official postgraduate application guide is missing | Check source access; update the endpoint or official-domain fallback. | 2026-08-11T08:04:44.041800+00:00 |
| University of Oxford | availability | error | unknown | Adapter failed 42 consecutive checks: Direct retrieval and browser fallback failed: direct=HTTP 403; browser=The read operation timed out | Check source access; update the endpoint or official-domain fallback. | 2026-07-14T03:14:35.526337+00:00 |
| University of Pennsylvania | data integrity | ok | partial | Exact window count fell from baseline 21 to 19. Observed window count fell from baseline 34 to 32. | Compare the official cycle with parsed windows before publication. | 2026-09-05T09:44:48.190574+00:00 |
| University of Southampton | data integrity | ok | needs-opening-date | 1 programme record(s) disappeared before their lifecycle could be treated as expired. | Check source access; update the endpoint or official-domain fallback. | 2026-09-05T09:24:11.812392+00:00 |
| University of Southern California | availability | error | unknown | Adapter failed 27 consecutive checks: HTTP 403 | Check source access; update the endpoint or official-domain fallback. | 2026-08-09T20:33:52.659548+00:00 |
| University of Toronto | availability | error | unknown | Adapter failed 42 consecutive checks: Expecting value: line 1 column 1 (char 0) | Check source access; update the endpoint or official-domain fallback. | 2026-07-23T15:17:30.251008+00:00 |
| University of Utah | availability | error | needs-opening-date | Adapter failed 5 consecutive checks: Utah Kahlert Fall 2027 deadline source produced zero windows | Check source access; update the endpoint or official-domain fallback. | 2026-08-31T12:18:58.457676+00:00 |
| University of Washington | availability | error | monitoring | Adapter failed 12 consecutive checks: Expecting value: line 1 column 1 (char 0) | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:26:39.832871+00:00 |
| University of Wollongong | data integrity | ok | monitoring | The official window-watch source changed in two consecutive checks, but the parsed window result did not change. | Review the official date signals and update window parsing if needed. | 2026-09-05T09:47:20.298823+00:00 |
| Technische Universität Wien | availability | error | monitoring | Adapter failed 12 consecutive checks: vienna-university-of-technology catalogue contained 0 master's programmes; expected at least 30 | Check source access; update the endpoint or official-domain fallback. | 2026-08-24T06:11:04.801811+00:00 |
| Yonsei University | availability | error | exact | Adapter failed 3 consecutive checks: Yonsei admissions page did not link both English campus guides | Check source access; update the endpoint or official-domain fallback. | 2026-09-02T10:17:20.581090+00:00 |

## Warnings

- King Abdulaziz University (KAU): catalogue count changed from 118 to 117; the adapter remains healthy while the cumulative change is monitored.
- Michigan State University: catalogue count changed from 181 to 172; the adapter remains healthy while the cumulative change is monitored.
- New York University (NYU): catalogue count changed from 234 to 226; the adapter remains healthy while the cumulative change is monitored.
- Newcastle University: catalogue count changed from 188 to 178; the adapter remains healthy while the cumulative change is monitored.
- Queen Mary University of London: catalogue count changed from 285 to 284; the adapter remains healthy while the cumulative change is monitored.
- Swinburne University of Technology: catalogue count changed from 47 to 46; the adapter remains healthy while the cumulative change is monitored.
- The University of Manchester: catalogue count changed from 271 to 264; the adapter remains healthy while the cumulative change is monitored.
- The University of Sydney: catalogue count changed from 174 to 169; the adapter remains healthy while the cumulative change is monitored.
- The University of Western Australia: catalogue count changed from 93 to 91; the adapter remains healthy while the cumulative change is monitored.
- Universiti Kebangsaan Malaysia (UKM): catalogue count changed from 177 to 176; the adapter remains healthy while the cumulative change is monitored.
- University of Glasgow: catalogue count changed from 248 to 241; the adapter remains healthy while the cumulative change is monitored.
- University of Groningen: catalogue count changed from 208 to 203; the adapter remains healthy while the cumulative change is monitored.
- University of Rochester: catalogue count changed from 83 to 82; the adapter remains healthy while the cumulative change is monitored.
- University of Southampton: catalogue count changed from 202 to 201; the adapter remains healthy while the cumulative change is monitored.
- University of St Andrews: catalogue count changed from 106 to 103; the adapter remains healthy while the cumulative change is monitored.

Expected `monitoring` status is not an error. The issue body is refreshed after
every full run, while consolidated reminder comments are limited to once every
seven days until all alerts clear.
