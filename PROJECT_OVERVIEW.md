# 项目总览

给中国品牌做跨境进入研究的多 Agent 流水线：输入 brief，输出可行性 / 缺口补证 / 开拓路径 / 竞品分析。另一半重心是**不依赖模型自评的产出校验**——提示词里的硬规则，模型经常不遵守，所以用代码当裁判。

技术细节：[`docs/system_design.md`](docs/system_design.md)。发现与对照实验：[`docs/findings.md`](docs/findings.md)。怎么跑：[`README.md`](README.md)。

---

## 主链路

`research_only`（默认）：可行性 → 缺口二轮补证 → 开拓 → 竞品，然后跑引用 / 评分 / 产物校验，并全程写 `tool_audit.jsonl`。

对照与实验（不是主推成品）：

- `--variant competitor_agentic`：自主研究版竞品，4 轮质量低于模板版，归档在 `outputs/东边野兽/agentic_v2/`
- `--variant research_depth` / `feasibility_depth`：证据地板实验，流水线可通，不当演示成品（见 [`docs/depth_v1_honest_summary.md`](docs/depth_v1_honest_summary.md)）
- `--variant research_qa`：研究链路 + QA（推理模型 `o4-mini`）；与机械校验互补，不互相替代

渠道策略 / 小红书 / 抖音 / TikTok / Instagram 内容 task 代码在、可显式调用，V1 不主推。

---

## 三个案例

| 案例 | 路径 | 角色 |
|---|---|---|
| 花知晓 → 泰国（彩妆） | `outputs/花知晓/backup_v4/` | 冻结演示，引用 0 严重 |
| 东边野兽 → 英国（护肤） | `outputs/东边野兽/backup_v8/` | 冻结对照，1 严重如实保留 |
| 石头科技 → 德国（家电） | `outputs/石头科技/v1/` | 跨行业；加权 3.15 → 暂缓铺货 |

`outputs/` 下的报告含已知事实错误，且刻意保留，用作「如何用代码发现 LLM 报告错误」的样本。完整说明见 [`DISCLAIMER.md`](DISCLAIMER.md)。

---

## 校验层（给尺子写测试）

| 层 | 位置 |
|---|---|
| 引用缺陷机械检测 | `src/marketing_crew/citation_check.py` |
| 评分表自洽重算 | `src/marketing_crew/scoring_check.py` |
| 产物地板 / Depth | `src/marketing_crew/artifact_check.py`、`research_depth_check.py` |
| 真实工具调用审计 | `src/marketing_crew/tool_audit.py` |
| 自我修正循环 | `src/marketing_crew/guardrails.py` |
| 回归测试 | `tests/`（`python -m pytest tests/`） |

尺子本身错过两次（漏检把基线报少、benchmark 匹配键虚高召回率），所以检验工具有独立测试，不靠「报告看起来没问题」。

---

## 现状（诚实）

- 三个案例已跑通；主演示冻结，不再为了「更好看」重跑覆盖。
- 缺口补证 agent 曾跨案例 0 次真实检索，已加 `search_effort` guardrail。
- Ablation 脚本还在，变体定义仍偏早期全流水线，与当前 V1 研究链路不完全对齐。
- 本项目是学习 / 研究仓，不适用于生产，也不构成市场进入建议。
