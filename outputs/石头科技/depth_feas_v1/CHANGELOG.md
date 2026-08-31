# CHANGELOG — depth_feas_v1（石头科技 / Roborock → Germany）

**Date:** 2026-08-12  
**Purpose:** Depth feasibility smoke vs research_only baseline `outputs/石头科技/v1/`  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/roborock_germany.json`  
**Python exit:** `1`（`${PIPESTATUS[0]}` / tee-safe `EXIT:1`）  
**Wall clock:** ~94s（19:36:56 → 19:38:09 tool_audit）  
**Artifacts:** this folder — `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log`（from `/tmp/roborock_feas_depth_v1.log`）  
**Pre-run backup of unrelated root outputs (东边野兽 UK):** `outputs/_pre_roborock_feas_depth_v1_backup/`  
**Frozen untouched:** `outputs/石头科技/v1/`、`outputs/东边野兽/backup_v8/`、`outputs/花知晓/backup_v4/`（mtimes unchanged）

---

## 1. Metrics — this run

| Metric | Result | Notes |
| --- | --- | --- |
| **Exit code** | **1** | Footer stopped on scoring under `--strict-citations` |
| **Tasks completed** | **2/2** | Feasibility Depth + gap-fill both `Task Completed` / Validated（soft-pass on feas） |
| **Serper** | **21**（21 ok / 0 err） | Feas ~15 + gap ~6 finished; audit 42 lines |
| **Scrape / fetch** | **0** | Search-only；footer warned no scrape tools |
| **Soft-pass banners** | **YES** | `组合 guardrail 已达共享软上限`（累计 **4** 次未通过 / 上限 **3**）at top of `market_feasibility.md` |
| **Guardrail (feas)** | **3× blocked** then soft-pass | All `feas_channel_social_only`（渠道可计入零售 URL 0） |
| **Gap-fill guardrail** | Passed | — |
| **Citation** | **0 severe / 0 human-review** | 2 files, 14 URLs |
| **Scoring (footer)** | **FAIL** — claimed/recomputed **None / None** | Parser latched onto `建议进入（加权总分 = 3.29）`（出处 `3.29）`），未吃到公式行 |
| **Scoring (manual)** | Claimed **3.29**；true **3.5** | `0.25×4+0.15×2+0.20×5+0.20×3+0.20×3 = 3.5`；结论档「建议进入」与错误书面分/真实分都不严谨 |
| **Artifact feas (offline)** | **1 sev / 1 warn** | sev `feas_channel_social_only`；warn `feas_falsifiable_thin`（footer 未跑到，scoring 先 exit） |
| **Depth gate (live footer)** | **Not reached** | Scoring `SystemExit` before `check_research_depth` / artifact floor |
| **Depth gate (offline replay)** | **0 sev / 0 warn** | Hydrated audit: 15 feas + 6 gap serper OK |
| **mtimes** | **this run** | feas 19:38:03；gap 19:38:22；audit 19:38:09；run.log 19:38:23 |

---

## 2. vs `石头科技/v1`（research_only baseline）

| | `v1` research_only | `depth_feas_v1`（this） |
| --- | --- | --- |
| **Exit** | （基线归档；当时规则集更旧） | **1** |
| **Scoring written** | **3.15**（重算 **3.15** ✅） | 书面 **3.29**（真值 **3.5**；footer 解析失败） |
| **Conclusion** | **先验证假设、暂缓铺货**（3.15 ∈ hold） | **建议进入**（与 v1 相反；且与真值 3.5 的 enter 档看似一致，但是建立在软通过渠道地板 + 算错分之上） |
| **Serper** | （v1 audit 更长/更旧栈） | **21** |
| **Depth / channel floor** | 无 Depth 硬证据地板 | Soft-pass 带着 `feas_channel_social_only` 出场 |
| **Citations** | 见 v1 CHANGELOG | **0 severe** |

### What this smoke shows

1. **Depth path runs end-to-end for Roborock DE**（feas + gap）under compose soft-budget — Crew 未死在 retry exhaustion。  
2. **Channel floor still not honestly cleared** — Amazon 分类页进了清单但不计零售地板；软上限放行后文件顶栏明确「不可直接当成品」。  
3. **Scoring regression vs v1** — v1 是当时「算术+档位」金样（3.15）；本跑书面 3.29≠3.5，且建议行括号分干扰了 parser → strict exit 1。  
4. **Conclusion flipped to 建议进入** without beating v1’s cautious hold on evidence quality — not a green light for full `research_depth`.

---

## 3. Verdict

| Gate | YES/NO | Why |
| --- | --- | --- |
| **Pipeline** | **YES** | Both Depth tasks completed; soft-pass avoided hard Crew abort |
| **Deliverable** | **NO** | Exit 1；soft-pass banner；artifact 1 sev channel；scoring parse fail + 3.29≠3.5 |
| **Ready for full `research_depth`?** | **NO** | Fix channel floor（Amazon.de PDP/店页进硬证据清单或诚实「证据不足」+≥2 零售向搜索）and scoring formula/conclusion line so footer is green before expanding to expansion+battlecard |

---

## 4. Trailing validation notes

- Live footer order effectively aborted at scoring；artifact/depth footer sections absent from `run.log`（stdout/stderr flush makes `SystemExit` line appear above buffered audit/citation/scoring blocks）.  
- Offline `artifact_check` on archived feas: **1 severe** `feas_channel_social_only`, **1 warn** `feas_falsifiable_thin`.  
- Offline depth with replayed `tool_audit.jsonl`: clean.

---

## Follow-up（code fixes only — not a re-run）

**Date:** 2026-08-12  
**Scope:** checker code + unit tests；**no** new LLM/`feasibility_depth` run；frozen `v1` / `backup_v8` / `backup_v4` untouched.

1. **`artifact_check._RETAIL_HOST_HINTS`** — allowlist DE appliance retail: `mediamarkt.de`, `saturn.de`, `otto.de`, `idealo.de`, `roborock.com`. Amazon is **not** a bare host hint: only PDP/shop paths (`/dp/`, `/gp/product/`, `/stores/`, `/shop/`, `/sp?`) count; category `/b?node=` stays out. Retail query markers extended for honest-gap searches.
2. **`scoring_check._extract_formula_rhs`** — prefer formula lines with `权重×得分` pairs; ignore short/parenthetical `加权总分 = N.NN` (fixes latch onto `建议进入（加权总分 = 3.29）`).
3. **Tests** — German retail hosts pass channel floor; Amazon category fails; parenthetical short claimed total no longer poisons formula parse.

**Archived `market_feasibility.md` still expected red offline:** channel section only has Amazon category URL (0 retailish); formula claims 3.29 vs true 3.5 (now correctly reported as arithmetic fail, not parse fail). Ready for **`feas_v2`** once the model writes Amazon.de PDP / MediaMarkt (etc.) into `### 渠道/零售可见度` and a arithmetically correct `加权总分 = … = X` line.
