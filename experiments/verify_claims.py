"""交叉核对：把报告里的「已核实」逐条拿去跟工具审计日志对质。

## 为什么需要这个

agentic 竞品分析的第三次运行，审计日志证明模型**确实调用了 6 次抓取工具、
全部成功返回**。但对照之后发现四层问题：

1. **抓的是首页/分类页**：6 次里 4 次是裸域名首页（首页上没有单品标价）
2. **一次抓到的是机器人验证页**：Aesop 那次只返回 106 字符
   `"Just a moment... Enable JavaScript and cookies to continue"`，
   一个价格都没有——而报告写「已用 scrape_page 核实，页面显示标价 £34.00」
3. **报告里的 URL ≠ 实际抓的 URL**：实际抓 `aesop.co.uk/hand-and-body.html`，
   报告写 `aesop.co.uk/hand-and-body/hand-washes-and-balms/`（后者从没被抓过）
4. 拿洗手液/身体护理对标面部护肤

病因不是"模型不用工具"，而是**它把「调用过工具」等同于「完成了核实」**——
调了 6 次就心安理得地每行写「已核实」，从不检查抓回来的内容里有没有那个价格。
106 字符的拦截页和 14000 字符的首页，在它眼里都是"抓过了"。

所以「核实状态」这一栏不该由模型自己填。这个脚本用审计日志里的**客观记录**
自动判定每一条，三条判据都是确定的、不需要模型配合：

- 报告里的 URL 在审计日志里找不到 → **未抓取，该条核实为伪造**
- 抓到了但返回内容过短 → **抓取被拦截，内容无效**
- 抓到了但内容里找不到报告写的标价 → **页面中未找到该标价**

## 用法

    PYTHONPATH=. python experiments/verify_claims.py \\
        outputs/competitor_battlecard_agentic.md \\
        --audit outputs/tool_audit.jsonl

    # 输出 markdown 表格，可直接贴进 changelog
    PYTHONPATH=. python experiments/verify_claims.py <报告> --audit <日志> --markdown

## 局限

- 价格比对是字符串搜索（做了 £65/£65.00/65 等变体），页面用图片或 JS 渲染
  价格时会误判为"找不到"
- 审计日志只记录了返回内容的前 300 字符预览。**完整内容没有留存**，
  所以"页面中找不到标价"这一判据目前只能基于预览，可靠性有限——
  真正要用好这一条，需要先扩大审计日志保存的内容长度（见文末 TODO）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<!\()\bhttps?://[^\s)\]|]+")
_PRICE_RE = re.compile(r"[£$€฿¥]\s?\d[\d,]*(?:\.\d+)?")

# 返回内容短于这个长度，基本可以断定不是真实页面内容
# （Aesop 那次的机器人验证页只有 106 字符）
_MIN_VALID_CONTENT = 500

# 常见的反爬/拦截页特征
_BLOCK_MARKERS = (
    "just a moment",
    "enable javascript",
    "checking your browser",
    "access denied",
    "captcha",
    "are you a human",
    "cloudflare",
)


@dataclass
class ScrapeRecord:
    url: str
    status: str
    output_length: int
    output_preview: str

    @property
    def normalized(self) -> str:
        return _normalize_url(self.url)

    @property
    def looks_blocked(self) -> bool:
        low = self.output_preview.lower()
        return any(m in low for m in _BLOCK_MARKERS) or self.output_length < _MIN_VALID_CONTENT


@dataclass
class Claim:
    """报告里一条「已核实」声明。"""

    brand_hint: str
    url: str
    claimed_price: str
    raw_line: str

    verdict: str = ""
    detail: str = ""

    @property
    def is_fabricated(self) -> bool:
        return self.verdict in ("未抓取", "URL 不符")


def _normalize_url(u: str) -> str:
    """去掉尾斜杠、查询参数、www，便于比对。

    审计里 `drhauschka.com/?srsltid=xxx` 与报告里 `drhauschka.com` 应视为同一页；
    但 `aesop.co.uk/hand-and-body.html` 与 `aesop.co.uk/hand-and-body/hand-washes-and-balms/`
    是**不同**页面，不能归一成同一条。
    """
    try:
        p = urlparse(u.strip().rstrip(".,;)"))
    except ValueError:
        return u
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (p.path or "").rstrip("/")
    return f"{host}{path}"


def load_audit(path: Path) -> list[ScrapeRecord]:
    records: list[ScrapeRecord] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        args = str(row.get("args", ""))
        if not args.lower().startswith(("website_url=", "url=")):
            continue
        if row.get("status") == "started":
            continue
        records.append(
            ScrapeRecord(
                url=args.split("=", 1)[1],
                status=str(row.get("status", "")),
                output_length=int(row.get("output_length") or 0),
                output_preview=str(row.get("output_preview") or ""),
            )
        )
    return records


def extract_claims(text: str) -> list[Claim]:
    """抽出报告里带「核实」字样的行，配上同段落的 URL 与标价。"""
    claims: list[Claim] = []
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line or "核实" not in line:
            continue
        # 跳过表头与说明性文字
        if line.startswith("|") and "核实结果" in line:
            continue

        price = ""
        pm = _PRICE_RE.search(line)
        if pm:
            price = pm.group(0).replace(" ", "")

        urls = [m.group(2) for m in _MD_LINK_RE.finditer(line)]
        urls += [m.group(0) for m in _BARE_URL_RE.finditer(line)]

        # 「核实状态」常与 URL 分行写，往上找 4 行
        if not urls:
            for back in range(1, 5):
                if idx - back < 0:
                    break
                prev = lines[idx - back]
                found = [m.group(2) for m in _MD_LINK_RE.finditer(prev)]
                found += [m.group(0) for m in _BARE_URL_RE.finditer(prev)]
                if found:
                    urls = found
                    if not price:
                        pm2 = _PRICE_RE.search(prev)
                        if pm2:
                            price = pm2.group(0).replace(" ", "")
                    break
        if not price:
            for back in range(1, 5):
                if idx - back < 0:
                    break
                if "标价" in lines[idx - back] or "价格" in lines[idx - back]:
                    pm3 = _PRICE_RE.search(lines[idx - back])
                    if pm3:
                        price = pm3.group(0).replace(" ", "")
                        break

        brand = ""
        for back in range(0, 8):
            if idx - back < 0:
                break
            hm = re.match(r"#+\s*\d*\.?\s*(.+)", lines[idx - back].strip())
            if hm:
                brand = hm.group(1).strip()[:30]
                break

        for u in urls:
            claims.append(
                Claim(
                    brand_hint=brand,
                    url=u.rstrip(".,;)"),
                    claimed_price=price,
                    raw_line=line[:120],
                )
            )
    return claims


def _price_variants(price: str) -> list[str]:
    out = [price]
    m = re.match(r"([£$€฿¥])\s?([\d,]+(?:\.\d+)?)", price)
    if not m:
        return out
    sym, num = m.group(1), m.group(2).replace(",", "")
    out += [f"{sym}{num}", num]
    if "." in num:
        out.append(f"{sym}{num.split('.')[0]}")
    else:
        out.append(f"{sym}{num}.00")
    return list(dict.fromkeys(out))


def adjudicate(claims: list[Claim], records: list[ScrapeRecord]) -> None:
    by_url = {r.normalized: r for r in records}
    for c in claims:
        key = _normalize_url(c.url)
        rec = by_url.get(key)

        if rec is None:
            # 看是不是同域名的其它页面被抓了（说明抓 A 写 B）
            host = key.split("/")[0]
            same_host = [r for r in records if r.normalized.split("/")[0] == host]
            if same_host:
                c.verdict = "URL 不符"
                c.detail = (
                    f"报告写的这个页面从未被抓取；同域名下实际抓的是："
                    f"{', '.join(r.url[:60] for r in same_host[:2])}"
                )
            else:
                c.verdict = "未抓取"
                c.detail = "审计日志里没有任何针对该 URL 的抓取记录，「已核实」为伪造"
            continue

        if rec.status != "finished":
            c.verdict = "抓取失败"
            c.detail = f"审计记录状态为 {rec.status}，不可能得到页面内容"
            continue

        if rec.looks_blocked:
            c.verdict = "抓取被拦截"
            c.detail = (
                f"返回仅 {rec.output_length} 字符，内容为反爬/验证页"
                f"（{rec.output_preview[:60]}…），页面上没有任何标价"
            )
            continue

        path = urlparse(c.url).path.strip("/")
        page_kind = "首页" if not path else ("分类页" if path.count("/") < 1 else "深层页")

        if not c.claimed_price:
            c.verdict = "已抓取"
            c.detail = f"抓取成功（{rec.output_length} 字符，{page_kind}），该行未声明标价"
            continue

        variants = _price_variants(c.claimed_price)
        if any(v in rec.output_preview for v in variants):
            c.verdict = "已核实"
            c.detail = f"抓取内容预览中找到 {c.claimed_price}（{page_kind}）"
        else:
            saved = len(rec.output_preview)
            truncated = saved < rec.output_length
            c.verdict = "标价未见于内容"
            c.detail = (
                f"抓取成功（{rec.output_length} 字符，{page_kind}），"
                f"但审计日志保存的 {saved} 字符内容里没有 {c.claimed_price}"
            )
            if truncated:
                c.detail += (
                    "；⚠️ 内容被截断，价格可能在未保存的部分，此项仅为线索。"
                    "若日志是用旧版审计（只存 300 字符）生成的，重跑一次即可得到可靠判据"
                )
            else:
                c.detail += "；内容**完整保存**，因此这条判定是可靠的"
            if page_kind == "首页":
                c.detail += "。另：抓的是**网站首页**，首页通常不含单品标价"


_ICONS = {
    "已核实": "✅",
    "已抓取": "🟡",
    "标价未见于内容": "🟠",
    "抓取被拦截": "🔴",
    "抓取失败": "🔴",
    "URL 不符": "❌",
    "未抓取": "❌",
}


def render(claims: list[Claim], report_name: str, audit_name: str, n_records: int) -> str:
    lines = [
        "=" * 78,
        "「已核实」交叉核对（报告自述 vs 工具审计日志）",
        "=" * 78,
        f"报告：{report_name}",
        f"审计：{audit_name}（{n_records} 条抓取记录）",
    ]
    if not claims:
        lines.append("\n报告里没有找到带「核实」字样的声明。")
        return "\n".join(lines)

    for c in claims:
        icon = _ICONS.get(c.verdict, "？")
        lines.append(f"\n{icon} [{c.verdict}] {c.brand_hint or '(未识别品牌)'}")
        lines.append(f"     报告 URL: {c.url[:78]}")
        if c.claimed_price:
            lines.append(f"     声称标价: {c.claimed_price}")
        lines.append(f"     判定依据: {c.detail}")

    fab = [c for c in claims if c.is_fabricated]
    blocked = [c for c in claims if c.verdict in ("抓取被拦截", "抓取失败")]
    suspect = [c for c in claims if c.verdict == "标价未见于内容"]
    ok = [c for c in claims if c.verdict == "已核实"]

    lines.append("")
    lines.append("-" * 78)
    lines.append(
        f"汇总：{len(claims)} 条「已核实」声明｜"
        f"**确证伪造 {len(fab)}**｜抓取无效 {len(blocked)}｜标价存疑 {len(suspect)}｜通过 {len(ok)}"
    )
    if fab:
        lines.append("")
        lines.append("确证伪造 = 报告声称核实的 URL，审计日志里根本没有抓取记录。")
        lines.append("这一项是硬结论，不受预览截断等因素影响。")
    lines.append("")
    lines.append("局限：「标价未见于内容」是否可靠，取决于审计日志有没有完整保存页面内容。")
    lines.append("      每条判定依据里会写明内容是否被截断——截断的只算线索，完整的才是结论。")
    return "\n".join(lines)


def render_markdown(claims: list[Claim]) -> str:
    out = ["| 品牌 | 报告 URL | 声称标价 | 判定 | 依据 |", "|---|---|---|---|---|"]
    for c in claims:
        out.append(
            f"| {c.brand_hint or '-'} | {c.url} | {c.claimed_price or '-'} | "
            f"{_ICONS.get(c.verdict,'')} {c.verdict} | {c.detail} |"
        )
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="用工具审计日志核对报告里的「已核实」声明")
    p.add_argument("report", help="报告 md 文件")
    p.add_argument("--audit", default="outputs/tool_audit.jsonl", help="工具审计 jsonl")
    p.add_argument("--markdown", action="store_true", help="输出 markdown 表格")
    args = p.parse_args()

    rp = Path(args.report)
    if not rp.is_absolute():
        rp = PROJECT_ROOT / args.report
    ap = Path(args.audit)
    if not ap.is_absolute():
        ap = PROJECT_ROOT / args.audit

    if not rp.exists():
        print(f"找不到报告：{rp}")
        raise SystemExit(2)
    if not ap.exists():
        print(f"找不到审计日志：{ap}")
        print("提示：审计日志在跑 crew 时自动生成（除非用了 --no-tool-audit）")
        raise SystemExit(2)

    records = load_audit(ap)
    claims = extract_claims(rp.read_text(encoding="utf-8"))
    adjudicate(claims, records)

    print(render_markdown(claims) if args.markdown else render(claims, rp.name, ap.name, len(records)))


if __name__ == "__main__":
    main()
