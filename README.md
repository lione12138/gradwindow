# GradWindow

[![Tests](https://github.com/lione12138/gradwindow/actions/workflows/tests.yml/badge.svg)](https://github.com/lione12138/gradwindow/actions/workflows/tests.yml)
[![Website](https://img.shields.io/badge/Website-GradWindow-1e6548)](https://gradwindow.com/)

[中文](README.zh-CN.md) · [Open GradWindow](https://gradwindow.com/) · [Application calendar](https://gradwindow.com/calendar.html) · [Report a data error](https://github.com/lione12138/gradwindow/issues/new?template=report-data-error.yml) · [Contribute](CONTRIBUTING.md)

> Official-source master's application windows for top-200 universities across major global rankings.

![GradWindow social card](web/og-image-multiranking.png)

## Why GradWindow

- Every published exact date links back to an official university source.
- Official dates, recurring policies, and calendar-shift estimates are visibly separated.
- Search, status filters, saved universities, alerts, and calendar export form one application workflow.
- QS is the default view; THE and ARWU top-200 views are live. U.S. News coverage is not presented as live yet.

**Coverage:** 302 canonical universities · 29,388 programmes · 5,399 verified exact windows

Status date: **2026-09-01**

> **Estimate** means the date is shifted from the latest verified cycle and is not an official forecast. Always confirm dates on the linked university source.

## Open Now

| QS | University | Coverage | Next deadline | Data | Links |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) | 8 open windows | 2026-10-01 | Official | [Admissions](https://oge.mit.edu/graduate-admissions/) · [All programme details](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| =2 | Imperial College London | 13 open windows | 2026-09-28 | Estimate | [Admissions](https://www.imperial.ac.uk/study/apply/postgraduate-taught/) · [All programme details](https://gradwindow.com/?q=Imperial%20College%20London) |
| 6 | University of Cambridge | 1 open window | 2027-05-14 | Estimate | [Admissions](https://www.postgraduate.study.cam.ac.uk/application-process) · [All programme details](https://gradwindow.com/?q=University%20of%20Cambridge) |
| 10 | National University of Singapore (NUS) | 14 open windows | 2026-09-30 | Official + Estimate | [Admissions](https://nusgs.nus.edu.sg/admissions/) · [All programme details](https://gradwindow.com/?q=National%20University%20of%20Singapore%20%28NUS%29) |
| 11 | The University of Hong Kong | 89 open windows | 2026-11-03 | Estimate | [Admissions](https://admissions.hku.hk/tpg/) · [All programme details](https://gradwindow.com/?q=The%20University%20of%20Hong%20Kong) |

[View every open window on GradWindow →](https://gradwindow.com/?status=open)

## Opening Within 30 Days

| QS | University | Coverage | Next opening | Data | Links |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) | 16 upcoming windows | 2026-09-03 | Official | [Admissions](https://oge.mit.edu/graduate-admissions/) · [All programme details](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| =2 | Imperial College London | 117 upcoming windows | 2026-09-29 | Official + Estimate | [Admissions](https://www.imperial.ac.uk/study/apply/postgraduate-taught/) · [All programme details](https://gradwindow.com/?q=Imperial%20College%20London) |
| 6 | University of Cambridge | 156 upcoming windows | 2026-09-03 | Estimate | [Admissions](https://www.postgraduate.study.cam.ac.uk/application-process) · [All programme details](https://gradwindow.com/?q=University%20of%20Cambridge) |
| 10 | National University of Singapore (NUS) | 18 upcoming windows | 2026-10-01 | Official + Estimate | [Admissions](https://nusgs.nus.edu.sg/admissions/) · [All programme details](https://gradwindow.com/?q=National%20University%20of%20Singapore%20%28NUS%29) |
| 15 | University of Pennsylvania | 23 upcoming windows | 2026-09-15 | Official + Estimate | [Admissions](https://www.upenn.edu/academics/graduate) · [All programme details](https://gradwindow.com/?q=University%20of%20Pennsylvania) |

[View every upcoming window on GradWindow →](https://gradwindow.com/?status=upcoming)

## Data Trust Model

Parsers create review candidates; they do not publish deadlines directly. An exact window needs a university, scope, intake, applicant category, opening and closing date, application URL, official source URL, and verification date. Month-only guidance remains guidance.

See [Contributing](CONTRIBUTING.md), [data methodology](docs/DATA_METHODOLOGY.md), and the [technical architecture](docs/TECHNICAL.md).

## Run Locally

```powershell
pip install -e ".[dev]"
gradwindow validate
gradwindow build-site
python -m http.server 8000 --directory site
```

**Licensing:** [Code](LICENSE) and [data](DATA_LICENSE.md) are licensed separately. Reuse of the curated admissions dataset requires attribution to GradWindow and is limited to noncommercial use under CC BY-NC 4.0. Official university pages remain the authoritative source.
