# CHANGELOG — depth_feas_v4

**Date:** 2026-08-12  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/flowerknows_thailand.json`  
**Run exit code:** `0`  
**Pytest (`tests/test_artifact_check.py`):** 11 passed  

Artifacts in this folder: `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log` (full stdout).  
Light pre-run backup of prior root outputs: `outputs/_pre_v4_backup/`.

---

## 1. Code changes before this run (scoring + citation guardrails)

Work landed on `feasibility_depth` so the **model cannot ship** a broken scoring table or soft citation failures without a retry loop. Relevant pieces:

| Area | What changed |
| --- | --- |
| Task YAML | `market_feasibility_depth.yaml` wires `guardrail: artifact_feasibility,scoring,citation` with `guardrail_max_retries: 2`. Order is intentional: hard-evidence floor → arithmetic → citations. Prompt now requires a verifiable weighted-total formula and band-consistent conclusion. |
| Guardrails | `guardrails.py`: `make_artifact_feasibility_guardrail`, `make_scoring_guardrail`; registry entries `artifact_feasibility` / `scoring` alongside existing `citation`. |
| Scoring check | `scoring_check.py` (+ main post-run path): recompute Σ(weight×score), weight sum = 1.0, conclusion band vs total; mismatch is **severe**. |
| Citation | Existing `citation_check` remains the third in-task gate; `--strict-citations` still fails the process on post-run severe citation / scoring errors. |
| Artifact floor | `artifact_check.py` + tests (`test_artifact_check.py`): channel evidence floor (retail/brand pages count; social/report padding does not). Post-run floor also runs for `feasibility_depth` under `--strict-depth`. |
| Depth | Research-depth / gap-fill checks unchanged in spirit; gap-fill thin-search remains a **warn**. |

Intent of this slice: nail down **scoring arithmetic** (the v3 “written ≠ recalculated” class of bug) **inside the agent loop**, not only as a postmortem print.

---

## 2. Runtime results vs `depth_feas_v3`

| Metric | depth_feas_v3 | depth_feas_v4 | Delta |
| --- | --- | --- | --- |
| **Artifact (feasibility floor)** | 0 severe / 1 warn (falsifiable thin); CHANNEL FLOOR PASSED via KONVY brand page | 0 severe / 0 warn; floor ✅ | Warn cleared; floor still pass |
| **Citation** | 1 severe (GMI Research number without URL); 3 warn (KONVY `/brand/` list-style) | **0 severe**; 4 warn (Watsons all-brands/list, KONVY `/m/brand/…` ×2 contexts, Beautrium bare homepage) | Severe citation gone; warn count +1, different URLs |
| **Scoring** | Written **3.5** vs recalculated **3.65** (same band 建议进入) — arithmetic inconsistency | Written **3.65** vs recalculated **3.65** — ✅ 权重/算术/档位全部自洽 | **Arithmetic severe class eliminated on final artifact** |
| **Depth gate** | (not highlighted as primary in v3 notes) | 0 severe / **1 warn** `gap_fill_thin_search` (3 successful gap-fill searches ≈ 4 gaps) | Honest thin补证 still present |
| **Serper searches** | 15 | **17** (17 success / 0 error) | +2 |
| **Fetch/scrape tools** | n/a in v3 note | Still **none** recorded (expected if agents are search-only) | Unchanged pattern |
| **Conclusion band** | 建议进入 | 建议进入（加权总分 3.65） | Same band; total now self-consistent |

Final scoring formula in v4 (matches code recompute):

`加权总分 = (0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4) = 3.65`

v3 used the **same** Σ terms but wrote **3.5** in the narrative — exactly the bug scoring guardrail is meant to catch.

---

## 3. Is scoring arithmetic “severe” gone?

**Yes, on the delivered final report.**

- Post-run scoring check: `报告总分 3.65，重算 3.65` → all checks pass.
- During the run, scoring guardrail **did** fire once (see §5): attempt 2 failed with「评分表未通过代码重算（1 处严重）」; a later attempt passed. So the failure mode still appears mid-loop, but **does not leak into the shipped markdown**.

---

## 4. Remaining issues (honest)

1. **Citation warns (4)** — still leaning on brand/list pages and a bare Beautrium homepage as evidence-shaped URLs. Not severe under current rules, but product-page quality is still soft vs Depth V1 ideal.
2. **Gap-fill thin search** — only ~3 successful补证 searches for ~4 gaps; most gaps remain open (FDA local agent status, consumer sentiment, Mistine/Cathy Doll sales, Rococo/maximalist acceptance). Depth warn is appropriate; do not treat补证 as “closed.”
3. **No scrape/fetch audit lines** — “已核实” language would still be untrustworthy if it appears; this run’s tool profile is search-only.
4. **Guardrail retries cost latency/tokens** — two blocked attempts before success (depth floor, then scoring). Worth watching cost on longer variants.
5. **`--strict-*` passed only because final severe counts were zero** — warns do not fail the run; human review of the four citation warns is still recommended before treating this as board-ready evidence.

---

## 5. Guardrail / retry log

Present in stdout / `run.log` (not under `/tmp/*guardrail*` files):

| Step | Event |
| --- | --- |
| Feasibility attempt 1 | **Blocked** — Depth 硬证据地板（1 处严重）→ retry |
| Feasibility attempt 2 | **Blocked** — 评分表未通过代码重算（1 处严重）→ retry |
| Later feasibility | **Guardrail Passed** (artifact + scoring + citation chain) |
| Gap-fill | Guardrail check started → **Passed** |

So: **yes, guardrail retries happened** (depth floor once, scoring arithmetic once) before the final feasibility output was accepted.

---

## 6. Trailing validation (captured from run)

Abbreviated from process footer:

- **Tool audit:** `search_the_internet_with_serper` ×17 (17 ok / 0 err); no fetch tools.
- **Citation:** 2 files, 20 URLs, **0 severe**, 4 human-review warns.
- **Scoring:** market_feasibility 3.65 = 3.65, all pass.
- **Depth:** 0 severe, 1 warn (`gap_fill_thin_search`).
- **Artifact:** feasibility floor ✅ — 0 severe / 0 warn.

---

## 7. Bottom line

v4 is a **real step past v3** on the two mechanical failure modes that matter for this experiment: **citation severe cleared**, and **scoring arithmetic is self-consistent on the final artifact** (after in-loop retries). Channel floor remains green. Remaining debt is evidence *quality* (list/home pages, thin gap-fill), not arithmetic or fake-domain citations.
