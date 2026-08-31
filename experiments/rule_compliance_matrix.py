"""跨版本规则遵守率矩阵：把散落在各版 changelog 里的结论变成一张可复算的表。

动机：之前每次都是「跑一版 → 人工通读 → 工具扫一遍 → 写 changelog」，
结论散在 6 份 changelog 里，没法回答「假域名到底是稳定消失了还是运气好」
这类跨版本问题。本脚本遍历所有归档版本，用同一套 citation_check 逻辑重扫，
按「版本 × 问题类型」聚合。

关键设计：
- 零 API 成本，只读已归档的 md
- 用**当前**版本的检测规则回溯扫描所有历史版本，所以历史版本的数字会比
  当年 changelog 里记的高（当年工具还没这些检测）——这是特性不是 bug，
  表格里会标注出来
- 跨案例分组：东边野兽（英国/护肤）和花知晓（泰国/彩妆）不混在一起比绝对值
- 除了绝对数量，还算「每 10 个 URL 的问题密度」，避免长报告天然显得问题多

用法：
    PYTHONPATH=. python experiments/rule_compliance_matrix.py
    PYTHONPATH=. python experiments/rule_compliance_matrix.py --markdown
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from marketing_crew.citation_check import check_text  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# 标准的研究产出。
# `evidence_gap_fill.md` 是后来新增的「缺口二轮补证」步骤，早期版本没有这个文件——
# 扫描时按存在与否处理，所以老版本不会因为缺它而报错。
# 曾经漏掉这一项，导致矩阵报花知晓 backup_v4 是 31 个 URL，而按四份产出实测是 37 个，
# 与 README 里的数字对不上。
TARGET_FILES = (
    "market_feasibility.md",
    "evidence_gap_fill.md",
    "market_expansion.md",
    "competitor_battlecard.md",
    # agentic 对照实验的产出用的是另一个文件名。漏掉它会让 agentic_v1/agentic_v2
    # 两个版本在矩阵里显示为「无产出」而被整行跳过——也就是**对照组根本没进对照表**。
    # 这跟之前漏掉 evidence_gap_fill.md 导致 URL 数少算 6 个是同一类错误：
    # 统计口径漏了一个文件，结论看起来照样成立，所以不会有人发现。
    "competitor_battlecard_agentic.md",
)

# 案例分组：目录名 → (显示名, 目标市场地区码)
# 地区码用于「他国站点当本地商品页」检测；不同案例不能混比绝对值
CASE_GROUPS = {
    "东边野兽": ("东边野兽 → 英国（护肤）", "uk"),
    "花知晓": ("花知晓 → 泰国（彩妆）", "th"),
    "石头科技": ("石头科技 → 德国（家电）", "de"),
}

# 问题类型的展示顺序与简称（对应 citation_check 里的 Issue.kind）
KIND_COLUMNS = [
    ("占位/假域名", "假域名"),
    ("未填模板占位符", "未填模板"),
    ("TBD 占位符代替证据", "TBD"),
    ("品牌首页当商品页", "品牌首页"),
    ("媒体文章页当商品页", "媒体页"),
    ("跨境代购站当本地零售证据", "跨境站"),
    ("他国站点当本地商品页", "他国站点"),
    ("疑似国际站冒充本地站", "国际站"),
    ("无来源数字（兜底措辞不豁免）", "无源数字"),
    ("市场份额/舆论缺证据", "舆论无源"),
    ("社媒账号页当舆论证据", "社媒主页"),
    ("研究机构首页当证据", "机构首页"),
    ("裸域名首页当证据", "裸域名"),
    ("疑似分类/系列页当商品页", "分类页"),
    ("参考文献退化", "参考退化"),
]


@dataclass
class VersionResult:
    case: str
    version: str
    locale: str
    url_count: int = 0
    file_count: int = 0
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_errors(self) -> int:
        return self._total("error")

    @property
    def total_warnings(self) -> int:
        return self._total("warning")

    def _total(self, severity: str) -> int:
        return sum(v for (k, sev), v in self._by_sev.items() if sev == severity)

    _by_sev: dict[tuple[str, str], int] = field(default_factory=dict)

    @property
    def density(self) -> float:
        """每 10 个 URL 的严重问题数，用于抵消报告长短带来的偏差。"""
        if not self.url_count:
            return 0.0
        return round(self.total_errors / self.url_count * 10, 1)


def discover_versions() -> list[tuple[str, str, Path, str]]:
    """返回 (案例目录名, 版本名, 版本路径, 地区码)，按案例和版本排序。"""
    found: list[tuple[str, str, Path, str]] = []
    for case_dir, (_, locale) in CASE_GROUPS.items():
        base = OUTPUTS_DIR / case_dir
        if not base.is_dir():
            continue
        for version_dir in sorted(base.iterdir()):
            if not version_dir.is_dir():
                continue
            if not any((version_dir / f).exists() for f in TARGET_FILES):
                continue
            found.append((case_dir, version_dir.name, version_dir, locale))
    return found


def _sort_key(version: str) -> tuple:
    """backup_v4.1 排在 backup_v4 之后、backup_v5 之前。"""
    digits = "".join(c if (c.isdigit() or c == ".") else " " for c in version).split()
    if not digits:
        return (999.0,)
    try:
        return (float(digits[0]),)
    except ValueError:
        return (999.0,)


def scan_version(case: str, version: str, path: Path, locale: str) -> VersionResult:
    result = VersionResult(case=case, version=version, locale=locale)
    for filename in TARGET_FILES:
        file_path = path / filename
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        report = check_text(text, file_label=filename, expected_locale=locale)
        result.file_count += 1
        result.url_count += report.url_count
        for issue in report.issues:
            result.counts[issue.kind] = result.counts.get(issue.kind, 0) + 1
            key = (issue.kind, issue.severity)
            result._by_sev[key] = result._by_sev.get(key, 0) + 1
    return result


def render_terminal(results: list[VersionResult]) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("跨版本规则遵守率矩阵")
    lines.append("（用当前检测规则回溯扫描所有历史版本，数字可能高于当年 changelog）")
    lines.append("=" * 78)

    for case_dir, (display, _) in CASE_GROUPS.items():
        group = [r for r in results if r.case == case_dir]
        if not group:
            continue
        lines.append(f"\n## {display}\n")
        header = f"{'版本':<14}{'URL':>5}{'严重':>5}{'警告':>5}{'密度':>7}   问题明细"
        lines.append(header)
        lines.append("-" * 78)
        for r in group:
            detail_parts = []
            for kind, short in KIND_COLUMNS:
                n = r.counts.get(kind, 0)
                if n:
                    detail_parts.append(f"{short}×{n}")
            if r.url_count == 0:
                # 0 个 URL 不是「干净」，是压根没有引用纪律——比有问题更糟
                detail = "⚠ 全文零引用（无证据可查，不等于干净）"
            elif detail_parts:
                detail = " ".join(detail_parts)
            else:
                detail = "（干净）"
            lines.append(
                f"{r.version:<14}{r.url_count:>5}{r.total_errors:>5}"
                f"{r.total_warnings:>5}{r.density:>7}   {detail}"
            )
    lines.append("\n密度 = 每 10 个 URL 的严重问题数（抵消报告长短差异）")
    lines.append("注意：URL 数为 0 的版本不是「合格」，是全文没有任何可核查引用，")
    lines.append("      密度指标对它没有意义，不要与有引用的版本直接比较。")
    return "\n".join(lines)


def render_markdown(results: list[VersionResult]) -> str:
    lines: list[str] = []
    lines.append("## 跨版本规则遵守率矩阵")
    lines.append("")
    lines.append(
        "> 用**当前**检测规则回溯扫描所有历史版本，因此数字可能高于各版 changelog "
        "当年记录的值（当年工具还没有这些检测）。跨案例不可直接比绝对值。"
    )

    for case_dir, (display, _) in CASE_GROUPS.items():
        group = [r for r in results if r.case == case_dir]
        if not group:
            continue
        lines.append("")
        lines.append(f"### {display}")
        lines.append("")
        heads = ["版本", "URL 数", "严重", "警告", "密度"] + [s for _, s in KIND_COLUMNS]
        lines.append("| " + " | ".join(heads) + " |")
        lines.append("|" + "|".join(["---"] * len(heads)) + "|")
        for r in group:
            cells = [
                r.version,
                str(r.url_count),
                str(r.total_errors),
                str(r.total_warnings),
                str(r.density),
            ]
            for kind, _ in KIND_COLUMNS:
                n = r.counts.get(kind, 0)
                cells.append(str(n) if n else "-")
            lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("密度 = 每 10 个 URL 的严重问题数（抵消报告长短带来的偏差）。")
    return "\n".join(lines)


def render_findings(results: list[VersionResult]) -> str:
    """自动回答几个跨版本问题，避免人工数表格。"""
    lines: list[str] = ["", "=" * 78, "自动结论", "=" * 78]

    def series(case: str, kind: str) -> list[tuple[str, int]]:
        return [(r.version, r.counts.get(kind, 0)) for r in results if r.case == case]

    # 0. 零引用版本（最容易被「干净」误导的情况）
    empty = [f"{r.case}/{r.version}" for r in results if r.url_count == 0]
    if empty:
        lines.append(
            f"0. 全文零引用的版本：{', '.join(empty)} —— "
            "这些版本没有任何可核查 URL，机械校验查不出问题不代表质量好，"
            "恰恰说明当时还没有引用纪律"
        )

    # 1. 假域名是否稳定消失
    hb = series("东边野兽", "占位/假域名")
    if hb:
        nonzero = [v for v, n in hb if n]
        if nonzero:
            lines.append(
                f"1. 假域名：出现在 {', '.join(nonzero)}；"
                f"其余 {len([1 for _, n in hb if not n])} 个版本为 0"
            )
        else:
            lines.append(f"1. 假域名：{len(hb)} 个版本全部为 0（东边野兽案例）")

    # 2. 舆论无源是否连续多版未遵守
    for case in CASE_GROUPS:
        s = series(case, "市场份额/舆论缺证据")
        if not s:
            continue
        streak = [v for v, n in s if n]
        if streak:
            lines.append(
                f"2. 舆论/口碑缺来源（{case}）：{len(streak)}/{len(s)} 个版本存在，"
                f"分别是 {', '.join(streak)}"
            )

    # 3. 新检测在旧版本上的回溯结果
    new_kinds = [
        "TBD 占位符代替证据",
        "品牌首页当商品页",
        "无来源数字（兜底措辞不豁免）",
    ]
    for kind in new_kinds:
        hits = [
            f"{r.case}/{r.version}×{r.counts[kind]}" for r in results if r.counts.get(kind)
        ]
        label = dict(KIND_COLUMNS).get(kind, kind)
        lines.append(
            f"3. 新检测「{label}」回溯：" + (", ".join(hits) if hits else "所有版本均为 0")
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="跨版本规则遵守率矩阵")
    parser.add_argument("--markdown", action="store_true", help="输出 markdown 表格")
    args = parser.parse_args()

    versions = discover_versions()
    if not versions:
        print(f"没有在 {OUTPUTS_DIR} 下找到任何归档版本目录")
        raise SystemExit(1)

    results = [scan_version(c, v, p, loc) for c, v, p, loc in versions]
    results.sort(key=lambda r: (list(CASE_GROUPS).index(r.case), _sort_key(r.version)))

    if args.markdown:
        print(render_markdown(results))
    else:
        print(render_terminal(results))
        print(render_findings(results))


if __name__ == "__main__":
    main()
