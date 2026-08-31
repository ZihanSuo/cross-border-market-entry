"""评分表自洽性校验 —— 检查报告的结论是不是真的由它自己的评分推出来的。

## 这解决什么问题

可行性报告里有一张五维加权评分表，以及一条规则（8.6）规定总分决定结论档位：

    ≥3.5 建议进入 / 2.5–3.5 先验证假设、暂缓铺货 / <2.5 暂不建议

问题是：**在此之前，没有任何环节检查过这张表算得对不对、结论跟不跟它一致。**
实测把四份已归档报告的加权式子重算一遍，结果：

    东边野兽 v8    报告写 3.35（→应判暂缓）  实际 3.65（→建议进入）   算错，且结论与自述分数矛盾
    花知晓 v4      报告写 3.55               实际 3.65               算错
    花知晓 v5      报告写 3.55               实际 3.80               算错
    石头科技 v1    报告写 3.15               实际 3.15               ✅

**四份里三份把自己的加权总分算错了**，而且东边野兽 v8 那份，报告写的分数按规则该判「暂缓」，
它却写了「建议进入」——**结论和它自己的评分表打架**。

这类错误特别隐蔽：式子和数字都写得整整齐齐，看起来极其量化，不动手重算根本发现不了。
而它恰恰发生在整份报告最关键的那一行上。

## 为什么这一定要交给代码

这是**纯客观、零歧义**的检查：加权求和是确定性运算，档位是明确的阈值。
让模型自查等于让它重做一遍同样会做错的事。发现五（评分锚点）之所以只算做了一半，
就是因为锚点约束了"每一维打几分"，却没人约束"这些分怎么汇总成结论"。

## 检查项

1. **权重和是否为 1.0**（否则加权无意义）
2. **加权求和的算术对不对**（重算式子，与报告写的总分比对）
3. **结论档位与总分是否一致**（按规则 8.6 的阈值）
4. **每一维得分是否在 1–5 内**
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 结论档位阈值（对应 market_feasibility.yaml 规则 8.6）
BAND_ENTER = 3.5
BAND_HOLD = 2.5

# 「加权总分 = 0.25*4 + 0.15×3 + ...= 3.35」这一行。
# 兼容 * 与 ×、兼容中间插了「Σ(权重×得分) =」的写法。
# 石头科技 depth_feas_v1：结论行「建议进入（加权总分 = 3.29）」也会匹配 ——
# 必须要求 RHS 含权重×得分项，短句「加权总分 = N.NN」一律忽略。
_TOTAL_LINE_RE = re.compile(r"加权总分\s*[=＝]\s*(.+)")
_PAIR_RE = re.compile(r"(\d*\.?\d+)\s*[*×xX]\s*(\d*\.?\d+)")
_TRAILING_NUM_RE = re.compile(r"[=＝]\s*\**\s*(\d+\.?\d*)\s*\**")


def _extract_formula_rhs(text: str) -> str | None:
    """只接受带「权重×得分」项的算式 RHS；跳过结论括号里的短总分。"""
    for line in text.splitlines():
        m = _TOTAL_LINE_RE.search(line)
        if not m:
            continue
        rhs = m.group(1)
        if _PAIR_RE.search(rhs):
            return rhs
    return None

# 结论措辞 → 档位。顺序重要：先匹配更长更具体的。
_CONCLUSION_PATTERNS = (
    ("hold", ("暂缓铺货", "先验证假设", "暂缓", "先验证")),
    ("no", ("暂不建议", "不建议进入", "不建议")),
    ("enter", ("建议进入", "可开始准备", "建议进")),
)


def _band_of(score: float) -> str:
    if score >= BAND_ENTER:
        return "enter"
    if score >= BAND_HOLD:
        return "hold"
    return "no"


_BAND_LABEL = {
    "enter": "建议进入",
    "hold": "先验证假设、暂缓铺货",
    "no": "暂不建议",
}

# 评分表行：| 维度 | 0.25 | 4 | ...
_TABLE_WEIGHT_SCORE_RE = re.compile(
    r"\|\s*(?!加权|合计|维度)[^|]+\|\s*(0\.\d+)\s*\|\s*([1-5])\s*\|"
)
_CLAIMED_TOTAL_RE = re.compile(
    r"(?:加权总分|总分)\s*[（(]?\s*(?:加权总分\s*)?[=：:]?\s*\**([0-9]+\.?[0-9]*)\**",
    re.I,
)


def _recompute_from_table_rows(text: str) -> float | None:
    pairs = _TABLE_WEIGHT_SCORE_RE.findall(text)
    if len(pairs) < 3:
        return None
    total = sum(float(w) * float(s) for w, s in pairs)
    return round(total, 4)


# 加权总分的取值范围。各维得分 1–5、权重和为 1，所以总分必然落在 [1,5]。
# 用它过滤掉同一行里的无关数字（增长率、年份、价格等）。
_TOTAL_MIN, _TOTAL_MAX = 1.0, 5.0


def _plausible_total(value: float) -> bool:
    return _TOTAL_MIN <= value <= _TOTAL_MAX


def _claimed_total_elsewhere(text: str) -> float | None:
    """从建议段或表格『加权总分』单元格取声称总分。

    ⚠️ 这里踩过一个会**凭空造出错误**的坑：早期实现是「找到含『总分』的行，
    取该行第一个小数」。于是

        - 结论：建议进入。目标市场 2024 年增长 12.5%，加权总分见下表

    会返回 **12.5**，再与重算值 3.45 一比，报出「报告写的总分是 12.5，实际应为 3.45」
    ——一条完全不存在的问题。**校验工具凭空制造违规，比漏检更糟**：
    漏检只是没帮上忙，误报会让人不再信任整套指标，而这套指标正是本项目的立身之本。

    现在两道防线：
    1. 数字必须**紧邻**「加权总分 / 总分」字样（而不是同一行任意位置）
    2. 数值必须落在 [1, 5]（各维 1–5 分、权重和为 1，总分不可能超出这个区间）
    """
    lines = text.splitlines()

    # 1) 表格行优先，且取**最后**一个合理数字。
    #    实测 `| **总分** | 1.00 |  | **3.45** |` —— 「1.00」是权重和那一列，
    #    离「总分」二字更近。若按「最近」取值会得到 1.00，再与重算的 3.45 比对，
    #    就会报出「总分算错：写 1.0 实际 3.45」这条**根本不存在的问题**。
    #    表格里总分总是排在最后一列，所以从右往左找第一个合理值才是对的。
    for line in lines:
        if "总分" not in line or "|" not in line:
            continue
        for raw in reversed(re.findall(r"([0-9]+\.?[0-9]*)", line)):
            try:
                value = float(raw)
            except ValueError:
                continue
            if _plausible_total(value):
                return value

    # 2) 散文行：取紧邻「(加权)总分」之后的第一个合理数字
    #    （「总分3.45，建议进入」「加权总分 = 3.45」都能命中）
    near_total = re.compile(r"(?:加权)?总分[^0-9\n]{0,12}?(\d+\.?\d*)")
    for line in lines[:60]:
        if "总分" not in line or "|" in line:
            continue
        for raw in near_total.findall(line):
            try:
                value = float(raw)
            except ValueError:
                continue
            if _plausible_total(value):
                return value
    return None


@dataclass
class ScoringIssue:
    file: str
    severity: str  # "error" | "warning"
    kind: str
    detail: str
    context: str = ""


@dataclass
class ScoringReport:
    file: str = ""
    found_table: bool = False
    claimed_total: float | None = None
    recomputed_total: float | None = None
    issues: list[ScoringIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ScoringIssue]:
        return [i for i in self.issues if i.severity == "error"]


def _stated_conclusion_band(text: str) -> tuple[str, str] | None:
    """从报告开头的结论行里读出档位。返回 (band, 原文片段)。

    只看前 40 行：结论应当在摘要区，正文里出现的「建议进入」多半是在讨论条件，
    拿去比对会误判。
    """
    head = "\n".join(text.splitlines()[:40])
    for line in head.splitlines():
        if "结论" not in line and "建议" not in line:
            continue
        for band, words in _CONCLUSION_PATTERNS:
            for w in words:
                if w in line:
                    return band, line.strip()
    return None


def check_scoring_text(text: str, file_label: str = "") -> ScoringReport:
    rep = ScoringReport(file=file_label)

    # 东边野兽 depth_v1：feas/comp soft-pass 横幅里写了「加权总分 = … = X」示例，
    # 被当成正文算式解析 → 整份评分校验假失败。与 citation 同源污染。
    from .citation_check import _strip_guardrail_banner

    text = _strip_guardrail_banner(text)

    total_line = _extract_formula_rhs(text)

    # 东边野兽 depth_feas_v2：把「加权总分 / 3.5」塞进表格单元格，没有「加权总分 = 0.25×4+…」行，
    # 旧逻辑直接跳过 → 算术闸形同关闭。有评分表却无算式 = 严重。
    has_score_table = (
        "需求匹配" in text
        and "0.25" in text
        and ("得分" in text or "评分" in text or "权重" in text)
    )

    if total_line is None:
        if has_score_table:
            rep.found_table = True
            # 尝试从表格行重算，仍要求补上标准算式行
            table_total = _recompute_from_table_rows(text)
            claimed = _claimed_total_elsewhere(text)
            if table_total is not None:
                rep.recomputed_total = table_total
            if claimed is not None:
                rep.claimed_total = claimed
            # 严重度取决于**是否还能核对**，而不是格式好不好看：
            #   - 从表格行重算成功且与声称值一致 → 算术其实已经验过了，只是写法不规范 → warning
            #   - 重算失败或对不上 → 算术闸真的关掉了 → error
            # 早期实现一律判 error，导致 花知晓/depth_v1、depth_research_v1 这两份
            # **数字完全正确**（声称 3.45、重算 3.45）的报告被判严重问题。
            # 校验工具误报的代价是信任崩塌，所以严重度必须与实际风险挂钩。
            verified_via_table = (
                table_total is not None
                and claimed is not None
                and abs(table_total - claimed) <= 0.005
            )
            rep.issues.append(
                ScoringIssue(
                    file=file_label,
                    severity="warning" if verified_via_table else "error",
                    kind="缺少加权总分算式",
                    detail=(
                        "报告有可行性评分表，但没有可解析的「加权总分 = 0.25×… + … = X」一行。"
                        "把总分只写在表格单元格或建议段，会让算术闸失去主判据（depth_feas_v2 踩过）。"
                        + (
                            f" 本次已从表格各行重算为 {table_total:.2f}，与文中声称的 {claimed} 一致，"
                            "所以只作格式提醒；但请补回算式行，否则下次表格格式一变就查不了。"
                            if verified_via_table
                            else (
                                f" 从表行重算约为 {table_total:.2f}，文中声称 {claimed}。"
                                if table_total is not None and claimed is not None
                                else " 且无法从表格行重算，本份报告的加权算术**完全没有被检查过**。"
                            )
                        )
                    ),
                )
            )
            if (
                table_total is not None
                and claimed is not None
                and abs(table_total - claimed) > 0.005
            ):
                rep.issues.append(
                    ScoringIssue(
                        file=file_label,
                        severity="error",
                        kind="加权总分算错",
                        detail=(
                            f"报告写的总分是 {claimed}，按评分表各行重算应为 {table_total:.2f}"
                        ),
                    )
                )
        return rep

    rep.found_table = True
    pairs = _PAIR_RE.findall(total_line)
    if not pairs:
        rep.issues.append(
            ScoringIssue(
                file=file_label,
                severity="error",
                kind="加权式子无法解析",
                detail="找到「加权总分 =」但没解析出「权重×得分」项，无法核算",
                context=total_line.strip()[:160],
            )
        )
        return rep

    weights = [float(a) for a, _ in pairs]
    scores = [float(b) for _, b in pairs]
    recomputed = sum(w * s for w, s in zip(weights, scores))
    rep.recomputed_total = round(recomputed, 4)

    claimed_nums = _TRAILING_NUM_RE.findall(total_line)
    claimed = float(claimed_nums[-1]) if claimed_nums else None
    rep.claimed_total = claimed

    # 1) 权重和
    wsum = sum(weights)
    if abs(wsum - 1.0) > 0.005:
        rep.issues.append(
            ScoringIssue(
                file=file_label,
                severity="error",
                kind="权重和不等于 1",
                detail=f"各维权重相加 = {wsum:.3f}，不是 1.0，加权总分没有意义",
                context=total_line.strip()[:160],
            )
        )

    # 2) 得分越界
    bad = [s for s in scores if not (1 <= s <= 5)]
    if bad:
        rep.issues.append(
            ScoringIssue(
                file=file_label,
                severity="error",
                kind="维度得分越界",
                detail=f"得分必须在 1–5，出现 {bad}",
                context=total_line.strip()[:160],
            )
        )

    # 3) 算术
    if claimed is not None and abs(claimed - recomputed) > 0.005:
        rep.issues.append(
            ScoringIssue(
                file=file_label,
                severity="error",
                kind="加权总分算错",
                detail=(
                    f"报告写的总分是 {claimed}，按它自己列出的式子重算应为 {recomputed:.2f}"
                    f"（差 {abs(claimed - recomputed):.2f}）。"
                    f"两个分数对应的结论档位分别是「{_BAND_LABEL[_band_of(claimed)]}」"
                    f"和「{_BAND_LABEL[_band_of(recomputed)]}」"
                ),
                context=total_line.strip()[:160],
            )
        )

    # 4) 结论与总分是否一致 —— 以报告自己写的总分为准比对，
    #    因为读者看到的是那个数字；算术错误已在上一条单独报出。
    stated = _stated_conclusion_band(text)
    basis = claimed if claimed is not None else recomputed
    if stated is not None:
        want = _band_of(basis)
        if stated[0] != want:
            rep.issues.append(
                ScoringIssue(
                    file=file_label,
                    severity="error",
                    kind="结论与评分表矛盾",
                    detail=(
                        f"总分 {basis:.2f} 按阈值应判「{_BAND_LABEL[want]}」，"
                        f"但报告的结论写的是「{_BAND_LABEL[stated[0]]}」。"
                        "评分表若不能决定结论，它就只是装饰"
                    ),
                    context=stated[1][:160],
                )
            )
    else:
        rep.issues.append(
            ScoringIssue(
                file=file_label,
                severity="warning",
                kind="未找到结论档位",
                detail="报告开头没有可识别的结论措辞，无法核对它与评分表是否一致",
            )
        )

    return rep


def check_scoring_files(paths: list[Path]) -> list[ScoringReport]:
    reports: list[ScoringReport] = []
    for p in paths:
        if not p.exists():
            continue
        rep = check_scoring_text(p.read_text(encoding="utf-8", errors="ignore"), str(p))
        if rep.found_table:
            reports.append(rep)
    return reports


def render_scoring_reports(reports: list[ScoringReport]) -> str:
    lines = ["=" * 78, "评分表自洽性校验", "=" * 78]
    if not reports:
        lines.append("（本次产出里没有找到评分表，跳过）")
        return "\n".join(lines)

    total_err = 0
    for rep in reports:
        name = Path(rep.file).name
        head = f"\n{name}：报告总分 {rep.claimed_total}，重算 {rep.recomputed_total}"
        lines.append(head)
        if not rep.issues:
            lines.append("  ✅ 权重、算术、结论档位全部自洽")
            continue
        for i in rep.issues:
            mark = "✖" if i.severity == "error" else "⚠"
            if i.severity == "error":
                total_err += 1
            lines.append(f"  {mark} 【{i.kind}】{i.detail}")
            if i.context:
                lines.append(f"     出处：{i.context}")

    lines.append("")
    if total_err:
        lines.append(
            f"合计 {total_err} 处严重问题。注意这类错误特别隐蔽：式子和数字都写得整整齐齐，"
            "不重算发现不了，而它恰恰在整份报告最关键的那一行上。"
        )
    else:
        lines.append("全部通过。")
    return "\n".join(lines)
