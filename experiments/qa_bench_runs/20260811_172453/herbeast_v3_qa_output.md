以下为对三份上游产出（market_feasibility.md、market_expansion.md、competitor_battlecard.md）的逐条机械核对结果。

一、逐 URL 核查表  
（类型分为：占位域名、机构/平台首页证据、他国/非本地站点、正常；结论为“通过”或“不通过”）

| 文件                       | URL                                                                                       | 类型                 | 结论     |
|----------------------------|-------------------------------------------------------------------------------------------|----------------------|----------|
| market_feasibility.md      | https://www.gov.uk/government/publications/cosmetics-regulation                           | 正常（gov.uk 规定页） | 通过     |
| market_feasibility.md      | https://www.gov.uk/guidance/what-you-need-to-know-about-reach                             | 正常（gov.uk 指南）   | 通过     |
| market_feasibility.md      | https://www.gov.uk/guidance/guide-to-labelling-and-packaging-cosmetics                     | 正常（gov.uk 指南）   | 通过     |
| market_feasibility.md      | https://www.statista.com/                                                                  | 机构首页证据          | 不通过   |
| market_feasibility.md      | https://www.mintel.com/                                                                    | 机构首页证据          | 不通过   |
| market_expansion.md        | https://www.example.com                                                                    | 占位域名              | 不通过   |
| market_expansion.md        | https://www.cultbeauty.co.uk                                                                | 机构首页证据          | 不通过   |
| market_expansion.md        | https://www.spacenk.com                                                                    | 机构首页证据          | 不通过   |
| market_expansion.md        | https://www.example.com                                                                    | 占位域名              | 不通过   |
| competitor_battlecard.md    | https://www.aesop.com/skin-care/moisturiser/mandarin-facial-hydrating-cream/              | 正常（单品详情页）    | 通过     |
| competitor_battlecard.md    | https://www.aesop.com/uk/skin-care/                                                        | 正常（渠道页）        | 通过     |
| competitor_battlecard.md    | https://www.weleda.com/product/skin-food-original-ultra-rich-cream-g009398                 | 正常（单品详情页）    | 通过     |
| competitor_battlecard.md    | https://www.weleda.com/category/face-2                                                     | 正常（品类页）        | 通过     |
| competitor_battlecard.md    | https://us.nealsyardremedies.com/collections/skincare/products/frankincense-facial-oil    | 他国/非本地站点       | 不通过   |
| competitor_battlecard.md    | https://www.nealsyardremedies.com/                                                         | 机构首页证据          | 不通过   |
| competitor_battlecard.md    | https://www.aesop.com/skin-care/                                                           | 品类首页／证据错配    | 不通过   |

二、模板占位符扫描  
仅在 market_feasibility.md 的“参考文献”一节发现 N/A 占位：  
- 文件：market_feasibility.md，章节：参考文献，原文片段：“品牌与市场信息 | N/A | N/A | A/B/C | 相关出具者需验证具体文献。”  

三、门槛清单状态值违规  
market_feasibility.md 中“进入门槛清单”状态列：  
- 第4行“待验证市场假设”→ 应为“待验证（市场假设）”（缺失括号）。  

四、行业标配合规误用校验  
三份文件中未将行业标配合规当作“品牌特有否决理由”，符合要求。  

五、品牌表达一致性  
三份文件未出现对“东边野兽 / Herbeast”名称、定位或创始人背景的自相矛盾表述，通过。  

六、夸大／绝对化用词与无证据偏见  
未发现“最”“第一”“100%”等绝对化表述；也无未提供 URL 即判“中国品牌不被信任”之类结论，通过。  

七、反向核查：应有证据却缺失  

| 文件                     | 字段                                      | 实际写法               | 判定                                    |
|--------------------------|-------------------------------------------|------------------------|-----------------------------------------|
| competitor_battlecard.md  | 竞品市场份额/增长率/排名                 | （未提供）             | 违规：既无 URL 也无“证据不足”          |
| competitor_battlecard.md  | 竞品公开舆论/口碑线索                    | （未提供）             | 违规：既无 URL 也无“证据不足”          |
| competitor_battlecard.md  | Neal's Yard Remedies 商品页 URL 本地化   | 使用 us.nealsyard...域 | 证据错配（非英国本地站点）             |
| market_feasibility.md     | （—）                                    | —                      | —                                       |
| market_expansion.md       | （—）                                    | —                      | —                                       |

八、与 brief 不符或无出处事实  
三份文件中，无处声称“来自 brief”而 brief 不含的具体数字或结论。  

九、必须修正（阻塞上线）  

1. 问题：引用 Statista、Mintel 时只给首页 URL。  
   出现：market_feasibility.md → 证据摘要“市场与趋势”两行  
   违反：机构首页≠具体报告，数字必须对应具体链接（硬规则1、2、5）。  
   应改：补具体报告页面 URL，或删掉对应数字。  

2. 问题：market_expansion.md 多处使用 example.com。  
   出现：DTC Market Report、Local Retailer Partnerships  
   违反：占位域名一律不通过。  
   应改：补真实报告或二手来源链接。  

3. 问题：Cult Beauty / Space NK 链接仅指向平台首页。  
   出现：market_expansion.md “直接相关依据 URL”列  
   违反：平台首页≠品牌入驻列表页（证据错配）。  
   应改：指向具体品牌列表页或案例报道。  

4. 问题：竞品分析中缺失市场份额/增长率/排名且无“证据不足”标注。  
   出现：competitor_battlecard.md  
   违反：竞品分析要求6，缺字段且无声明。  
   应改：添加来源 URL 和数据，或注明“证据不足”。  

5. 问题：竞品公开舆论/口碑线索未填且无“证据不足”。  
   出现：competitor_battlecard.md  
   违反：需明确有 URL 或“证据不足”。  
   应改：补具体帖子/测评链接，或写“未找到一手公开讨论”。  

6. 问题：Neal's Yard Remedies 商品页用 US 域，不是 UK 本地站点。  
   出现：competitor_battlecard.md  
   违反：商品页 URL 必须为目标市场本地站点（硬规则3/4）。  
   应改：替换为英国站点的单品详情页 URL。  

7. 问题：门槛表第4行状态“待验证市场假设”格式不符。  
   出现：market_feasibility.md  
   违反：状态值只能是“待验证（市场假设）”。  
   应改：加括号，改为“待验证（市场假设）”。  

8. 问题：可行性评分表“竞争强度”依据列写“竞品资料”，不符格式要求。  
   出现：market_feasibility.md 可行性评分表  
   违反：“依据”列只能填 URL、“用户资料”或“证据不足”。  
   应改：若来源 brief，改为“用户资料”；如二手来源，改为具体 URL；否则“证据不足”。  

十、上线前检查清单  

- [ ] 无 example.com / 占位域名  
- [ ] 无机构首页/品牌首页当数据证据  
- [ ] 商品页均为目标市场本地站点的单品详情页  
- [ ] 参考文献表无 N/A 或未填占位符  
- [ ] 门槛表状态值合法，且“规则已核实”行均有 URL  
- [ ] **竞品市场份额、舆论口碑等字段无“既无 URL 也无证据不足”**  
- [ ] **报告引用 brief 的事实均可在 brief 中找到；分歧处注明来源**  
- [ ] 无行业标配合规被当成品牌特有否决理由  
- [ ] 品牌表达跨文件一致  

以上问题全部整改后，方可上线。