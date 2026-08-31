# CHANGELOG — depth_feas_v3（东边野兽 → UK）

**Date:** 2026-08-12  
**Purpose:** Re-smoke after scoring_check learned to fail missing formula lines (v2 offline: 缺少加权总分算式 + 3.5≠~3.6).  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/herbeast_uk_v2.json`（东边野兽 → UK）  
**Run exit code:** `0`  
**Pytest (pre-run):** `tests/test_artifact_check.py` + `tests/test_checks.py` → **47 passed**  
**Artifacts:** this folder — `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log`（from `/tmp/herbeast_feas_depth_v3.log`）  
**Frozen:** `outputs/东边野兽/backup_v8/` **not touched**.

---

## 0. Pre-run offline check on `depth_feas_v2` (scoring hardening proof)

On frozen `outputs/东边野兽/depth_feas_v2/market_feasibility.md`:

| Check | Result |
| --- | --- |
| **scoring_check** | **2 severe** — `缺少加权总分算式`（表内写 3.5、无 `加权总分 = 0.25×…` 行）+ `加权总分算错`（声称 3.5，表行重算 **3.60**） |
| **Pytest** | **47 passed**（table-row / missing-formula fixtures green; no regex fix needed） |

---

## 1. Metrics — this run (`depth_feas_v3`)

| Metric | Result | Notes |
| --- | --- | --- |
| **Exit code** | **0** | Strict footer gates clean on severe |
| **Pytest** | **47 passed** | `test_artifact_check` + `test_checks` |
| **Scoring (footer)** | **✅ formula found; written 3.8 == recompute 3.8** | Line: `加权总分 = 0.25×4 + 0.15×4 + 0.20×4 + 0.20×3 + 0.20×4 = 3.80` |
| **Artifact floor (footer)** | **0 severe / 0 warn** | Channel floor + appendix present after retries |
| **Citation severe** | **0** | 2 files, 20 URLs; **3** human-review（aesop.com homepage + Boots 参考文献退化×2） |
| **Serper** | **14**（14 ok / 0 err） | tool_audit 28 lines = 14 started + 14 finished; **no fetch/scrape** |
| **Guardrail retries (feas)** | **2 blocked → pass** | (1) `feas_missing_appendix`；(2) `feas_channel_social_only` |
| **Gap-fill guardrail** | Passed first check | — |
| **Soft-pass / compose soft-budget** | **Not observed** | — |
| **Depth gate** | **0 severe / 2 warn** | `gap_fill_thin_search`；`gap_fill_status_contradiction`（缺口 #4 有 URL 却写「本轮检索无果」） |

---

## 2. vs `depth_feas_v2` (same case)

| | `depth_feas_v2` | `depth_feas_v3` (this) |
| --- | --- | --- |
| **Exit** | **0** | **0** |
| **Scoring footer** | Skipped / offline NOW: missing formula + 3.5≠3.6 | **3.8 = 3.8 ✅** |
| **Artifact** | 0 severe / 1 warn `feas_falsifiable_thin` | **0 severe / 0 warn** |
| **Depth gate** | 0 severe / 1 warn | 0 severe / **2** warn（thin_search + status_contradiction） |
| **Citations** | 0 severe / 5 homepage warns | 0 severe / **3** review |
| **Serper** | 17 | **14** |
| **Feas guardrail** | 3× channel floor | 2× (appendix + channel) |

### What improved

1. **Scoring gate closed** — formula line present and arithmetic matches; v2’s skip/miss class is gone on this run.
2. **Artifact floor clean** — no severe, no warn on live footer.
3. **Offline scoring_check** now correctly fails v2 archive (proof before this smoke).

### Residual (warn-only)

1. Gap-fill still thin-search; one status contradiction warn.
2. Search-only audit (no scrape/fetch).
3. Some homepage / ref-degradation citation reviews remain (not severe).

---

## 3. Recommendation — full `research_depth`?

**YES** — success criteria met:

| Criterion | Status |
| --- | --- |
| exit 0 | ✅ |
| scoring formula found AND written == recompute | ✅ 3.8 == 3.8 |
| artifact 0 severe | ✅ |
| depth 0 severe (warn OK) | ✅ (2 warn) |

---

## Paths

| Item | Path |
| --- | --- |
| This backup | `outputs/东边野兽/depth_feas_v3/` |
| Run log (tee) | `/tmp/herbeast_feas_depth_v3.log` → copied to `…/depth_feas_v3/run.log` |
| Prior case | `outputs/东边野兽/depth_feas_v2/` |
| Untouched | `outputs/东边野兽/backup_v8/` |
