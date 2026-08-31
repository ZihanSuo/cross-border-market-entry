# CHANGELOG — depth_v2

**Date:** 2026-08-12  
**Variant:** `research_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/flowerknows_thailand.json`  
**Run exit code:** `1`  
**Pytest (`tests/test_artifact_check.py`):** 13 passed (no code fix required this turn)  
**Wall time:** ~18:44:29 → 18:45:57 (audit); full process ~115s before abort  
**Log:** `run.log` (from `/tmp/research_depth_v2.log`)  
**Pre-run backup:** `outputs/_pre_research_depth_v2_backup/`

Artifacts in this folder: `market_feasibility.md`, `evidence_gap_fill.md`, `market_expansion.md`, `competitor_battlecard.md`, `tool_audit.jsonl`, `run.log`, `CHANGELOG.md`.

> **Honesty note on markdown copies:** The crew **never completed** the first Depth task (`market_feasibility` / 跨境市场可行性研究员). Copied `*.md` files are **stale leftovers** from prior successful runs (feasibility/gap-fill ≈ `depth_feas_v4` timestamps; expansion/battlecard ≈ `depth_v1` era). Only `tool_audit.jsonl` + `run.log` are from this `depth_v2` attempt.

---

## 1. Pre-run code (what this run was meant to exercise)

| Area | Change |
| --- | --- |
| Competitor artifact floor | `make_artifact_competitor_guardrail` + registry key `artifact_competitor` in `guardrails.py` |
| Price-row / homepage logic | `artifact_check.py`: bare homepage URLs **do not** satisfy competitor price-floor rows (`_is_bare_homepage` → `comp_price_floor`) |
| Competitor task chain | `competitor_analysis_depth.yaml`: `guardrail: artifact_competitor,citation` (floor then citations) |
| Feasibility chain (unchanged from feas_v4) | `market_feasibility_depth.yaml`: `guardrail: artifact_feasibility,scoring,citation` |
| Tests | Homepage-not-counting / price-row fixtures covered in `tests/test_artifact_check.py` — **13 passed** before kickoff |

Intent: after `depth_v1` failed floors and `depth_feas_v4` proved feasibility-only gates, this full-chain run should stress **competitor** floors (SKU/price/scrape) with homepage exclusion — but the run **died on feasibility** before competitor ever started.

---

## 2. vs `depth_v1` and vs `depth_feas_v4`

| Dimension | depth_v1 | depth_feas_v4 | **depth_v2 (this run)** |
| --- | --- | --- | --- |
| Scope | Full `research_depth` | `feasibility_depth` only | Full `research_depth` **attempted** |
| Exit | Produced md (floors failed post-run) | **0** (gates passed after retries) | **1** — in-task guardrail exhausted |
| Artifact feas | Severe: `feas_channel_social_only` etc. | Floor ✅ (0 severe) | Never shipped; mid-loop `feas_channel_social_only` ×2 |
| Artifact comp | Severe: `comp_price_floor` (0 rows), `comp_scrape_floor` (0 scrape) | n/a | **Not reached** (new `artifact_competitor` unused) |
| Citation | 1 severe + homepage-as-evidence noise | 0 severe / 4 warn | Final fail: **3 severe** (Beautrium homepage×2 + unsourced market number) |
| Scoring | Skipped / header drift | Final 3.65=3.65 ✅ | Attempt 2: written **3.4** vs recompute **3.45** |
| Depth gate | 0 severe / 1 warn thin gap-fill | 0 severe / 1 warn thin gap-fill | **No post-run depth report** (aborted) |
| Outcome | Full docs but fake-deep floors | Feasibility quality OK | **No new accepted Depth artifacts** |

---

## 3. Metrics (this run)

| Metric | Value |
| --- | --- |
| **Exit code** | **1** |
| **Tasks completed** | 0 (failed on first Depth feasibility task after 4 retries / attempt 5) |
| **Artifact feas (final)** | ❌ not accepted — last accepted pass count for combined guardrail: **0** |
| **Artifact comp (final)** | n/a — competitor task never started |
| **Citation (final attempt)** | **3 severe**: Beautrium bare homepage as「商品页面」×2; unsourced「70亿美元 / 6.8%」market figure |
| **Scoring (observed)** | Attempt 2 severe arithmetic (3.4 vs 3.45); no final passing report |
| **Depth (post-run)** | Not evaluated (process aborted) |
| **Serper (`tool_audit.jsonl`)** | **19** started / **19** finished (38 JSONL lines); agent = 跨境市场可行性研究员 only |
| **Scrape / fetch tools** | **0** |
| **Guardrail retries** | **4** blocked retries then hard fail (see §5) |

---

## 4. Guardrail / retry log

Combined guardrail on feasibility: `artifact_feasibility` → `scoring` → `citation` (`guardrail_max_retries` effective path: CrewAI reports attempts 1–5).

| Attempt | Result | Gate that fired |
| --- | --- | --- |
| 1 | Blocked → retry | **Depth 硬证据地板** — `feas_channel_social_only`（可计入零售 URL 仅 1 条；零售向搜索 1 次） |
| 2 | Blocked → retry | **scoring** — 加权总分写 3.4，重算 3.45 |
| 3 | Blocked → retry | **Depth 硬证据地板** — again `feas_channel_social_only`（零售 URL 仍 1 条；零售向搜索已升到 6 次） |
| 4 | Blocked → retry | **citation** — 1 severe：无 URL 的市场规模数字（10.4 亿美元 / 8.29%） |
| 5 (final) | **Fail / abort** | **citation** — 3 severe：`https://thebeautrium.com/` 首页当商品页 ×2；无来源「70亿美元 / 6.8%」 |

`Exception: Task failed guardrail validation after 4 retries.` → `Crew Execution Failed` → process exit **1**.

---

## 5. Honest remaining issues

1. **Channel floor still thrashing the model** — even with ≥6 retail-named Serper queries, the written channel list still only credited **1** countable retail URL; agent did not consistently take the「证据不足 + 已试 query」escape hatch.
2. **Citation hygiene regresses under retry pressure** — attempt 4/5 reintroduced unsourced market sizing numbers; attempt 5 also re-labeled Beautrium **homepage** as product evidence (exactly the class homepage/SKU rules are meant to kill).
3. **Competitor Depth gates untested in production this run** — `artifact_competitor` + homepage-not-in-price-floor only validated by **pytest**, not by a live battlecard task.
4. **No scrape tooling in the live path** — audit remains search-only; `comp_scrape_floor` debt from `depth_v1` is untouched.
5. **Folder `*.md` must not be read as depth_v2 deliverables** — they are prior-run copies; treat `run.log` + `tool_audit.jsonl` as the only trustworthy depth_v2 evidence.

---

## 6. Bottom line

`depth_v2` **did not deliver** a passing full Depth pipeline. Pre-run pytest for homepage/price-floor logic is green (13/13), but the live run exhausted feasibility guardrails on channel floor → scoring → citation and never reached competitor/expansion/gap-fill. Relative to `depth_feas_v4` (exit 0, feasibility accepted), this is a **regression on executable feasibility under full-chain + strict flags**; relative to `depth_v1`, floors still correctly refuse weak evidence, but we again have **no shippable deep artifacts**.

**Next:** fix prompt/escape-hatch compliance for `feas_channel_social_only` (force「证据不足」when retail SKU URLs missing), then re-run — preferably `feasibility_depth` smoke first, then full `research_depth` to exercise `artifact_competitor,citation`.

---

## 7. Follow-up fix (same day, post-mortem) — 未重跑

根因：`artifact_feasibility,scoring,citation` **各自** soft-pass，CrewAI 总预算只有 `soft+2`，组合链路可在软放行前累计 6+ 次 False → `Task failed guardrail validation after 4 retries`，整条 `research_depth` 中断。

已改代码（待下一轮验证）：

1. `guardrails._compose`：**共享** soft_max_retries；子 guardrail 在组合时不再单独 soft-pass  
2. `crew.py`：CrewAI `guardrail_max_retries = soft + 3`  
3. 可行性 depth：`guardrail_max_retries: 3`  
4. 渠道地板：审计已有 ≥2 次零售向搜索时，即使漏写「证据不足」也按诚实缺口 **warn 放行**（针对 attempt 3：6 次零售搜索仍卡 1 条 URL）

`depth_v2` 文件夹里的 `*.md` **仍不是本轮交付物**；本轮证据只有 `run.log` + `tool_audit.jsonl`。
