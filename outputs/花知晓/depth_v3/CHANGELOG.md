# CHANGELOG — depth_v3

**Date:** 2026-08-12  
**Variant:** `research_depth` + `--strict-depth` + `--strict-citations`  
**Brief:** `briefs/flowerknows_thailand.json`  
**Wall time:** 18:56:37 → 18:59:02 CST (~2.4 min)  
**Log:** `run.log` (from `/tmp/research_depth_v3.log`)  
**Pre-run backup:** `outputs/_pre_research_depth_v3_backup/`

Artifacts in this folder: `market_feasibility.md`, `evidence_gap_fill.md`, `market_expansion.md`, `competitor_battlecard.md`, `tool_audit.jsonl`, `run.log`, `CHANGELOG.md`.

---

## Honesty note (mtimes / deliverables)

Unlike `depth_v2` (which aborted on feasibility and left **stale** markdown), **all four markdown outputs + `tool_audit.jsonl` are from this run**:

| File | mtime (CST) | In run window 18:56:37–18:59:02? |
| --- | --- | --- |
| `market_feasibility.md` | 18:57:13 | yes |
| `evidence_gap_fill.md` | 18:57:31 | yes |
| `market_expansion.md` | 18:57:43 | yes |
| `tool_audit.jsonl` | 18:58:39 | yes |
| `competitor_battlecard.md` | 18:59:00 | yes |
| `run.log` | 18:59:02 | yes (tee log) |

No stale leftover claim for the four task md files.

---

## Exit code (important)

| Measurement | Value | Notes |
| --- | --- | --- |
| **Python / true process exit** | **1** | After Crew completed, post-run `citation_check` found 1 severe → `raise SystemExit("引用校验未通过…")` (string SystemExit → status 1). Scoring / depth / artifact **post-run** blocks were **not reached** in-process. |
| Shell `$?` after `… \| tee` **without** `pipefail` | 0 | **Misleading** — that was `tee`’s success. Do not treat pipe exit as Python’s. |

**Critical success criterion still met:** process did **not** abort mid-Crew with `Task failed guardrail validation after N retries`. Soft-pass banner fired on competitor; all four tasks reached `Task Completed`.

---

## Metrics table

| Metric | depth_v3 (this run) |
| --- | --- |
| **Exit code (Python)** | **1** (post-run citation SystemExit) |
| **Crew hard abort** | **no** |
| **Tasks completed** | **4 / 4** — feasibility, gap fill, expansion, competitor |
| **Competitor ran?** | **yes** |
| **Compose soft-pass banner** | **yes** — competitor: `组合 guardrail 已达共享软上限`（累计 3 次未通过 / 上限 2） |
| **Scrape count** | **0** (audit: no fetch/scrape tools) |
| **Serper** | **22** finished / **0** error (feas 7, gap 3, competitor 12; expansion agent **0** tool calls) |
| **Artifact feas (offline recompute)** | **0 severe** / 2 warn — `feas_channel_honest_gap`, `feas_falsifiable_thin` |
| **Artifact comp (offline + soft-pass reason)** | **2 severe** — `comp_price_floor` (3 price rows &lt; 5), `comp_scrape_floor` (0 scrape) |
| **Citation (live, caused exit 1)** | **1 severe** + 13 human-review warns — see §Citation honesty |
| **Scoring (offline; skipped live)** | **3.65 = 3.65** ✅ |
| **Depth gate (offline; skipped live)** | **0 severe** / 1 warn `gap_fill_thin_search` |
| **Guardrail retries** | Feas: **1** blocked (scoring) then pass; Comp: **2** blocked (depth floors) then **soft-pass** |

---

## vs depth_v1 / depth_v2 / depth_feas_v5

| Dimension | depth_v1 | depth_v2 (failed) | depth_feas_v5 | **depth_v3** |
| --- | --- | --- | --- | --- |
| Scope | Full `research_depth` | Full attempted | `feasibility_depth` smoke | Full `research_depth` |
| Flags | (floors post-hoc) | `--strict-*` | `--strict-*` | `--strict-*` |
| Exit | Produced md; floors failed quality | **1** mid-task abort | **0** | **1** post-run citation only |
| Tasks done | 4 | **0** (died on feas) | 2 (feas+gap) | **4** |
| Hard `Task failed guardrail…` | n/a (older path) | **yes** (feas after 4 retries) | **no** | **no** |
| Soft-pass banner | n/a | n/a (hard abort first) | none (not needed) | **yes on competitor** |
| Artifact feas | severe channel/social | never shipped | 0 severe / 1 warn | **0 severe** / honest-gap warn |
| Artifact comp | price 0 rows + 0 scrape | not reached | n/a | price **3** rows + **0** scrape (still severe) |
| Citation | 1 severe TBD + homepage noise | 3 severe (abort cause) | 0 severe | 1 severe (banner TBD FP) |
| Scoring | header drift / skip | failed mid-loop | 3.65=3.65 | **3.65=3.65** |
| Serper | lower | 19 (feas only) | 14 | **22** |
| Scrape | 0 | 0 | 0 | **0** |
| Deliverable honesty | real files, fake-deep | **stale md** warning | real feas+gap | **real all 4 md** |

### What improved vs depth_v2

1. **Compose soft-budget works on full chain:** feasibility no longer kills the Crew; competitor soft-passes instead of `Task failed guardrail validation after N retries`.
2. **All four tasks write fresh artifacts** with mtimes inside this run.
3. Feasibility scoring recovered in one retry (same pattern as feas_v5); channel path used **honest gap** rather than hard `feas_channel_social_only` abort.

### What did **not** improve enough vs depth_v1 floors

1. Competitor still **0 real scrapes**; battlecard *claims* scrape on Watson’s URLs but audit proves zero `scrape_page`.
2. Price floor still short (**3** qualifying rows vs **≥5**).
3. Soft-pass **embeds the unresolved guardrail text** at the top of `competitor_battlecard.md` — correct signal that it is **not** a finished product.

### vs depth_feas_v5

- feas_v5 proved soft-budget safety on the short pipeline without needing the banner.
- depth_v3 is the first full-chain run that **exercises soft-pass for real** (competitor floors exhausted soft budget).
- Feasibility quality is in the same ballpark as feas_v5 (scoring OK; channel honest-gap / thin falsifiable warns).

---

## Guardrail / retry log

| Task | Event |
| --- | --- |
| Feasibility attempt 1/7 | **Blocked** — scoring arithmetic (重算不符) → retry |
| Feasibility later | **Guardrail Passed** → Task Completed |
| Gap fill | **Guardrail Passed** → Task Completed |
| Expansion | Task Completed (no blocked retries observed; **0** Serper in audit) |
| Competitor attempt 1/6 | **Blocked** — `comp_price_floor` + `comp_scrape_floor` |
| Competitor attempt 2/6 | **Blocked** — same 2 severes |
| Competitor final | **Soft-pass banner** (shared soft cap 3 fails / max 2) → Task Completed; floors **still failing** |

No `Exception: Task failed guardrail validation after N retries`.

---

## Citation honesty (exit 1 cause)

Post-run citation report: **1 severe**, 13 warns.

The **severe** hit is:

- ❌ `TBD 占位符` inside `competitor_battlecard.md`

**Root cause:** soft-pass **quotes** the prior guardrail remediation text (`禁止…TBD 行凑数`) into the battlecard preamble. The citation scanner treats that quoted `TBD` as a placeholder-as-evidence failure. This is largely a **soft-pass banner false positive**, not an agent inventing a TBD price row in the价带表 (the table has 3 Watson’s product URLs, no TBD cells).

Warns remain real quality issues: bare brand homepages as evidence; KONVY brand/list paths used like product pages.

Because `--strict-citations` SystemExit’d here, live process **skipped** printing scoring / depth / artifact footers. Those were **recomputed offline** for this CHANGELOG from the same artifacts + `tool_audit.jsonl`.

---

## Remaining issues (do not ship as finished Depth)

1. **Competitor floors still red** after soft-pass — need ≥2 real `scrape_page` successes and ≥5 price rows with non-homepage SKU URLs.
2. **Claimed scrapes without tools** — battlecard “- scrape” lines are model prose; audit = 0.
3. **Citation strict exit** tripped by soft-pass banner text containing `TBD` — consider stripping/quoting remediation banners out of citation scope, or rewriting banner copy without the token `TBD`.
4. **Expansion agent used 0 searches** — thin downstream strategy risk.
5. **Gap-fill thin** (`gap_fill_thin_search`) — 3 searches ≈ 3 gaps.
6. Feasibility channel still only **1** countable retail URL (honest-gap warn, not severe).

---

## Bottom line

`depth_v3` **clears the soft-pass / no-hard-abort bar** that `depth_v2` failed: full four-task Crew finishes with fresh artifacts. It does **not** clear quality floors on competitor (price+scrape) and exits **1** under `--strict-citations` due to a TBD hit in the soft-pass banner quote. Treat as a successful **pipeline** experiment and an unsuccessful **Depth deliverable**.

---

## Follow-up fix (post depth_v3, 未重跑全量)

1. **`citation_check._strip_guardrail_banner`**：识别「组合 guardrail / 共享软上限 / Depth 地板」等文首引用块，避免 soft-pass 横幅里的「TBD」被当成正文严重项（depth_v3 exit 1 根因）。
2. **竞品 task**：`guardrail: scrape_effort,artifact_competitor,citation` —— 先强制审计可见的 scrape，再验价带地板。
3. 下一轮应再跑 `research_depth`（或至少竞品一步）验证 scrape 投入闸是否逼出真实抓取。
