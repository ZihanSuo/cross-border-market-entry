# 2606 CrewAI — 出海市场研究 Multi-Agent

用 CrewAI 做 **跨境进入研究**：可行性（进入条件 / 就绪度）→ 缺口补证 → 开拓路径 → 竞品分析。

V1 主叙事是市场研究，**不是**小红书/抖音内容工厂。内容策略与渠道内容属于后续 V2。

项目的另一半重心是**产出质量的自动化评估**——因为实测发现提示词里写了规则模型也经常不遵守，
所以配了一套不依赖模型自评的机械校验（见下方「评估体系」）。

> ### ⚠️ 先读这个
>
> **`outputs/` 下的报告包含已知的事实错误，而且是刻意保留的。**
> 部分 URL 已失效、部分价格未经核实、早期版本有无来源数字。
>
> 本项目的研究对象**不是**「生成漂亮的市场报告」，而是「**如何用代码发现 LLM 报告里的错误**」。
> 错误是研究材料。每一处已知问题都记录在对应版本的 `CHANGELOG.md` 里（共 16 份）。
>
> 报告涉及的品牌与公司均为公开信息讨论对象，内容**不代表任何评价或建议，不应用于实际决策**。
> 完整说明见 **[DISCLAIMER.md](DISCLAIMER.md)**。
>
> **要看什么**：看 `src/marketing_crew/` 下的校验层、`experiments/` 下的评估脚本、
> 以及 `tests/`（给检验工具本身写的 60 个回归测试）。

---

## 🔖 直接看结果（不想跑代码的话）

| 案例            | 冻结 / 金样                                                 | 说明              |
| ------------- | ---------------------------------------------------- | -------------------------------- |
| 花知晓 → 泰国（彩妆）  | [`outputs/花知晓/backup_v4/`](outputs/花知晓/backup_v4/)   | FREEZE｜**0 严重** / 3 待复核（37 URL） |
| 东边野兽 → 英国（护肤） | [`outputs/东边野兽/backup_v8/`](outputs/东边野兽/backup_v8/) | FREEZE｜**1 严重** / 6 待复核（36 URL） |
| 石头科技 → 德国（家电） | [`outputs/石头科技/v1/`](outputs/石头科技/v1/) | 金样｜**3.15 → 暂缓铺货**（结论首次降级） |

> 东边野兽那 1 处严重问题值得单独说：跑 v8 当时校验是 0 严重，**是后来新增的
> 「SKU 名与 URL 品类矛盾」检测回溯扫描才抓出来的**——一条 Aesop 商品页 URL 路径写着
> `/body/`（身体护理）但 SKU 名是面部产品。这个问题从 v4.1 起跨越了五个版本、
> 三层检查都没发现，直到把它编码成规则才被永久拦住。
> **这正是「用当前规则回溯扫描历史版本」的意义，也是不粉饰数字的例子。**

三个案例刻意选了**不同品类 + 不同市场 + 第三案换行业**，用来测试规则是通用能力还是过拟合
（结论：语义类规则迁移得好，模板类规则会过拟合——详见 `docs/storyline.md` 4.5 节）。

对照分支：[`outputs/东边野兽/agentic_v2/`](outputs/东边野兽/agentic_v2/) 是把竞品分析改成
自主研究模式的失败实验（跑了 4 轮），**刻意保留**。

**Depth 实验室**（`research_depth` / `feasibility_depth` 归档在各品牌 `depth_*`）：流水线可通，
**不当演示成品**。诚实收口见 [`docs/depth_v1_honest_summary.md`](docs/depth_v1_honest_summary.md)。

每个目录里的 `CHANGELOG.md` 写清了「改了什么 / 还差什么 / 客观校验结果」。

发现与对照实验：[`docs/storyline.md`](docs/storyline.md)。
一页纸：[`docs/interview_one_pager.md`](docs/interview_one_pager.md)。

## 你现在最该用的命令

在仓库根目录：

```bash
source .venv/bin/activate

# 东边野兽 → 英国
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/herbeast_uk_v2.json

# 花知晓 → 泰国（泛化测试）
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/flowerknows_thailand.json
```

Depth V1（实验变体，**不改** `research_only`）：正文少灌水，文末「硬证据清单」做中度地板
（渠道 URL / 价带行 / 摘录 / 可证伪）；跑完多一道 `artifact_check`。

```bash
# 全链路 Depth（贵）
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_depth \
  --brief-file briefs/flowerknows_thailand.json

# 便宜试验：只跑可行性 + 补证 Depth
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant feasibility_depth \
  --brief-file briefs/flowerknows_thailand.json
```

输出（会被下次重跑覆盖）：

- `outputs/market_feasibility.md`
- `outputs/evidence_gap_fill.md` ← **缺口二轮补证**（专打「证据不足」）
- `outputs/market_expansion.md`
- `outputs/competitor_battlecard.md`

如何备份成 `backup_vN`：看 [`outputs/README.md`](outputs/README.md)。  
Brief 怎么填：看 [`briefs/README.md`](briefs/README.md)。

---

## 环境（只做一次；别覆盖已有 key）

### 1. 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

以后每次开终端：`source .venv/bin/activate`。

### 2. API Key（`.env`）

需要：

| 变量                  | 用途                 |
| ------------------- | ------------------ |
| `OPENAI_API_KEY`    | Agent 写报告（必填）      |
| `SERPER_API_KEY`    | 联网搜索；强烈建议，否则报告容易虚  |
| `OPENAI_MODEL_NAME` | 默认可用 `gpt-4o-mini` |

**安全规则（重要）：**

```bash
# ✅ 只有「还没有 .env」时才从模板创建（-n = 不覆盖已有文件）
cp -n .env.example .env

# ❌ 禁止在已有 key 时再执行下面这行——会把真 key 盖成占位符
# cp .env.example .env
```

然后用编辑器打开 `.env`，填入真实 key。  
`.env` 已在 `.gitignore`，不要提交。

若 key 被盖掉：优先用 Cursor 本地历史恢复；不要指望 git（`.env` 本来就不进库）。

建议把仓库放在 **非 iCloud 同步** 的路径，减少 `.env` 被云同步误覆盖的风险。

---

## 变体（常用就这几个）

| `--variant`          | 做什么                                              |
| -------------------- | ------------------------------------------------ |
| `research_only`      | **默认推荐**：可行性 → **缺口二轮补证** → 开拓 → 竞品              |
| `feasibility_only`   | 可行性 + 缺口补证（测「深度」时用这个，更省）                         |
| `expansion_only`     | 开拓（自动带上游可行性 + 缺口补证）                              |
| `research_qa`        | 研究链路 + QA 审校（QA 用推理模型 `o4-mini`，见 `agents.yaml`） |
| `competitor_agentic` | 可行性 + 开拓 + **自主研究版竞品分析**（agentic 对照实验，输出到独立文件）   |
| `full`               | 含内容等旧链路，V1 主叙事一般不用                               |

深度相关设计：**锁证据质量、不锁检索剧本**。可行性必须先搜索再写「已有市场空间」；补证每个缺口要覆盖态度向 + 零售/品牌渠道向（query 自定）。跑完会打印「研究深度门禁」（对照 `tool_audit`）；可用 `--strict-depth` 让严重项直接非零退出。

也可：`--tasks market_feasibility_task`（逗号分隔多个；会自动展开上游 `context`）。

**注意：** 参数名是 `--brief-file`，不是 `--brief`。

---

## Brief 文件

| 文件                                 | 用途                  |
| ---------------------------------- | ------------------- |
| `briefs/herbeast_uk_v2.json`       | 东边野兽 → 英国           |
| `briefs/flowerknows_thailand.json` | 花知晓 → 泰国（换品类+市场做泛化） |
| `briefs/sample_brief.json`         | 旧精简样例               |

也可不用文件，用 CLI 字段（`--product-name` 等），但正式 case 请用 JSON brief。

`--materials-file` 可重复传入；只允许读项目内 `inputs/` 或 `knowledge/user/`。

---

## 目录（精简）

```text
2606CrewAI/
├── briefs/                 # 案例 brief
├── knowledge/              # 来源规则 + 市场包（uk / thailand…）
├── src/marketing_crew/     # 主代码与 task/prompt 配置
├── outputs/                # 最新报告 + backup_vN 快照
├── experiments/            # ablation / 评估脚本
├── tests/                  # 检验工具的回归测试
├── docs/                   # 设计 / 叙事 / 评估结果页
├── .env.example            # 模板（无真 key）
└── .env                    # 本地密钥（勿提交、勿用 cp 覆盖）
```

---

## 评估体系（这个项目的另一半重心）

动机很直接：提示词里写了 20+ 条硬规则（禁止 example.com、禁止拿首页当证据、无 URL 不写数字…），
但历史输出证明模型经常不遵守，而原有的评分脚本只数 `https://` 出现次数——**`example.com` 一样计满分**。
所以做了三层不依赖模型自评的验证。

### 三层分工

| 层               | 做什么                           | 强项 / 弱项                  |
| --------------- | ----------------------------- | ------------------------ |
| **机械校验**（代码）    | 18 类可枚举的质量缺陷                  | 100% 覆盖、零边际成本；但只认写进代码的模式 |
| **QA 审校**（推理模型） | 需要回查原始材料的判断（引用无出处、与 brief 不符） | 能发现工具没被教过的问题；但不保证覆盖每一行   |
| **人工通读**        | 发现**新的**问题类型                  | 判断力最强；但注意力不稳定、不可规模化      |

关键认识：**人工的产出不应该是「这一版有什么问题」，而应该是「从此每一版都自动查这个问题」。**
现有 18 类检测，每一条都来自一次人工发现。详见 `docs/storyline.md` 4.5 节。

### 零成本命令（随时可跑，不花 API）

```bash
# 引用校验：18 类检测（假域名/占位符/首页当证据/他国站点/无来源数字/社媒主页当舆论…）
python3 src/marketing_crew/citation_check.py --locale th outputs/花知晓/backup_v4/*.md
python3 src/marketing_crew/citation_check.py --locale uk outputs/东边野兽/backup_v8/*.md

# 跨版本规则遵守率矩阵：33 个归档版本 × 18 类检测，含问题密度指标
PYTHONPATH=. python experiments/rule_compliance_matrix.py
```

### 需要 API / 联网的

```bash
# QA 审校召回率 benchmark（标注测试集 18 条已知问题；--repeat 3 看稳定性）
PYTHONPATH=. python experiments/qa_bench.py --all

# URL 是否真实存在（独立发 HTTP 请求，不问模型）
PYTHONPATH=. python experiments/verify_urls.py <报告.md> --product-only

# 报告里的「已核实」是真是假（拿工具审计日志逐条对质）
PYTHONPATH=. python experiments/verify_claims.py <报告.md> --audit <该轮 tool_audit.jsonl>
```

### 工具调用审计

每次运行自动记录**真实的**工具调用（工具名、参数、返回长度、报错）到 `outputs/tool_audit.jsonl`，
用 `--no-tool-audit` 可关闭。

存在的理由：模型曾在报告里写下 10 条「已用 scrape_page 核实，页面显示标价 £XX」，
拿审计日志逐条对质**通过 0 条**——有的 URL 从没被抓过，有的抓回来是 106 字符的反爬拦截页。
**自我报告不可信，执行状态必须由代码记录。** 详见 `outputs/东边野兽/agentic_v2/CHANGELOG.md`。

> ⚠️ 归档快照时**务必把 `tool_audit.jsonl` 一起拷贝**，否则该轮的「已核实」声明将无法验证。

---

## Ablation（可选）

```bash
PYTHONPATH=. python experiments/run_ablation.py
```

结果在 `outputs/ablation_report.json` 与 `outputs/ablation/<variant>/`。

**注意**：变体定义仍是按早期全流水线（含内容生产）设计的，与当前 V1 = 研究链路的定位不一致，
重跑前需先对齐基准，否则数字对不上现在讲的故事。

---

## 测试

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -q
```

给检验工具本身写的回归测试（引用 / 评分 / 产物地板 / 市场包路由）。`pytest` 已写进 `requirements.txt`。

---

## 常见坑

1. **`cp .env.example .env` 覆盖真 key** → 用 `cp -n`，或先确认没有 `.env`
2. **只备份不重跑** → `mkdir/cp` 不会跑研究；见 `outputs/README.md`
3. **写错参数** → 用 `--brief-file`，路径相对项目根目录
4. **没激活 venv / 没设 `PYTHONPATH=.`** → 导入失败或跑到系统 Python
