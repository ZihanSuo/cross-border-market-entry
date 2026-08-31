# 跨境市场进入研究 Multi-Agent —— 以及一套检验它输出的代码

*A multi-agent pipeline for cross-border market entry research, plus the code that checks whether its output can be trusted.*

用 CrewAI 编排的研究流水线：**市场可行性 → 证据缺口补证 → 进入路径 → 竞品战卡**。
但这个项目真正花力气的地方是另一半——**一套不依赖模型自评的验证体系**。

> **起因**：提示词里写了 20 多条硬规则（禁止 example.com、禁止拿首页当证据、无 URL 不写数字），
> 但历史输出证明模型经常不遵守；而当时的评分脚本只数 `https://` 出现次数——**`example.com` 一样计满分**。
>
> 于是问题从「怎么让它写得更好」变成了「**怎么用代码判断它到底写得对不对**」。

| | |
|---|---|
| 案例 | 3 个（护肤 / 彩妆 / 家电，英国 / 泰国 / 德国） |
| 归档版本 | 33 个，每版一份 CHANGELOG |
| 机械检测 | 18 类，每一条都来自一次真实失败 |
| 回归测试 | 60 个，**测的是检验工具本身** |

---

## 📊 先看这个

**[评估结果页 →](https://zihansuo.github.io/cross-border-market-entry/)**
（也可克隆后直接打开 `docs/index.html`，单文件、离线可读）

不想读代码的话，这一页有全部结论：跨版本遵守率热力矩阵、逐份评分表核算、
规避方式的演化时间线，以及一份公开的未解决问题清单。

**页面由脚本从归档数据现场重算生成，没有手写死的数字。**

---

## ⚠️ 关于 `outputs/` 里的报告

**这些报告包含已知的事实错误，而且是刻意保留的。**

本项目的研究对象不是「生成漂亮的市场报告」，而是「**如何用代码发现 LLM 报告里的错误**」。
错误是研究材料。每一处已知问题都记录在对应版本的 `CHANGELOG.md` 里。

报告涉及的品牌与公司均为公开信息讨论对象，内容**不代表任何评价或建议，不应用于实际决策**。
完整说明见 **[DISCLAIMER.md](DISCLAIMER.md)**。

---

## 测出了什么

三条最有代表性的，完整七条见 **[docs/findings.md](docs/findings.md)**。

**① 换个案例，才能发现原案例永远发现不了的 bug**

前五轮都在同一案例上调规则，每版都更好看。换成另一个品类 + 另一个市场第一次跑，
整份泰国报告在讨论「英国市场份额」——「英国」被写死成了模板字段名。
**这个 bug 在原案例下永远正确、永远不报错。**

**② 检测工具自己也有盲区，导致基线数字是错的**

工具当时报「5 处严重问题」，补上两类检测后，同一批文件的真实数字是 **15 处**。
基线错了不是读错一次，**是从此以后所有版本对比都是反的**。

**③ 那张五维加权评分表，连算术都是错的**

把每份报告的加权式子重算一遍：**31 份里 19 份有严重问题**，
其中若干份的结论与它自己写的分数直接矛盾——分数和结论是各写各的。
这类错误极其隐蔽：式子和数字都写得整整齐齐，不动手重算根本发现不了。

---

## 四层代码把关

共用一条原则：**凡是能被客观判定的事，都不留给模型自述。**
模型可以决定「下一步查什么」，但不能决定「这一步算不算做完了」。

| 检查 | 判据 | 由哪次失败催生 |
|---|---|---|
| [`citation_check.py`](src/marketing_crew/citation_check.py) | 18 类可枚举的引用缺陷 | 模型写 `example.com` 当参考文献并标高置信度 |
| [`scoring_check.py`](src/marketing_crew/scoring_check.py) | 重算加权总分、核对结论档位 | 多数报告把自己的加权总分算错 |
| [`tool_audit.py`](src/marketing_crew/tool_audit.py) | 事件总线记录的**真实**工具调用 | 报告写 10 条「已核实」，逐条对质通过 0 条 |
| [`guardrails.py`](src/marketing_crew/guardrails.py) | 代码当裁判的自我修正循环 | 补证环节 0 次调用却写出三条「检索策略」 |

配套评估脚本：
[`qa_bench.py`](experiments/qa_bench.py)（QA 召回率，18 条人工标注）、
[`rule_compliance_matrix.py`](experiments/rule_compliance_matrix.py)（33 版本 × 18 类检测矩阵）、
[`verify_urls.py`](experiments/verify_urls.py) / [`verify_claims.py`](experiments/verify_claims.py)（独立 HTTP 核实与对质）。

### 为什么给检验工具也写测试

这个项目真实发生过两次「**尺子本身是错的**」——
校验工具漏检导致基线被记成 5 处（真实 15 处）；
benchmark 用品牌名当匹配键，召回率从 38% 虚高到 75%。

**报告错了只影响一份产出，尺子错了会让所有版本的对比结论都反过来。**
所以 [`tests/`](tests/) 里 60 个用例测的是检验工具，每个用例都对应一次真实踩过的坑。

---

## 三个案例的设计

每个案例都为**证伪一个具体假设**而加，不是凑数量。

| | 东边野兽 → 英国 | 花知晓 → 泰国 | 石头科技 → 德国 |
|---|---|---|---|
| 行业 | 护肤 | 彩妆 | **家电 / 智能硬件** |
| 要测什么 | 基线 | 模板是否过拟合到首个案例 | 规则里的美妆表述是否也是硬编码 |
| 合规框架 | RP + UK REACH | Thai FDA 通知制 | CE + EU 能效标签 + WEEE |
| 结果 | — | **逮到写死的「英国」** | **美妆硬编码零残留** |

冻结产物：[`outputs/花知晓/backup_v4/`](outputs/花知晓/backup_v4/) · [`outputs/东边野兽/backup_v8/`](outputs/东边野兽/backup_v8/)

对照实验分支（**刻意保留的失败记录**）：
[`outputs/东边野兽/agentic_v2/`](outputs/东边野兽/agentic_v2/) 把竞品分析改成自主研究模式，跑了 4 轮；
各品牌 `depth_*` 是 Depth 变体实验，流水线可通但**未产出可交付质量**，收口说明见
[`docs/depth_v1_honest_summary.md`](docs/depth_v1_honest_summary.md)。

---

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env        # 然后填入 OPENAI_API_KEY / SERPER_API_KEY

PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/flowerknows_thailand.json
```

不花 API 也能跑的检查：

```bash
PYTHONPATH=. python -m pytest tests/ -q                    # 60 个回归测试
PYTHONPATH=. python experiments/rule_compliance_matrix.py  # 跨版本矩阵
```

变体、参数、加新市场、常见问题 → **[docs/SETUP.md](docs/SETUP.md)**

---

## 文档

| | |
|---|---|
| [docs/findings.md](docs/findings.md) | **七个发现的完整推导**，含一次被自己推翻的过度解读 |
| [docs/system_design.md](docs/system_design.md) | 架构与三层验证体系设计 |
| [docs/experiments.md](docs/experiments.md) | 对照实验记录（单变量模型对比、agentic 四轮、QA benchmark） |
| [docs/SETUP.md](docs/SETUP.md) | 安装、变体、加市场、常见问题 |
| [DISCLAIMER.md](DISCLAIMER.md) | 已知错误清单与使用限制 |

---

个人学习项目，不适用于生产环境。MIT License。
