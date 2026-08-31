以下是对三份上游产出（market_feasibility.md、market_expansion.md、competitor_battlecard.md）的逐条机械核对报告。

1. 逐 URL 核查表  
（去重后共14个URL）

| 文件                      | URL                                                                                                         | 类型               | 结论     |
|-------------------------|------------------------------------------------------------------------------------------------------------|------------------|--------|
| market_feasibility.md   | https://www.grandviewresearch.com/horizon/outlook/clean-beauty-market/uk                                     | 正常（报告数据源）    | 通过     |
| market_feasibility.md   | https://truebotanicals.com/                                                                               | 首页证据            | 不通过   |
| market_feasibility.md   | https://ravenbotanicals.com/                                                                              | 首页证据            | 不通过   |
| market_feasibility.md   | https://www.mintel.com/insights/beauty-and-personal-care/conscious-cosmetics-the-rise-of-clean-beauty/      | 正常（报告数据源）    | 通过     |
| market_feasibility.md   | https://www.gov.uk/guidance/making-cosmetic-products-available-to-consumers-in-great-britain                | 正常               | 通过     |
| market_feasibility.md   | https://www.biorius.com/cosmetic-regulations/uk-responsible-person/                                         | 正常               | 通过     |
| market_feasibility.md   | https://submit.cosmetic-product-notifications.service.gov.uk/                                              | 正常               | 通过     |
| market_feasibility.md   | https://www.gov.uk/guidance/making-cosmetic-products-available-to-consumers-in-great-britain (重复)         | 重复               | —      |
| market_feasibility.md   | https://www.ecosistant.eu/en/the-responsible-person-role-under-the-cosmetics-regulation-1223-2009/           | 正常               | 通过     |
| market_expansion.md     | https://www.herbeast.world/about                                                                            | 正常               | 通过     |
| market_expansion.md     | https://www.cultbeauty.co.uk/                                                                               | 首页证据            | 不通过   |
| market_expansion.md     | https://www.spacenk.com/                                                                                    | 首页证据            | 不通过   |
| competitor_battlecard.md| https://www.aesop.com/uk/p/body/parley-seed-facial-hydrating-cream/                                          | 正常               | 通过     |
| competitor_battlecard.md| https://www.cosmopolitan.com/uk/beauty-hair/news/a29237191/aesop-skincare-reviews/                           | 正常               | 通过     |
| competitor_battlecard.md| https://www.weleda.co.uk/product/skin-food-30ml                                                             | 正常               | 通过     |
| competitor_battlecard.md| https://www.goodhousekeeping.com/uk/product-reviews/healthandbeauty/g35008149/weleda-skincare-reviews/       | 正常               | 通过     |
| competitor_battlecard.md| https://www.nealsyardremedies.com/frankincense-hydrating-cream-50g                                          | 正常               | 通过     |
| competitor_battlecard.md| https://www.thesiteguide.com/blog/neals-yard-remedies-review/                                               | 正常               | 通过     |
| competitor_battlecard.md| https://www.paiskincare.com/products/chamomile-rosehip-calming-day-cream                                    | 正常               | 通过     |
| competitor_battlecard.md| https://www.huffpost.com/entry/pai-skincare-review_n_78d5c3c2e4b0780f5ea63257                               | 正常               | 通过     |

2. 应有证据却缺失的位置（反向核查）

| 文件                    | 字段                           | 实际写法                                                                   | 判定                            |
|-----------------------|------------------------------|--------------------------------------------------------------------------|---------------------------------|
| market_feasibility.md | 证据摘要 → 竞争格局速写         | “L1 竞品包括Aesop、Weleda、Neal's Yard Remedies等，以其品牌知名度及市场信任度来衡量。” | 违规：既无 URL 也无 “证据不足” |

3. 与 brief 不符或无出处的事实清单

| 类别   | 文件                    | 报告里的说法                                                        | brief 里的实际内容                                                          | 判定                    |
|------|-----------------------|------------------------------------------------------------------|-------------------------------------------------------------------------|-----------------------|
| 推断类 | market_feasibility.md | 核心叙事基于东方草本…符合目标市场对天然护肤的高需求（来源于Brief）            | brief 只说目标受众“有 clean/natural/botanical 习惯”，并未说“高需求”                 | 推断超出原文                |
| 推断类 | market_feasibility.md | 团队具有国际背景和研发经验，可加强品牌在新市场的信任度                            | brief 提到团队“有欧洲市场相关经历”，但未直接得出“可加强信任度”                         | 推断超出原文                |

4. 未填模板占位符清单  
- 经检视，无出现 `N/A`、空单元格等典型模板占位符。

5. 门槛表状态值违规清单  
- 经核对，只出现「规则已核实」「品牌侧未知」「待验证市场假设」，均为允许值，无违规。

6. 必须修正（阻塞上线）

| 问题                                                         | 文件／节                                    | 违反规则                    | 应该怎么改                                                      |
|------------------------------------------------------------|-----------------------------------------|---------------------------|-------------------------------------------------------------|
| 竞争格局速写没有任何 URL 或 “证据不足” 标注                        | market_feasibility.md → 证据摘要 → 竞争格局速写 | 规则27：标注“规则已核实”行必须有 URL；证据摘要表每行须 URL   | 要么补具体来源 URL，要么标“证据不足”                                |
| 使用品牌首页作为品类可见度证据（True Botanicals、Raven Botanicals、Cult Beauty、Space NK） | market_feasibility.md & market_expansion.md   | 禁止机构首页当数据来源             | 换成具体商品/报告/目录页 URL，或标“证据不足”                         |
| 将“合规要求，如任命负责人”列为“品牌特有风险”                        | market_feasibility.md → 最大风险 Top3       | 行业标配合规不得当品牌特有洞察或否决理由 | 将其归类为行业标配，不列入品牌特有风险；风险表中可保留但类型改为“行业标配” |

7. 建议优化（不阻塞，但值得改）
- “团队…可加强信任度”此类推断建议改为“基于团队背景，可假设有助于信任度（待调研）”并附 brief 对应原文。
- 证据摘要中“用户与信任”可拆分成具体第三方报道或论坛舆论链接，提升 A/B 级别判断精度。

8. 上线前检查清单  
[ ] 无 example.com / test.com / placeholder.com  
[ ] 无机构首页当数据证据（已调整 True Botanicals、Raven、Cult Beauty、Space NK）  
[ ] 商品页均为目标市场本地站点的单品详情页  
[ ] 参考文献表无未填占位符  
[ ] 门槛表状态值合法且“依据”列均有 URL 或明确“证据不足”  
[ ] 市场份额、舆论口碑等字段无“既无 URL 也无证据不足”的情况  
[ ] 报告中声明来自 brief 的事实均能在 brief 中找到；推断超出 brief 的已改写或加注  
[ ] 无行业标配合规被当成品牌特有否决理由  
[ ] 品牌表达跨文件一致  

9. 交叉一致性自查  
- 同一 URL 在不同表格中的判定一致  
- 检查清单的勾选与阻塞问题一致  
- “已写证据不足”前必须过数字关，含数字者务必补 URL  

以上问题需在上线前全部修正。