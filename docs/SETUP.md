# 安装与运行

## 1. 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. API Key

复制模板后填入真实 key：

```bash
cp -n .env.example .env
```

> `-n` 表示「文件已存在就不覆盖」。不加这个参数会把已填好的 key 冲成占位符。

| 变量 | 用途 | 必需 |
|---|---|---|
| `OPENAI_API_KEY` | Agent 生成报告 | 是 |
| `SERPER_API_KEY` | 联网搜索 | 强烈建议，否则报告缺乏可核查来源 |
| `OPENAI_MODEL_NAME` | 默认 `gpt-4o-mini` | 否 |

`.env` 及其所有变体（`.env.bak`、`.env.local` 等）均已在 `.gitignore` 中。

## 3. 跑一个案例

```bash
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/flowerknows_thailand.json
```

产出写入 `outputs/`（会被下次运行覆盖，归档方式见 [`outputs/README.md`](../outputs/README.md)）：

- `market_feasibility.md` — 市场可行性（含五维加权评分表）
- `evidence_gap_fill.md` — 针对上游「证据不足」的第二轮定向补证
- `market_expansion.md` — 进入路径
- `competitor_battlecard.md` — 竞品战卡

运行结束会自动打印四道检查：引用校验、评分表自洽性、研究深度门禁、工具调用审计汇总。

---

## 变体

| `--variant` | 内容 |
|---|---|
| `research_only` | **默认**：可行性 → 缺口补证 → 开拓 → 竞品 |
| `feasibility_only` | 可行性 + 缺口补证（最省，适合调规则时反复跑） |
| `expansion_only` | 开拓（自动带上游依赖） |
| `research_qa` | 研究链路 + QA 审校（QA 用推理模型，见 `config/agents.yaml`） |
| `competitor_agentic` | 竞品分析换成自主研究模式（对照实验，输出到独立文件） |
| `research_depth` / `feasibility_depth` | Depth 实验变体：正文之外要求「硬证据清单」，跑完多一道 `artifact_check` |
| `full` | 含内容生产等早期链路，未验证产出质量 |

也可以直接指定任务：`--tasks market_feasibility_task`（逗号分隔多个，会自动展开上游 `context` 依赖）。

**常用开关**

| 参数 | 作用 |
|---|---|
| `--strict-citations` | 引用校验或评分表校验有严重问题时以非零码退出 |
| `--strict-depth` | 深度门禁有严重问题时以非零码退出 |
| `--no-guardrails` | 关闭 task 级自我修正循环（省钱调试用） |
| `--no-tool-audit` | 关闭工具调用审计 |

---

## Brief 文件

| 文件 | 案例 |
|---|---|
| `briefs/herbeast_uk_v2.json` | 东边野兽 → 英国（护肤） |
| `briefs/flowerknows_thailand.json` | 花知晓 → 泰国（彩妆） |
| `briefs/roborock_germany.json` | 石头科技 → 德国（家电） |

字段说明与「没有一手资料时怎么找公开信息」的方法论见 [`briefs/README.md`](../briefs/README.md)。

`--materials-file` 可重复传入补充材料，出于安全考虑只允许读取项目内 `inputs/` 或 `knowledge/user/`。

---

## 加一个新市场

市场映射**只维护在 `knowledge/registry.yaml` 一处**，加一条 `market_mappings` 即可：

```yaml
- match: ["france", "法国"]     # 匹配词；长度 ≤3 的拉丁词按「词」匹配，其余按子串
  locale: fr                    # 引用校验地区码，留空则跳过地区一致性检查
  files:
    - markets/eu_common.md      # 可加载多个包，共享包在前、国别包在后
```

配了 `locale` 就要同步加进 `citation_check._LOCALE_SEGMENTS`，否则该市场的地区检测会**静默失效**。`tests/test_checks.py` 里有一条测试专门守这个一致性。

未匹配的市场会回落到默认包，并在运行前**明确打印警告**——静默回落是这个项目里代价最大的一类 bug。

---

## 零成本检查（不花 API）

```bash
# 引用校验
python3 src/marketing_crew/citation_check.py --locale th outputs/花知晓/backup_v4/*.md

# 跨版本遵守率矩阵
PYTHONPATH=. python experiments/rule_compliance_matrix.py

# 重新生成评估结果页
PYTHONPATH=. python experiments/build_report_page.py

# 检验工具自己的回归测试
PYTHONPATH=. python -m pytest tests/ -q
```

## 需要 API / 联网的检查

```bash
# QA 召回率 benchmark（18 条人工标注问题）
PYTHONPATH=. python experiments/qa_bench.py --all

# URL 是否真实存在（独立发 HTTP 请求，不问模型）
PYTHONPATH=. python experiments/verify_urls.py <报告.md> --product-only

# 报告里的「已核实」是真是假（与工具审计日志逐条对质）
PYTHONPATH=. python experiments/verify_claims.py <报告.md> --audit <该轮 tool_audit.jsonl>
```

---

## 常见问题

**导入失败** — 检查是否激活了 venv、是否带了 `PYTHONPATH=.`。

**参数名** — 是 `--brief-file`，不是 `--brief`；路径相对项目根目录。

**归档时漏了审计日志** — 快照一定要把 `outputs/tool_audit.jsonl` 一起拷走，否则该轮报告里的「已核实」声明事后无法验证。

**产出文件没更新** — 运行结束会自动比对每个输出文件的修改时间与本轮开始时间，未更新的会大声报出来。看到这个警告不要直接归档，先查日志里对应 task 为什么失败。
