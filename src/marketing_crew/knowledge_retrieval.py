"""检索式知识加载（RAG 的最小实现）。

## 为什么要有这个模式

`knowledge_mode: registry` 会把目标市场的知识包**整份**拼进提示词。
知识包现在每份几 KB，整份加载没问题；但市场和规则越加越多之后，
整份加载会挤占上下文，也会把和当前任务无关的规则一起塞给模型。

检索模式把这一步改成「先检索、再注入」：

1. registry 先圈定范围（元数据过滤）——德国报告只在德国知识包里检索，
   不会检索到泰国规则。这是 registry 当初要解决的「跨市场串包」问题，检索模式必须保留。
2. 核心规则（`core_files`，如来源硬规则）**整份加载，不参与检索**：硬规则不能因为
   检索没命中就被漏掉。
3. 市场知识包按 `##` 标题切块。标题带「务必重视」「优先检索」的段落始终加载；
   其余段落用 brief 的目标和重点关注领域当查询，BM25 打分取 top-k。

## 检索器的选择

用的是 BM25 关键词检索（中文按相邻两字切词），纯标准库、零依赖、结果可复算。
没有用向量检索：知识包目前只有几十个段落，向量检索的收益不大，还会引入
embedding API 调用和缓存。检索器被隔离在 `rank_chunks()` 里，以后换成向量检索
只需要替换这一个函数。

## 怎么开

- 单个任务：task yaml 里写 `knowledge_mode: retrieval`（可选 `knowledge_top_k: 6`）
- 全局试验：环境变量 `KNOWLEDGE_RETRIEVAL=1`，所有 `registry` 模式的任务改走检索
- 默认关闭，已冻结的演示产出不受影响
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TOP_K = 6

# 知识包作者在标题里标注的必读段落：始终加载，不参与排名，也不占 top-k 名额。
# 来由：2026-09-28 德国对照实验里，「第三方测评（务必重视）」因关键词重合度不高没进前 6，
# 报告的测评一行随之失去证据链接。「会不会被检索到」不该决定「必读规则在不在」。
PINNED_MARKERS = ("务必重视", "优先检索")

_LATIN = re.compile(r"[a-z0-9]+")
_CJK = re.compile(r"[一-鿿]+")


@dataclass
class Chunk:
    source: str  # 知识包文件名，如 markets/germany.md
    heading: str  # 所在章节，如「德国市场包 / 监管与合规」
    text: str  # 章节正文（含标题行）
    order: int  # 在全部候选块里的原始顺序，拼回时按原文顺序排


def tokenize(text: str) -> list[str]:
    """英文和数字按词切，中文按相邻两字切（单字段保留单字）。"""
    lowered = text.lower()
    tokens = _LATIN.findall(lowered)
    for run in _CJK.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def split_markdown(source: str, content: str, start_order: int = 0) -> list[Chunk]:
    """按二级标题切块；一级标题下、第一个二级标题前的导语单独成块。"""
    title = source
    chunks: list[Chunk] = []
    current_heading = ""
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            heading = f"{title} / {current_heading}" if current_heading else title
            chunks.append(Chunk(source, heading, body, start_order + len(chunks)))

    for line in content.splitlines():
        if line.startswith("# ") and not current_heading and not buffer:
            title = line[2:].strip()
            buffer.append(line)
            continue
        if line.startswith("## "):
            flush()
            buffer = [line]
            current_heading = line[3:].strip()
            continue
        buffer.append(line)
    flush()
    return chunks


def rank_chunks(query: str, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 打分。以后换向量检索只需替换这个函数。"""
    if not chunks:
        return []
    docs = [tokenize(c.heading + "\n" + c.text) for c in chunks]
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs or 1.0
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    query_terms = set(tokenize(query))

    scores: list[float] = []
    for d in docs:
        tf = Counter(d)
        dl = len(d)
        score = 0.0
        for term in query_terms:
            freq = tf.get(term)
            if not freq:
                continue
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append(score)
    return scores


def is_pinned(chunk: Chunk) -> bool:
    return any(marker in chunk.heading for marker in PINNED_MARKERS)


def retrieve(query: str, chunks: list[Chunk], top_k: int = DEFAULT_TOP_K) -> list[Chunk]:
    """必读段落 + 其余段落里得分最高的 top_k 块，按原文顺序返回。

    非必读段落全部零分时只返回必读段落；连必读段落都没有时返回空列表（调用方回退整份加载）。
    """
    pinned = [c for c in chunks if is_pinned(c)]
    rest = [c for c in chunks if not is_pinned(c)]
    scores = rank_chunks(query, rest)
    ranked = sorted(
        (pair for pair in zip(scores, rest) if pair[0] > 0),
        key=lambda pair: pair[0],
        reverse=True,
    )[:top_k]
    return sorted(pinned + [c for _, c in ranked], key=lambda c: c.order)


def build_retrieved_knowledge(
    knowledge_dir: Path,
    always_files: list[str],
    candidate_files: list[str],
    query: str,
    top_k: int = DEFAULT_TOP_K,
    verbose: bool = True,
) -> str:
    """核心文件整份加载 + 候选文件检索 top-k 块。"""
    sections: list[str] = []
    for filename in always_files:
        path = knowledge_dir / filename
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content and content not in sections:
                sections.append(content)

    chunks: list[Chunk] = []
    full_candidates: list[str] = []
    for filename in candidate_files:
        if filename in always_files:
            continue
        path = knowledge_dir / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        full_candidates.append(content.strip())
        chunks.extend(split_markdown(filename, content, start_order=len(chunks)))

    selected = retrieve(query, chunks, top_k)
    if selected:
        sections.extend(f"<!-- 检索自 {c.source} -->\n{c.text}" for c in selected)
    else:
        # 查询与知识包零重合时宁可整份加载，也不静默丢掉市场规则
        sections.extend(full_candidates)

    if verbose:
        full_chars = sum(len(t) for t in full_candidates)
        used_chars = sum(len(c.text) for c in selected) if selected else full_chars
        picked = "；".join(c.heading for c in selected) or "无命中，回退整份加载"
        print(
            f"[knowledge] retrieval: {len(selected)}/{len(chunks)} 块，"
            f"市场知识 {used_chars}/{full_chars} 字符｜{picked}"
        )

    return "\n\n".join(sections).strip()
