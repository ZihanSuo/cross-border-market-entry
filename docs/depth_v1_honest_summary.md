# Depth V1 诚实摘要（2026-08-12 收口）

> **一句话**：Depth 提高了「能不能被代码拦住」的可控性，**没有**产出可直接交付的咨询级深度包。面试主推仍是 Workflow + 评测闸 + agentic 失败对照；Depth 是实验分支，不是第三份 demo。

设计与结论写在 [`docs/storyline.md`](storyline.md) 发现七；实现见 `src/marketing_crew/artifact_check.py`、`research_depth_check.py`。

---

## 1. Depth 是什么 / 不是什么

| Depth 是 | Depth 不是 |
|---|---|
| 可选变体 `research_depth` / `feasibility_depth`（**不改**冻结的 `research_only`） | 自主 McKinsey / 换模型就能变深 |
| 文末「硬证据清单」+ 中度机械地板（零售 URL、价带行、摘录、可证伪、scrape 努力） | 咨询成品；soft-pass 横幅写明「不可直接当成品」 |
| `artifact_check` + 深度门禁 + 与 citation/scoring 组合的 guardrail | 解决「算错加权分」「抓了不看结果」的根因（只能抓住） |

---

## 2. 三案对照（演示 vs 实验室）

### 演示冻结（面试直接打开）

| 案例 | 路径 | 角色 |
|---|---|---|
| 花知晓 → 泰国 | `outputs/花知晓/backup_v4/` | 主 demo，引用 0 严重 |
| 东边野兽 → 英国 | `outputs/东边野兽/backup_v8/` | 第二 demo，1 严重如实保留 |
| 石头科技 → 德国 | `outputs/石头科技/v1/` | **跨行业 + 结论首次降级**（3.15 → 暂缓铺货）；**不是** Depth，但是金样 |

对照失败实验：`outputs/东边野兽/agentic_v2/`（agentic 竞品，四轮演化）。

### Depth 实验室（勿当成品 demo）

| 案例 | 最新有意义归档 | 流水线 | 成品 | 备注 |
|---|---|---|---|---|
| 花知晓 | `outputs/花知晓/depth_v3/` | YES（4/4） | NO | 竞品 soft-pass；scrape=0 |
| 东边野兽 | `outputs/东边野兽/depth_v1/` | YES（4/4） | NO | feas+竞品双 soft-pass；scrape=4；价带 4&lt;5；书面分曾与真值差 0.02 |
| 石头科技 | `outputs/石头科技/depth_feas_v3/` | feas+gap YES | NO | **未上全链**；评分 soft-pass 3.34≠3.15；引用「待补充」严重；v2 曾 2.95=2.95 且渠道清 |

石头 Depth 冒烟迭代（停在 v3，不再刷）：

| 轮次 | 清掉了什么 | 仍红 |
|---|---|---|
| `depth_feas_v1` | 流水线通 | 渠道 soft-pass；评分解析被结论行干扰 |
| `depth_feas_v2` | 渠道严重清；**2.95=2.95**；结论暂缓 | `gap_fill_no_retail_pivot`×2 |
| `depth_feas_v3` | DE 零售 marker 对齐；offline depth 0 sev | 评分 3.34≠3.15；citation TBD；gap 仍少真实 MediaMarkt pivot |

代码侧已跟进（德国零售 allowlist / Amazon PDP、算式行解析、DE retail pivot markers）——**检查器更严了，模型算术与占位仍会红**。

---

## 3. 实验结论（可直接当面试答）

1. **可控性 ↑，咨询深度 ≠ 自动 ↑**  
   地板能逼出零售向搜索、scrape 次数（东边野兽 Depth scrape=4 vs 花知晓 Depth scrape=0）、诚实「证据不足」警告；不能保证价带凑满、公式自洽、或阅读抓取结果。

2. **Soft-pass 是功能，不是粉饰**  
   重试耗尽后放行并打横幅，避免「task 静默失败、磁盘留着上一案旧文件」（石头首跑曾把花知晓泰国竞品原样归档）。**有横幅 = 不可交付。**

3. **跨市场要扩 allowlist，不是改 prompt 口号**  
   英国美妆零售主机 ≠ 德国家电（MediaMarkt / Amazon.de PDP / Otto…）。Depth 暴露的是「地板过拟合到第一案品类」。

4. **与发现五同一条线**  
   石头 `research_only` v1 仍是「锚点让系统说 no」的最强实证。Depth feas 反而多次写出「建议进入」或算错分——**更深的模板没有自动带来更诚实的结论。**

5. **何时停**  
   再刷 `feas_v4` / 未绿上全链，边际故事几乎为零。收口标准：演示用冻结包；Depth 用本文件讲边界。

---

## 4. 面试怎么讲（30 秒插句）

> 后来我加了一层 Depth：不是让 Agent 更自由，而是给报告加机械证据地板。流水线能跑通，但带 soft-pass 横幅的输出我明确不当成品。真正改变结论行为的，还是更早那次——给评分锚点之后，石头科技德国案第一次算出 3.15、说了「先别进」。

更长版本见 `docs/storyline.md` 发现七。

---

## 5. 不要做什么

- 不要覆盖 `backup_v4` / `backup_v8` / `石头科技/v1`
- 不要把 `depth_*` 目录当「更新后的 demo」
- 不要声称 Depth 已达到顾问交付标准
- 不要在 Depth 未绿时默认开全链烧钱重跑
