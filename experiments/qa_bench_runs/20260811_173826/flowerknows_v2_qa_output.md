以下是针对三份上游产出（market_feasibility.md、market_expansion.md、competitor_battlecard.md）的机械化审校，逐条列出所有问题及分类。

1. 逐 URL 核查表  
文件 | URL | 类型 | 结论  
---|---|---|---  
market_feasibility.md | https://www.custommarketinsights.com/report/thailand-beauty-and-personal-care-market/ | 正常 | 相关  
market_feasibility.md | https://www.statista.com/outlook/cmo/beauty-personal-care/thailand/#:~:text=Trends… | 正常 | 相关  
market_feasibility.md | https://www.statista.com/topics/7578/beauty-and-personal-care-in-thailand/?srsltid=… | 正常 | 相关  
market_feasibility.md | https://www.ice.it/en/sites/default/files/inline-files/beauty-and-personal-care-industry-2024-.pdf | 正常 | 相关  
market_feasibility.md | http://www.fda.moph.go.th | 首页证据 | 需换成具体备案/指南页面  
market_feasibility.md | https://www.asean.org/ | 首页证据 | 需换成具体 ASEAN Cosmetic Directive 文档  
market_feasibility.md | https://www.facebook.com/flowerknowsthailand/ | 证据错配 | Facebook 主页无法证明电商占有位  
market_expansion.md      | https://shopee.co.th                          | 首页证据 | 需换成示例商品页或店铺后台截图  
market_expansion.md      | https://www.lazada.co.th                     | 首页证据 | 同上  
market_expansion.md      | https://www.konvy.com                        | 首页证据 | 需换成 Flower Knows 在 KONVY 的具体商品页  
market_expansion.md      | https://instagram.com                        | 首页证据 | 需换成具体影响者帖子  
competitor_battlecard.md | https://www.mistine.co.th/eyeshadow         | 正常 | 相关  
competitor_battlecard.md | https://www.cathydoll.com/th/               | 首页证据 | 需换成具体产品详情页  
competitor_battlecard.md | https://www.srichand.com/                   | 首页证据 | 需换成具体产品详情页  
competitor_battlecard.md | https://www.facebook.com/mistine            | 首页证据/证据错配 | 主页不能当口碑线索  
competitor_battlecard.md | https://www.instagram.com/cathydolland      | 首页证据/证据错配 | 同上  
competitor_battlecard.md | https://twitter.com/srichand                | 首页证据/证据错配 | 同上  

2. 应有证据却缺失的位置（反向校验）  
文件 | 字段 | 实际写法 | 判定  
---|---|---|---  
market_feasibility.md | 品牌—市场匹配·现有零售线索 | “Flower Knows 产品目前在泰国 KONVY 和 Beautrium 有售（未确认具体销售状况）” | 违规：既无 URL 也无“证据不足”  
competitor_battlecard.md | Mistine 市场份额 | “约 25%（证据不足）” | 违规：含数字必须附 URL  
competitor_battlecard.md | Cathy Doll 市场份额 | “约 18%（证据不足）” | 同上  
competitor_battlecard.md | Srichand 市场份额 | “约 15%（证据不足）” | 同上  
competitor_battlecard.md | Mistine 公开舆论/口碑线索 | URL 是主页 | 违规：需要具体帖子或第三方测评链接  
competitor_battlecard.md | Cathy Doll 公开舆论/口碑线索 | URL 是主页 | 同上  
competitor_battlecard.md | Srichand 公开舆论/口碑线索 | URL 是主页 | 同上  
competitor_battlecard.md | Cathy Doll 商品页 URL | URL 是主页 | 违规：需单品详情页  
competitor_battlecard.md | Srichand 商品页 URL | URL 是主页 | 同上  
market_expansion.md      | 路径对比表·Shopee/Lazada | URL 是平台首页 | 违规：需具体商品或店铺后台截图  
market_expansion.md      | 路径对比表·KONVY/Beautrium | URL 是主页 | 同上  
market_expansion.md      | 路径对比表·Influencer | URL 是 instagram.com | 违规：需具体帖子链接  

3. 与 brief 不符或无出处的事实清单  
类别 | 文件 | 报告说法 | brief 原文 | 判定  
---|---|---|---|---  
推断 | market_feasibility.md | “表明已按计划扩展至泰国市场” | brief 仅说“名单里布局”，未说已进入 | 推断超出原文  

4. 未填模板占位符清单  
— 无 N/A、空单元格等占位符。

5. 门槛表状态值违规清单  
文件 | 违规写法 | 应改为  
---|---|---  
market_feasibility.md | “待验证市场假设” | “待验证（市场假设）”  

6. 必须修正（阻塞上线）  
问题 | 文件/节 | 原因 | 应改  
---|---|---|---  
Thai FDA 链接用的是首页 | market_feasibility.md·进入门槛清单 | 官网首页不能证明具体备案要求 | 换成 Thai FDA 关于化妆品备案的具体文档 URL  
ASEAN 引用用的是首页 | 同上 | 同上 | 链接 ASEAN Cosmetic Directive 原文页  
Flower Knows 泰国线索无 URL | market_feasibility.md·品牌—市场匹配 | 需来源证明 | 补充 KONVY/Beautrium 具体商品或门店页 URL  
Shopee/Lazada/Lazada URL 均为首页 | market_expansion.md·路径对比表 | 仅首页无效 | 补具体商品页或店铺后台截图  
KONVY URL 为主页 | market_expansion.md·路径对比表 | 主页不能证明合作 | 补 Flower Knows 在 KONVY 的商品详情 URL  
影响者路径用 instagram.com | 同上 | 主页无实证 | 补具体帖文链接  
Cathy Doll、Srichand 商品页 URL 均为首页 | competitor_battlecard.md | 需单品详情 | 补各品牌对应单品详情页  
竞品舆论线索均为主页 | competitor_battlecard.md | 品牌主页≠公开舆论 | 补具体用户评论串或第三方测评文章  
竞品市场份额含数字无 URL | competitor_battlecard.md | 含具体数字必须附来源 | 补权威报告链接或移除数字  

7. 建议优化（非阻塞）  
- all homepage 链接可考虑替换为带 UTM 的直接商品页或 API 截图。  
- “待验证（市场假设）”括号一致性。  
- 补充“证据分级”标注 A/B 级别到所有引用。  

8. 上线前检查清单（阻塞项未满足时请勿打勾）  
[ ] 无 example.com 等占位域名  
[ ] 无机构/品牌首页当数据证据  
[ ] 商品页均为目标市场本地站点的单品详情页  
[ ] 参考文献表无占位符  
[ ] 门槛表状态值合法且“依据”列均有具体 URL 或“证据不足”  
[ ] 市场份额、舆论口碑等字段无“既无 URL 也无证据不足”的情况  
[ ] 报告中声称来自 brief 的事实均在 brief 可查；无推断超范围  
[ ] 无行业标配合规被当作品牌特有否决理由  
[ ] 品牌表达跨文件一致  

请按照上述“必须修正”逐条完成修改，确保所有硬规则完全合规后方可上线。