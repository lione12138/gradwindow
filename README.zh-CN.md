# GradWindow

[![Tests](https://github.com/lione12138/qs-master-applications/actions/workflows/tests.yml/badge.svg)](https://github.com/lione12138/qs-master-applications/actions/workflows/tests.yml)
[![Website](https://img.shields.io/badge/Website-GradWindow-1e6548)](https://gradwindow.com/)

[English](README.md) · [Open GradWindow](https://gradwindow.com/) · [Application calendar](https://gradwindow.com/calendar.html) · [Report a data error](https://github.com/lione12138/qs-master-applications/issues/new?template=report-data-error.yml) · [Contribute](CONTRIBUTING.md)

> 面向全球主流排名前 200 大学、以学校官网为依据的硕士申请窗口追踪工具。

![GradWindow social card](web/og-image-multiranking.png)

## 为什么使用 GradWindow

- 每一条正式精确日期都可回溯到学校官网。
- 官网日期、周期规则与按历史平移的参考日期始终分层展示。
- 搜索、状态筛选、收藏、提醒和日历导出组成完整申请流程。
- QS 是默认视图，THE 与软科前 200 视图已经上线；U.S. News 暂不标为已上线。

**当前覆盖：**302 所标准化大学 · 29,033 个项目 · 5,281 条官网精确窗口

状态日期：**2026-08-23**

> **预测参考**表示日期由最近一个官网核验周期平移一年得到，不是学校官方预测。申请前请始终核对表格中的官网来源。

## 正在开放

| QS | 大学 | 覆盖范围 | 最近截止 | 数据类型 | 链接 |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) / 麻省理工学院 | 1 个当前开放窗口 | 2026-10-01 | 官网核验 | [招生官网](https://oge.mit.edu/graduate-admissions/) · [查看全部项目](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| =2 | Imperial College London / 帝国理工学院 | 13 个当前开放窗口 | 2026-09-28 | 预测参考 | [招生官网](https://www.imperial.ac.uk/study/apply/postgraduate-taught/) · [查看全部项目](https://gradwindow.com/?q=Imperial%20College%20London) |
| 6 | University of Cambridge / 剑桥大学 | 1 个当前开放窗口 | 2027-05-14 | 预测参考 | [招生官网](https://www.postgraduate.study.cam.ac.uk/application-process) · [查看全部项目](https://gradwindow.com/?q=University%20of%20Cambridge) |
| =8 | UCL / 伦敦大学学院 | 10 个当前开放窗口 | 2026-08-28 | 官网核验 | [招生官网](https://www.ucl.ac.uk/prospective-students/graduate/applying-graduate-study) · [查看全部项目](https://gradwindow.com/?q=UCL) |
| 10 | National University of Singapore (NUS) / 新加坡国立大学 | 18 个当前开放窗口 | 2026-08-31 | 官网核验 | [招生官网](https://nusgs.nus.edu.sg/admissions/) · [查看全部项目](https://gradwindow.com/?q=National%20University%20of%20Singapore%20%28NUS%29) |

[在 GradWindow 查看全部正在开放的窗口 →](https://gradwindow.com/?status=open)

## 30 天内即将开放

| QS | 大学 | 覆盖范围 | 最近开放 | 数据类型 | 链接 |
|---:|---|---|---|---|---|
| 1 | Massachusetts Institute of Technology (MIT) / 麻省理工学院 | 20 个即将开放窗口 | 2026-09-01 | 官网核验 | [招生官网](https://oge.mit.edu/graduate-admissions/) · [查看全部项目](https://gradwindow.com/?q=Massachusetts%20Institute%20of%20Technology%20%28MIT%29) |
| 6 | University of Cambridge / 剑桥大学 | 156 个即将开放窗口 | 2026-09-03 | 预测参考 | [招生官网](https://www.postgraduate.study.cam.ac.uk/application-process) · [查看全部项目](https://gradwindow.com/?q=University%20of%20Cambridge) |
| 10 | National University of Singapore (NUS) / 新加坡国立大学 | 9 个即将开放窗口 | 2026-09-01 | 官网核验 + 预测参考 | [招生官网](https://nusgs.nus.edu.sg/admissions/) · [查看全部项目](https://gradwindow.com/?q=National%20University%20of%20Singapore%20%28NUS%29) |
| 11 | The University of Hong Kong / 香港大学 | 89 个即将开放窗口 | 2026-09-01 | 预测参考 | [招生官网](https://admissions.hku.hk/tpg/) · [查看全部项目](https://gradwindow.com/?q=The%20University%20of%20Hong%20Kong) |
| 15 | University of Pennsylvania / 宾夕法尼亚大学 | 16 个即将开放窗口 | 2026-09-15 | 预测参考 | [招生官网](https://www.upenn.edu/academics/graduate) · [查看全部项目](https://gradwindow.com/?q=University%20of%20Pennsylvania) |

[在 GradWindow 查看全部即将开放的窗口 →](https://gradwindow.com/?status=upcoming)

## 数据可信边界

解析器只会创建待审核候选，不会直接发布截止日期。正式窗口必须同时具备学校、适用范围、入学季、申请人类别、开放和截止日期、申请入口、官网来源与核验日期。只有月份的说明仍保留为规则指引，不会伪装成精确日期。

详见[贡献指南](CONTRIBUTING.md)、[数据方法](docs/DATA_METHODOLOGY.md)和[技术架构](docs/TECHNICAL.md)。

## 本地运行

```powershell
pip install -e ".[dev]"
gradwindow validate
gradwindow build-site
python -m http.server 8000 --directory site
```

**许可说明：**[代码](LICENSE)与[数据](DATA_LICENSE.md)采用不同许可证。复用 GradWindow 整理的申请数据集必须署名，并仅限 CC BY-NC 4.0 允许的非商业用途。大学官网始终是权威信息来源。
