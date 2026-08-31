# CHANGELOG — depth_feas_v2（石头科技 / Roborock → Germany）

**Date:** 2026-08-12  
**Purpose:** Re-run after DE retail allowlist + scoring formula-line fixes vs `depth_feas_v1` / research_only `v1`  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/roborock_germany.json`  
**Python exit:** `1`（`--strict-depth` depth gate；tee 包装在 zsh 下 `PIPESTATUS` 空、外壳曾显示 0，以日志 `深度门禁未通过…中断` + 离线复现为准记 **EXIT:1**）  
**Wall clock:** ~70s（19:44:13 → 19:45:23）  
**Artifacts:** this folder — `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log`（from `/tmp/roborock_feas_depth_v2.log`）  
**Pre-run backup of prior root outputs:** `outputs/_pre_roborock_feas_depth_v2_backup/`  
**Frozen untouched:** `outputs/石头科技/v1/`、`outputs/石头科技/depth_feas_v1/`、`outputs/东边野兽/backup_v8/`、`outputs/花知晓/backup_v4/`（mtimes unchanged）

---

## 1. Metrics — this run

| Metric | Result | Notes |
| --- | --- | --- |
| **Exit code** | **1** | Depth gate `gap_fill_no_retail_pivot` ×2 under `--strict-depth`（artifact 未跑到） |
| **Tasks completed** | **2/2** | Feasibility Depth + gap-fill both `Task Completed` / Validated |
| **Serper** | **14**（14 ok / 0 err） | Feas agent 9 finished + gap 5 finished；jsonl 28 lines = start+finish |
| **Scrape / fetch** | **0** | Search-only |
| **Soft-pass banners** | **NO** | Feas guardrail：1× scoring block → pass；无「组合软上限」顶栏 |
| **Guardrail (feas)** | **1× blocked** then pass | Scoring arithmetic/conclusion mismatch on first draft（3.15 vs 2.95 + 建议进入） |
| **Gap-fill guardrail** | Passed | — |
| **Citation** | **0 severe / 0 human-review** | 2 files, 22 URLs |
| **Scoring (footer)** | **PASS** — claimed/recomputed **2.95 / 2.95** | Formula-line extract works；结论「先验证假设、暂缓铺货」与 2.5–3.5 档一致 |
| **Channel / artifact (offline)** | **0 sev / 1 warn** | Amazon.de **PDP** 计入 1 条零售 URL；`feas_channel_honest_gap`（零售向搜索 ≥3，地板放行）。**不再** `feas_channel_social_only` |
| **Depth gate (live footer)** | **FAIL — 2 sev / 1 warn** | `gap_fill_no_retail_pivot` #1+#2；warn `gap_fill_angles_rely_on_upstream` |
| **Depth gate (offline replay)** | same | Hydrated audit matches live |
| **mtimes** | **this run** | feas 19:45:04；gap 19:45:21；audit 19:45:09；run.log 归档自本次 tee |

---

## 2. vs `depth_feas_v1` and `石头科技/v1`

| | `v1` research_only | `depth_feas_v1` | `depth_feas_v2`（this） |
| --- | --- | --- | --- |
| **Exit** | （旧基线归档） | **1**（scoring parse / claimed≠recomputed） | **1**（depth retail-pivot；scoring 已绿） |
| **Soft-pass** | n/a | **YES**（渠道 social_only 软上限） | **NO** |
| **Channel floor** | 无 Depth 硬证据地板 | sev `feas_channel_social_only` | warn honest_gap only（PDP + 零售搜索放行） |
| **Scoring claimed=recomputed** | **3.15=3.15** ✅ | FAIL（书面 3.29≠3.5；parser 吃括号分） | **2.95=2.95** ✅ |
| **Conclusion** | 先验证假设、暂缓铺货 | 建议进入（不可信） | **先验证假设、暂缓铺货**（与分档一致） |
| **Citation** | 见 v1 | 0 sev | 0 sev |
| **Depth gate** | n/a / 未达 | Not reached（scoring 先 exit） | **2 sev** gap retail pivot |
| **Serper** | （更旧栈） | 21 | 14 |

### What changed after the code fixes

1. **Scoring formula-line fix worked** — footer 不再被 `（加权总分 = …）` 括号行带偏；claimed=recomputed，strict-citations 绿。  
2. **DE retail allowlist worked enough to clear channel severe** — Amazon `/dp/` 计入；不再软通过顶栏；artifact 仅 honest_gap 警告。  
3. **New blocker is gap-fill depth** — 未关闭缺口块未做零售/品牌+渠道第二角度 → `--strict-depth` exit 1。

---

## 3. Verdict

| Gate | YES/NO | Why |
| --- | --- | --- |
| **Pipeline** | **YES** | Both Depth tasks completed without soft-pass / Crew abort |
| **Deliverable** | **NO** | Exit 1；depth 2 sev；artifact 仍有渠道诚实缺口警告 |
| **Ready for full `research_depth`?** | **NO** | Gap-fill must retail-pivot on open gaps（or close them with evidence）so depth footer is green；再扩 expansion+battlecard |

---

## 4. Trailing notes

- Live footer aborted at depth → **artifact_check 未打印**；offline hydrated audit: 0 sev / 1 warn.  
- Tee wrapper: on zsh use `${pipestatus[1]}`（1-based），不是 bash `${PIPESTATUS[0]}`。  
- Frozen paths confirmed pre/post：`v1` feas 13:38:57；`depth_feas_v1` feas 19:38:03；`backup_v8` / `backup_v4` dirs unchanged.

---

## Follow-up (code-only, post v2)

**Date:** 2026-08-12  
**Why:** v2 depth gate `gap_fill_no_retail_pivot` ×2 — open gaps #1/#2 only listed attitude/review queries (sales data / Stiftung Warentest); `_angle_bucket` lacked DE appliance retail markers that `artifact_check._RETAIL_QUERY_MARKERS` already had.

**Code changes (not a re-run of this folder):**
1. `research_depth_check._angle_bucket` — add DE retail markers (MediaMarkt / Saturn / Otto / Idealo / amazon.de / Joybuy / Kaufland / €) aligned with channel floor; **do not** treat bare `roborock`/`zeo` as retail pivot.
2. `evidence_gap_fill_depth.yaml` (+ feas depth whitelist examples) — DE retail pivot examples (MediaMarkt, Amazon.de PDP, Otto, Saturn); Stiftung Warentest alone ≠ second angle.
3. `tests/test_research_depth_check.py` — DE marker honesty + open-gap pivot gate.

**Next:** re-run as `depth_feas_v3` (agent must actually write retail-oriented gap queries; marker expansion alone does not rewrite archived v2 gaps).
