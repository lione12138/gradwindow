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

**Coverage:** 302 canonical universities · 30,045 programmes · 6,304 verified exact windows

Status date: **2026-10-31**

> **Estimate** means the date is shifted from the latest verified cycle and is not an official forecast. Always confirm dates on the linked university source.

## Open Now

| QS | University | Coverage | Next deadline | Data | Links |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) | 23 open windows | 2026-11-01 | Official | [Admissions](https://oge.mit.edu/graduate-admissions/) · [All programme details](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| =2 | Imperial College London | 181 open windows | 2027-01-06 | Official + Estimate | [Admissions](https://www.imperial.ac.uk/study/apply/postgraduate-taught/) · [All programme details](https://gradwindow.com/?q=Imperial%20College%20London) |
| =2 | Stanford University | 1 open window | 2026-12-08 | Official | [Admissions](https://gradadmissions.stanford.edu/apply) · [All programme details](https://gradwindow.com/?q=Stanford%20University) |
| 6 | University of Cambridge | 159 open windows | 2026-11-18 | Official + Estimate | [Admissions](https://www.postgraduate.study.cam.ac.uk/application-process) · [All programme details](https://gradwindow.com/?q=University%20of%20Cambridge) |
| =8 | UCL | 26 open windows | 2027-03-27 | Official + Estimate | [Admissions](https://www.ucl.ac.uk/prospective-students/graduate/applying-graduate-study) · [All programme details](https://gradwindow.com/?q=UCL) |

[View every open window on GradWindow →](https://gradwindow.com/?status=open)

## Opening Within 30 Days

| QS | University | Coverage | Next opening | Data | Links |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) | 1 upcoming window | 2026-11-01 | Official | [Admissions](https://oge.mit.edu/graduate-admissions/) · [All programme details](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| =8 | ETH Zurich | Institution-level window | 2026-11-01 | Estimate | [Admissions](https://ethz.ch/en/studies/master/application.html) · [All programme details](https://gradwindow.com/?q=ETH%20Zurich) |
| 12 | Nanyang Technological University, Singapore (NTU Singapore) | 1 upcoming window | 2026-11-01 | Estimate | [Admissions](https://www.ntu.edu.sg/admissions/graduate) · [All programme details](https://gradwindow.com/?q=Nanyang%20Technological%20University%2C%20Singapore%20%28NTU%20Singapore%29) |
| 14 | Tsinghua University | 1 upcoming window | 2026-11-01 | Estimate | [Admissions](https://yz.tsinghua.edu.cn/en/) · [All programme details](https://gradwindow.com/?q=Tsinghua%20University) |
| =22 | EPFL – École polytechnique fédérale de Lausanne | 1 upcoming window | 2026-11-15 | Estimate | [Admissions](https://www.epfl.ch/education/admission/admission-2/master-admission-criteria-application/) · [All programme details](https://gradwindow.com/?q=EPFL%20%E2%80%93%20%C3%89cole%20polytechnique%20f%C3%A9d%C3%A9rale%20de%20Lausanne) |

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
