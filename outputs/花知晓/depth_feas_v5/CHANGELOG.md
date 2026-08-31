# CHANGELOG — depth_feas_v5

**Date:** 2026-08-12  
**Purpose:** Smoke after **composed-guardrail soft-budget** fix  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/flowerknows_thailand.json`  
**Run exit code:** `0`  
**Pytest (`tests/test_artifact_check.py`):** **14 passed** (pre-run)  

Artifacts in this folder: `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log` (full stdout from `/tmp/feas_depth_v5.log`).  
Light pre-run backup of prior root outputs: `outputs/_pre_feas_v5_backup/`.

---

## 1. What this smoke validates

Confirm that the composed guardrail soft-budget path does **not** abort CrewAI with `Task failed guardrail validation after N retries`, and that both Depth tasks still complete under `--strict-*`.

---

## 2. Runtime results vs `depth_feas_v4`

| Metric | depth_feas_v4 | depth_feas_v5 | Notes |
| --- | --- | --- | --- |
| **Exit code** | 0 | **0** | Preferred path |
| **Pipeline completed** | yes (feas + gap fill) | **yes** (both `Task Completed`) | No CrewAI abort |
| **Guardrail hard abort** | no | **no** | Never saw `Task failed guardrail validation after N retries` |
| **Compose soft-pass banner** (`共享软上限` / `组合 guardrail`) | n/a | **did not appear** | Soft-pass not needed this run; hard retries cleared issues first |
| **Guardrail retries (feasibility)** | 2 blocked then pass | **2 blocked then pass** | attempt 1/7 channel floor; attempt 2/7 scoring arithmetic |
| **Gap-fill guardrail** | Passed | **Passed** | — |
| **Scoring (written vs recompute)** | 3.65 = 3.65 ✅ | **3.65 = 3.65** ✅ | Self-consistent |
| **Citation severe** | 0 | **0** | 11 human-review warns (bare homepage / list-style pages) |
| **Artifact floor (feasibility)** | 0 severe / 0 warn | **0 severe / 1 warn** `feas_falsifiable_thin` | Floor not severe; falsifiable subsection thin |
| **Depth gate** | 0 severe / 1 warn `gap_fill_thin_search` | **0 severe / 1 warn** `gap_fill_thin_search` | ~3 successful补证 searches vs ~4 gaps |
| **Serper** | 17 (17 ok / 0 err) | **14** (14 ok / 0 err) | Log summary; no fetch/scrape tools |
| **Pytest artifact_check** | 11 passed | **14 passed** | Suite grew with soft-budget / compose coverage |

---

## 3. Soft-pass / compose soft-budget

- **Soft-pass banners:** none (`共享软上限` / `组合 guardrail` not in `run.log`).
- **Critical criterion still met:** process did **not** die on composed guardrail retry exhaustion; feasibility recovered via normal retries (2), then gap-fill passed.
- Interpretation: soft-budget is a safety net; this smoke exercised the happy path where mid-loop fixes land before soft-pass is required.

---

## 4. Remaining issues (honest)

1. **Citation warns (11)** — KONVY/Beautrium bare homepages and KONVY brand/list paths still used as evidence-shaped URLs; 0 severe under current rules.
2. **`gap_fill_thin_search`** —补证 still thin; do not treat gaps as closed.
3. **`feas_falsifiable_thin`** — falsifiable subsection present but missing claim/verify elements (warn only).
4. **No scrape/fetch** in tool audit — search-only profile unchanged.
5. Soft-pass path itself was **not observed** this run; a dedicated forced soft-pass scenario would still be useful if you need banner proof.

---

## 5. Guardrail / retry log (from `run.log`)

| Step | Event |
| --- | --- |
| Feasibility attempt 1/7 | **Blocked** — Depth 硬证据地板 `feas_channel_social_only` → retry |
| Feasibility attempt 2/7 | **Blocked** — 评分表未通过代码重算（wrote 3.6, recompute 3.65）→ retry |
| Later feasibility | **Guardrail Passed** |
| Gap-fill | **Guardrail Passed** → Task Completed |

---

## 6. Trailing validation (footer)

- **Tool audit:** `search_the_internet_with_serper` ×14 (14 ok / 0 err); no fetch tools.
- **Citation:** 2 files, 20 URLs, **0 severe**, 11 human-review warns.
- **Scoring:** `报告总分 3.65，重算 3.65` — all pass.
- **Depth:** 0 severe, 1 warn (`gap_fill_thin_search`).
- **Artifact:** 0 severe, 1 warn (`feas_falsifiable_thin`).

---

## 7. Bottom line

v5 smoke **passes** the composed-guardrail soft-budget acceptance bar for this run: **exit 0**, **both tasks completed**, **no CrewAI guardrail-abort death**. Soft-pass banners did not fire because retries cleared severe issues first. Residual debt is evidence quality / thin gap-fill (warns), same class as v4, plus a new falsifiable-thin warn vs v4’s clean artifact floor.
