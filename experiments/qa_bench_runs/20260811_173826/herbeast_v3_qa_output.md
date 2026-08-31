以下为对三份上游产出（market_feasibility.md、market_expansion.md、competitor_battlecard.md）的逐条机械审校结果。

1. 逐 URL 核查表  
（去重后共 15 条）

| 文件                      | URL                                                                                                                     | 类型                              | 结论                                            |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------|-----------------------------------|-------------------------------------------------|
| market_feasibility.md     | https://www.gov.uk/government/publications/cosmetics-regulation                                                         | 正常                              | 与“RP 任命”结论匹配，有效                          |
| market_feasibility.md     | https://www.gov.uk/guidance/what-you-need-to-know-about-reach                                                            | 正常                              | 与“UK REACH合规”匹配                              |
| market_feasibility.md     | https://www.gov.uk/guidance/guide-to-labelling-and-packaging-cosmetics                                                  | 正常                              | 与“宣称合规”匹配                                  |
| market_feasibility.md     | https://www.statista.com/                                                                                                | 首页证据，需要换成具体报告或图表页 | 单写 statista.com 首页，无法定位“超 10 亿英镑”数据  |
| market_feasibility.md     | https://www.mintel.com/                                                                                                  | 首页证据，需要换成具体报告页       | 单写 mintel.com 首页，无法定位“35% 清洁美容认同”数据 |
| market_expansion.md       | https://www.example.com                                                                                                  | 占位域名／不通过                   | example.com 明显占位                                  |
| market_expansion.md       | https://www.cultbeauty.co.uk                                                                                             | 证据错配                          | 仅指向品牌列表首页，却用来支持“已有良好销售业绩”      |
| market_expansion.md       | https://www.spacenk.com                                                                                                  | 证据错配                          | 仅指向 Space NK 首页，却用来支持“渠道合作路径”        |
| market_expansion.md       | https://www.example.com                                                                                                  | 占位域名／不通过                   | 同上 example.com                                    |
| competitor_battlecard.md   | https://www.aesop.com/skin-care/moisturiser/mandarin-facial-hydrating-cream/                                            | 正常                              | 具体 SKU 详情页，与“代表 SKU”匹配                    |
| competitor_battlecard.md   | https://www.aesop.com/uk/skin-care/                                                                                      | 正常                              | UK 站点品类页，可作为“英国渠道线索”                   |
| competitor_battlecard.md   | https://www.weleda.com/product/skin-food-original-ultra-rich-cream-g009398                                               | 正常                              | 具体 SKU 详情页                                    |
| competitor_battlecard.md   | https://www.weleda.com/category/face-2                                                                                   | 正常                              | UK 站点品类页，可作为“英国渠道线索”                   |
| competitor_battlecard.md   | https://us.nealsyardremedies.com/collections/skincare/products/frankincense-facial-oil                                  | 他国站点                          | US 站点详情页，非 UK 本地站点                         |
| competitor_battlecard.md   | https://www.nealsyardremedies.com/                                                                                        | 首页证据，需要换成具体详情页       | 仅品牌首页，不能证明“英国渠道线索”                    |
| competitor_battlecard.md   | https://www.aesop.com/skin-care/                                                                                         | 证据错配                          | 仅是 Aesop 全站护肤分类页，却用作 Aesop 产品页证据     |

2. 应有证据却缺失的位置（反向核查）

| 文件                    | 字段                                     | 实际写法                          | 判定                                       |
|-------------------------|------------------------------------------|-----------------------------------|--------------------------------------------|
| competitor_battlecard.md | 每家竞品的市场份额/增长率/排名          | 未见任何相关数据或“证据不足”文字 | 违规：既无 URL 也无“证据不足”               |
| competitor_battlecard.md | 每家竞品的公开舆论/口碑线索             | 未提此字段                        | 违规：既无 URL 也无“证据不足”               |
| competitor_battlecard.md | Neal’s Yard Remedies 的商品页 URL      | 链向 US 站点，非 UK 详情          | 违规：需 UK 本地站点详情页                   |
| market_feasibility.md    | 可行性评分表→“合规可完成性”一行依据列   | 写“gov.uk”却无具体链接            | 违规：既无 URL 也非“证据不足”               |
| market_feasibility.md    | 可行性评分表→“竞争强度”一行依据列       | 写“竞品资料”无链接或说明         | 违规：既无 URL 也非“证据不足”               |

3. 与 brief 不符或无出处的事实清单

| 类别   | 文件                    | 报告里的说法                                            | brief 里实际内容                        | 判定                          |
|--------|-------------------------|--------------------------------------------------------|-----------------------------------------|-------------------------------|
| 事实   | market_feasibility.md   | “Clean Beauty 市场…预计到2024年将超出10亿英镑”         | brief 未提供该数字                      | brief 中不存在 / 需来源        |
| 事实   | market_feasibility.md   | “2022 年…有 35% 认同‘清洁美容’概念”                    | brief 未提供该数字                      | brief 中不存在 / 需来源        |
| 推断   | market_expansion.md     | “市场研究显示品牌受欢迎有潜力”                          | brief 未提及任何“品牌受欢迎”数据        | 推断超出原文                    |
| 分歧   | 无                      | —                                                      | —                                       | —                             |

4. 未填模板占位符清单

| 文件                  | 章节       | 原文片段                                               |
|-----------------------|------------|--------------------------------------------------------|
| market_feasibility.md | 参考文献   | “品牌与市场信息 | N/A | N/A | A/B/C | 相关出具者需验证具体文献。” |

5. 门槛表状态值违规清单

（无违规——状态值皆为四种合法值）

6. 必须修正（阻塞上线）

1) 占位域名  
   问题：market_expansion.md 中多处 `https://www.example.com`  
   违反规则：占位域名直接判「不通过」  
   改法：替换为真实报告或市场调研来源的具体链接；无链接时写“证据不足”。

2) 机构首页当数据来源  
   问题：market_feasibility.md 中 statista.com 和 mintel.com 均为首页  
   违反规则：首页 ≠ 具体数据页  
   改法：替换为具体报告/图表的深链，如 Statista 报告详情页，或若无法检索写“待验证”。

3) 竞品本地商品页不符  
   问题：Neal’s Yard Remedies 商品页指向 US 站点  
   违反规则：必须本地站点详情页  
   改法：改为 UK 站点对应 SKU 链接，或写“证据不足”。

4) 可行性评分表依据列缺链接  
   问题：合规可完成性 / 竞争强度 两行仅写文字无 URL  
   违反规则：标“规则已核实”行必须给 URL；评分表最后列也不能留空  
   改法：补充具体 gov.uk 页面链接；或若非 URL 来源，写“证据不足”。

5) 竞品分析缺必要字段  
   问题：competitor_battlecard.md 未给市场份额/排名和公开舆论线索字段  
   违反规则：competitor_analysis 要求给市场份额/增长率/排名和口碑线索；无则“证据不足”  
   改法：补充相应数据来源及链接，或在对应行写“证据不足”。

6) 参考文献占位符未填  
   问题：market_feasibility.md 参考文献一行留 `N/A | N/A`  
   违反规则：禁止空引用占位  
   改法：移除该行或补入正确文献信息。

7) 证据错配  
   - market_expansion.md 中 cultbeauty.co.uk、spacenk.com 均为平台首页/品牌列表页，却被当“直接相关依据”  
   改法：需提供支持“已有草本类销售”“目标用户集中”等论断的具体数据页或案例链接，否则写“证据不足”。

7.5 特别提醒：上面所有含“具体数字”（10亿英镑、35%）却无深链的，不能靠“写了数字也写了来源机构”来豁免，必须给具体 URL。

7.6 品牌自营账号主页无出现在本次产出中，无需额外处理。

8. 建议优化（非阻塞）

- market_expansion.md 路径对比中，“直接相关依据 URL”一栏改为多列：① 目标市场 DTC 渠道报告；② 典型案例链接，提升可验证度。  
- competitor_battlecard.md 可补“公开舆论/口碑”字段，如 Trustpilot/Reddit/英国社媒笔记帖链。  
- 在 market_feasibility.md “机会与风险”处加注“资料时效性风险（2024–2026）”。  
- 三份文件中对“草本成分”与“非低价定位”的描述，可统一成“Herbeast = 东方草本中高端定位”，避免同一要素措辞不一。

上线前检查清单（务必逐项确认）

- [ ] 无 example.com / 占位域名  
- [ ] 无机构首页/品牌首页当数据证据  
- [ ] 商品页均为 UK 本地站点单品详情页  
- [ ] 参考文献表无 N/A 或占位符  
- [ ] 门槛表状态值合法且「依据」列均有 URL 或“证据不足”  
- [ ] 无任何“市场份额/口碑”等字段既无 URL 也无“证据不足”  
- [ ] 报告中所有数字声明皆有深链支持  
- [ ] 无行业标配合规被当品牌特有否决理由  
- [ ] 品牌名、定位、成立年份等跨文件表述一致  

以上问题全部修正后，即可上线。