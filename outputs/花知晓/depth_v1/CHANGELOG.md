# depth_v1（research_depth 全链路，花知晓 → 泰国）

- **variant**: `research_depth`
- **brief**: `briefs/flowerknows_thailand.json`
- **date**: 2026-08-12
- **runtime artifact_check**: 3 severe — `feas_channel_social_only`, `comp_price_floor` (0 行), `comp_scrape_floor` (0 scrape)
- **citation**: 1 severe（TBD/待补充）, 9 人工复核（品牌首页当证据）
- **scoring_check**: 跳过（评分表表头漂成「评分」而非标准「得分」列，解析不到）
- **depth gate**: 0 severe / 1 warn (`gap_fill_thin_search`)

## 诚实结论

Depth V1 **地板能拦假深**，但本轮**没有真正抬深**：

1. 可行性渠道清单用 FB + 法规页凑数 → 被 `feas_channel_social_only`（随后又收紧：研报/法规页也不计）拦住。
2. 竞品 0 次 scrape；价带表是品牌首页 + 宽区间 +「待补充」行 → 引用与地板双杀。
3. 「放开正文」后评分表格式漂移，自洽性校验失效——下一步 prompt 已强制标准表头。

**下一步（已改代码/prompt，未重跑）**：社媒+法规页不计渠道地板；竞品强制 scrape/单品 URL/禁止 TBD 行；价带正则兼容 `69-450`；可行性 expected_output 钉死评分表。

建议：调完后再跑一次 `feasibility_depth` 验证渠道地板，再决定是否付费重跑全链路。
