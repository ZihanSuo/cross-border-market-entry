"""独立 URL 验证：由代码真的去抓报告里的链接，不相信报告里的「已核实」自述。

## 为什么需要这个

agentic 版竞品分析的第二次运行里，报告写着：

    代表 SKU：Aesop Parsley Seed Anti-Oxidant **Serum**
    商品页 URL：.../p/body/parley-seed-facial-hydrating-**cream**/
    核实状态：**已用 scrape_page 核实，页面显示标价 £65**

SKU 说精华、URL 说面霜，`parley` 还是拼错的——如果真抓过页面，不可能没发现
产品名对不上。**「已核实」是模型自己填的一栏，跟它之前声称「相关网页的抓取和
数据验证已成功完成」但报告里 0 个链接，是同一类问题：自我报告不可信。**

所以核实这件事必须由代码独立做一遍。这个脚本不问模型，直接：
1. 从报告里抽出所有 URL（重点是标了「商品页」的）
2. 真的发 HTTP 请求
3. 报告每条：能不能打开、页面标题是什么、报告里写的标价在页面上找不找得到

## 用法

    # 验证单份报告
    PYTHONPATH=. python experiments/verify_urls.py outputs/competitor_battlecard_agentic.md

    # 只验证商品页（跳过参考文献等）
    PYTHONPATH=. python experiments/verify_urls.py <file> --product-only

    # 输出 markdown 表格，可直接贴进 changelog
    PYTHONPATH=. python experiments/verify_urls.py <file> --markdown

## 局限（重要，别把结果当绝对判据）

- **抓不到 ≠ URL 是假的**：很多商业站点有反爬（403）、需要 JS 渲染、
  或按地区跳转。抓取失败只能说明"无法用简单请求核实"，不等于链接编造
- **价格匹配是字符串搜索**：页面上可能写 `£65.00` 而报告写 `£65`，
  脚本做了几种常见变体的匹配，但仍可能漏判
- 因此本脚本的定位是**给人工复核提供线索**，不是自动判罚
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<!\()\bhttps?://[^\s)\]|]+")
_PRICE_RE = re.compile(r"[£$€฿¥]\s?\d[\d,]*(?:\.\d+)?")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


@dataclass
class UrlCheck:
    url: str
    context_line: str = ""
    is_product_page: bool = False
    claimed_price: str = ""
    status: str = ""        # ok / http_error / network_error
    http_code: int = 0
    page_title: str = ""
    price_found: str = ""   # found / not_found / n/a
    note: str = ""

    @property
    def verdict(self) -> str:
        if self.status != "ok":
            return f"无法核实（{self.note}）"
        if not self.claimed_price:
            return "页面可访问（报告未在此行给出标价，无从比对）"
        if self.price_found == "found":
            return f"页面可访问，且找到标价 {self.claimed_price}"
        return f"⚠ 页面可访问，但**页面上找不到** {self.claimed_price}"


def extract_urls_with_context(text: str, product_only: bool) -> list[UrlCheck]:
    """按行抽取 URL，并记录该行是否是「商品页」、该行/邻近是否写了标价。"""
    checks: list[UrlCheck] = []
    lines = text.splitlines()
    seen: set[str] = set()

    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        urls = [m.group(2) for m in _MD_LINK_RE.finditer(line)]
        urls += [m.group(0) for m in _BARE_URL_RE.finditer(line)]
        if not urls:
            continue

        is_product = "商品页" in line or "代表 SKU" in line
        if product_only and not is_product:
            continue

        # 标价：先看本行，再往上找 3 行（常见写法是标价与 URL 分行）
        price = ""
        m = _PRICE_RE.search(line)
        if m:
            price = m.group(0).replace(" ", "")
        else:
            for back in range(1, 4):
                if idx - back < 0:
                    break
                prev = lines[idx - back]
                if "标价" in prev or "价格" in prev:
                    pm = _PRICE_RE.search(prev)
                    if pm:
                        price = pm.group(0).replace(" ", "")
                        break

        for u in urls:
            u = u.rstrip(".,;)")
            key = (u, is_product)
            if key in seen:
                continue
            seen.add(key)  # type: ignore[arg-type]
            checks.append(
                UrlCheck(
                    url=u,
                    context_line=line[:110],
                    is_product_page=is_product,
                    claimed_price=price,
                )
            )
    return checks


def _price_variants(price: str) -> list[str]:
    """£65 → ['£65', '£65.00', '65.00', '65']，提高匹配命中率。"""
    out = [price]
    m = re.match(r"([£$€฿¥])\s?([\d,]+(?:\.\d+)?)", price)
    if not m:
        return out
    sym, num = m.group(1), m.group(2).replace(",", "")
    out.append(f"{sym}{num}")
    if "." in num:
        out.append(f"{sym}{num.split('.')[0]}")
        out.append(num)
    else:
        out.append(f"{sym}{num}.00")
        out.append(num)
    return list(dict.fromkeys(out))


def check_one(item: UrlCheck, timeout: int = 15) -> UrlCheck:
    try:
        import requests  # 延迟导入，--help 时不需要
    except ImportError:
        item.status = "network_error"
        item.note = "未安装 requests，pip install requests"
        return item

    try:
        resp = requests.get(
            item.url, timeout=timeout, headers={"User-Agent": UA}, allow_redirects=True
        )
        item.http_code = resp.status_code
        if resp.status_code >= 400:
            item.status = "http_error"
            item.note = f"HTTP {resp.status_code}"
            return item

        item.status = "ok"
        html = resp.text
        tm = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if tm:
            item.page_title = re.sub(r"\s+", " ", tm.group(1)).strip()[:90]

        if item.claimed_price:
            body = re.sub(r"<[^>]+>", " ", html)
            body = re.sub(r"\s+", " ", body)
            hit = any(v in body for v in _price_variants(item.claimed_price))
            item.price_found = "found" if hit else "not_found"
        else:
            item.price_found = "n/a"
        return item

    except Exception as exc:  # noqa: BLE001
        item.status = "network_error"
        item.note = f"{type(exc).__name__}"
        return item


def render_terminal(checks: list[UrlCheck], source: str) -> str:
    lines = ["=" * 78, f"URL 独立验证：{source}", "=" * 78, ""]
    prod = [c for c in checks if c.is_product_page]
    other = [c for c in checks if not c.is_product_page]

    def block(title: str, items: list[UrlCheck]) -> None:
        if not items:
            return
        lines.append(f"\n## {title}（{len(items)} 条）")
        for c in items:
            icon = {"ok": "✅", "http_error": "❌", "network_error": "⚠️"}.get(c.status, "?")
            if c.status == "ok" and c.price_found == "not_found":
                icon = "🔴"
            lines.append(f"\n{icon} {c.url}")
            if c.page_title:
                lines.append(f"     页面标题: {c.page_title}")
            lines.append(f"     结论: {c.verdict}")

    block("商品页 URL（重点核实对象）", prod)
    block("其它 URL", other)

    ok = sum(1 for c in checks if c.status == "ok")
    mismatch = sum(1 for c in checks if c.status == "ok" and c.price_found == "not_found")
    fail = len(checks) - ok
    lines.append("")
    lines.append("-" * 78)
    lines.append(
        f"汇总：{len(checks)} 条 URL｜可访问 {ok}｜无法访问 {fail}｜"
        f"**可访问但页面上找不到报告所写标价 {mismatch}**"
    )
    lines.append("")
    lines.append("局限：抓不到 ≠ 链接是编的（反爬/需 JS/地区跳转都会导致失败）；")
    lines.append("      价格比对是字符串搜索，页面用图片或 JS 渲染价格时会误判为找不到。")
    lines.append("      本脚本用于给人工复核提供线索，不作为自动判罚依据。")
    return "\n".join(lines)


def render_markdown(checks: list[UrlCheck]) -> str:
    lines = [
        "| URL | 类型 | 报告所写标价 | HTTP | 页面标题 | 核实结论 |",
        "|---|---|---|---|---|---|",
    ]
    for c in checks:
        kind = "商品页" if c.is_product_page else "其它"
        code = str(c.http_code or "-")
        title = (c.page_title or "-").replace("|", "／")
        lines.append(
            f"| {c.url} | {kind} | {c.claimed_price or '-'} | {code} | {title} | {c.verdict} |"
        )
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="独立验证报告里的 URL（不依赖模型自述）")
    p.add_argument("files", nargs="+", help="要验证的 md 文件")
    p.add_argument("--product-only", action="store_true", help="只验证标了「商品页」的 URL")
    p.add_argument("--markdown", action="store_true", help="输出 markdown 表格")
    p.add_argument("--delay", type=float, default=1.0, help="每次请求间隔秒数，默认 1.0")
    args = p.parse_args()

    for fp in args.files:
        path = Path(fp)
        if not path.is_absolute():
            path = PROJECT_ROOT / fp
        if not path.exists():
            print(f"找不到文件：{path}")
            continue

        text = path.read_text(encoding="utf-8")
        checks = extract_urls_with_context(text, args.product_only)
        if not checks:
            print(f"{path.name}: 没有找到需要验证的 URL")
            continue

        print(f"[验证] {path.name}：{len(checks)} 条 URL ...", flush=True)
        done: list[UrlCheck] = []
        for i, c in enumerate(checks, 1):
            print(f"  ({i}/{len(checks)}) {c.url[:70]} ...", flush=True)
            done.append(check_one(c))
            if i < len(checks):
                time.sleep(args.delay)

        print()
        print(render_markdown(done) if args.markdown else render_terminal(done, path.name))


if __name__ == "__main__":
    main()
