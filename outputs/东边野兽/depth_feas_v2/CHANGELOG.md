# CHANGELOG — depth_feas_v2（东边野兽 → UK）

**Date:** 2026-08-12  
**Purpose:** Re-smoke after allowlist / channel-floor / scoring-check hardening — same stack as v1 on `briefs/herbeast_uk_v2.json`.  
**Variant:** `feasibility_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/herbeast_uk_v2.json`（东边野兽 → UK）  
**Run exit code:** `0`  
**Pytest (pre-run):** `tests/test_artifact_check.py` + `tests/test_checks.py` → **46 passed**  
**Artifacts:** this folder — `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log`（from `/tmp/herbeast_feas_depth_v2.log`）  
**Frozen:** `outputs/东边野兽/backup_v8/` **not touched**.

---

## 0. Pre-run offline check on `depth_feas_v1` (regression proof)

On frozen `outputs/东边野兽/depth_feas_v1/market_feasibility.md`:

| Check | Result |
| --- | --- |
| **artifact_check** | **exit 1** — `feas_channel_social_only`（可计入零售/电商 URL 仅 1 条；清单其它链接多为非零售；零售向搜索 0）。v1 硬证据用 BeautyMatter/YanLab press + HSE/合规类链接凑渠道，现已被地板拒掉。 |
| **scoring_check** | **exit 1** — 报告总分 **3.8**，重算 **3.65**（差 0.15）；现已能读到书面总分（v1 CHANGELOG 里曾记为 None）。 |

---

## 1. Metrics — this run (`depth_feas_v2`)

| Metric | Result | Notes |
| --- | --- | --- |
| **Exit code** | **0** | Both Depth tasks completed; footer strict gates clean on severe |
| **Pytest** | **46 passed** | No fixture breakage from allowlist (konvy/beautrium still OK for depth_feasibility_ok) |
| **Scoring (footer)** | **Skipped**（未找到可解析的「加权总分 = 式子」行） | Table exists and writes **3.5**; rows recompute manually to **3.6** (`0.25×4+0.15×4+0.20×3+0.20×3+0.20×4`). Checker only keys off formula line → **missed 3.5≠3.6** |
| **Artifact floor (footer)** | **0 severe / 1 warn** `feas_falsifiable_thin` | Channel section used Weleda + Neal's Yard brand-home URLs as「出路 A」 |
| **Citation severe** | **0** | 2 files, 20 URLs; **5** human-review（bare homepage：Cult Beauty / Weleda / Neal's Yard） |
| **Serper** | **17**（17 ok / 0 err） | tool_audit 34 lines = 17 started + 17 finished; **no fetch/scrape** |
| **Guardrail retries (feas)** | **3 blocked → pass** | All three: `feas_channel_floor`（0 条可计入零售 URL） |
| **Gap-fill guardrail** | Passed | — |
| **Soft-pass / compose soft-budget** | **Not observed** | No `共享软上限` / `组合 guardrail` banners |
| **Depth gate** | **0 severe / 1 warn** `gap_fill_thin_search` | 补证 ~3 successful searches vs ~5 gaps |

---

## 2. vs `depth_feas_v1` (same case)

| | `depth_feas_v1` | `depth_feas_v2` (this) |
| --- | --- | --- |
| **Exit** | **1**（depth gate severe） | **0** |
| **Depth gate** | 1 severe `gap_fill_single_angle` | 0 severe / 1 warn `gap_fill_thin_search` |
| **Artifact (live run)** | Passed first try on weak channel evidence | 3× `feas_channel_floor` block then pass with brand-home「出路 A」 |
| **Offline artifact on artifact** | NOW fails channel floor (BeautyMatter/HSE-shaped padding) | Footer 0 severe; still homepage-grade channel URLs |
| **Scoring** | Wrote 3.8 vs 3.65; old run missed / offline NOW catches | Wrote **3.5** vs true **3.6**; footer **skipped** (no formula line) |
| **Serper** | 7 | **17** |
| **Guardrail retries** | 0 | **3** (channel floor) |
| **Citations** | 0 severe / 0 warn | 0 severe / **5** homepage warns |

### What improved

1. **Strict exit green** — depth gate no longer severe; gap-fill at least searched Cult Beauty / Space NK / Aesop angles.
2. **Channel floor is live** — BeautyMatter + HSE/compliance padding no longer first-pass green; retries forced until清单 had ≥2 retail-ish URLs (even if only brand homes).
3. **Tool volume** closer to Flower Knows class (~17 vs v1’s 7).
4. **Offline checkers** correctly fail v1 on channel + 3.8≠3.65 (pytest 46 green).

### What did not fully heal

1. **Channel quality still thin** — Cult Beauty / Weleda / Neal's Yard are mostly **bare homepages**, not PDPs/assortment/price pages; YanLab BeautyMatter press still in narrative/score row.
2. **Scoring evasion** — model omitted the `0.25×…=总分` formula line → scoring_check skipped while table arithmetic is still wrong (3.5 vs 3.6).
3. **Falsifiable subsection** still warn-thin; gap-fill still thin-search warn.
4. **Search-only** — still no scrape/fetch in audit.

---

## 3. vs Flower Knows `depth_feas_v5`

| | Flower Knows `depth_feas_v5` | Herbeast `depth_feas_v2` |
| --- | --- | --- |
| Exit | **0** | **0** |
| Depth gate | 0 severe / 1 warn `gap_fill_thin_search` | **Same class** |
| Scoring footer | 3.65 = 3.65 ✅ | **Skipped** (no formula); manual 3.5≠3.6 |
| Feas guardrail | 2 blocked (channel + scoring) then pass | **3 blocked** (channel only) then pass |
| Soft-pass | Not needed | Not needed |
| Serper | 14 | **17** |
| Citations | 0 severe / 11 homepage-ish warns | 0 severe / 5 homepage warns |
| Artifact | 0 severe / 1 warn `feas_falsifiable_thin` | **Same** |
| Channel shape | TH retail-ish (KONVY/Beautrium class, homepage warns) | UK brand homes (Weleda / Neal's Yard) + Cult Beauty home — **not** Boots/Cult PDP-class |

**Migrated:** same pipeline + strict flags; composed soft-budget unused but no CrewAI abort; depth/artifact warn profile mirrors FK v5.

**Still weaker than FK v5:** scoring self-check not exercised (formula omitted); UK retail evidence is homepage-proxy rather than specialty-retail product/brand-shop pages.

---

## 4. Recommendation — full `research_depth` yet?

**Not yet — conditional hold.**

`feasibility_depth` is now **operationally** at FK v5’s exit/gate shape (exit 0, depth severe=0, citations severe=0), and allowlist/channel-floor regressions on v1 are proven offline. Remaining blockers before spending a full `research_depth`:

1. Force / require the **weighted formula line** so scoring_check cannot be skipped (catch 3.5≠3.6 class slips).
2. Prefer **path-bearing retail URLs** (Cult Beauty brand/PDP, Boots, Lookfantastic, etc.) over bare `.co.uk/` homes and BeautyMatter press in渠道硬证据.
3. Optionally tighten gap-fill past `gap_fill_thin_search` if full research will inherit the same补证 budget.

After a green feasibility_depth re-smoke with scoring footer ✅ and less homepage-only channel evidence, full `research_depth` is reasonable.

---

## 5. Follow-up（同日）

有评分表却无 `加权总分 = 0.25×…` 行 → 旧校验整段跳过。已改为 **严重：缺少加权总分算式**（并可从表行重算交叉验证）。下一枪 `depth_feas_v3`。

---

## Paths

| Item | Path |
| --- | --- |
| This backup | `outputs/东边野兽/depth_feas_v2/` |
| Run log (tee) | `/tmp/herbeast_feas_depth_v2.log` → copied to `…/depth_feas_v2/run.log` |
| Prior case | `outputs/东边野兽/depth_feas_v1/` |
| FK reference | `outputs/花知晓/depth_feas_v5/` |
| Untouched | `outputs/东边野兽/backup_v8/` |
