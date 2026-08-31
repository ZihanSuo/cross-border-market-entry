from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 允许独立运行 / 被 run_ablation.py 以 `PYTHONPATH=.` 方式导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.marketing_crew.citation_check import check_text  # noqa: E402


@dataclass
class EvaluationMetrics:
    structure_completeness: float
    traceability_score: float
    channel_adaptation_score: float
    output_file_count: int
    total_chars: int
    fake_citation_count: int = 0
    suspect_citation_count: int = 0
    citation_validity_score: float = 1.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "structure_completeness": round(self.structure_completeness, 4),
            "traceability_score": round(self.traceability_score, 4),
            "channel_adaptation_score": round(self.channel_adaptation_score, 4),
            "output_file_count": self.output_file_count,
            "total_chars": self.total_chars,
            "fake_citation_count": self.fake_citation_count,
            "suspect_citation_count": self.suspect_citation_count,
            "citation_validity_score": round(self.citation_validity_score, 4),
        }


REQUIRED_SECTIONS = [
    "市场",
    "竞品",
    "策略",
    "小红书",
    "抖音",
]

TRACEABILITY_MARKERS = [
    "来源",
    "source",
    "http://",
    "https://",
]

CHANNEL_MARKERS = {
    "xhs": ["小红书", "笔记", "种草", "标题", "标签"],
    "douyin": ["抖音", "投流", "脚本", "3秒", "完播"],
}


def _safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def evaluate_output_files(files: list[Path]) -> EvaluationMetrics:
    contents = [_safe_read(path) for path in files if path.exists()]
    merged = "\n".join(contents)
    total_chars = len(merged)
    if not merged:
        return EvaluationMetrics(0.0, 0.0, 0.0, 0, 0)

    section_hits = sum(1 for sec in REQUIRED_SECTIONS if sec in merged)
    structure_completeness = section_hits / len(REQUIRED_SECTIONS)

    trace_hits = sum(len(re.findall(re.escape(marker), merged, flags=re.IGNORECASE)) for marker in TRACEABILITY_MARKERS)
    raw_traceability_score = min(1.0, trace_hits / 12.0)

    xhs_hit = sum(1 for marker in CHANNEL_MARKERS["xhs"] if marker in merged) / len(CHANNEL_MARKERS["xhs"])
    dy_hit = sum(1 for marker in CHANNEL_MARKERS["douyin"] if marker in merged) / len(CHANNEL_MARKERS["douyin"])
    channel_adaptation_score = (xhs_hit + dy_hit) / 2

    # `raw_traceability_score` 只是数 http(s):// 出现次数，example.com 也算满分——
    # 用 citation_check 做一次真实性核查，把假引用从"可追溯"里扣掉。
    citation_report = check_text(merged, file_label="merged")
    fake_citation_count = sum(1 for i in citation_report.issues if i.kind == "占位/假域名")
    suspect_citation_count = sum(1 for i in citation_report.issues if i.severity == "warning")
    total_urls = citation_report.url_count

    if total_urls == 0:
        citation_validity_score = 0.0 if trace_hits > 0 else 1.0  # 声称有来源却一个 URL 都没有 -> 0
    else:
        citation_validity_score = max(0.0, 1.0 - (fake_citation_count / total_urls))

    traceability_score = raw_traceability_score * citation_validity_score

    return EvaluationMetrics(
        structure_completeness=structure_completeness,
        traceability_score=traceability_score,
        channel_adaptation_score=channel_adaptation_score,
        output_file_count=len(contents),
        total_chars=total_chars,
        fake_citation_count=fake_citation_count,
        suspect_citation_count=suspect_citation_count,
        citation_validity_score=citation_validity_score,
    )

