"""机械化引用校验：不依赖模型自评，直接用规则扫描输出文件里的 URL/参考文献质量。

动机：source_rules.md 和各 task 的 description 里写了大量"禁止 example.com / 禁止空引用 /
禁止拿首页当证据"的硬规则，但历史输出（见 outputs/backup_v3）证明模型经常不遵守，而现有的
`experiments/evaluate_outputs.py` 只是数 `https://` 出现次数，example.com 一样计满分。
本模块作为运行后的"事后把关"，不改模型行为，只负责把违规的地方明确列出来。

用法：
    from src.marketing_crew.citation_check import check_files
    report = check_files([Path("outputs/market_feasibility.md")])
    print(report.render())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

# 一眼假的占位域名：模型编造引用时最常用这些
FAKE_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "yourdomain.com",
    "placeholder.com",
    "test.com",
    "foo.com",
    "domain.com",
    "website.com",
    "somewebsite.com",
}

# 常被模型当"高置信度市场数据来源"乱用的机构首页；本身不是假的，
# 但 source_rules.md 明确禁止用它们的首页（而非具体报告页）当证据
KNOWN_RESEARCH_HOMEPAGES = {
    "statista.com",
    "mintel.com",
    "euromonitor.com",
    "grandviewresearch.com",
}

# 分类/系列页常见路径特征：competitor_analysis.yaml 硬规则 4 明确禁止用这类 URL
# 当"商品页"证据（历史上 backup_v4.1/v5 都出现过 Neal's Yard 用 /collections/xxx 冒充商品页）
_COLLECTION_PATH_MARKERS = (
    "collections/",
    "collection/",
    "categories/",
    "category/",
    "/c/",
    "all-brands/",
    "/brands/",
    "/brand/",
)

# 媒体/杂志站点：文章或榜单页不能当商品页证据（花知晓泰国案例里出现过拿
# cosmopolitan.com 的「2024 泰国必买美妆」文章当 4U2 的商品页）
_MEDIA_DOMAINS = {
    "cosmopolitan.com",
    "elle.com",
    "vogue.com",
    "harpersbazaar.com",
    "allure.com",
    "byrdie.com",
    "refinery29.com",
    "buzzfeed.com",
    "marieclaire.com",
    "glamour.com",
    "instyle.com",
    "wwd.com",
    "beautymatter.com",
    "cosmeticsdesign-asia.com",
    "graziamagazine.com",
}

# 跨境代购/转运平台：不能当作目标市场的本地零售证据
# （花知晓案例里出现过拿美国亚米网 yami.com/us/... 支撑泰铢标价）
_CROSS_BORDER_RESELLERS = {
    "yami.com",
    "ubuy.vn",
    "ubuy.com",
    "amazon.com",
}

# 站点路径里的国家/地区代码段，用来发现"他国站点当本地证据"
# URL 路径里可能出现的地区/语言段。用于「他国站点当本地商品页」检测。
# 加新市场时这里也要加，否则该市场的地区检测会**静默失效**——
# 路径里的地区段认不出来，`found` 为空，检查直接跳过且不报错。
# 这是漏检不是误判，但同样属于「没报错 ≠ 查过了」，所以与 registry.yaml 一起维护。
_LOCALE_SEGMENTS = {
    "us", "uk", "gb", "cn", "hk", "tw", "jp", "kr", "th", "vn",
    "sg", "my", "id", "ph", "au", "ca", "in",
    # 欧盟 27 国（与 knowledge/registry.yaml 的 locale 字段一一对应，
    # 由 tests/test_checks.py::test_eu_locales_are_known_to_citation_check 守着不漂移）
    "fr", "de", "it", "es", "nl", "pl", "se", "be", "at", "dk", "fi", "ie", "pt",
    "gr", "cz", "hu", "ro", "bg", "hr", "sk", "si", "lt", "lv", "ee", "lu", "mt", "cy",
}

# 占位符：模型用 TBD 之类的词代替证据，既没信息也逃过了"证据不足"的警示
# （花知晓泰国案例里评分表依据列 5 行全是 TBD，旧版校验工具完全放过）
#
# 注意：拉丁字母的占位符必须用词边界匹配，不能用子串——`n/a` 会命中
# `watsons.co.th/en/all-brands/...` 里的 "en/a"，`tbd` 也可能出现在 URL 短码里。
# 检测前还会先把 URL 从行里剔除，双保险。
# 占位符分两类，处理方式不同 —— 这是被一个误报逼出来的区分。
#
# 石头科技那轮，模型写了：
#     - 新事实：未找到 Stiftung Warentest 对 Zeo 系列的评测。 | URL: 未找到 | 级别 N/A
# 这**正是 brief 要求的诚实表述**（查不到就写未找到，禁止编造评级），却被判成违规。
# 根因是我把「TBD」和「N/A」当成了一回事，但它们的语义完全相反：
#
#   - **推诿型**（TBD / 待补充 / 待更新）：承诺「以后会有」，把空白伪装成待办。
#     这是纯粹的逃避，任何情况下都该拦。
#   - **声明型**（N/A / 不适用）：声明「这里本来就没有」。当证据确实不存在时，
#     「证据级别」这一栏无级别可填，写 N/A 是合理的，甚至比硬编一个级别诚实。
#
# 所以推诿型无条件拦；声明型只在**该行没有诚实说明缺失原因**时才拦。
_DEFERRAL_LATIN_RE = re.compile(r"(?<![a-z0-9])(tbd|to\s*be\s*determined)(?![a-z0-9])", re.IGNORECASE)
_NA_LATIN_RE = re.compile(r"(?<![a-z0-9])(n/a|n\.a\.)(?![a-z0-9])", re.IGNORECASE)
_TBD_CJK_PATTERNS = (
    "待更新",
    "待补充",
    "待确认链接",
    "链接待",
    "待检索",
    "待填",
    "待定",
)

# 诚实声明缺失的表述。同一行里出现这些词时，N/A 是与之一致的补充说明，
# 而不是在掩盖什么 —— 此时不再判为占位符违规。
#
# 注意这不会放过「有数字却没来源」的行：那由 `_check_evidence_lines` 的
# 数字关独立负责，且那一关不看这些词（加免责词不豁免含数字的断言）。
# 两关职责分明，所以这里放宽不会开出漏洞。
_HONEST_ABSENCE_RE = re.compile(
    r"(证据不足|未找到|未查到|查无|无公开|无法核实|尚未找到|未检索到|不适用|无相关)"
)

# competitor_analysis.yaml 要求 6：市场份额/舆论口碑必须有 URL，没有就得明确写"证据不足"类措辞，
# 不能两者都没有就直接下结论。用 expected_output 里实际的字段名前缀匹配（而不是松散关键词），
# 避免"承接上游要点"这类泛泛提到"市场份额"三个字的转述句被误判
_EVIDENCE_LINE_KEYWORDS = (
    "市场份额",
    "增长率",
    "公开舆论",
    "口碑线索",
)
_EVIDENCE_FALLBACK_MARKERS = ("证据不足", "待验证", "未找到", "尚无确切证据", "检索无果")

# 行内出现的具体数字（百分比、倍数、排名）。用于识别
# 「市场份额约为 30%（待验证）」这种写法：给了没来源的数字，
# 又用「待验证」当挡箭牌骗过 fallback 检测。有数字就必须有 URL，
# 兜底措辞只对**纯定性、不含数字**的句子有效。
_NUMERIC_CLAIM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|倍|名|位)")

# markdown 链接 [text](url) 和裸链接
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<!\()\bhttps?://[^\s)\]]+")

# 明显是没填完的模板占位符（参考文献表格里写死的 N/A | N/A | ...）
_TEMPLATE_PLACEHOLDER_RE = re.compile(r"N/A\s*\|\s*N/A", re.IGNORECASE)


@dataclass
class Issue:
    file: str
    severity: str  # "error" | "warning"
    kind: str
    detail: str
    context: str = ""

    def render(self) -> str:
        icon = "❌" if self.severity == "error" else "⚠️"
        line = f"{icon} [{self.kind}] {self.detail}"
        if self.context:
            line += f"\n     上下文: {self.context.strip()[:160]}"
        return line


@dataclass
class FileReport:
    file: str
    url_count: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass
class Report:
    file_reports: list[FileReport] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        return sum(fr.error_count for fr in self.file_reports)

    @property
    def total_warnings(self) -> int:
        return sum(fr.warning_count for fr in self.file_reports)

    @property
    def total_urls(self) -> int:
        return sum(fr.url_count for fr in self.file_reports)

    def render(self) -> str:
        lines: list[str] = []
        lines.append("=== 引用校验报告 ===")
        for fr in self.file_reports:
            lines.append(f"\n[{fr.file}]  共 {fr.url_count} 个 URL")
            if not fr.issues:
                lines.append("  ✅ 未发现假引用 / 占位符 / 可疑首页证据")
                continue
            for issue in fr.issues:
                for sub in issue.render().split("\n"):
                    lines.append("  " + sub)
        lines.append(
            f"\n汇总：{len(self.file_reports)} 个文件，{self.total_urls} 个 URL，"
            f"{self.total_errors} 处严重问题"
            f"（假域名/未填模板/TBD 占位符/媒体页当商品页/跨境代购站/他国站点/市场份额舆论缺证据），"
            f"{self.total_warnings} 处需人工复核（首页当证据/分类页当商品页/参考文献退化）"
        )
        if self.total_errors:
            lines.append("建议：严重问题必须重跑或人工改写对应段落，不要直接当成品交付。")
        return "\n".join(lines)


def _extract_urls(text: str) -> list[tuple[str, str]]:
    """返回 (url, 附近上下文) 列表，markdown 链接优先，兼容裸链接。"""
    found: list[tuple[str, str]] = []
    seen_spans: list[tuple[int, int]] = []

    for m in _MD_LINK_RE.finditer(text):
        url = m.group(2)
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 10)
        found.append((url, text[start:end]))
        seen_spans.append((m.start(), m.end()))

    for m in _BARE_URL_RE.finditer(text):
        if any(s <= m.start() < e for s, e in seen_spans):
            continue
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 10)
        found.append((m.group(0), text[start:end]))

    return found


# 判断一条 URL 是不是被当作"证据/依据"在用（而不是顺带提一句某平台的名字）。
# 用于「裸域名首页当证据」检测：只在证据位置报警，避免误伤正文里正常的平台提及。
_EVIDENCE_CONTEXT_MARKERS = (
    "依据",
    "证据",
    "来源",
    "参考",
    "URL",
    "url",
    "商品页",
    "代表 SKU",
    "置信度",
    "级别",
)


# 官方/政府域名：这类站点的首页或服务入口页本身就是合法证据
# （例如"须完成化妆品备案"这条结论，引用备案提交门户的入口页是恰当的），
# 不适用"首页证明不了具体结论"那条规则，否则会产生大量噪声。
_OFFICIAL_DOMAIN_SUFFIXES = (
    ".gov",
    ".gov.uk",
    ".service.gov.uk",
    ".go.th",
    ".go.jp",
    ".gov.sg",
    ".europa.eu",
    ".asean.org",
)


def _is_official_domain(host: str) -> bool:
    """域名是否属于官方/政府站点。

    注意要同时匹配「后缀」与「恰好等于」两种情况——`gov.uk` 本身就是一个有效域名，
    而 `"gov.uk".endswith(".gov.uk")` 是 False，只判后缀会漏掉它。
    """
    return any(
        host == suffix.lstrip(".") or host.endswith(suffix)
        for suffix in _OFFICIAL_DOMAIN_SUFFIXES
    )


def _is_evidence_context(context: str) -> bool:
    if any(marker in context for marker in _EVIDENCE_CONTEXT_MARKERS):
        return True
    # 表格单元格里的 URL 几乎一定是在当证据/依据用（证据摘要表、评分表、
    # 路径对比表、对比矩阵都是这个形态）。而上下文窗口只取前后几十个字符，
    # 常常截不到表头的「依据」「URL」字样——v7 里 `weleda.co.uk` 就在
    # 「| UK草本产品认知度 | 草本护肤市场 | [Weleda UK](...) | A |」这样的行里，
    # 靠关键词匹配会漏掉。
    if "|" in context:
        return True
    # markdown 链接形式 `[名字](url)` 本身就是"引用"的书写意图，与正文里
    # 顺带贴一个裸链接不同。v8 里 `[True Botanicals](https://truebotanicals.com/)`
    # 被用来支撑"品牌可见度高"这个结论，但那一行既不在表格里、也没有
    # 「依据」字样，纯关键词匹配漏掉了（是 QA 审校发现的）。
    return bool(_MD_LINK_RE.search(context))


# 目标市场对应的本地站点特征：域名后缀 + 路径里可能出现的地区段。
# 用于发现「国际站冒充本地站」——v7 里 `weleda.com/products/skin-food` 和
# `paiskincare.com/products/...` 标着 £ 价格，但都不是英国站，而旧的地区码检测
# 只看路径里的 /us/ /tw/ 这类片段，对这种"主域名 + 无地区码路径"完全失效。
LOCALE_SITE_HINTS: dict[str, dict[str, tuple[str, ...]]] = {
    "uk": {"tld": (".co.uk", ".uk"), "path": ("/uk/", "/en-gb/", "/gb/")},
    "th": {"tld": (".co.th", ".th"), "path": ("/th/", "/th-en/")},
    "jp": {"tld": (".co.jp", ".jp"), "path": ("/jp/", "/ja/")},
    "sg": {"tld": (".com.sg", ".sg"), "path": ("/sg/",)},
    "my": {"tld": (".com.my", ".my"), "path": ("/my/",)},
    "vn": {"tld": (".com.vn", ".vn"), "path": ("/vn/", "/vi/")},
}

_BOLD_LABEL_RE = re.compile(r"\*\*(.+?)\*\*")


def _is_evidence_field_line(line: str) -> bool:
    """这一行是不是「市场份额/舆论」这类**字段行**，而不是正文散文。

    只在字段标签位置匹配关键词，避免误伤正文里正常出现的说法
    （例："竞争对手壁垒高，新品牌难以获得市场份额" 是论述，不是数据字段）。
    字段行的形态：`- **公开舆论/口碑线索**：xxx` 或 `市场份额：xxx`。
    """
    labels: list[str] = _BOLD_LABEL_RE.findall(line)
    for sep in ("：", ":"):
        if sep in line:
            labels.append(line.split(sep, 1)[0])
    if not labels:
        return False
    return any(k in lbl for lbl in labels for k in _EVIDENCE_LINE_KEYWORDS)


# 社媒平台域名：品牌自己的主页/账号页不能当作"公开舆论/口碑"的证据
# （花知晓 v2 里三家竞品的舆论证据分别是 facebook.com/mistine、
# instagram.com/cathydolland、twitter.com/srichand——全是品牌自营账号，
# 证明不了公众口碑。这类 URL 有路径所以不算裸域名，旧检测完全漏掉）
_SOCIAL_PLATFORM_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "weibo.com",
    "xiaohongshu.com",
}


def _check_social_profile_as_sentiment(text: str, file_label: str) -> list[Issue]:
    """舆论/口碑字段引用社媒**账号主页**（而非具体帖子/评论）时报警。

    判定：域名在社媒名单里，且路径深度 <= 1（即 /brandname 这种账号页，
    不是 /brandname/posts/12345 这种具体内容页）。
    """
    issues: list[Issue] = []
    for line in text.splitlines():
        if not _is_evidence_field_line(line):
            continue
        if not any(k in line for k in ("公开舆论", "口碑线索", "舆论")):
            continue
        for url, _ in _extract_urls(line):
            host = _host_of(url)
            if host not in _SOCIAL_PLATFORM_DOMAINS:
                continue
            if _path_depth(url) <= 1:
                issues.append(
                    Issue(
                        file=file_label,
                        severity="error",
                        kind="社媒账号页当舆论证据",
                        detail=(
                            f"{url} 是社媒账号主页，不是具体的帖子/评论页；"
                            "品牌自己的账号页证明不了公众口碑，"
                            "需引用可核实的具体讨论内容（帖子、评论、测评文章）"
                        ),
                        context=line.strip(),
                    )
                )
    return issues


# SKU 名与 URL 路径的品类词对照表。
# 用于发现「报告写的产品」与「URL 指向的产品」不是同一个东西。
#
# 真实案例（跨 v4.1/v7/v8/agentic 四个版本没被任何一层发现）：
#   代表 SKU：Aesop Parsley Seed Anti-Oxidant **Serum**
#   商品页 URL：.../p/**body**/parley-seed-facial-hydrating-**cream**/
# SKU 说是精华、URL 说是面霜，路径分类段还写着 body（身体护理），
# 而报告声称"已用 scrape_page 核实，页面显示标价 £65"。
# 这类矛盾机械可查，不需要真的打开页面。
_CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "serum": ("serum", "精华液", "精华油", "精华"),
    "cream": ("cream", "面霜", "乳霜", "霜"),
    "cleanser": ("cleanser", "cleansing", "洁面", "洁颜"),
    "oil": ("facial-oil", "face-oil", "面部油"),
    "balm": ("balm", "膏"),
    "toner": ("toner", "爽肤水", "化妆水"),
    "mask": ("mask", "面膜"),
    "powder": ("powder", "散粉", "蜜粉"),
    "lipstick": ("lipstick", "口红", "唇膏"),
    "eyeshadow": ("eyeshadow", "eye-shadow", "眼影"),
    "sunscreen": ("sunscreen", "spf", "防晒"),
}

# URL 路径里的身体部位/大类段，与产品名里的部位词矛盾时报警
_BODY_PART_IN_PATH = ("/body/", "/hair/", "/hand/", "/foot/")
_FACE_TERMS = ("facial", "face", "面部", "面霜", "脸")


def _sku_url_conflict(sku_text: str, url: str) -> str:
    """返回冲突描述；无冲突返回空串。

    只在**两边都能明确识别出品类**时才判定冲突，避免误报。
    """
    sku_low = sku_text.lower()
    url_low = url.lower()

    # 1) 品类词冲突：SKU 说 serum，URL 说 cream
    sku_cats = {
        cat for cat, terms in _CATEGORY_TERMS.items()
        if any(t in sku_low for t in terms)
    }
    url_cats = {
        cat for cat, terms in _CATEGORY_TERMS.items()
        if any(t in url_low for t in terms)
    }
    if sku_cats and url_cats and not (sku_cats & url_cats):
        return (
            f"SKU 名显示品类为 {'/'.join(sorted(sku_cats))}，"
            f"但 URL 路径显示为 {'/'.join(sorted(url_cats))}"
        )

    # 2) 部位冲突：URL 路径分类段是 body/hair，产品名却是面部产品
    part = next((p for p in _BODY_PART_IN_PATH if p in url_low), "")
    if part and any(t in sku_low for t in _FACE_TERMS):
        return f"URL 路径含分类段 {part}（非面部），但 SKU 名是面部产品"

    return ""


def _check_sku_url_consistency(text: str, file_label: str) -> list[Issue]:
    """在「代表 SKU」与「商品页 URL」成对出现的段落里，核对两者品类是否一致。

    做法：按行扫描，记住最近一次看到的「代表 SKU」内容，
    遇到同一段落内的「商品页 URL」时做对照。
    """
    issues: list[Issue] = []
    current_sku = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "代表 SKU" in line or "代表SKU" in line:
            # 取冒号后的内容作为 SKU 名
            for sep in ("：", ":"):
                if sep in line:
                    current_sku = line.split(sep, 1)[1].strip().strip("*").strip()
                    break
            continue
        if not current_sku:
            continue
        if "商品页" not in line:
            continue
        for url, _ in _extract_urls(line):
            conflict = _sku_url_conflict(current_sku, url)
            if conflict:
                issues.append(
                    Issue(
                        file=file_label,
                        severity="error",
                        kind="SKU 名与 URL 品类矛盾",
                        detail=(
                            f"{conflict}；报告里的产品与链接指向的产品对不上，"
                            "这条引用不能支撑该 SKU 的标价"
                        ),
                        context=f"SKU「{current_sku}」 / {url}",
                    )
                )
        current_sku = ""
    return issues


def _check_evidence_lines(text: str, file_label: str) -> list[Issue]:
    """市场份额/舆论口碑这类行必须有 URL，没有 URL 时必须明确写"证据不足"类措辞，
    两者都没有就是硬规则 6 的违规（口头下结论但既无来源也不老实承认没来源）。"""
    issues: list[Issue] = []
    for line in text.splitlines():
        if not _is_evidence_field_line(line):
            continue
        has_url = "http://" in line or "https://" in line
        has_number = bool(_NUMERIC_CLAIM_RE.search(line))

        if has_url:
            # 有 URL 还不够——如果是数字类断言，来源必须是**具体页面**。
            #
            # 第七种规避方式（花知晓 backup_v5 实测发现）：
            #   「Mistine 在泰国市场占据约 15% 的市场份额（来源：cosmeticsdesign-asia.com/）」
            #   「Cathy Doll 占据约 12%（来源：beautymatter.com/）」
            # 给一个真实但**无关**的媒体首页，就绕过了「无来源数字」检测——
            # 因为确实有 URL。但媒体首页证明不了 15% 这个具体数字，
            # 等同于没有来源，只是伪装得更像。
            #
            # 判据：该行含数字，且**所有** URL 都是裸域名首页 → error。
            # 只要有一条带路径的 URL 就放行（那可能是真正的来源页）。
            if has_number:
                urls = [u for u, _ in _extract_urls(line)]
                non_official = [u for u in urls if not _is_official_domain(_host_of(u))]
                if non_official and all(_path_depth(u) == 0 for u in non_official):
                    issues.append(
                        Issue(
                            file=file_label,
                            severity="error",
                            kind="数字来源是裸域名首页",
                            detail=(
                                "该行给出了具体数字，但所有来源 URL 都是没有路径的域名首页"
                                f"（{', '.join(non_official[:2])}）；"
                                "首页证明不了这个具体数字，等同于无来源——"
                                "请换成刊载该数据的具体报告/文章页，或整行改写为「证据不足」"
                            ),
                            context=line.strip(),
                        )
                    )
            continue

        has_fallback = any(m in line for m in _EVIDENCE_FALLBACK_MARKERS)

        if has_number:
            # 有具体数字却没有 URL：无论有没有「待验证」都是违规。
            # 硬规则「无 https 不写数字」不接受任何兜底措辞。
            issues.append(
                Issue(
                    file=file_label,
                    severity="error",
                    kind="无来源数字（兜底措辞不豁免）",
                    detail=(
                        "该行给出了具体数字却没有任何 URL；"
                        "「待验证」「证据不足」这类措辞只能用于**不含数字**的定性描述，"
                        "不能拿来给无来源的数字背书（无 https 不写数字）"
                    ),
                    context=line.strip(),
                )
            )
            continue

        if not has_fallback:
            issues.append(
                Issue(
                    file=file_label,
                    severity="error",
                    kind="市场份额/舆论缺证据",
                    detail="该行提到市场份额/舆论/口碑但既没有 URL 也没有标注「证据不足」类措辞，属于口头下结论",
                    context=line.strip(),
                )
            )
    return issues


def _check_brand_homepage_as_product(url: str, context: str, file_label: str) -> list[Issue]:
    """商品页位置上出现"裸域名首页"——competitor_analysis.yaml 硬规则 4 第一条
    明确禁止用品牌首页当商品页，但旧版只认 statista/mintel 这几个研究机构域名，
    品牌自己的首页是盲区（花知晓 v1 里五家竞品商品页全是 mistine.com/ 这类首页）。
    """
    if "商品页" not in context and "代表 SKU" not in context:
        return []
    try:
        parsed = urlparse(url.rstrip(".,)"))
    except ValueError:
        return []
    path = (parsed.path or "").strip("/")
    if path:
        return []
    return [
        Issue(
            file=file_label,
            severity="error",
            kind="品牌首页当商品页",
            detail=(
                f"{url} 是裸域名首页，没有任何路径；"
                "商品页必须指向单一 SKU 的详情页，首页证明不了某个具体 SKU 的标价与在售状态"
            ),
            context=context,
        )
    ]


def _check_tbd_placeholders(text: str, file_label: str) -> list[Issue]:
    """TBD / 待更新 这类占位符不能代替证据。规则要求没证据就写「证据不足」。

    只在"看起来像证据位"的行上报错：表格行（含 |）或明确提到依据/URL/来源的行，
    避免把正文里正常出现的词误判。
    """
    issues: list[Issue] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # 先把 URL 整段剔除，避免把链接里的字符当成占位符（如 /en/all-brands/ 里的 "n/a"）
        stripped = _MD_LINK_RE.sub(" ", line)
        stripped = _BARE_URL_RE.sub(" ", stripped)

        # 1) 推诿型：无条件拦
        hit: str | None = None
        m = _DEFERRAL_LATIN_RE.search(stripped)
        if m:
            hit = m.group(1)
        else:
            hit = next((p for p in _TBD_CJK_PATTERNS if p in stripped), None)

        # 2) 声明型：只有在**没有诚实说明缺失**时才拦。
        #    「| URL: 未找到 | 级别 N/A」= 已说明，放行；
        #    「| URL: N/A | 市占 34%」= 没说明且在藏东西，仍然拦（且数字关会另行报错）。
        if not hit:
            m_na = _NA_LATIN_RE.search(stripped)
            if m_na and not _HONEST_ABSENCE_RE.search(stripped):
                hit = m_na.group(1)

        if not hit:
            continue
        # 只关心证据位：表格行，或提到 URL/依据/来源/链接/参考文献的行
        looks_like_evidence_slot = "|" in line or any(
            k in line for k in ("URL", "url", "依据", "来源", "链接", "参考文献", "证据")
        )
        if not looks_like_evidence_slot:
            continue
        issues.append(
            Issue(
                file=file_label,
                severity="error",
                kind="TBD 占位符代替证据",
                detail=(
                    f"该行用「{hit}」这类占位符占据了证据/URL 位置；"
                    "规则要求没有证据就写「证据不足」，TBD 把空白伪装成待办"
                ),
                context=line,
            )
        )
    return issues


def _check_product_page_quality(url: str, context: str, file_label: str) -> list[Issue]:
    """商品页 URL 的额外质量检查：媒体文章页、跨境代购站、他国站点。

    只在上下文提到「商品页」时才判定，避免把正常的媒体引用误报成商品页问题。
    """
    issues: list[Issue] = []
    if "商品页" not in context and "代表 SKU" not in context:
        return issues

    host = _host_of(url)
    if not host:
        return issues

    if host in _MEDIA_DOMAINS:
        issues.append(
            Issue(
                file=file_label,
                severity="error",
                kind="媒体文章页当商品页",
                detail=(
                    f"{url} 是媒体/杂志站点的文章或榜单页，不是商品页——"
                    "文章里提到了产品和价格也不行，competitor_analysis.yaml 硬规则 4 禁止这种用法"
                ),
                context=context,
            )
        )

    if host in _CROSS_BORDER_RESELLERS:
        issues.append(
            Issue(
                file=file_label,
                severity="error",
                kind="跨境代购站当本地零售证据",
                detail=(
                    f"{url} 是跨境代购/转运平台，不能当作目标市场的本地零售证据"
                    "（历史错误：用美国站页面支撑泰铢标价）"
                ),
                context=context,
            )
        )

    return issues


def check_locale_consistency(text: str, file_label: str, expected_locale: str = "") -> list[Issue]:
    """商品页 URL 的地区段与目标市场是否一致。

    expected_locale 传入目标市场的地区码（如 'th'）时才做严格判定；
    不传则只在同一文档内出现多个不同地区码时提示人工复核。
    """
    issues: list[Issue] = []
    if not expected_locale:
        return issues

    expected = expected_locale.strip().lower()
    for url, ctx in _extract_urls(text):
        if "商品页" not in ctx and "代表 SKU" not in ctx:
            continue
        try:
            parsed = urlparse(url.rstrip(".,)"))
        except ValueError:
            continue
        segments = [s.lower() for s in (parsed.path or "").split("/") if s]
        found = [s for s in segments if s in _LOCALE_SEGMENTS]
        if found and expected not in found:
            issues.append(
                Issue(
                    file=file_label,
                    severity="error",
                    kind="他国站点当本地商品页",
                    detail=(
                        f"{url} 路径里的地区段是 {found}，与目标市场 '{expected}' 不一致；"
                        "标价与在售状态须来自目标市场本地站点"
                    ),
                    context=ctx,
                )
            )
            continue

        # 盲区修补（v7 发现）：上面只看路径里的地区码，对「国际站主域名 + 路径无地区码」
        # 完全失效——weleda.com/products/skin-food 与 paiskincare.com/products/... 标着
        # £ 价格却都不是英国站，旧逻辑一个都没抓到。
        # 这里补一条：目标市场有已知的本地站特征时，既不是本地域名后缀、路径里也没有
        # 本地地区段的商品页，标 warning 让人工确认（不判 error，因为有些品牌确实
        # 只有单一全球站点，不宜一律当违规）。
        hints = LOCALE_SITE_HINTS.get(expected)
        if not hints:
            continue
        host = _host_of(url)
        path_lower = (parsed.path or "").lower()
        has_local_tld = any(host.endswith(tld) for tld in hints["tld"])
        has_local_path = any(seg in path_lower for seg in hints["path"])
        if not has_local_tld and not has_local_path:
            issues.append(
                Issue(
                    file=file_label,
                    severity="warning",
                    kind="疑似国际站冒充本地站",
                    detail=(
                        f"{url} 既不是 {expected} 的本地域名后缀（{'、'.join(hints['tld'])}），"
                        f"路径里也没有本地地区段（{'、'.join(hints['path'])}）；"
                        "该页的标价与在售状态未必适用于目标市场，需人工确认是否有本地站页面"
                    ),
                    context=ctx,
                )
            )
    return issues


def _path_depth(url: str) -> int:
    try:
        parsed = urlparse(url.rstrip(".,)"))
    except ValueError:
        return 0
    path = (parsed.path or "").strip("/")
    if not path:
        return 0
    return len([seg for seg in path.split("/") if seg])


def _host_of(url: str) -> str:
    try:
        host = (urlparse(url.rstrip(".,)")).netloc or "").lower()
    except ValueError:
        return ""
    host = host.split(":")[0]
    return host[4:] if host.startswith("www.") else host


_REFERENCES_HEADING_RE = re.compile(r"^#+\s*参考文献", re.MULTILINE)


def _check_reference_precision(text: str, file_label: str) -> list[Issue]:
    """参考文献列表不得把正文已用过的精确商品页链接换成更笼统的品牌首页
    （competitor_analysis.yaml 硬规则 5；v4.1/v5 连续两版都在这里退化）。"""
    issues: list[Issue] = []
    m = _REFERENCES_HEADING_RE.search(text)
    if not m:
        return issues

    body_text = text[: m.start()]
    ref_text = text[m.start() :]

    body_best_depth: dict[str, int] = {}
    for url, _ in _extract_urls(body_text):
        host = _host_of(url)
        if not host:
            continue
        body_best_depth[host] = max(body_best_depth.get(host, 0), _path_depth(url))

    for url, ctx in _extract_urls(ref_text):
        host = _host_of(url)
        if not host or host not in body_best_depth:
            continue
        ref_depth = _path_depth(url)
        if ref_depth <= 1 and body_best_depth[host] >= 2:
            issues.append(
                Issue(
                    file=file_label,
                    severity="warning",
                    kind="参考文献退化",
                    detail=(
                        f"参考文献里 {url}（{host}）比正文同一域名用过的链接笼统得多"
                        f"（正文路径深度最高 {body_best_depth[host]}，参考文献只有 {ref_depth}），"
                        "未复用正文的精确 URL"
                    ),
                    context=ctx,
                )
            )
    return issues


# 文首失败标记：任一命中则剥掉整段引用块（含组合 soft-pass / 评分 / Depth 地板）。
# depth_v3：组合 soft-pass 横幅里写了「待补充/TBD」作为修改要求，被 TBD 检测当成正文严重项。
_GUARDRAIL_BANNER_MARKERS = (
    "本文未通过引用校验",
    "组合 guardrail",
    "共享软上限",
    "未通过 Depth",
    "未通过评分表",
    "硬证据地板",
    "自动重试上限",
)


def _is_guardrail_banner_line(line: str) -> bool:
    s = line.strip()
    if not s.startswith(">"):
        return False
    return any(m in s for m in _GUARDRAIL_BANNER_MARKERS)


def _strip_guardrail_banner(text: str) -> str:
    """去掉 guardrail 写在文首的失败标记块，再做校验。

    ## 为什么必须去掉

    guardrail 重试耗尽时会在产出顶部插入一段引用块，逐条列出没修好的问题，例如：

        > ⚠️ **本文未通过引用校验，且已达到自动重试上限**（2 次）...
        > - 【品牌首页当商品页】https://www.miele.de 是裸域名首页，没有具体商品路径

    这段话是**对问题的描述**，不是问题本身。但下一次校验读到它时，会把里面引用的
    `https://www.miele.de` 当成一条新的违规引用重新报一遍——于是同一个问题被数了两次，
    而且越标记越多。实测：石头科技 v1 的竞品报告报 2 处严重，其中 1 处就是标记在自我指认。

    depth_v3 又踩了一次：组合 soft-pass 横幅里的「禁止待补充/TBD」被 TBD 检测扫成正文严重项，
    在 `--strict-citations` 下把本来已跑完的 research_depth 打成 exit 1。

    这是「检测器读到了自己的输出」这类经典污染。**任何会把校验结果写回被校验文本的
    设计，都必须同时保证下一轮校验能认出并排除这段自我描述**，否则指标会自我膨胀。
    """
    lines = text.splitlines()
    if not any(_is_guardrail_banner_line(ln) for ln in lines[:8]):
        return text
    out: list[str] = []
    in_banner = False
    for ln in lines:
        stripped = ln.strip()
        if not in_banner and _is_guardrail_banner_line(ln):
            in_banner = True
            continue
        if in_banner:
            # 引用块内（含 "> " 开头的行与块内空行）继续跳过，遇到正文即结束
            if stripped.startswith(">") or not stripped:
                continue
            in_banner = False
        out.append(ln)
    return "\n".join(out)


def check_text(text: str, file_label: str = "", expected_locale: str = "") -> FileReport:
    """扫描一份输出文档。

    expected_locale：目标市场地区码（如 'th'/'uk'），传入时会额外检查
    商品页 URL 是不是他国站点。不传则跳过这项检查。
    """
    # 先剥掉 guardrail 自己写上去的失败标记，否则它引用的违规 URL 会被重复计一次
    text = _strip_guardrail_banner(text)
    fr = FileReport(file=file_label)
    urls = _extract_urls(text)
    fr.url_count = len(urls)

    for url, context in urls:
        try:
            parsed = urlparse(url.rstrip(".,)"))
        except ValueError:
            fr.issues.append(
                Issue(file=file_label, severity="error", kind="URL 解析失败", detail=url, context=context)
            )
            continue

        host = (parsed.netloc or "").lower()
        host = host.split(":")[0]
        if host.startswith("www."):
            host = host[4:]

        if host in FAKE_DOMAINS:
            fr.issues.append(
                Issue(
                    file=file_label,
                    severity="error",
                    kind="占位/假域名",
                    detail=f"{url} 是明显的占位域名，不能当真实引用",
                    context=context,
                )
            )
            continue

        raw_path = parsed.path or ""
        path = raw_path.strip("/")
        is_homepage_only = not path and not parsed.query
        if is_homepage_only and host in KNOWN_RESEARCH_HOMEPAGES:
            fr.issues.append(
                Issue(
                    file=file_label,
                    severity="error",
                    kind="研究机构首页当证据",
                    detail=f"{url} 只是机构首页，source_rules.md 规定不得作为数据证据，需换成具体报告/文章页",
                    context=context,
                )
            )
        elif is_homepage_only and _is_evidence_context(context) and not _is_official_domain(host):
            # 盲区修补（v7 发现）：旧版首页检测只认 statista/mintel 等四个研究机构域名，
            # 结果 backup_v7 里 `weleda.co.uk`、`cultbeauty.co.uk` 两个裸域名首页
            # 被当成证据（其中一条还标了 A 级）却完全没报警。
            # 任何裸域名出现在证据/依据位置都该提示人工确认。
            fr.issues.append(
                Issue(
                    file=file_label,
                    severity="warning",
                    kind="裸域名首页当证据",
                    detail=(
                        f"{url} 是没有任何路径的域名首页，却出现在证据/依据位置；"
                        "首页只能证明这个品牌或平台存在，证明不了具体结论，需换成具体页面"
                    ),
                    context=context,
                )
            )

        # Shopify 等常见「/collections/xxx/products/sku」仍是单品详情页，不能只因
        # 含 collections/ 就误杀（花知晓全链路里 Srichand 真 PDP 被误报过）。
        path_low = raw_path.lower()
        looks_like_collection = any(marker in path_low for marker in _COLLECTION_PATH_MARKERS)
        is_shopify_style_pdp = "/products/" in path_low or re.search(r"/product/[^/]+", path_low)
        if looks_like_collection and not is_shopify_style_pdp:
            fr.issues.append(
                Issue(
                    file=file_label,
                    severity="warning",
                    kind="疑似分类/系列页当商品页",
                    detail=f"{url} 路径像分类/系列/品牌列表页（如 /collections/xxx、/all-brands/...），competitor_analysis.yaml 硬规则 4 要求商品页须为单品详情页，拿不准应标「商品页待确认」",
                    context=context,
                )
            )

        fr.issues.extend(_check_product_page_quality(url, context, file_label))
        fr.issues.extend(_check_brand_homepage_as_product(url, context, file_label))

    fr.issues.extend(_check_evidence_lines(text, file_label))
    fr.issues.extend(_check_sku_url_consistency(text, file_label))
    fr.issues.extend(_check_social_profile_as_sentiment(text, file_label))
    fr.issues.extend(_check_reference_precision(text, file_label))
    fr.issues.extend(_check_tbd_placeholders(text, file_label))
    if expected_locale:
        fr.issues.extend(check_locale_consistency(text, file_label, expected_locale))

    if _TEMPLATE_PLACEHOLDER_RE.search(text):
        fr.issues.append(
            Issue(
                file=file_label,
                severity="error",
                kind="未填模板占位符",
                detail="参考文献表格里还留着 `N/A | N/A` 这种没填的模板行",
            )
        )

    return fr


def check_files(paths: list[Path], expected_locale: str = "") -> Report:
    report = Report()
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            rel_label = str(path)
        except Exception:  # pragma: no cover
            rel_label = path.name
        fr = check_text(text, file_label=rel_label, expected_locale=expected_locale)
        report.file_reports.append(fr)
    return report


def _main() -> None:
    import sys

    args = [a for a in sys.argv[1:]]
    expected_locale = ""
    # 可选参数：--locale th
    if "--locale" in args:
        idx = args.index("--locale")
        if idx + 1 < len(args):
            expected_locale = args[idx + 1]
            del args[idx : idx + 2]

    if not args:
        print(
            "用法: python -m src.marketing_crew.citation_check "
            "[--locale th] <file1.md> [file2.md ...]"
        )
        raise SystemExit(2)

    paths = [Path(p) for p in args]
    report = check_files(paths, expected_locale=expected_locale)
    print(report.render())
    if report.total_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    _main()
