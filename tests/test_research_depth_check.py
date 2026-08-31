"""Unit tests for research_depth_check retail-pivot markers.

出处：石头科技 depth_feas_v2 — 缺口块仍开放且查询全是态度/评测向
（sales data / Stiftung Warentest），触发 gap_fill_no_retail_pivot ×2。
artifact_check 已有 DE 零售 query markers，但 _angle_bucket 未对齐。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketing_crew.research_depth_check import (  # noqa: E402
    _angle_bucket,
    check_research_depth,
)
from src.marketing_crew.tool_audit import ToolCall  # noqa: E402


def _gap_call(query: str) -> ToolCall:
    return ToolCall(
        tool_name="search_the_internet_with_serper",
        agent_role="证据缺口补证研究员",
        args=f"search_query={query}",
        status="finished",
    )


def _feas_call(query: str) -> ToolCall:
    return ToolCall(
        tool_name="search_the_internet_with_serper",
        agent_role="跨境市场可行性研究员",
        args=f"search_query={query}",
        status="finished",
    )


class _FakeAudit:
    def __init__(self, calls: list[ToolCall]) -> None:
        self.calls = calls


# --------------------------------------------------------------------------
# _angle_bucket: DE / UK / TH markers + honesty (no bare brand fake-pass)
# --------------------------------------------------------------------------


def test_de_retail_queries_count_as_retail_pivot() -> None:
    de_retail = [
        "Roborock Zeo MediaMarkt Preis",
        "Waschtrockner site:mediamarkt.de",
        "Roborock Zeo site:amazon.de /dp/",
        "Waschmaschine Saturn Otto Idealo Vergleich",
        "amazon.de Roborock Zeo PDP",
        "media markt Waschtrockner €899",
        "Joybuy Roborock washer dryer Germany",
    ]
    for q in de_retail:
        assert _angle_bucket(q) == "retail_or_brand_channel", q


def test_de_attitude_queries_stay_attitude() -> None:
    """Stiftung Warentest / sales data / consumer attitude ≠ retail pivot."""
    attitude = [
        "Zeo series washing machine sales data in Germany",
        "Stiftung Warentest Roborock Zeo rating",
        "Germany consumer attitude towards Chinese brands white appliances",
        "market penetration rate of washing machines in Germany",
        "EU energy label ratings for washing machines Zeo series Roborock",
    ]
    for q in attitude:
        assert _angle_bucket(q) == "attitude_or_concept", q


def test_uk_and_th_retail_markers_still_work() -> None:
    assert _angle_bucket("Herbeast Cult Beauty Boots price") == "retail_or_brand_channel"
    assert _angle_bucket("Flower Knows site:konvy.com") == "retail_or_brand_channel"
    assert _angle_bucket("Mistine Shopee Lazada 在售") == "retail_or_brand_channel"


def test_bare_roborock_or_zeo_is_not_retail_pivot() -> None:
    """Do not fake-pass review/sales queries that only name the brand."""
    assert _angle_bucket("Roborock Zeo One review") == "attitude_or_concept"
    assert _angle_bucket("Zeo series Germany market share") == "attitude_or_concept"


# --------------------------------------------------------------------------
# gap_fill_no_retail_pivot on open DE gaps
# --------------------------------------------------------------------------


_OPEN_GAP_ATTITUDE = """本报告目标市场：德国；补证轮次：可行性后第二轮（Depth）

## 从上游提取的证据缺口

### 缺口 1: Zeo系列在德国的实际销量或市占率
- 已试检索角度：
  1. "Zeo series washing machine sales data in Germany"
  2. "market penetration rate of washing machines in Germany"
- 更新后状态：本轮检索无果。

### 缺口 2: Stiftung Warentest 对Zeo系列的具体评价
- 已试检索角度：
  1. "Stiftung Warentest Roborock Zeo rating"
  2. "Roborock Zeo One review"
- 更新后状态：本轮检索无果。
"""


_OPEN_GAP_WITH_DE_RETAIL = """本报告目标市场：德国；补证轮次：可行性后第二轮（Depth）

## 从上游提取的证据缺口

### 缺口 1: Zeo系列在德国的实际销量或市占率
- 已试检索角度：
  1. "Zeo series washing machine sales data in Germany"
  2. "Roborock Zeo MediaMarkt Preis site:mediamarkt.de"
- 更新后状态：本轮检索无果。

### 缺口 2: Stiftung Warentest 对Zeo系列的具体评价
- 已试检索角度：
  1. "Stiftung Warentest Roborock Zeo rating"
  2. "Roborock Zeo site:amazon.de PDP Preis"
- 更新后状态：仍证据不足。
"""


def test_open_de_gaps_without_retail_trigger_pivot_error(
    tmp_path: Path,
) -> None:
    gap_path = tmp_path / "evidence_gap_fill.md"
    gap_path.write_text(_OPEN_GAP_ATTITUDE, encoding="utf-8")
    audit = _FakeAudit(
        [
            _feas_call("Waschtrockner price site:amazon.de"),
            _gap_call("Zeo series washing machine sales data in Germany"),
            _gap_call("Stiftung Warentest Roborock Zeo rating"),
            _gap_call("market penetration rate of washing machines in Germany"),
        ]
    )
    report = check_research_depth(audit, gap_fill_path=gap_path)
    pivot_errs = [i for i in report.errors if i.code == "gap_fill_no_retail_pivot"]
    assert len(pivot_errs) == 2, [i.message for i in report.errors]


def test_open_de_gaps_with_retail_queries_clear_pivot_error(
    tmp_path: Path,
) -> None:
    gap_path = tmp_path / "evidence_gap_fill.md"
    gap_path.write_text(_OPEN_GAP_WITH_DE_RETAIL, encoding="utf-8")
    audit = _FakeAudit(
        [
            _feas_call("Waschtrockner price site:amazon.de"),
            _gap_call("Zeo series washing machine sales data in Germany"),
            _gap_call("Roborock Zeo MediaMarkt Preis site:mediamarkt.de"),
            _gap_call("Stiftung Warentest Roborock Zeo rating"),
            _gap_call("Roborock Zeo site:amazon.de PDP Preis"),
        ]
    )
    report = check_research_depth(audit, gap_fill_path=gap_path)
    assert not any(i.code == "gap_fill_no_retail_pivot" for i in report.errors), [
        i.message for i in report.errors
    ]
