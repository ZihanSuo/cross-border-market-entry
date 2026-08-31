以下为对上游三份文件（market_feasibility.md、market_expansion.md、competitor_battlecard.md）做的“逐条机械核对”结果。

## 1. 逐 URL 核查表
（去重后共 19 条）

| 文件                            | URL                                                                                                        | 类型                  | 结论                              |
|---------------------------------|------------------------------------------------------------------------------------------------------------|-----------------------|-----------------------------------|
| market_feasibility.md           | https://www.grandviewresearch.com/horizon/outlook/clean-beauty-market/uk                                    | 正常                  | 相关—支持“2025年规模4.68亿英镑、2033年16.57亿英镑” |
| market_feasibility.md           | https://truebotanicals.com/                                                                                | 首页证据              | 首页证据，需要换成具体产品页       |
| market_feasibility.md           | https://ravenbotanicals.com/                                                                               | 首页证据              | 首页证据，需要换成具体产品页       |
| market_feasibility.md           | https://www.mintel.com/insights/beauty-and-personal-care/conscious-cosmetics-the-rise-of-clean-beauty/      | 正常                  | 相关—支持 clean beauty 兴起        |
| market_feasibility.md           | https://www.gov.uk/guidance/making-cosmetic-products-available-to-consumers-in-great-britain               | 正常                  | 相关—支持 RP 任命要求             |
| market_feasibility.md           | https://www.biorius.com/cosmetic-regulations/uk-responsible-person/                                         | 正常                  | 相关—支持 UK REACH 注册解释       |
| market_feasibility.md           | https://submit.cosmetic-product-notifications.service.gov.uk/                                               | 正常                  | 相关—支持“任命本地责任人/代理”    |
| market_feasibility.md           | https://www.ecosistant.eu/en/the-responsible-person-role-under-the-cosmetics-regulation-1223-2009/         | 正常                  | 相关—支持标签与宣称合规            |
| market_expansion.md             | https://www.herbeast.world/about                                                                           | 正常                  | 相关—支持“已有英文本地化尝试”      |
| market_expansion.md             | https://www.cultbeauty.co.uk/                                                                              | 首页证据              | 首页证据，需要换成目标品类具体页   |
| market_expansion.md             | https://www.spacenk.com/                                                                                   | 首页证据              | 首页证据，需要换成目标品类具体页   |
| competitor_battlecard.md        | https://www.aesop.com/uk/p/body/parley-seed-facial-hydrating-cream/                                         | 正常                  | 相关—支持 Aesop 产品页            |
| competitor_battlecard.md        | https://www.cosmopolitan.com/uk/beauty-hair/news/a29237191/aesop-skincare-reviews/                          | 正常                  | 相关—支持“Aesop 用户评价极高”      |
| competitor_battlecard.md        | https://www.weleda.co.uk/product/skin-food-30ml                                                             | 正常                  | 相关—支持 Weleda Skin Food         |
| competitor_battlecard.md        | https://www.goodhousekeeping.com/uk/product-reviews/healthandbeauty/g35008149/weleda-skincare-reviews/       | 正常                  | 相关—支持“Weleda 用户反馈普遍积极” |
| competitor_battlecard.md        | https://www.nealsyardremedies.com/frankincense-hydrating-cream-50g                                          | 正常                  | 相关—支持 Neal's Yard 产品页      |
| competitor_battlecard.md        | https://www.thesiteguide.com/blog/neals-yard-remedies-review/                                               | 正常                  | 相关—支持“Neal's Yard 用户反馈”   |
| competitor_battlecard.md        | https://www.paiskincare.com/products/chamomile-rosehip-calming-day-cream                                    | 正常                  | 相关—支持 Pai 产品页               |
| competitor_battlecard.md        | https://www.huffpost.com/entry/pai-skincare-review_n_78d5c3c2e4b0780f5ea63257                               | 正常                  | 相关—支持“Pai 用户好评”           |

## 2. 应有证据却缺失的位置（反向核查）
（必须有 URL 或明确写“证据不足”，否则违规）

| 文件                         | 字段                                    | 实际写法                              | 判定                                |
|------------------------------|-----------------------------------------|---------------------------------------|-------------------------------------|
| market_feasibility.md        | 可行性评分表–“渠道可达”                | 证据不足（得分3）                     | 违规：得分含数字但无 URL            |
| market_feasibility.md        | 可行性评分表–“竞争强度”                | 证据不足（得分4）                     | 违规：得分含数字但无 URL            |
| market_feasibility.md        | 可行性评分表–“品牌资产匹配”            | 证据不足（得分4）                     | 违规：得分含数字但无 URL            |
| competitor_battlecard.md     | Aesop–“目标市场本地市场份额/排名”      | “排名前列，具体市场份额证据不足”     | 违规：排名定性无 URL 亦无“证据不足” |

## 3. 与 brief 不符或无出处的事实清单

| 文件                      | 报告里的说法                                  | brief 里的实际内容                            | 判定 |
|---------------------------|-----------------------------------------------|-----------------------------------------------|------|
| —                         | —                                             | —                                             | —    |

（——三份文件中并未引用 brief 外的数字/渠道/人群断言，未发现“brief 中不存在”的情形）

## 4. 未填模板占位符清单

三份文件中未见 `N/A`、`TBD`、空单元格等占位符。

## 5. 门槛表状态值违规清单

| 文件                    | 违规写法                          | 应改为               |
|-------------------------|-----------------------------------|----------------------|
| market_feasibility.md   | 风险 Top3 中“合规要求，如任命负责人的必要性及相关法规的遵循”被当作“最大风险” | 不可将行业标配当品牌特有风险，应移入附录或备注，不列为风险 |

## 6. 必须修正（阻塞上线）

1. market_feasibility.md 可行性评分表中三行（渠道可达/竞争强度/品牌资产匹配）的“证据不足”需补 URL。  
2. competitor_battlecard.md Aesop 条目中“排名前列”缺来源且未标“证据不足”，须补 URL 或改为“证据不足”。  
3. market_expansion.md 入驻 Cult Beauty 和 Space NK 两行仅给首页 URL，需换为目标品类或具体产品/分类页面。  
4. market_feasibility.md Top 3 风险中不应将“合规要求”列为品牌特有风险，需移出风险列表或改为“行业标配——已核实”附录条目。  

## 7. 建议优化（不阻塞，但值得改）

- market_feasibility.md 品类与文化接受度节中的 True Botanicals 与 Raven Botanicals 均用首页，建议改为具体产品或零售页。  
- 可行性评分表若能加“用户访谈”或“三方数据”URL，整体置信度更高。  
- competitor_battlecard.md 除市场份额/排名，可加增长率或在售 SKU 数量以丰富竞品洞察。  

## 8. 上线前检查清单

- [ ] 无 example.com / test.com 等占位域名  
- [ ] 无机构/品牌首页做为数据证据  
- [ ] 商品页均指向目标市场本地站点的单品详情页  
- [ ] 参考文献表无任何占位符  
- [ ] 门槛表状态值仅为四种合法值；“依据”列均有 URL 或“证据不足”  
- [ ] 市场份额/舆论口碑等字段无“既无 URL 也无证据不足”  
- [ ] 报告引用 brief 的事实均可在 brief 中找到；分歧处已注明来源  
- [ ] 无行业标配合规被当作品牌特有否决理由  
- [ ] 品牌表达（名称、定位、团队）跨文件保持一致  

## 9. 交叉一致性自查

1. 各处同一 URL 判定一致。  
2. 拥有阻塞问题的检查项不再打勾。  
3. “已写证据不足”位置均先验数字关；含数字处要求补 URL，不可豁免。