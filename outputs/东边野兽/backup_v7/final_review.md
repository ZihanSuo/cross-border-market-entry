## 逐 URL 核查表

| 文件/节点                                     | URL                                                                                                  | 类型              | 结论                         |
|---------------------------------------------|------------------------------------------------------------------------------------------------------|------------------|------------------------------|
| 品类与文化接受度 → UK草本产品认知度          | https://weleda.co.uk                                                                                 | 机构首页          | 首页证据，需要换成具体页面   |
| 品类与文化接受度 → Clean beauty 市场份额      | https://www.mintel.com/insights/beauty-and-personal-care/conscious-cosmetics-the-rise-of-clean-beauty | 正常              | 相关                         |
| 进入门槛清单 → 英国市场化妆品法规             | https://submit.cosmetic-product-notifications.service.gov.uk/                                        | 正常              | 相关                         |
| 进入门槛清单 → UK REACH注册                   | https://www.hse.gov.uk/reach/about.htm                                                               | 正常              | 相关                         |
| 进入门槛清单 → 宣称合规                       | https://www.ctpa.org.uk/resources-claims/#:~:text=Both%20the%20UK%20and%20EU,that%20they%20do%20not%20have%22. | 正常          | 相关                         |
| 证据摘要 → Clean beauty 正增长               | https://www.mintel.com/insights/beauty-and-personal-care/conscious-cosmetics-the-rise-of-clean-beauty | 正常              | 相关                         |
| 证据摘要 → UK草本产品认知度                   | https://weleda.co.uk                                                                                 | 机构首页          | 首页证据，需要换成具体页面   |
| 证据摘要 → 清洁产品偏好增长                   | https://www.fortunebusinessinsights.com/clean-beauty-market-111332                                   | 正常              | 相关                         |
| 可行性评分表 → 合规可完成性依据               | https://submit.cosmetic-product-notifications.service.gov.uk/                                        | 正常              | 相关                         |
| 可行性评分表 → 渠道可达依据                   | https://www.mintel.com/insights/beauty-and-personal-care/conscious-cosmetics-the-rise-of-clean-beauty | 正常              | 相关                         |
| 路径对比表 → DTC独立站法规依据               | https://submit.cosmetic-product-notifications.service.gov.uk/                                        | 正常              | 相关                         |
| 路径对比表 → YanLab London 文章              | https://beautymatter.com/articles/partner-season-ii-c-beauty-brands-yanlab-london                    | 正常              | 相关                         |
| 路径对比表 → Cult Beauty 官方                 | https://www.cultbeauty.co.uk                                                                         | 机构首页          | 首页证据，需要换成具体页面   |
| Battlecard — Aesop                           | https://www.aesop.com/uk/p/body/aura-restorative-face-cream/                                         | 正常              | 相关                         |
| Battlecard — Weleda                          | https://www.weleda.com/products/skin-food                                                           | 正常              | 相关                         |
| Battlecard — Pai Skincare                    | https://www.paiskincare.com/products/camellia-rose-gentle-hydrating-cleanser                         | 正常              | 相关                         |

## 未填模板占位符清单

- 经检查，上游所有表格和参考文献中未发现 `N/A | N/A` 或连续空单元格等占位符。

## 门槛表状态值违规清单

- 进入门槛清单中所有“状态”均为“规则已核实”，符合允许值（规则已核实 / 品牌侧未完成/未知 / 待验证（市场假设） / 红线），未发现违规。

## 必须修正（阻塞上线）

1. 问题：UK草本产品认知度使用 Weleda 首页作为证据  
   出现位置：决策备忘录 → 品类与文化接受度 → 证据摘要（“UK草本产品认知度”）  
   违反规则：机构首页≠具体产品/报告页面，不符合“禁止机构首页当数据证据”  
   应改为：替换为 Weleda 上明确展示草本护肤类产品的具体商品页 URL

2. 问题：Cult Beauty 路径对比中使用官网首页作为证据  
   出现位置：决策备忘录 → 路径对比表 → “选择本地化电商平台如Cult Beauty进行入驻”  
   违反规则：机构首页≠证据，应引用具体平台中草本/clean beauty 商品页  
   应改为：替换为 Cult Beauty 上至少一个相关草本护肤产品的具体商品页 URL

3. 问题：品牌背景中“东边野兽成立于2021年”未经引用  
   出现位置：决策备忘录 → 品牌—市场匹配 → 品牌背景  
   违反规则：数字/事实必须有可点击来源，单写年份无出处属于“无证据不得当事实”  
   应改为：附上 herbeast.world 或其他公开来源的具体页面链接，并注明来源

## 建议优化（不阻塞，但值得改）

- 建议在“消费者对清洁产品偏好增长”补充更高等级（A 级）的公开研究链接，提升证据信度。  
- 可行性评分表中“用户资料”可考虑补充实际 URL（如官网 About 页）增强可追溯性。  
- 品牌—市场匹配中提及 JOYCE Beauty 入驻，可增加 ELLE 中国报道链接作为二次佐证。  
- 进入门槛清单中 CTPA 链接包含复杂锚点，建议简化为顶层声明页或明确参数后的静态页面。

## 上线前检查清单

- [x] 无 example.com / test.com / placeholder.com 等占位域名  
- [ ] 无机构首页当数据证据  
- [x] 参考文献表无未填占位符  
- [x] 门槛表状态值合法  
- [x] 无行业标配合规被当成品牌特有否决理由  
- [ ] 品牌表达跨文件一致（成立年份需统一并引用）