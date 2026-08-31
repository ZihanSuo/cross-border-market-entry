"""研究深度门禁：对照 tool_audit 与报告正文，抓「没搜就下结论 / 补证不换角度」。

设计原则：
- 不规定 Agent 必须搜哪几个固定 query（保自由度）
- 只检查结果是否自洽：宣称「已有市场空间」却 0 次搜索；补证每缺口只有单一角度查询等
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tool_audit import ToolAuditListener, ToolCall


FEASIBILITY_ROLE_HINTS = ("可行性研究员", "market_researcher_feasibility")
GAP_FILL_ROLE_HINTS = ("缺口补证", "证据缺口", "evidence_gap")

# 可行性正文里「过于乐观的品类接受度」信号（没搜就写这些 = 深度造假）
OPTIMISTIC_ACCEPTANCE_PATTERNS = [
    r"已有市场空间",
    r"存在一定可见度",
    r"至少有\s*\d+\s*款",
    r"至少\s*\d+\s*款",
    r"有\s*\d+\s*款相关产品在售",
]

SEARCH_TOOL_HINTS = ("serper", "search the internet", "search_query", "google")


# 提取 URL，用于比对补证报告与上游报告的来源重合度
_URL_RE = re.compile(r"https?://[^\s)\]>|]+")


@dataclass
class DepthIssue:
    severity: str  # error | warn
    code: str
    message: str


@dataclass
class DepthReport:
    issues: list[DepthIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[DepthIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warns(self) -> list[DepthIssue]:
        return [i for i in self.issues if i.severity == "warn"]

    def render(self) -> str:
        lines = [
            "=" * 78,
            "研究深度门禁（对照 tool_audit，非模型自述）",
            "=" * 78,
        ]
        if not self.issues:
            lines.append("\n✅ 未发现「零搜索下结论 / 补证不换角度」类问题。")
            return "\n".join(lines)
        lines.append("")
        for i in self.issues:
            icon = "❌" if i.severity == "error" else "⚠️"
            lines.append(f"  {icon} [{i.code}] {i.message}")
        lines.append("")
        lines.append(
            f"汇总：{len(self.errors)} 处严重，{len(self.warns)} 处警告。"
        )
        if self.errors:
            lines.append(
                "严重项：建议修对应段落或重跑相关 task；"
                "若用了 --strict-depth，进程会非零退出（文件通常已写完，可先人工改再备份）。"
            )
        elif self.warns:
            lines.append("仅有警告：可备份交付，但建议在 CHANGELOG 里记下薄弱点。")
        return "\n".join(lines)


def _role_matches(role: str, hints: tuple[str, ...]) -> bool:
    r = role or ""
    return any(h in r for h in hints)


def _is_search_call(call: "ToolCall") -> bool:
    name = (call.tool_name or "").lower()
    args = (call.args or "").lower()
    if "search_query=" in args or args.startswith("query="):
        return True
    return any(h in name for h in SEARCH_TOOL_HINTS)


def _finished_searches(audit: "ToolAuditListener", role_hints: tuple[str, ...]) -> list["ToolCall"]:
    out: list[ToolCall] = []
    for c in audit.calls:
        if c.status != "finished":
            continue
        if not _is_search_call(c):
            continue
        if role_hints and not _role_matches(c.agent_role, role_hints):
            continue
        out.append(c)
    return out


def _query_text(call: "ToolCall") -> str:
    args = call.args or ""
    if "=" in args:
        return args.split("=", 1)[1].strip().lower()
    return args.strip().lower()


def _angle_bucket(query: str) -> str:
    """粗分检索角度：零售/品牌渠道 vs 态度概念。不规定用词，只看是否换过桶。"""
    retail_markers = (
        # TH beauty / marketplace
        "shopee",
        "lazada",
        "konvy",
        "beautrium",
        # Generic retail / commerce signals
        "site:",
        "retail",
        "store",
        "product",
        "price",
        "pricing",
        "baht",
        "฿",
        "£",
        "gbp",
        "€",
        " eur",  # avoid matching "european"
        "euro ",
        "sku",
        "availability",
        "in stock",
        "在售",
        "标价",
        "official",
        "pdp",
        "tiktok shop",
        # UK beauty retail
        "ulta",
        "watson",
        "boots",
        "cult beauty",
        "cultbeauty",
        "space nk",
        "spacenk",
        "lookfantastic",
        "sephora",
        "watsons",
        "selfridges",
        "aesop",
        "weleda",
        "neals yard",
        "pai skincare",
        # DE appliance / general retail (align with artifact_check._RETAIL_QUERY_MARKERS)
        # Honest: platform/currency/commerce cues only — bare "roborock"/"zeo" alone
        # must NOT count (Stiftung Warentest / sales-data queries stay attitude).
        "mediamarkt",
        "media markt",
        "saturn",
        "otto.de",
        "otto ",
        "idealo",
        "amazon.de",
        "amazon",
        "joybuy",
        "kaufland",
    )
    brand_channel = (
        "flower knows",
        "flowerknows",
        "herbeast",
        "东边野兽",
        "花知晓",
        "mistine",
        "cathy doll",
        "srichand",
        "partnership",
        "distributor",
        "reseller",
        "comparison",  # 价格/竞品对比通常带渠道或标价意图
    )
    q = query.lower()
    if any(m in q for m in retail_markers) or any(m in q for m in brand_channel):
        return "retail_or_brand_channel"
    return "attitude_or_concept"


def check_research_depth(
    audit: "ToolAuditListener | None",
    *,
    feasibility_path: Path | None = None,
    gap_fill_path: Path | None = None,
) -> DepthReport:
    report = DepthReport()
    if audit is None:
        report.issues.append(
            DepthIssue("warn", "no_audit", "未启用 tool_audit，跳过深度门禁。")
        )
        return report

    feas_searches = _finished_searches(audit, FEASIBILITY_ROLE_HINTS)
    gap_searches = _finished_searches(audit, GAP_FILL_ROLE_HINTS)

    feas_text = ""
    if feasibility_path and feasibility_path.exists():
        feas_text = feasibility_path.read_text(encoding="utf-8")

    if feas_text:
        optimistic = [
            p
            for p in OPTIMISTIC_ACCEPTANCE_PATTERNS
            if re.search(p, feas_text)
        ]
        if not feas_searches:
            if optimistic:
                report.issues.append(
                    DepthIssue(
                        "error",
                        "feasibility_zero_search_optimistic",
                        "可行性研究员 0 次成功搜索，却写出「"
                        + " / ".join(optimistic[:2])
                        + "」类品类接受度结论。必须先搜索再下结论，或改回「证据不足」。",
                    )
                )
            else:
                report.issues.append(
                    DepthIssue(
                        "warn",
                        "feasibility_zero_search",
                        "可行性研究员 0 次成功搜索。桌面研究章节可信度存疑。",
                    )
                )
        # 首页冒充：正文用平台根域却声称多款在售
        if re.search(r"至少有\s*\d+\s*款|至少\s*\d+\s*款", feas_text) and re.search(
            r"https?://(www\.)?(shopee|lazada)\.[a-z.]+/?\)", feas_text
        ):
            report.issues.append(
                DepthIssue(
                    "error",
                    "homepage_as_sku_evidence",
                    "可行性用电商平台首页支撑「多款在售」类断言；需要具体商品/搜索结果页 URL，或改为证据不足。",
                )
            )

    if gap_fill_path and gap_fill_path.exists():
        gap_text = gap_fill_path.read_text(encoding="utf-8")
        # 每个「### 缺口」块检查查询多样性
        blocks = re.split(r"\n###\s*缺口", gap_text)
        gap_blocks = [b for b in blocks[1:]] if len(blocks) > 1 else []
        # 「补证」是否真的补进了新东西：把补证报告的 URL 与上游可行性报告比对。
        # 为什么要查这个：石头科技那轮，补证报告 3 个 URL 里 2 个是从上游照抄的
        # （同一条 jiemian.com 用了两次），却写着「新事实」。这类产出最有害的地方在于
        # **它让缺口看起来关闭了，实际上一点没动**——下游会当成已补证的内容直接引用。
        if feas_text:
            up_urls = {u.rstrip(".,);") for u in _URL_RE.findall(feas_text)}
            gap_urls = [u.rstrip(".,);") for u in _URL_RE.findall(gap_text)]
            if gap_urls:
                fresh = [u for u in gap_urls if u not in up_urls]
                if not fresh:
                    report.issues.append(
                        DepthIssue(
                            "error",
                            "gap_fill_no_new_url",
                            f"补证报告里 {len(gap_urls)} 个 URL **全部**来自上游可行性报告，"
                            "没有任何新增来源。这是复述不是补证，缺口实际未关闭。",
                        )
                    )
                elif len(fresh) < len(gap_urls) / 2:
                    report.issues.append(
                        DepthIssue(
                            "warn",
                            "gap_fill_mostly_recycled_urls",
                            f"补证报告 {len(gap_urls)} 个 URL 中只有 {len(fresh)} 个是新增的，"
                            "其余来自上游。注意区分「新查到的事实」与「复述上游」。",
                        )
                    )

        if not gap_searches:
            report.issues.append(
                DepthIssue(
                    "error",
                    "gap_fill_zero_search",
                    "缺口补证研究员 0 次成功搜索。"
                    "⚠️ 若报告里仍写有「检索策略：搜索 xxx」，那是**伪造的过程描述**——"
                    "审计日志显示这个 agent 一次工具调用都没发起过。",
                )
            )
        else:
            buckets = {_angle_bucket(_query_text(c)) for c in gap_searches}
            # 全链路时可行性常已做过 KONVY/在售检索；把可行性的零售向搜索一并计入
            # 「流水线是否出现过第二角度」，避免补证只补态度缺口时被误杀。
            feas_buckets = {
                _angle_bucket(_query_text(c))
                for c in _finished_searches(audit, FEASIBILITY_ROLE_HINTS)
            }
            pipeline_buckets = buckets | feas_buckets
            if buckets == {"attitude_or_concept"} and "retail_or_brand_channel" not in pipeline_buckets:
                report.issues.append(
                    DepthIssue(
                        "error",
                        "gap_fill_single_angle",
                        "补证（且可行性）查询都落在「态度/概念」角度，没有零售平台、标价对比或品牌+渠道名的第二角度。"
                        "首轮挖不动时必须换角度再搜（query 自定，不锁死关键词）。",
                    )
                )
            elif buckets == {"attitude_or_concept"} and "retail_or_brand_channel" in feas_buckets:
                report.issues.append(
                    DepthIssue(
                        "warn",
                        "gap_fill_angles_rely_on_upstream",
                        "补证本轮查询偏态度/概念，但可行性已做过零售/渠道向搜索；建议补证仍自己补一刀零售角度，暂不挡交付。",
                    )
                )
            elif len(gap_searches) < 4 and gap_blocks and len(gap_blocks) >= 2:
                report.issues.append(
                    DepthIssue(
                        "warn",
                        "gap_fill_thin_search",
                        f"补证仅 {len(gap_searches)} 次成功搜索、缺口约 {len(gap_blocks)} 个；"
                        "通常不足以覆盖「每缺口多角度」。",
                    )
                )

        # 逐缺口：状态自洽 + 宣称无果时是否换过零售/品牌角度
        for i, block in enumerate(gap_blocks, 1):
            has_fact_url = bool(re.search(r"https?://", block))
            says_empty = "本轮检索无果" in block
            if has_fact_url and says_empty:
                report.issues.append(
                    DepthIssue(
                        "warn",
                        "gap_fill_status_contradiction",
                        f"缺口块 #{i} 既有 URL 又写「本轮检索无果」。"
                        "有旁证应标「部分补证 / 仍证据不足」，无果仅用于完全无可用链接时。",
                    )
                )
            still_open = says_empty or "仍证据不足" in block
            if still_open and _angle_bucket(block) != "retail_or_brand_channel":
                # 块内检索策略/查询词未见零售或品牌+渠道角度
                report.issues.append(
                    DepthIssue(
                        "error",
                        "gap_fill_no_retail_pivot",
                        f"缺口块 #{i} 仍未关闭，但块内查询未见零售平台/品牌+渠道第二角度。"
                        "首轮态度向挖不动时必须换角度再搜（具体用词自定）。",
                    )
                )

    return report
