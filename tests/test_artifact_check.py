"""Unit tests for Depth V1 artifact floors."""

from __future__ import annotations

from pathlib import Path

from src.marketing_crew.artifact_check import (
    check_competitor_artifacts,
    check_feasibility_artifacts,
    render_artifact_reports,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_feasibility_floor_passes():
    text = (FIXTURES / "depth_feasibility_ok.md").read_text(encoding="utf-8")
    report = check_feasibility_artifacts(text)
    assert report.errors == [], [i.message for i in report.errors]


def test_feasibility_floor_fails_without_appendix():
    report = check_feasibility_artifacts("## 建议\n- 建议进入\n")
    assert any(i.code == "feas_missing_appendix" for i in report.errors)


def test_feasibility_floor_fails_with_one_channel_url():
    text = """## 硬证据清单
### 渠道/零售可见度
- https://example.com/only-one | 仅一条
"""
    report = check_feasibility_artifacts(text)
    assert any(i.code == "feas_channel_floor" for i in report.errors)


def test_competitor_floor_passes_without_audit():
    text = (FIXTURES / "depth_competitor_ok.md").read_text(encoding="utf-8")
    report = check_competitor_artifacts(text, audit=None)
    # no audit → scrape is warn only
    assert not any(i.code == "comp_price_floor" for i in report.errors)
    assert not any(i.code == "comp_excerpt_floor" for i in report.errors)
    assert not any(i.code == "comp_falsifiable_floor" for i in report.errors)
    assert any(i.code == "comp_no_audit" for i in report.warns)


def test_competitor_price_floor_fails():
    text = """## 硬证据清单
### 价带点
| ฿100 | A | SKU1 | https://a.example/x | 搜索 |
### 摘录
- hi | https://a.example/x
- hi2 | https://a.example/y
- hi3 | https://a.example/z
### 可证伪主张
- 主张：有空隙
- 打脸条件：若竞品已占满
- 验证方法：看榜单
"""
    report = check_competitor_artifacts(text, audit=None)
    assert any(i.code == "comp_price_floor" for i in report.errors)


def test_feasibility_rejects_social_only_channel_urls():
    text = """## 硬证据清单
### 渠道/零售可见度
- https://www.instagram.com/reel/abc | 促销 Reel
- https://www.facebook.com/brandthai/ | 粉丝页
"""
    report = check_feasibility_artifacts(text)
    assert any(i.code == "feas_channel_social_only" for i in report.errors)


def test_feasibility_rejects_report_pages_as_channel():
    text = """## 硬证据清单
### 渠道/零售可见度
- https://www.custommarketinsights.com/report/thailand-beauty-and-personal-care-market/ | 市场规模
- https://cosmetic.chemlinked.com/cosmepedia/thailand-cosmetic-regulation | 法规
"""
    report = check_feasibility_artifacts(text)
    assert any(i.code == "feas_channel_social_only" for i in report.errors)


def test_feasibility_rejects_press_and_gov_as_channel():
    """东边野兽 UK：BeautyMatter / HSE 不得计入渠道地板。"""
    text = """## 硬证据清单
### 渠道/零售可见度
- https://beautymatter.com/articles/partner-season-ii-c-beauty-brands-yanlab-london | YanLab 报道
- https://www.hse.gov.uk/reach/about.htm | REACH
"""
    report = check_feasibility_artifacts(text)
    assert any(i.code == "feas_channel_social_only" for i in report.errors)


def test_feasibility_german_appliance_retail_hosts_count():
    """石头科技 DE：MediaMarkt / Amazon PDP 等应计入渠道地板。"""
    text = """## 硬证据清单
### 渠道/零售可见度
- https://www.mediamarkt.de/de/product/_roborock-zeo-mini-123.html | MediaMarkt 在售
- https://www.amazon.de/-/en/roborock-Zeo-cycle-Temperature/dp/B0F3XGCS8H | Amazon.de PDP
"""
    report = check_feasibility_artifacts(text)
    assert report.errors == [], [i.message for i in report.errors]


def test_feasibility_amazon_category_page_does_not_count():
    """Amazon 分类浏览页不得凑渠道地板（depth_feas_v1 踩过）。"""
    text = """## 硬证据清单
### 渠道/零售可见度
- https://www.amazon.de/-/en/Washing-Machines-Tumble-Dryers/b?ie=UTF8&node=1399929031 | 分类页
- https://www.mykitchens.de/en/magazine/manufacturer-comparison | 媒体对比
"""
    report = check_feasibility_artifacts(text)
    assert any(i.code == "feas_channel_social_only" for i in report.errors)


def test_scoring_parses_bold_trailing_total():
    from src.marketing_crew.scoring_check import check_scoring_text

    text = """
## 建议（一页纸）
- 结论：建议进入（加权总分 3.8）
加权总分 = 0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4 = **3.8**
"""
    rep = check_scoring_text(text)
    assert rep.found_table
    assert rep.claimed_total == 3.8
    assert rep.recomputed_total == 3.65
    assert any(i.kind == "加权总分算错" for i in rep.errors)


def test_scoring_ignores_parenthetical_short_claimed_total():
    """结论行「建议进入（加权总分 = 3.29）」不得盖住真实公式行（depth_feas_v1）。"""
    from src.marketing_crew.scoring_check import check_scoring_text

    text = """
## 建议
建议进入（加权总分 = 3.29）

| 维度 | 权重(合计1.0) | 得分(1-5) | 对照哪条锚点 | 依据 | URL |
| 需求匹配 | 0.25 | 4 | x | y | z |
| 合规可完成性 | 0.15 | 2 | x | y | z |
| 渠道可达 | 0.20 | 5 | x | y | z |
| 竞争强度 | 0.20 | 3 | x | y | z |
| 品牌资产匹配 | 0.20 | 3 | x | y | z |

加权总分 = 0.25×4 + 0.15×2 + 0.20×5 + 0.20×3 + 0.20×3 = 3.29
"""
    rep = check_scoring_text(text)
    assert rep.found_table
    assert rep.claimed_total == 3.29
    assert rep.recomputed_total == 3.5
    assert any(i.kind == "加权总分算错" for i in rep.errors)
    assert not any(i.kind == "加权式子无法解析" for i in rep.errors)


def test_scoring_errors_when_table_lacks_formula_line():
    """depth_feas_v2：总分只在表格单元格 → 必须报缺少算式。"""
    from src.marketing_crew.scoring_check import check_scoring_text

    text = """
## 建议
建议进入（加权总分 3.5）

| 维度 | 权重(合计1.0) | 得分(1-5) | 对照哪条锚点 | 依据 | URL |
| 需求匹配 | 0.25 | 4 | x | y | z |
| 合规可完成性 | 0.15 | 4 | x | y | z |
| 渠道可达 | 0.20 | 3 | x | y | z |
| 竞争强度 | 0.20 | 3 | x | y | z |
| 品牌资产匹配 | 0.20 | 4 | x | y | z |
| **加权总分** | **= Σ** | **3.5** | | | |
"""
    rep = check_scoring_text(text)
    assert any(i.kind == "缺少加权总分算式" for i in rep.errors)


def test_scoring_ignores_soft_pass_banner_formula_noise():
    """东边野兽 depth_v1：横幅里的算式示例不得污染正文核对。"""
    from src.marketing_crew.scoring_check import check_scoring_text

    text = """> ⚠️ **组合 guardrail 已达共享软上限**
>
> 正确加权总分应约为 **3.85**。请把「加权总分 = … = X」里的 X 改成这个数

## 建议（一页纸）
- 结论：建议进入（加权总分 3.85）

加权总分 = 0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4 = 3.85
"""
    # Note: real 3.85 is wrong for these weights (should be 3.65); we only assert banner didn't win
    rep = check_scoring_text(text)
    assert rep.found_table
    assert rep.claimed_total == 3.85
    # Must use body formula, not banner-only garbage
    assert "共享软上限" not in (rep.issues[0].context if rep.issues else "")


def test_feasibility_honest_gap_needs_retail_searches_without_audit():
    text = """## 硬证据清单
### 渠道/零售可见度
- 证据不足。已试检索：Flower Knows KONVY / site:shopee.co.th Flower Knows
"""
    # 无 audit 时零售搜索=0，不能走诚实放行
    report = check_feasibility_artifacts(text, audit=None)
    assert any(i.code == "feas_channel_social_only" for i in report.errors)


def test_render_smoke():
    text = (FIXTURES / "depth_feasibility_ok.md").read_text(encoding="utf-8")
    out = render_artifact_reports([check_feasibility_artifacts(text)])
    assert "硬证据地板" in out


def test_scoring_guardrail_rejects_bad_math():
    from src.marketing_crew.guardrails import build_guardrail

    bad = """
## 建议（一页纸）
- 结论：建议进入（加权总分 3.5）

加权总分 = 0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4 = 3.5
"""
    g = build_guardrail("scoring", soft_max_retries=2)
    assert g is not None
    ok, payload = g(bad)
    assert ok is False
    assert "算错" in str(payload) or "3.65" in str(payload)


def test_scoring_guardrail_accepts_correct_math():
    from src.marketing_crew.guardrails import build_guardrail

    good = """
## 建议（一页纸）
- 结论：建议进入（加权总分 3.65）

加权总分 = 0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4 = 3.65
"""
    g = build_guardrail("scoring", soft_max_retries=2)
    ok, _ = g(good)
    assert ok is True


def test_competitor_rejects_homepage_price_rows():
    text = """## 硬证据清单
### 价带点
| 69-450 | Mistine | 各类型 | https://www.mistine.com | 搜索 |
| 79-350 | Cathy | 各类型 | https://www.cathydoll.com | 搜索 |
| 100-500 | Sri | 散粉 | https://www.srichand.com | 搜索 |
| 199 | A | SKU1 | https://www.shopee.co.th/a-sku | scrape |
| 249 | B | SKU2 | https://www.shopee.co.th/b-sku | scrape |
### 摘录
- a | https://www.shopee.co.th/a-sku
- b | https://www.shopee.co.th/b-sku
- c | https://www.shopee.co.th/c-sku
### 可证伪主张
- 主张：有空隙
- 打脸条件：若已占满
- 验证方法：看榜
"""
    report = check_competitor_artifacts(text, audit=None)
    # 3 homepage rows ignored → only 2 priced → price floor
    assert any(i.code == "comp_price_floor" for i in report.errors)


def test_artifact_competitor_guardrail_registered():
    from src.marketing_crew.guardrails import GUARDRAIL_FACTORIES, build_guardrail

    assert "artifact_competitor" in GUARDRAIL_FACTORIES
    g = build_guardrail("artifact_competitor,citation", soft_max_retries=2)
    assert g is not None


def test_composed_guardrail_soft_passes_before_crewai_exhaustion():
    """组合链路必须共享软上限，否则会像 depth_v2 一样把整条 Crew 打断。"""
    from src.marketing_crew.guardrails import build_guardrail

    # scoring 会失败；soft=1 → 第二次 False 应变 True（软放行）
    bad = """
## 建议（一页纸）
- 结论：建议进入（加权总分 3.5）
加权总分 = 0.25×4 + 0.15×3 + 0.20×4 + 0.20×3 + 0.20×4 = 3.5
"""
    g = build_guardrail("scoring,citation", soft_max_retries=1)
    assert g is not None
    ok1, _ = g(bad)
    assert ok1 is False
    ok2, payload2 = g(bad)
    assert ok2 is True
    assert "共享软上限" in str(payload2) or "软上限" in str(payload2)


def test_soft_pass_banner_tbd_not_counted_as_body_severe():
    """depth_v3：组合 soft-pass 横幅里的「TBD」不得触发引用严重项。"""
    from src.marketing_crew.citation_check import check_text

    text = """> ⚠️ **组合 guardrail 已达共享软上限**（累计 3 次未通过 / 上限 2）。
>
> 1. 【comp_price_floor】禁止「待补充 / TBD」行凑数
>
> - 禁止「待补充 / TBD」行；优先真搜。

本报告目标市场：泰国；本地货币：THB

## 参考文献
- Mistine | https://www.watsons.co.th/en/mistine-soft-matte-01/p/BP_321580 | B
"""
    report = check_text(text, file_label="banner_fp.md")
    tbd_errors = [i for i in report.issues if i.severity == "error" and "TBD" in (i.kind or "")]
    # also match Chinese kind
    tbd_errors += [
        i
        for i in report.issues
        if i.severity == "error" and ("TBD" in i.detail or "待补充" in i.detail or "占位" in (i.kind or ""))
    ]
    # Dedup by identity
    tbd_errors = list({id(i): i for i in tbd_errors}.values())
    assert not tbd_errors, [f"{i.kind}: {i.detail}" for i in tbd_errors]
