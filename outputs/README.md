# outputs 怎么存

## 🔖 演示入口（面试/展示直接看这些）

| 案例 | 冻结 / 金样 | 引用校验（按**当前**规则回溯扫描） |
|---|---|---|
| **花知晓 → 泰国（彩妆）** | [`花知晓/backup_v4/`](花知晓/backup_v4/) | FREEZE FOR DEMO｜**0 严重** / 3 待复核（37 URL） |
| **东边野兽 → 英国（护肤）** | [`东边野兽/backup_v8/`](东边野兽/backup_v8/) | FREEZE FOR DEMO｜**1 严重** / 6 待复核（36 URL） |
| **石头科技 → 德国（家电）** | [`石头科技/v1/`](石头科技/v1/) | 跨行业金样｜**research_only**；加权 **3.15** → **先验证假设、暂缓铺货**（结论首次降级） |

> 东边野兽那 1 处严重问题是**后来新增的检测回溯扫出来的**：一条 Aesop 商品页 URL
> 路径写着 `/body/`（身体护理）但 SKU 名是面部产品。跑 v8 当时校验是 0 严重，
> 这个问题从 v4.1 起跨了五个版本没被发现，直到编码成「SKU 名与 URL 品类矛盾」规则。
> 数字如实保留，不回头粉饰。

> 石头科技 **不是** `backup_*` 冻结命名，但是面试「系统会说 no」的唯一实证，**勿用 Depth 目录覆盖它**。

对照分支（**刻意保留的失败 / 实验，不是主推产物**）：

- [`东边野兽/agentic_v2/`](东边野兽/agentic_v2/) —— 把竞品分析改成自主研究模式，跑了 4 轮，
  产出质量稳定低于模板版。价值在于失败模式的演化数据与由此建成的三层验证工具，
  详见该目录 CHANGELOG。
- **Depth 实验室**（流水线可通，**成品一律 NO**；详 [`docs/depth_v1_honest_summary.md`](../docs/depth_v1_honest_summary.md)）：
  - `花知晓/depth_v3/`、`东边野兽/depth_v1/`、`石头科技/depth_feas_v1`…`v3/`
  - 有 soft-pass 横幅或 exit≠0 的，**不要**当演示包打开给面试官当「最终报告」。

每个冻结 / 金样目录里都有 `CHANGELOG.md`，写清了「相对上版改了什么 / 还差什么 / 为什么冻结」。

---

## 目录约定

```text
outputs/
├── README.md
├── market_feasibility.md          ← 最近一次运行的产物（会被下次运行覆盖）
├── evidence_gap_fill.md
├── market_expansion.md
├── competitor_battlecard.md
├── competitor_battlecard_agentic.md ← agentic 变体的独立输出，不覆盖上面那份
├── tool_audit.jsonl               ← 工具调用审计日志，同样会被下次运行覆盖
├── 东边野兽/
│   ├── backup_v1 … backup_v8/     ← workflow 主线，v8 为冻结版
│   ├── depth_v1/、depth_feas_*     ← Depth 实验室（非 demo）
│   └── agentic_v2/                ← agentic 对照分支
├── 花知晓/
│   ├── v1、v2/                     ← 早期命名（未加 backup_ 前缀，保持原状不改名）
│   ├── backup_v3、backup_v4/       ← v4 为冻结版
│   └── depth_*/                    ← Depth 实验室（非 demo）
└── 石头科技/
    ├── v1/                         ← 跨行业金样（research_only）
    └── depth_feas_v1…v3/           ← Depth feas 冒烟（未上全链；非 demo）
```

**版本号命名**：配置有实质改动 → 进位整数（v4 → v5）；同配置重跑 → 用小数（v4 → v4.1）。
`backup_` 前缀是后来才统一的，花知晓早期两个目录 `v1`/`v2` 保持原名不动，避免破坏 CHANGELOG 里的交叉引用。

---

## 完整流程（复制粘贴）

### ① 先重跑

```bash
source .venv/bin/activate

# 花知晓 → 泰国（主演示案例）
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/flowerknows_thailand.json

# 东边野兽 → 英国
PYTHONPATH=. python -m src.marketing_crew.main \
  --variant research_only \
  --brief-file briefs/herbeast_uk_v2.json
```

参数名是 **`--brief-file`**，不要写成 `--brief`。

可选严格模式：`--strict-citations`（引用有严重问题就非零退出）、`--strict-depth`（深度门禁）。

跑完确认根目录文件时间戳是刚才的：

```bash
ls -la outputs/*.md outputs/tool_audit.jsonl
```

### ② 立刻归档（**含审计日志**）

```bash
BRAND="花知晓"        # 或 东边野兽
N=5                   # 勿覆盖已有版本号
mkdir -p "outputs/$BRAND/backup_v$N"
cp outputs/market_feasibility.md \
   outputs/evidence_gap_fill.md \
   outputs/market_expansion.md \
   outputs/competitor_battlecard.md \
   outputs/tool_audit.jsonl \
   "outputs/$BRAND/backup_v$N/" 2>/dev/null || true
```

> ⚠️ **`tool_audit.jsonl` 必须一起归档。** 报告里「已用 scrape_page 核实」这类声明，
> 只有对照审计日志才能验证真假——本项目实测过模型会写下 10 条「已核实」而逐条对质**通过 0 条**。
> 花知晓 `backup_v4` 就因为漏存日志，导致它那两条核实声明至今无法验证（已在其 CHANGELOG 记账）。

> ⚠️ **归档要在下一次运行之前做。** 本项目已经因为「忘归档就重跑」丢过三次中间版本
> （花知晓首轮、东边野兽 v7 之后那批、agentic 第 2/3 轮）。

### ③ 立刻写 CHANGELOG

在 `outputs/$BRAND/backup_v$N/CHANGELOG.md` 写清四件事：

1. 相对上一版好了什么（有数字最好）
2. 还差什么（**如实记账，别粉饰**）
3. 改了哪些配置 / brief
4. 客观校验结果（贴命令输出，不要只写"变好了"）

---

## 一键体检（零 API 成本，随时可跑）

```bash
# 1) 引用校验：两个冻结版本都应为 0 严重
python3 src/marketing_crew/citation_check.py --locale th outputs/花知晓/backup_v4/*.md
python3 src/marketing_crew/citation_check.py --locale uk outputs/东边野兽/backup_v8/*.md

# 2) 跨版本规则遵守率矩阵（33 个归档版本 × 18 类检测）
PYTHONPATH=. python experiments/rule_compliance_matrix.py

# 3) QA 审校召回率 benchmark（需 API，约几毛钱；--repeat 3 可看稳定性）
PYTHONPATH=. python experiments/qa_bench.py --all
```

需要联网、按需跑的两个：

```bash
# URL 是否真实存在（独立发 HTTP 请求，不问模型）
PYTHONPATH=. python experiments/verify_urls.py outputs/花知晓/backup_v4/competitor_battlecard.md --product-only

# 报告里的「已核实」是真是假（拿审计日志对质，需该轮日志已归档）
PYTHONPATH=. python experiments/verify_claims.py <报告> --audit <该轮的 tool_audit.jsonl>
```

---

## 原则

- **先跑后备**：没有 ①，② 只会复制上一次的旧文件
- **backup 只增不改**；不满意就 N+1，不要回头改老版本
- **根目录 md = 最近一次运行的结果**，换 brief 会覆盖；以品牌子目录的 backup 为准
- **同配置重跑会有明显波动**（实测 v6 = 0 严重 → v7 = 3 严重），
  所以「重跑一次看看会不会更好」通常不划算，改配置再跑才有意义
- 大 outputs 不必强行 git 提交；展示时打开对应 `backup_vN/` + `CHANGELOG.md` 即可

## 关于 `.env`

配置 key 见根目录 [`README.md`](../README.md)。
**永远不要**在已有 `.env` 时执行 `cp .env.example .env`（会覆盖 API key）；只用 `cp -n .env.example .env`。
