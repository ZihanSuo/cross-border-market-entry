# CHANGELOG — depth_feas_v1（东边野兽 → UK）

**Date:** 2026-08-12  
**Purpose:** Cross-case generalization smoke after Flower Knows depth work — same `feasibility_depth` + `--strict-depth` + `--strict-citations` stack on a **different** brand/market (`briefs/herbeast_uk_v2.json`), not Flower Knows.  
**Variant:** `feasibility_depth`  
**Brief:** `briefs/herbeast_uk_v2.json`（东边野兽 → UK）  
**Run exit code:** `1`（`--strict-depth`：深度门禁 1 severe）  
**Artifacts:** this folder only — `market_feasibility.md`, `evidence_gap_fill.md`, `tool_audit.jsonl`, `run.log`（from `/tmp/herbeast_feas_depth_v1.log`）  
**Frozen:** `outputs/东边野兽/backup_v8/` **not touched**.

---

## 1. Metrics (this run)

| Metric | Result | Notes |
| --- | --- | --- |
| **Exit code** | **1** | Both Depth tasks completed; footer `--strict-depth` abort on depth gate |
| **Scoring written vs recompute** | Report claims **3.8**; table recompute **3.65**; checker printed **None vs 3.65** and still ✅ | Written total mismatched arithmetic (`0.25×4+0.15×3+0.20×4+0.20×3+0.20×4=3.65`); parser failed to read written total → missed the 3.8≠3.65 inconsistency |
| **Artifact floor (guardrail)** | **Passed first try** | Feasibility `Guardrail Passed` with no Blocked retries; hard-evidence used YanLab press + REACH page (see §3) |
| **Citation severe** | **0** | 2 files, 18 URLs, 0 severe / 0 human-review |
| **Serper** | **7**（7 ok / 0 err） | Log summary; tool_audit 14 lines = 7 started + 7 finished; **no fetch/scrape** |
| **Guardrail retries** | **0** | Feasibility + gap-fill each passed on first evaluation |
| **Soft-pass / compose soft-budget** | **Not observed** | No `共享软上限` / `组合 guardrail` banners; no CrewAI `Task failed guardrail validation after N retries` |
| **Depth gate** | **1 severe** `gap_fill_single_angle` | 补证（且可行性）queries stayed on attitude/concept / regulation / market-report angles — no retail platform, price compare, or brand+channel second angle |

---

## 2. Channel evidence quality

**Expected UK retail anchors (Cult Beauty / Boots / Sephora / Space NK / Lookfantastic, etc.): not present.**

What the report actually used:

| Claimed channel evidence | Reality |
| --- | --- |
| YanLab London via BeautyMatter article | Press / partner-season narrative that Herbeast is in a YanLab London concept — **not** a retailer PDP, assortment, or price page |
| HSE REACH / gov notification URLs in「硬证据清单」 | **Compliance**, not channel/retail visibility — list padding |
| Grand View / clean-beauty market reports (feas + gap fill) | Category TAM/CAGR **report padding**, not shelf/channel proof |
| Gap-fill biorius / Statfold regulation guides | Regulatory explainers — useful for门槛, not for渠道可达 |

**Social padding:** little/no Instagram/TikTok-as-channel; failure mode here is **report + regulation + partner press**, not social. Still fails the depth intent of “second angle = retail/price/brand+channel.”

---

## 3. Honest vs Flower Knows `depth_feas_v5`

| | Flower Knows `depth_feas_v5` | Herbeast `depth_feas_v1` (this) |
| --- | --- | --- |
| Exit | **0** | **1** |
| Depth gate | 0 severe / 1 warn `gap_fill_thin_search` | **1 severe** `gap_fill_single_angle` |
| Scoring | 3.65 = 3.65 ✅ | Wrote **3.8**, true **3.65**; checker saw **None** |
| Guardrail retries | Feas 2 blocked then pass | **0** retries (passed weak evidence first try) |
| Soft-pass | Not needed | Not needed / not seen |
| Serper | 14 | **7** |
| Citations | 0 severe (11 human-review warns) | 0 severe / 0 warn |
| Channel shape | TH retail-ish URLs (KONVY/Beautrium class, with homepage warns) | **No** Cult Beauty/Boots-class URLs; YanLab press + compliance |

### What migrated

- Pipeline shape: `feasibility_depth` → gap fill → tool audit → citations → scoring → depth gate.
- Composed guardrail soft-budget path did not abort CrewAI (same as v5 happy-path property).
- `--strict-citations` clean on severe fake/placeholder checks.
- Artifact/guardrail **surface** (硬证据清单 + 中度地板 wording) present and green.

### What broke / did not generalize

1. **Depth gate severe** — gap-fill + feas searches never pivoted to UK retail/price/brand+channel queries; FK only had thin-search **warn**.
2. **Scoring honesty** — arithmetic slip (3.8 vs 3.65) plus checker parsing **None** so self-consistency ✅ is weaker than FK v5.
3. **Channel floor false comfort** — guardrail accepted partner-press + REACH as channel/硬证据; did not force Cult Beauty/Boots-class or in-stock pages.
4. **Thinner tool use** — half the Serper volume of FK v5; still search-only.

---

## 4. Bottom line / next step

Generalization **partially** works operationally (tasks finish, citations severe=0, no guardrail death) but **fails** the strict depth bar that Flower Knows cleared. Channel evidence is press/report/compliance-shaped, not UK specialty/drugstore retail.

**Recommendation on full `research_depth` next:** **Not yet.** Fix or re-smoke `feasibility_depth` until depth gate is clean (retail/price/brand+channel second angle + scoring written=recompute) before spending a full research_depth run on this case.

---

## 5. Follow-up（同日，已改尺子，正在跑 depth_feas_v2）

1. 渠道地板：**黑名单 → 零售白名单**（BeautyMatter / HSE 不再计入）
2. 评分：`= **3.8**` 可解析 claimed → 算术闸能拦
3. 补证：英系零售 markers + depth prompt 写明 Cult Beauty/Boots 等第二角度
