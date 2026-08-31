# CHANGELOG — depth_v1（东边野兽 / Herbeast → UK）

**Date:** 2026-08-12  
**Variant:** `research_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/herbeast_uk_v2.json`  
**Wall time:** 19:17:17 → 19:21:03 CST (~3.7 min)  
**Log:** `run.log`（from `/tmp/herbeast_research_depth_v1.log`）  
**Pre-run backup:** `outputs/_pre_herbeast_research_depth_v1_backup/`  
**Frozen:** `outputs/东边野兽/backup_v8/` **not touched**.

Artifacts in this folder: `market_feasibility.md`, `evidence_gap_fill.md`, `market_expansion.md`, `competitor_battlecard.md`, `tool_audit.jsonl`, `run.log`, `CHANGELOG.md`.

---

## Honesty note (mtimes / deliverables)

All four markdown outputs + `tool_audit.jsonl` are from **this** run (not stale leftovers from `depth_feas_v3` / prior backups):

| File | mtime (CST) | In run window 19:17:17–19:21:03? |
| --- | --- | --- |
| `market_feasibility.md` | 19:18:42 | yes |
| `evidence_gap_fill.md` | 19:18:59 | yes |
| `market_expansion.md` | 19:19:10 | yes |
| `tool_audit.jsonl` | 19:20:36 | yes |
| `competitor_battlecard.md` | 19:21:01 | yes |
| `run.log` | 19:21:02 | yes (tee log) |

`backup_v8/` had **0** files newer than run start.

---

## Exit code (important)

| Measurement | Value | Notes |
| --- | --- | --- |
| **Python / true process exit** | **1** | Crew finished writing 4 tasks; post-run `scoring_check` → `raise SystemExit("评分表自洽性校验未通过…")` (string SystemExit → status **1**). |
| Shell `$?` after `… \| tee` **without** `pipefail` | **0** | **Misleading** — that was `tee`’s success. Do not treat pipe exit as Python’s. |
| Live post-run order reached | citation ✅ → **scoring ✖ exit** | Depth gate + artifact footers **not printed live** (skipped after scoring SystemExit). Recomputed offline below. |

**Critical pipeline criterion met:** process did **not** abort mid-Crew with `Task failed guardrail validation after N retries`. Soft-pass banners fired; all four tasks reached `Task Completed`.

---

## Metrics table — this run

| Metric | depth_v1 (this run) |
| --- | --- |
| **Exit code (Python)** | **1** (post-run scoring SystemExit) |
| **Crew hard abort** | **no** |
| **Tasks completed** | **4 / 4** — feasibility, gap fill, expansion, competitor |
| **Scrape count** | **4** finished `read_website_content`（2× thin/JS-wall 106–130 chars；2× usable 7.7k / 10.7k） |
| **Serper** | **27** finished / **0** error（feas **15**, gap **3**, competitor **9** scrapes+search mix: competitor **13** finished tool rows = serper+scrape；expansion agent **0** tools） |
| **Artifact feas (offline)** | **0 severe** / **1 warn** — `feas_falsifiable_thin` |
| **Artifact comp (offline)** | **1 severe** — `comp_price_floor`（4 price+URL rows &lt; 5）；scrape floor **PASS**（≥2 real scrapes） |
| **Citation (live + offline)** | **0 severe** / **9** human-review（bare homepages as evidence）; 47 URLs across 4 files |
| **Scoring (live footer)** | **FAIL** — `加权式子无法解析`（soft-pass banner 含 `加权总分 = … = X`，解析器先命中横幅） |
| **Scoring (body, honesty)** | Banner soft-pass reason: claimed **3.83** vs recompute **3.85**（差 0.02）；正文仍写 `= 3.83` /「建议进入」 |
| **Depth gate (offline; skipped live)** | **0 severe** / **1 warn** `gap_fill_thin_search` |
| **Guardrail retries** | Feas: **3×** blocked `feas_channel_social_only` → later soft-pass on **scoring arithmetic**；Gap: passed；Expansion: completed（0 tools）；Comp: **3×** blocked `comp_scrape_floor` → soft-pass on **`comp_price_floor`** |
| **Soft-pass / compose soft-budget** | **YES** — shared soft cap（累计 **4** 次未通过 / 上限 **3**）；banner on **both** `market_feasibility.md` and `competitor_battlecard.md`（文首写明「不可直接当成品」） |

---

## vs `东边野兽/depth_feas_v3`（feas-only GREEN）

| Dimension | `depth_feas_v3` | **`depth_v1` full research_depth** |
| --- | --- | --- |
| Scope | `feasibility_depth` only | Full `research_depth`（4 tasks） |
| Exit (Python) | **0** | **1**（scoring） |
| Tasks done | 2（feas+gap） | **4** |
| Scoring | **3.8 = 3.8** ✅ | Live parse **FAIL**；body **3.83 ≠ 3.85** |
| Artifact feas | 0 severe / 0 warn | 0 severe / 1 warn `feas_falsifiable_thin` |
| Artifact comp | n/a | **1 severe** `comp_price_floor` |
| Citation | 0 severe / 3 review | 0 severe / **9** review |
| Serper | 14 | **27** |
| Scrape | 0 | **4** |
| Soft-pass | none | **yes**（feas + competitor） |
| Depth gate | 0 severe / 2 warn | 0 severe / **1** warn |

### What improved vs feas_v3

1. Full chain exercised: expansion + competitor artifacts written with fresh mtimes.  
2. Real scrapes appeared（4），竞品 scrape 地板 offline 可通过（FK depth_v3 当时是 0 scrape）。  
3. Soft-budget prevented hard Crew abort（与花知晓 depth_v3 同模式）。

### What regressed vs feas_v3

1. **Lost exit 0 / scoring GREEN** — feas_v3 的 3.8=3.8 在全链 soft-pass 后被打烂（正文仍 3.83，且横幅毒化 footer 解析）。  
2. Feasibility 文首带 soft-pass「不可直接当成品」——不能再当 feas smoke 的可交付成功。  
3. 竞品价带地板仍红（4&lt;5）。

---

## vs `花知晓/depth_v3`（FK full depth）

| Dimension | 花知晓 `depth_v3` | 东边野兽 **`depth_v1`** |
| --- | --- | --- |
| Exit (Python) | **1**（citation TBD FP in soft-pass banner） | **1**（scoring parse / arithmetic） |
| Tasks | 4 / 4 | 4 / 4 |
| Soft-pass | competitor only | **feas + competitor** |
| Scrape | **0** | **4** |
| Serper | 22 | **27** |
| Artifact feas | 0 severe / 2 warn | 0 severe / 1 warn |
| Artifact comp | **2 severe**（price + scrape） | **1 severe**（price only；scrape OK） |
| Citation | **1 severe**（banner TBD） | **0 severe** / 9 review |
| Scoring | offline 3.65=3.65（live skipped） | live **FAIL**；body 3.83≠3.85 |
| Depth gate | 0 severe / 1 warn thin_search | 0 severe / 1 warn thin_search |
| Expansion tools | 0 | **0**（same thin pattern） |

### Relative read

- Pipeline / soft-pass story matches FK depth_v3: Crew completes, strict footer still fails.  
- Herbeast scrape story is **stronger** than FK v3（真实抓取 ≥2，comp scrape floor green）。  
- Herbeast scoring / feas soft-pass story is **weaker** than FK v3（FK feas 未 soft-pass，offline 分还能自洽）。

---

## Guardrail / retry log

| Task | Event |
| --- | --- |
| Feasibility attempts 1–3/7 | **Blocked** — `feas_channel_social_only`（retail URL 0→1） |
| Feasibility final | **Soft-pass banner** — scoring arithmetic 3.83 vs 3.85 → Task Completed |
| Gap fill | **Guardrail Passed** → Task Completed（3 Serper） |
| Expansion | Task Completed；**0** tool calls in audit |
| Competitor attempts 1–3/7 | **Blocked** — `comp_scrape_floor`（0 有效抓取） |
| Competitor final | Scrapes succeed but **Soft-pass banner** on `comp_price_floor`（4&lt;5）→ Task Completed |

No `Exception: Task failed guardrail validation after N retries`.

---

## Scoring honesty (exit 1 cause)

1. **Live `scoring_check`:** finds `加权总分 =` inside the **soft-pass remediation quote** (`把「加权总分 = … = X」里的 X 改成…`) → `加权式子无法解析` → `--strict-citations` SystemExit **1**.  
2. **Body formula (below banner):** `0.25×4 + 0.15×3 + 0.20×4 + 0.20×4 + 0.20×4 = 3.83` but true Σ = **3.85** — same class of error that triggered the in-loop soft-pass.  
3. Contrast: `depth_feas_v3` had clean `3.80 = 3.80` and exit 0.

---

## Remaining issues (do not ship as finished Depth)

1. Soft-pass banners on feas **and** competitor explicitly say **不可直接当成品**.  
2. Feasibility score still wrong in body（3.83 vs 3.85）and footer parse poisoned by banner.  
3. Competitor **price floor** still red（4 qualifying rows）.  
4. 2/4 scrapes were bot-wall / thin（Aesop/Boots）；only Neal’s Yard + Best Seasons Beauty returned real product text.  
5. Expansion agent **0 searches** — strategy section under-evidenced.  
6. Gap-fill thin_search warn；multiple homepage-as-evidence citation reviews.  
7. Channel path only cleared via soft-budget history — not a clean floor pass like feas_v3.

---

## Bottom line — shippable Depth deliverable?

### **NO**

| Bar | Result |
| --- | --- |
| Pipeline success（4 tasks, no hard abort, fresh mtimes） | **YES** |
| Strict footer green（exit 0 under `--strict-*`） | **NO**（Python exit **1**） |
| Soft-pass free / “可当成品” | **NO**（dual soft-pass banners） |
| Competitor Depth floors | **NO**（`comp_price_floor`） |
| Scoring self-consistent | **NO**（3.83≠3.85 + banner parse fail） |

Treat as a successful **pipeline** experiment on the UK case after green `depth_feas_v3`, and an unsuccessful **Depth deliverable**.

---

## Follow-up（同日，未重跑）

1. **`scoring_check` 先剥 soft-pass 横幅**再解析算式（横幅里的「加权总分 = … = X」示例曾污染核对）。
2. scoring guardrail 反馈文案去掉易被当成算式的 `加权总分 = … = X` 写法。
3. **进展**：本轮竞品 **scrape=4**（花知晓 depth_v3 为 0）——`scrape_effort` 闸有效；仍卡在价带 4&lt;5。

---

## Paths

| Item | Path |
| --- | --- |
| This backup | `outputs/东边野兽/depth_v1/` |
| Run log (tee) | `/tmp/herbeast_research_depth_v1.log` → `…/depth_v1/run.log` |
| Pre-run md backup | `outputs/_pre_herbeast_research_depth_v1_backup/` |
| Feas-only baseline | `outputs/东边野兽/depth_feas_v3/` |
| FK full-depth baseline | `outputs/花知晓/depth_v3/` |
| Untouched | `outputs/东边野兽/backup_v8/` |
