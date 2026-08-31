以下是对三份上游产出（market_feasibility.md、market_expansion.md、competitor_battlecard.md）的机械化逐条核对，严格按照 `source_rules.md` 中的硬规则。

一、逐 URL 核查表（去重）  
说明：类型判定时，如果只是首页/平台首页却被当数据证据，标「首页证据，需要换」；如果 URL 与旁边结论内容不匹配，标「证据错配」；否则标「相关」。

| 文件                     | URL                                                                                                                    | 类型                   | 结论     |
|--------------------------|------------------------------------------------------------------------------------------------------------------------|------------------------|----------|
| market_feasibility.md    | https://www.custommarketinsights.com/report/thailand-beauty-and-personal-care-market/                                  | 正常                   | 相关     |
| market_feasibility.md    | https://www.statista.com/outlook/cmo/beauty-personal-care/thailand/#:~:text=Trends%20in%20the%20market%3A%20In,…       | 正常                   | 相关     |
| market_feasibility.md    | https://www.ice.it/en/sites/default/files/inline-files/beauty-and-personal-care-industry-2024-.pdf                      | 证据错配               | Market Reports 未必支持“本土标杆品牌Mistine/Cathy Doll主导” |
| market_feasibility.md    | http://www.fda.moph.go.th                                                                                                | 首页证据，需要换       | 需指向具体备案页面      |
| market_feasibility.md    | https://www.asean.org/                                                                                                 | 首页证据，需要换       | 需指向ASEAN Cosmetic Directive具体章节 |
| market_feasibility.md    | https://www.facebook.com/flowerknowsthailand/                                                                           | 首页证据，需要换       | 品牌主页，不能证明电商在售 |
| market_feasibility.md    | https://www.statista.com/topics/7578/beauty-and-personal-care-in-thailand/?srsltid=…                                   | 正常                   | 相关     |
| market_feasibility.md    | https://www.cosmeticsdesign-asia.com/Article/2024/06/20/flower-knows-sees-international-expansion-as-a-major-focus/    | 正常                   | 相关     |
| market_expansion.md      | https://shopee.co.th                                                                                                   | 首页证据，需要换       | 需具体商品页或店铺页面 |
| market_expansion.md      | https://www.lazada.co.th                                                                                               | 首页证据，需要换       | 需具体商品页或店铺页面 |
| market_expansion.md      | https://www.konvy.com                                                                                                  | 首页证据，需要换       | 需具体商品页或品牌店铺页 |
| market_expansion.md      | https://instagram.com                                                                                                  | 首页证据，需要换       | 平台首页，和具体推广无关 |
| competitor_battlecard.md | https://www.mistine.co.th/eyeshadow                                                                                     | 证据错配               | 应链接到具体SKU详情页     |
| competitor_battlecard.md | https://www.cathydoll.com/th/                                                                                          | 首页证据，需要换       | 品牌/分类页，非产品详情页 |
| competitor_battlecard.md | https://www.srichand.com/                                                                                              | 首页证据，需要换       | 品牌首页，非产品详情页   |
| competitor_battlecard.md | https://www.facebook.com/mistine                                                                                        | 首页证据，需要换       | 品牌主页，不是舆论内容页 |
| competitor_battlecard.md | https://www.instagram.com/cathydolland                                                                                  | 首页证据，需要换       | 品牌主页，不是舆论内容页 |
| competitor_battlecard.md | https://twitter.com/srichand                                                                                            | 首页证据，需要换       | 品牌主页，不是舆论内容页 |

二、扫描参考文献表/证据摘要表占位符  
仅发现一处空单元格式占位，需补充或删除：

| 文件                  | 章节              | 原文片段                    |
|-----------------------|-------------------|-----------------------------|
| market_feasibility.md | 证据摘要 → 用户与信任 | “证据不足（需调查中国品牌的市场信任度）”后，缺失 URL/级别/置信度等列 |

三、门槛清单状态值违规  
上游使用了三种状态，其中“待验证市场假设”不完全匹配硬规则要求的“待验证（市场假设）”。

| 文件                  | 违规写法           | 应改为                 |
|-----------------------|--------------------|------------------------|
| market_feasibility.md | 待验证市场假设     | 待验证（市场假设）     |

四、行业标配合规未当品牌特有原因  
- 未发现把行业标配（备案、本地代理）当作“品牌特有否决理由”或“主要否决点”。

五、品牌表达一致性  
- 三份文档中“花知晓 / Flower Knows”成立年份（2016）、定位描述一致，无矛盾。

六、夸大/绝对化用词  
- 未发现“最”“第一”“100%”等绝对化断言或无 URL 的偏见性结论。

七、必须补充/修正的“应有 URL 但缺失”字段  
按硬规则 7，以下字段要么有数字要么必须有 URL，否则违规：

| 文件                     | 字段                           | 实际写法                                | 判定                                             |
|--------------------------|--------------------------------|-----------------------------------------|--------------------------------------------------|
| competitor_battlecard.md | Mistine 市场份额               | 约 25%（证据不足）                     | 违规：含数字无 URL                               |
| competitor_battlecard.md | Cathy Doll 市场份额            | 约 18%（证据不足）                     | 违规：含数字无 URL                               |
| competitor_battlecard.md | Srichand 市场份额              | 约 15%（证据不足）                     | 违规：含数字无 URL                               |
| competitor_battlecard.md | Mistine 公开舆论/口碑线索      | https://www.facebook.com/mistine        | 违规：URL 指向品牌主页，非第三方具体内容页       |
| competitor_battlecard.md | Cathy Doll 公开舆论/口碑线索   | https://www.instagram.com/cathydolland  | 违规：URL 指向品牌主页，非第三方具体内容页       |
| competitor_battlecard.md | Srichand 公开舆论/口碑线索     | https://twitter.com/srichand            | 违规：URL 指向品牌主页，非第三方具体内容页       |

八、与 brief 不符或无出处的事实  
- 未发现引用 brief 中不存在的“数据、数字或年份”。唯一新增的“正面反馈率超过 60%”为验证标准，属于内部执行计划，无需 brief 出处校对。

九、未填模板占位符清单  
- 仅“市场可行性研究 → 证据摘要 → 用户与信任”一行单元格未完整填写。

十、必须修正（阻塞上线）  
1. 竞品份额（Mistine/Cathy Doll/Srichand）都含具体数字且无有效来源 URL。  
   → 删除或替换为确切链接或改为定性“无数据”/“待验证”。  
2. 竞品“公开舆论/口碑”引用的均为品牌自营主页，需更换为第三方帖文/评论串/测评文章 URL，或改标“证据不足”。  
3. 竞品“商品页 URL”多为品牌分类页或首页，需替换为目标市场本地站点的单品**详情页** URL。  
4. ASEAN Cosmetic Directive、Thai FDA 均指向机构首页，需链接到具体法规/备案指南页面。  
5. Shopee/Lazada/KONVY/Instagram 都只是平台首页，不可当“本品牌可售”证据，需补充具体 Flower Knows 在泰国站点的商品详情页或官方店铺链接。  
6. ICE PDF 用于证明“本土品牌主导市场”关联度不足，需更换或标“待验证”。

十一、建议优化（非阻塞）  
- “待验证市场假设”状态建议统一为“待验证（市场假设）”。  
- 在可行性评分表的“渠道可达”一栏，区分 KONVY vs Beautrium；分别提供各自具体渠道页面。  
- 在“90 天验证动作”中，若使用量化标准（如 60%+），可注明数据来源和方法。

十二、上线前检查清单（务必全部核对并修正阻塞项后打勾）  
- [ ] 无 example.com / 占位域名  
- [ ] 无机构首页/品牌首页当数据证据  
- [ ] 商品页均为目标市场本地站点的单品详情页  
- [ ] 参考文献表无未填占位符  
- [ ] 门槛表状态值合法且“依据”列均有 URL 或明确“证据不足”  
- [ ] 市场份额、舆论口碑字段无“既无 URL 也无证据不足”的情况  
- [ ] 报告中声称来自 brief 的事实均能在 brief 里找到；有分歧的事实已注明出处  
- [ ] 无行业标配合规被当成品牌特有否决理由  
- [ ] 品牌表达跨文件一致