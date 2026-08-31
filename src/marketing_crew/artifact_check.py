"""Depth V1 artifact floors: parse 「硬证据清单」and compare to tool_audit.

Design: narrative body stays free-form; only the evidence appendix is mechanically scored.
Used by `--variant research_depth` (not research_only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tool_audit import ToolAuditListener

_URL_RE = re.compile(r"https?://[^\s)\]>|\"']+")
_PRICE_RE = re.compile(
    r"(?:£|€|¥|฿|\$|USD|GBP|THB|EUR)\s*\d[\d,]*(?:\.\d+)?|"
    r"\d[\d,]*(?:\.\d+)?\s*(?:英镑|泰铢|元|日元|欧元|baht|pound|THB)|"
    # 表内常见「69-450」价位区间（仍须同行有 URL；首页凑数另由 citation 管）
    r"\b\d{2,5}\s*[-–]\s*\d{2,5}\b",
    re.I,
)
# 社媒主页/Reel 不能当「渠道/零售可见度」硬证据——depth_feas_v1 实测用 IG+FB 凑满 2 条过地板。
_SOCIAL_HOST_RE = re.compile(
    r"https?://(www\.)?(instagram\.com|facebook\.com|fb\.com|tiktok\.com|x\.com|twitter\.com|youtube\.com)/",
    re.I,
)
# 东边野兽 UK 冒烟：黑名单不够——BeautyMatter 报道 / HSE REACH 页也被当成「渠道」。
# 改为零售/电商/品牌店 **白名单**；媒体、法规、研报默认不计。
# 石头科技 DE：家电零售（MediaMarkt / Saturn / Otto / Idealo / Roborock 店）+ Amazon **仅 PDP/店页**。
_RETAIL_HOST_HINTS = (
    "konvy.com",
    "beautrium.com",
    "shopee.",
    "lazada.",
    "watsons.",
    "boots.com",
    "cultbeauty.",
    "spacenk.",
    "lookfantastic.",
    "sephora.",
    "selfridges.",
    "harveynichols.",
    "ulta.com",
    "oliveyoung.",
    "herbeast.world",
    "herbeast.cn",
    "flowerknows.",
    "aesop.com",
    "weleda.",
    "nealsyardremedies.",
    "paiskincare.",
    "drhauschka.",
    "theordinary.",
    "deciem.",
    "yanlab",  # 概念店域名若出现；纯媒体报道域名仍不在此列
    # DE appliance / general retail (Roborock Germany depth_feas)
    "mediamarkt.de",
    "saturn.de",
    "otto.de",
    "idealo.de",
    "roborock.com",
)

# Amazon：域名可零售，但分类浏览页 /b?node=、搜索 /s? 不能凑渠道地板；只认 PDP / 店铺。
_AMAZON_HOST_RE = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*?amazon\.[a-z.]{2,}/",
    re.I,
)
_AMAZON_RETAIL_PATH_RE = re.compile(
    r"/(?:dp|gp/product|gp/aw/d)/[A-Z0-9]{8,10}"
    r"|/stores/"
    r"|/shop/"
    r"|/sp\?",
    re.I,
)


def _is_social_url(url: str) -> bool:
    return bool(_SOCIAL_HOST_RE.match(url or ""))


def _is_amazon_retail_url(url: str) -> bool:
    """Amazon 仅商品页（/dp/…）或品牌店（/stores/、/shop/）计入；分类页不计。"""
    if not _AMAZON_HOST_RE.match(url or ""):
        return False
    return bool(_AMAZON_RETAIL_PATH_RE.search(url or ""))


def _is_retailish_channel_url(url: str) -> bool:
    """渠道地板只认白名单零售/电商/品牌店域名（Amazon 另走 PDP/店页路径规则）。"""
    if not url or _is_social_url(url):
        return False
    if _is_amazon_retail_url(url):
        return True
    u = url.lower()
    return any(h in u for h in _RETAIL_HOST_HINTS)


def _retailish_urls(urls: list[str]) -> list[str]:
    return [u for u in urls if _is_retailish_channel_url(u)]


COMPETITOR_ROLE_HINTS = ("竞品", "competitor")
FEASIBILITY_ROLE_HINTS = ("可行性研究员", "market_researcher_feasibility")


@dataclass
class ArtifactIssue:
    severity: str  # error | warn
    code: str
    message: str


@dataclass
class ArtifactReport:
    label: str = ""
    issues: list[ArtifactIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ArtifactIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warns(self) -> list[ArtifactIssue]:
        return [i for i in self.issues if i.severity == "warn"]


def _section_after(text: str, heading: str) -> str:
    """Return markdown body after a heading line containing `heading`, until next ##."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#") and heading in line:
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## ") and heading not in lines[j]:
            end = j
            break
    return "\n".join(lines[start:end])


def _subsection(block: str, name: str) -> str:
    lines = block.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#") and name in line:
            start = i + 1
            break
    if start is None:
        # also allow bold mini-headers
        for i, line in enumerate(lines):
            if name in line and (line.strip().startswith("**") or line.strip().startswith("-")):
                start = i
                break
    if start is None:
        return block  # fall back: search whole 硬证据清单
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("### "):
            end = j
            break
    return "\n".join(lines[start:end])


def _urls(text: str) -> list[str]:
    return [u.rstrip(".,);\"'") for u in _URL_RE.findall(text or "")]


def _is_scrape_call(call) -> bool:
    name = (call.tool_name or "").lower()
    args = (call.args or "").lower()
    if "website_url=" in args:
        return True
    return any(h in name for h in ("scrape", "read website", "website content"))


def _role_matches(role: str, hints: tuple[str, ...]) -> bool:
    r = role or ""
    return any(h in r for h in hints)


def extract_evidence_appendix(text: str) -> str:
    return _section_after(text, "硬证据清单")


def _is_search_call(call) -> bool:
    name = (call.tool_name or "").lower()
    args = (call.args or "").lower()
    if "search_query=" in args or args.startswith("query="):
        return True
    return any(h in name for h in ("serper", "search the internet", "search"))


_RETAIL_QUERY_MARKERS = (
    "konvy",
    "beautrium",
    "shopee",
    "lazada",
    "watsons",
    "boots",
    "sephora",
    "cult beauty",
    "cultbeauty",
    "space nk",
    "spacenk",
    "lookfantastic",
    "selfridges",
    "olive young",
    "mediamarkt",
    "saturn",
    "otto.de",
    "otto ",
    "idealo",
    "amazon.de",
    "amazon",
    "roborock",
    "商品页",
    "在售",
    "pdp",
    "retail",
)


def _retail_search_count(audit: "ToolAuditListener | None", role_hints: tuple[str, ...]) -> int:
    if audit is None:
        return 0
    n = 0
    for c in audit.calls:
        if c.status != "finished" or not _is_search_call(c):
            continue
        if role_hints and not _role_matches(c.agent_role, role_hints):
            continue
        q = (c.args or "").lower()
        if any(m in q for m in _RETAIL_QUERY_MARKERS):
            n += 1
    return n


def _channel_block_and_urls(appendix: str) -> tuple[str, list[str], bool]:
    """Returns (block_text, urls, heading_present)."""
    heading_present = "渠道" in appendix or "零售" in appendix
    if heading_present:
        channel_block = _subsection(appendix, "渠道")
        if not channel_block.strip():
            channel_block = _subsection(appendix, "零售")
        urls = _urls(channel_block) if channel_block.strip() else _urls(appendix)
        return channel_block or appendix, urls, True
    return appendix, _urls(appendix), False


def check_feasibility_artifacts(
    text: str,
    audit: "ToolAuditListener | None" = None,
) -> ArtifactReport:
    report = ArtifactReport(label="feasibility")
    appendix = extract_evidence_appendix(text)
    if not appendix.strip():
        report.issues.append(
            ArtifactIssue(
                "error",
                "feas_missing_appendix",
                "可行性报告缺少「## 硬证据清单」——Depth V1 用它做地板验收，不是装饰章节。",
            )
        )
        return report

    channel_block, channel_urls, heading_present = _channel_block_and_urls(appendix)
    if not heading_present:
        report.issues.append(
            ArtifactIssue(
                "warn",
                "feas_channel_heading_missing",
                "硬证据清单未见「渠道/零售」子节；将用整节 URL 计数（可能偏松）。"
                "请使用 `### 渠道/零售可见度` 子标题。",
            )
        )

    retail = _retailish_urls(channel_urls)
    honest_gap = ("证据不足" in channel_block) or ("检索无果" in channel_block)
    retail_searches = _retail_search_count(audit, FEASIBILITY_ROLE_HINTS)
    # 审计已证明做过足够零售向搜索时，即使漏写「证据不足」也按诚实缺口放行（depth_v2 attempt 3：
    # 6 次零售搜索仍只有 1 条可计入 URL——模型卡在「必须填满链接」而不是声明不足）。
    audit_proves_effort = retail_searches >= 2

    if len(retail) >= 2:
        pass  # floor met
    elif (honest_gap or audit_proves_effort) and retail_searches >= 2:
        report.issues.append(
            ArtifactIssue(
                "warn",
                "feas_channel_honest_gap",
                f"渠道硬证据不足（可计入零售 URL {len(retail)}），但审计显示至少 {retail_searches} 次"
                "零售向搜索。地板按诚实缺口放行；请在清单写明「证据不足」+ 已试 query；"
                "「渠道可达」得分不得偏乐观。",
            )
        )
    elif len(channel_urls) < 2 and not honest_gap and not audit_proves_effort:
        report.issues.append(
            ArtifactIssue(
                "error",
                "feas_channel_floor",
                f"渠道/零售可见度硬证据仅 {len(channel_urls)} 条 URL，中度地板要求 ≥2 条可计入的零售链接，"
                "或在 `### 渠道/零售可见度` 写明「证据不足」并先做 ≥2 次零售向搜索（审计可见）。",
            )
        )
    else:
        report.issues.append(
            ArtifactIssue(
                "error",
                "feas_channel_social_only",
                f"渠道硬证据里可计入的零售/电商 URL 仅 {len(retail)} 条"
                f"（清单里其它链接 {len(channel_urls) - len(retail)} 条；零售向搜索 {retail_searches} 次）。\n"
                "不要用市场规模报告、法规咨询页、品牌官网首页、社媒来凑渠道地板。\n"
                "两条合法出路：\n"
                "1) 搜出目标市场零售/电商商品页或品牌店页写入清单"
                "（美妆例：KONVY / Shopee / Lazada / Beautrium；"
                "德国家电例：MediaMarkt / Saturn / Otto / Idealo / Amazon.de **PDP 或店页**——"
                "Amazon 分类浏览页 `/b?node=` 不计）；\n"
                "2) 真搜过仍没有 → 在 `### 渠道/零售可见度` 写「证据不足」+ 已试 query，"
                "并保证工具审计里有 ≥2 次含零售平台名的搜索。",
            )
        )

    falsifiable = _subsection(appendix, "可证伪")
    if falsifiable.strip():
        has_claim = ("主张" in falsifiable) or ("若" in falsifiable)
        has_test = ("验证" in falsifiable) or ("打脸" in falsifiable) or ("若错" in falsifiable)
        if not (has_claim and has_test):
            report.issues.append(
                ArtifactIssue(
                    "warn",
                    "feas_falsifiable_thin",
                    "可行性硬证据清单有「可证伪」子节，但缺少主张/验证要素之一。",
                )
            )
    return report


def _is_bare_homepage(url: str) -> bool:
    """品牌官网根路径不能当价带商品页。"""
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        return (p.path or "").strip("/") == ""
    except Exception:
        return False


def check_competitor_artifacts(
    text: str,
    audit: "ToolAuditListener | None" = None,
) -> ArtifactReport:
    report = ArtifactReport(label="competitor")
    appendix = extract_evidence_appendix(text)
    if not appendix.strip():
        report.issues.append(
            ArtifactIssue(
                "error",
                "comp_missing_appendix",
                "竞品报告缺少「## 硬证据清单」。",
            )
        )
        return report

    price_block = _subsection(appendix, "价带")
    price_lines = [
        ln
        for ln in (price_block or appendix).splitlines()
        if ln.strip().startswith("|") or ln.strip().startswith("-")
    ]
    priced = []
    for ln in price_lines:
        if "价位" in ln and "品牌" in ln and "---" not in ln:
            continue  # header
        if "---" in ln:
            continue
        if any(tok in ln for tok in ("待补充", "待确认", "TBD", "证据不足")):
            continue
        urls = _urls(ln)
        if not urls or not _PRICE_RE.search(ln):
            continue
        if all(_is_bare_homepage(u) for u in urls):
            continue  # 官网首页不算价带点
        priced.append(ln)
    if len(priced) < 5:
        report.issues.append(
            ArtifactIssue(
                "error",
                "comp_price_floor",
                f"价带硬证据仅 {len(priced)} 行同时含价格+非首页 URL，中度地板要求 ≥5。"
                "禁止品牌官网首页、待补充/TBD 行凑数；需要单品页或零售商品页。",
            )
        )

    excerpt_block = _subsection(appendix, "摘录")
    excerpt_urls = _urls(excerpt_block if excerpt_block.strip() else "")
    excerpt_lines = [
        ln
        for ln in (excerpt_block or "").splitlines()
        if ln.strip().startswith("-") and _urls(ln)
    ]
    if len(excerpt_lines) < 3 and len(excerpt_urls) < 3:
        report.issues.append(
            ArtifactIssue(
                "error",
                "comp_excerpt_floor",
                f"摘录硬证据不足（带 URL 的条目约 {max(len(excerpt_lines), len(excerpt_urls))}），要求 ≥3。",
            )
        )

    falsifiable = _subsection(appendix, "可证伪")
    ok_f = (
        falsifiable.strip()
        and (("主张" in falsifiable) or ("若" in falsifiable))
        and (("验证" in falsifiable) or ("打脸" in falsifiable) or ("若错" in falsifiable))
    )
    # Also accept falsifiable written in main 差异化 section
    diff = _section_after(text, "差异化")
    if not ok_f:
        if ("可证伪" in diff or "若" in diff) and ("验证" in diff or "打脸" in diff):
            ok_f = True
        else:
            report.issues.append(
                ArtifactIssue(
                    "error",
                    "comp_falsifiable_floor",
                    "缺少可证伪主张（硬证据清单或差异化节）：需要主张 + 打脸/验证条件。",
                )
            )

    # scrape floor via audit
    if audit is not None:
        scrapes = [
            c
            for c in audit.calls
            if c.status == "finished"
            and _is_scrape_call(c)
            and _role_matches(c.agent_role, COMPETITOR_ROLE_HINTS)
        ]
        # if role filter empty (naming drift), count all scrapes
        if not scrapes:
            scrapes = [
                c for c in audit.calls if c.status == "finished" and _is_scrape_call(c)
            ]
            if scrapes:
                report.issues.append(
                    ArtifactIssue(
                        "warn",
                        "comp_scrape_role_unmatched",
                        "未匹配到竞品角色名的 scrape，已回退统计全链路 scrape 次数。",
                    )
                )
        if len(scrapes) < 2:
            report.issues.append(
                ArtifactIssue(
                    "error",
                    "comp_scrape_floor",
                    f"有效 scrape 仅 {len(scrapes)} 次，中度地板要求 ≥2（对照 tool_audit，非模型自述）。",
                )
            )
    else:
        report.issues.append(
            ArtifactIssue(
                "warn",
                "comp_no_audit",
                "无 tool_audit，跳过 scrape 地板。",
            )
        )

    # wild URL soft check: URLs in 差异化 should appear in appendix or 参考文献
    allowed = set(_urls(appendix)) | set(_urls(_section_after(text, "参考文献")))
    wild = []
    for section_name in ("差异化", "建议"):
        body = _section_after(text, section_name)
        if not body.strip():
            continue
        for u in _urls(body):
            if u not in allowed and "硬证据清单" not in section_name:
                wild.append(u)
    if wild:
        report.issues.append(
            ArtifactIssue(
                "warn",
                "comp_wild_url",
                f"差异化/建议节出现 {len(set(wild))} 个未在硬证据清单或参考文献出现的 URL（V1 仅警告）。"
                f" 例：{next(iter(set(wild)))}",
            )
        )

    return report


def check_research_depth_artifacts(
    *,
    feasibility_path: Path | None,
    competitor_path: Path | None,
    audit: "ToolAuditListener | None" = None,
) -> list[ArtifactReport]:
    reports: list[ArtifactReport] = []
    if feasibility_path and feasibility_path.exists():
        reports.append(
            check_feasibility_artifacts(
                feasibility_path.read_text(encoding="utf-8"),
                audit=audit,
            )
        )
    elif feasibility_path:
        r = ArtifactReport(label="feasibility")
        r.issues.append(
            ArtifactIssue("error", "feas_file_missing", f"缺少文件：{feasibility_path}")
        )
        reports.append(r)

    if competitor_path and competitor_path.exists():
        reports.append(
            check_competitor_artifacts(
                competitor_path.read_text(encoding="utf-8"), audit=audit
            )
        )
    # competitor optional for feasibility_only-style runs
    return reports


def render_artifact_reports(reports: list[ArtifactReport]) -> str:
    lines = [
        "=" * 78,
        "Depth V1 硬证据地板（artifact_check，非模型自述）",
        "=" * 78,
    ]
    if not reports:
        lines.append("\n（无报告可检）")
        return "\n".join(lines)

    total_e = total_w = 0
    for rep in reports:
        lines.append(f"\n### {rep.label}")
        if not rep.issues:
            lines.append("  ✅ 地板通过")
            continue
        for i in rep.issues:
            icon = "❌" if i.severity == "error" else "⚠️"
            lines.append(f"  {icon} [{i.code}] {i.message}")
            if i.severity == "error":
                total_e += 1
            else:
                total_w += 1
    lines.append("")
    lines.append(f"汇总：{total_e} 处严重，{total_w} 处警告。")
    if total_e:
        lines.append("严重项：补硬证据清单或重跑 research_depth；`--strict-depth` 时非零退出。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Usage: python -m src.marketing_crew.artifact_check "
            "<feasibility.md> [competitor.md]",
            file=sys.stderr,
        )
        return 2
    reports = []
    reports.append(
        check_feasibility_artifacts(Path(args[0]).read_text(encoding="utf-8"), audit=None)
    )
    if len(args) > 1:
        reports.append(
            check_competitor_artifacts(Path(args[1]).read_text(encoding="utf-8"), audit=None)
        )
    print(render_artifact_reports(reports))
    return 1 if any(r.errors for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())

