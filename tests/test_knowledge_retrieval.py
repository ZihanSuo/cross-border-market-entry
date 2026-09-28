"""检索式知识加载的回归测试。

检索模式最容易出的三种错，每条对应一个用例：
1. 跨市场串包：德国报告检索到泰国规则（registry 当初就是为堵这个）
2. 硬规则被检索漏掉：来源规则必须整份加载，不能看检索分数
3. 默认行为被改：不开检索时，registry 模式必须和改动前逐字一致（冻结产物依赖它）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketing_crew.config_loader import build_task_description  # noqa: E402
from src.marketing_crew.knowledge_retrieval import (  # noqa: E402
    retrieve,
    split_markdown,
    tokenize,
)

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
CONFIG = ROOT / "src" / "marketing_crew" / "config"

SPEC_REGISTRY = {
    "description": "评估目标市场的合规要求与认证门槛。\n{brief}",
    "include_global_knowledge": False,
    "knowledge_mode": "registry",
}
SPEC_RETRIEVAL = {**SPEC_REGISTRY, "knowledge_mode": "retrieval", "knowledge_top_k": 2}


def _core_text() -> str:
    return (KNOWLEDGE / "core" / "source_rules.md").read_text(encoding="utf-8").strip()


def test_tokenize_mixes_chinese_bigrams_and_latin_words():
    assert tokenize("CE认证") == ["ce", "认证"]
    assert tokenize("德国市场") == ["德国", "国市", "市场"]


def test_split_markdown_by_h2_keeps_heading_context():
    content = (KNOWLEDGE / "markets" / "germany.md").read_text(encoding="utf-8")
    chunks = split_markdown("markets/germany.md", content)
    assert len(chunks) >= 5
    assert any("监管与合规" in c.heading for c in chunks)
    assert all(c.heading.startswith("德国市场包") for c in chunks)


def test_retrieve_ranks_compliance_section_for_compliance_query():
    content = (KNOWLEDGE / "markets" / "germany.md").read_text(encoding="utf-8")
    chunks = split_markdown("markets/germany.md", content)
    top = retrieve("监管与合规 认证 要求", chunks, top_k=1)
    assert top and "监管与合规" in top[0].heading


def test_retrieval_mode_never_leaks_other_market():
    text = build_task_description(SPEC_RETRIEVAL, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    assert "泰国市场包" not in text


def test_retrieval_mode_always_keeps_core_rules_in_full():
    text = build_task_description(SPEC_RETRIEVAL, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    assert _core_text() in text


def test_retrieval_mode_loads_less_than_registry_mode():
    full = build_task_description(SPEC_REGISTRY, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    slim = build_task_description(SPEC_RETRIEVAL, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    assert len(slim) < len(full)


def test_registry_mode_unchanged_when_retrieval_off():
    os.environ.pop("KNOWLEDGE_RETRIEVAL", None)
    text = build_task_description(SPEC_REGISTRY, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    germany = (KNOWLEDGE / "markets" / "germany.md").read_text(encoding="utf-8").strip()
    assert germany in text


def test_env_flag_switches_registry_tasks_to_retrieval():
    os.environ["KNOWLEDGE_RETRIEVAL"] = "1"
    try:
        text = build_task_description(SPEC_REGISTRY, CONFIG, KNOWLEDGE, "目标市场：德国", "德国")
    finally:
        os.environ.pop("KNOWLEDGE_RETRIEVAL", None)
    assert "<!-- 检索自 markets/" in text


def test_pinned_sections_always_loaded_even_if_query_misses():
    """德国对照实验：「第三方测评（务必重视）」曾因关键词重合度不高被检索漏掉。"""
    content = (KNOWLEDGE / "markets" / "germany.md").read_text(encoding="utf-8")
    chunks = split_markdown("markets/germany.md", content)
    picked = retrieve("完全无关的查询词", chunks, top_k=1)
    headings = [c.heading for c in picked]
    assert any("务必重视" in h for h in headings)
    assert any("优先检索" in h for h in headings)


def test_focused_query_is_used_when_given():
    spec = {**SPEC_RETRIEVAL, "knowledge_top_k": 1}
    text = build_task_description(
        spec, CONFIG, KNOWLEDGE, "目标市场：德国", "德国",
        retrieval_query="渠道可达性：Amazon.de、MediaMarkt/Saturn、Otto",
    )
    assert "渠道结构" in text
