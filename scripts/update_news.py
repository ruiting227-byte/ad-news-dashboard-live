#!/usr/bin/env python3
import html
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "news.json"
INDEX_PATH = ROOT / "index.html"
SHANGHAI = timezone(timedelta(hours=8))

AD_TERMS = (
    "advertising", "advertiser", "ads", "ad product", "marketing", "campaign",
    "commerce", "shop", "shopping", "creator", "reels", "retail media",
    "brand", "performance", "ai", "automation",
)
CPG_TERMS = (
    "cpg", "fmcg", "beauty", "cosmetic", "skincare", "makeup", "retail",
    "grocery", "food", "beverage", "snack", "consumer packaged",
)
PLAY_TERMS = (
    "smart+", "advantage+", "symphony", "affiliate", "shop", "search",
    "reels", "stories", "video", "catalog", "product showcase", "live", "ai",
)
OFFICIAL_DOMAINS = (
    "newsroom.tiktok.com", "ads.tiktok.com", "business.tiktok.com",
    "about.fb.com", "facebook.com/business", "business.instagram.com",
)
TITLE = "\u7ade\u5a92\u5c0f\u52a8\u6001"
SCOPE = "\u8fc7\u53bb 12 \u4e2a\u6708\uff5cTikTok\u3001Meta\uff5cCPG\uff1a\u7f8e\u5986\u3001\u96f6\u552e\u3001\u98df\u54c1"
INITIAL_STATUS = "\u521d\u59cb\u7248"
HIGH_TITLE = "\u9ad8\u4f18\u5148\u7ea7"
NORMAL_TITLE = "\u8865\u5145\u89c2\u5bdf"
SOURCE_PREFIX = "\u6765\u6e90\uff1a"
FOOTER_PREFIX = "\u624b\u673a\u684c\u9762\u5165\u53e3\u6253\u5f00\u5373\u53ef\u67e5\u770b\u3002\u6bcf\u5929\u5317\u4eac\u65f6\u95f4 10:00 \u4e91\u7aef\u81ea\u52a8\u66f4\u65b0\uff1b\u82e5\u5f53\u5929\u6682\u65e0\u65b0\u95fb\uff0c\u4e5f\u4f1a\u4ece\u8fd1 12 \u4e2a\u6708\u65b0\u95fb\u6c60\u8f6e\u6362\u4eca\u65e5\u7b80\u62a5\u3002\u6700\u8fd1\u68c0\u67e5\uff1a"
AI_CATEGORY = "AI/\u81ea\u52a8\u5316"
PLAY_CATEGORY = "\u5e7f\u544a\u73a9\u6cd5"
DEFAULT_EN_SUMMARY = "This update is tracked as a competitor signal for Kwai CPG operations across social commerce, creators, AI creative, shopping ads, or automated media products."
DEFAULT_ZH_SUMMARY = "\u8fd9\u662f Kwai CPG \u8fd0\u8425\u9700\u5173\u6ce8\u7684\u7ade\u5a92\u4fe1\u53f7\uff0c\u53ef\u7528\u4e8e\u8ddf\u8e2a\u793e\u4ea4\u7535\u5546\u3001\u521b\u4f5c\u8005\u5408\u4f5c\u3001AI \u521b\u610f\u3001\u8d2d\u7269\u5e7f\u544a\u6216\u81ea\u52a8\u5316\u6295\u653e\u4ea7\u54c1\u7684\u53d8\u5316\u3002"

TITLE_ZH = {
    "Meta Launches New Era Of Shopping Experiences Powered By AI , Reels & Creators": "Meta \u63a8\u51fa\u7531 AI\u3001Reels \u548c\u521b\u4f5c\u8005\u9a71\u52a8\u7684\u8d2d\u7269\u4f53\u9a8c",
    "Thai beauty platform Konvy secures US$15 million from Cool Japan Fund": "\u6cf0\u56fd\u7f8e\u5986\u5e73\u53f0 Konvy \u83b7 Cool Japan Fund 1500 \u4e07\u7f8e\u5143\u6295\u8d44",
    "TikTok Shop honors standout creators at 2026 Creator Awards": "TikTok Shop \u5728 2026 \u521b\u4f5c\u8005\u5956\u4e2d\u8868\u5f70\u5934\u90e8\u521b\u4f5c\u8005",
    "Zalando hires TikTok veteran to get brands to pay for marketing": "Zalando \u5f15\u5165 TikTok \u8001\u5c06\u63a8\u52a8\u54c1\u724c\u4ed8\u8d39\u8425\u9500",
    "Branded Buzz + Search Hubs": "\u54c1\u724c\u79cd\u8349\u58f0\u91cf + \u641c\u7d22\u4e2d\u5fc3",
    "Symphony + Reference to Video": "Symphony + \u53c2\u8003\u56fe\u751f\u89c6\u9891",
    "Tag , Youre Liable : What Instagram New Affiliate Reels Mean for Retailers | Ballard Spahr LLP": "Instagram \u65b0\u8054\u76df Reels \u5bf9\u96f6\u552e\u5546\u7684\u98ce\u9669\u548c\u673a\u4f1a",
    "Meta trial raises stakes as possible exit from New Mexico sparks concerns for local businesses": "Meta \u8bc9\u8bbc\u98ce\u9669\u5f15\u53d1\u672c\u5730\u5546\u5bb6\u5bf9\u5e73\u53f0\u9000\u51fa\u7684\u62c5\u5fe7",
    "Walmart Has 23 . 6 % of U . S . Grocery Sales - But Costco Owns the AI Answer - 5W Grocery Retail AI Visibility Index 20": "5W \u96f6\u552e AI \u53ef\u89c1\u5ea6\u6307\u6570\uff1aWalmart \u5360\u7f8e\u56fd\u98df\u54c1\u96f6\u552e 23.6%\uff0cCostco \u5728 AI \u7b54\u6848\u4e2d\u66f4\u5f3a",
    "Nykaa sued over alleged copyright misuse of songs on Instagram reels": "Nykaa \u56e0 Instagram Reels \u97f3\u4e50\u7248\u6743\u4f7f\u7528\u95ee\u9898\u88ab\u8d77\u8bc9",
    "TikTok launches international ad platform campaign": "TikTok \u53d1\u8d77\u56fd\u9645\u5e7f\u544a\u5e73\u53f0\u8425\u9500\u6218\u5f79",
    "TikTok Shop on Track to Seize 10 % of Retail Sales": "TikTok Shop \u6709\u671b\u5360\u636e\u96f6\u552e\u9500\u552e 10% \u4efd\u989d",
    "FAQ on brand safety : How AI content and creator marketing are reshaping risk in 2026": "\u54c1\u724c\u5b89\u5168 FAQ\uff1aAI \u5185\u5bb9\u548c\u521b\u4f5c\u8005\u8425\u9500\u5982\u4f55\u6539\u5199 2026 \u5e74\u98ce\u9669",
    "Beauty Giants Race to Own the AI Shopping Moment": "\u7f8e\u5986\u5de8\u5934\u4e89\u593a AI \u8d2d\u7269\u573a\u666f",
    "How to use social media for retail brands : 5 key strategies": "\u96f6\u552e\u54c1\u724c\u5982\u4f55\u4f7f\u7528\u793e\u4ea4\u5a92\u4f53\uff1a5 \u4e2a\u5173\u952e\u7b56\u7565",
    "Kewei Zhu : The creative systems architect behind TikTok Shop biggest U . S . selling moments": "TikTok Shop \u7f8e\u56fd\u5927\u4fc3\u80cc\u540e\u7684\u521b\u610f\u7cfb\u7edf\u8bbe\u8ba1\u8005 Kewei Zhu",
    "Smart+ / Pulse View+ / Collage Carousel": "Smart+ / Pulse View+ / Collage Carousel",
    "Best strategies for FMCG to sell on TikTok Shop": "FMCG \u54c1\u724c\u5728 TikTok Shop \u9500\u552e\u7684\u5173\u952e\u7b56\u7565",
}

SUMMARY_ZH = {
    "Branded Buzz + Search Hubs": "TikTok \u628a\u8fbe\u4eba\u6279\u91cf\u79cd\u8349\u548c\u641c\u7d22\u9876\u90e8\u54c1\u724c\u9635\u5730\u6253\u901a\uff0c\u7ade\u5a92\u91cd\u70b9\u5728\u4e8e\u5c06\u5185\u5bb9\u5174\u8da3\u627f\u63a5\u5230\u4e3b\u52a8\u641c\u7d22\u548c\u8f6c\u5316\u8def\u5f84\u3002",
    "Symphony + Reference to Video": "TikTok \u63d0\u5347 Symphony AI \u89c6\u9891\u751f\u6210\u7684\u53ef\u63a7\u6027\uff0c\u5bf9 SKU \u591a\u3001\u7d20\u6750\u66f4\u65b0\u5feb\u7684 CPG \u54c1\u7c7b\u5177\u6709\u7ade\u5a92\u53c2\u8003\u4ef7\u503c\u3002",
    "Smart+ / Pulse View+ / Collage Carousel": "TikTok \u5f3a\u5316 Smart+\u3001Pulse View+ \u548c\u5546\u54c1\u5c55\u793a\u5f62\u6001\uff0c\u663e\u793a\u5176\u5728\u81ea\u52a8\u5316\u6295\u653e\u4e0e\u5185\u5bb9\u7535\u5546\u627f\u63a5\u4e0a\u6301\u7eed\u52a0\u7801\u3002",
}

SUMMARY_EN = {
    "Branded Buzz + Search Hubs": "TikTok connects scaled creator buzz with branded search hubs, turning content interest into search demand and conversion paths.",
    "Symphony + Reference to Video": "TikTok is making Symphony AI video generation more controllable, a useful competitor signal for CPG categories with many SKUs and fast creative cycles.",
    "Smart+ / Pulse View+ / Collage Carousel": "TikTok is expanding Smart+, Pulse View+, and commerce-forward formats, showing continued investment in automation and shoppable content.",
}


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def load_data():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {
        "title": TITLE,
        "updatedAt": "",
        "lastCheckedAt": "",
        "scope": SCOPE,
        "status": INITIAL_STATUS,
        "items": [],
    }


def zh_title_for(title, platform):
    if title in TITLE_ZH:
        return TITLE_ZH[title]
    if re.search(r"shop|shopping|commerce|retail", title, re.I):
        return f"{platform} \u7535\u5546/\u96f6\u552e\u76f8\u5173\u7ade\u5a92\u52a8\u6001\uff1a{title[:72]}"
    if re.search(r"creator|reels|affiliate|influencer", title, re.I):
        return f"{platform} \u521b\u4f5c\u8005/\u5185\u5bb9\u5408\u4f5c\u52a8\u6001\uff1a{title[:72]}"
    if re.search(r"ai|automation|smart\+|advantage\+|symphony", title, re.I):
        return f"{platform} AI \u4e0e\u81ea\u52a8\u5316\u5e7f\u544a\u52a8\u6001\uff1a{title[:72]}"
    return f"{platform} \u7ade\u5a92\u8425\u9500\u52a8\u6001\uff1a{title[:72]}"


def zh_summary_for(item):
    title = item.get("titleEn") or item.get("title", "")
    if title in SUMMARY_ZH:
        return SUMMARY_ZH[title]
    platform = item.get("platform", "\u7ade\u5a92")
    category = item.get("category", "\u5e7f\u544a/\u8425\u9500")
    return f"{platform} \u8fd9\u4e00\u52a8\u6001\u4e0e {category} \u76f8\u5173\uff0c\u53ef\u4f5c\u4e3a Kwai \u8ddf\u8e2a CPG \u7ade\u5a92\u4ea7\u54c1\u3001\u5185\u5bb9\u7535\u5546\u548c\u521b\u610f\u4f9b\u7ed9\u53d8\u5316\u7684\u4fe1\u53f7\u3002"


def has_cjk(value):
    return bool(re.search(r"[\u4e00-\u9fff]", value or ""))


def en_category(category):
    mapping = {
        "AI/\u81ea\u52a8\u5316": "AI and automation",
        "\u5e7f\u544a\u73a9\u6cd5": "ad formats and marketing plays",
        "\u65b0\u54c1/\u5927\u4fc3": "new-product launches and retail moments",
        "AI \u521b\u610f": "AI creative",
        "\u81ea\u52a8\u5316": "automation",
        "\u54c1\u724c\u66dd\u5149": "brand exposure",
        "\u793e\u4ea4\u7535\u5546": "social commerce",
        "AI \u8d2d\u7269": "AI shopping",
        "AI \u6295\u653e": "AI media buying",
    }
    return mapping.get(category, "advertising and marketing")


def en_summary_for(item):
    title = item.get("titleEn") or item.get("title", "")
    if title in SUMMARY_EN:
        return SUMMARY_EN[title]
    summary = item.get("summary", "")
    if summary and "\u65b0\u62a5\u9053\u63d0\u5230" not in summary:
        return summary
    platform = item.get("platform", "The competitor")
    category = en_category(item.get("category", ""))
    return f"{platform} shows movement in {category}, making it a competitor signal for Kwai to monitor across CPG operations, social commerce, and creative supply."


def normalize_item(item):
    title_en = clean(item.get("titleEn") or item.get("title", ""))
    item["titleEn"] = title_en
    item["titleZh"] = clean(item.get("titleZh") or zh_title_for(title_en, item.get("platform", "\u7ade\u5a92")))
    if not item.get("summaryEn") or has_cjk(item.get("summaryEn", "")):
        item["summaryEn"] = en_summary_for(item)
    item["summaryEn"] = clean(item["summaryEn"])
    item["summaryZh"] = clean(item.get("summaryZh") or zh_summary_for(item))
    item.pop("value", None)
    item.pop("summary", None)
    return item


def normalize_data(data):
    data["items"] = [normalize_item(item) for item in data.get("items", [])]
    return data


def gdelt(query, now):
    params = urlencode({
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "50",
        "sort": "HybridRel",
        "startdatetime": (now - timedelta(days=32)).strftime("%Y%m%d%H%M%S"),
        "enddatetime": now.strftime("%Y%m%d%H%M%S"),
    })
    req = Request(
        f"https://api.gdeltproject.org/api/v2/doc/doc?{params}",
        headers={"User-Agent": "ad-news-dashboard/1.0"},
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")).get("articles", [])


def label(url):
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if "tiktok" in host:
        return "TikTok Newsroom" if "newsroom" in host else "TikTok for Business"
    if host in ("about.fb.com", "facebook.com") or "instagram" in host:
        return "Meta Newsroom"
    return host or "Source"


def score(platform, title, url):
    text = f"{title} {url}".lower()
    total = 8 if platform.lower() in text else 0
    total += sum(3 for term in AD_TERMS if term in text)
    total += sum(4 for term in CPG_TERMS if term in text)
    total += sum(2 for term in PLAY_TERMS if term in text)
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if any(host.endswith(domain) for domain in OFFICIAL_DOMAINS):
        total += 8
    if any(term in text for term in ("stock", "earnings", "lawsuit", "ban")):
        total -= 8
    return total


def candidates(now):
    searches = [
        ("TikTok", '(TikTok OR "TikTok Shop") (advertising OR marketing OR ads OR creator OR commerce OR Symphony OR Smart+) (beauty OR retail OR food OR beverage OR CPG OR FMCG)'),
        ("Meta", '(Meta OR Instagram OR Facebook) (advertising OR marketing OR ads OR Reels OR "Advantage+" OR "Business AI" OR creator OR commerce) (beauty OR retail OR food OR beverage OR CPG OR FMCG)'),
    ]
    out = []
    for platform, query in searches:
        try:
            articles = gdelt(query, now)
        except Exception as exc:
            print(f"warning: failed to fetch {platform}: {exc}", file=sys.stderr)
            continue
        for article in articles:
            title = clean(article.get("title", ""))
            url = clean(article.get("url", ""))
            if not title or not url:
                continue
            points = score(platform, title, url)
            if points < 13:
                continue
            seen_date = clean(article.get("seendate", ""))
            match = re.match(r"(\d{4})(\d{2})(\d{2})", seen_date)
            date = "-".join(match.groups()) if match else now.strftime("%Y-%m-%d")
            out.append({
                "platform": platform,
                "date": date,
                "category": AI_CATEGORY if re.search(r"ai|smart\+|advantage\+|automation|symphony", title, re.I) else PLAY_CATEGORY,
                "priority": "high" if points >= 24 else "normal",
                "title": title[:120],
                "titleEn": title[:120],
                "sourceLabel": label(url),
                "sourceUrl": url,
                "_score": points,
            })
    unique = {}
    for item in sorted(out, key=lambda x: x["_score"], reverse=True):
        unique.setdefault(item["sourceUrl"].split("?")[0], item)
    return list(unique.values())


def prune(items, now):
    cutoff = (now - timedelta(days=365)).date()
    kept, seen = [], set()
    for item in sorted(items, key=lambda x: x.get("date", ""), reverse=True):
        item = normalize_item(item)
        item.pop("_score", None)
        key = f"{item.get('sourceUrl', '').split('?')[0]}::{item.get('title', '')}"
        if key in seen:
            continue
        seen.add(key)
        try:
            item_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            item_date = now.date()
        if item_date >= cutoff:
            kept.append(item)
    return kept[:18]


def article_html(item):
    hot = " hot" if item.get("priority") == "high" else ""
    title_zh = item.get("titleZh") or item.get("title", "")
    title_en = item.get("titleEn") or item.get("title", "")
    summary_zh = item.get("summaryZh") or ""
    summary_en = item.get("summaryEn") or item.get("summary", "")
    return (
        "<article>"
        f"<div class=\"meta\"><span class=\"tag{hot}\">{html.escape(item.get('platform', ''))}</span>"
        f"<span class=\"tag{hot}\">{html.escape(item.get('date', ''))}</span>"
        f"<span class=\"tag retail\">{html.escape(item.get('category', ''))}</span></div>"
        f"<h2>{html.escape(title_zh)}<span>{html.escape(title_en)}</span></h2>"
        f"<p>{html.escape(summary_zh)}</p>"
        f"<p class=\"en\">{html.escape(summary_en)}</p>"
        f"<a href=\"{html.escape(item.get('sourceUrl', ''))}\">{SOURCE_PREFIX}{html.escape(item.get('sourceLabel', ''))}</a>"
        "</article>"
    )


def daily_items(items, date_key, limit=9):
    def daily_rank(item):
        key = f"{date_key}|{item.get('sourceUrl', '')}|{item.get('title', '')}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        priority_boost = 0 if item.get("priority") == "high" else 1
        return (priority_boost, digest)

    return sorted(items, key=daily_rank)[:limit]


def render(data):
    data = normalize_data(data)
    date_key = data.get("updatedAt") or datetime.now(SHANGHAI).strftime("%Y-%m-%d")
    today = daily_items(data["items"], date_key)
    high = [item for item in today if item.get("priority") == "high"]
    normal = [item for item in today if item.get("priority") != "high"]
    high_html = "\n    ".join(article_html(item) for item in high)
    normal_html = "\n    ".join(article_html(item) for item in normal)
    status = html.escape(f"{data.get('updatedAt', '')} {data.get('status', '')}".strip())
    scope = html.escape(data.get("scope", ""))
    checked = html.escape(data.get("lastCheckedAt", ""))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#f6f3ed">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="{TITLE}">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <title>{TITLE}</title>
  <style>
    :root{{color-scheme:light;--ink:#171717;--muted:#646464;--line:#ddd7cc;--soft:#f6f3ed;--panel:#fff;--green:#0f766e;--orange:#b45309;--blue:#2563eb}}
    *{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:var(--soft);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.42;-webkit-font-smoothing:antialiased}}
    main{{max-width:520px;margin:0 auto;padding:calc(18px + env(safe-area-inset-top)) 14px calc(24px + env(safe-area-inset-bottom))}}
    header{{position:sticky;top:0;z-index:3;margin:-18px -14px 12px;padding:calc(16px + env(safe-area-inset-top)) 14px 12px;background:rgba(246,243,237,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}}
    h1{{margin:0;font-size:22px;font-weight:780;letter-spacing:0}}.sub{{margin:5px 0 0;color:var(--muted);font-size:12px}}.status{{display:inline-flex;margin-top:10px;border:1px solid #b7d9d3;background:#e9f7f4;color:#0b625b;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:720}}
    .section-title{{margin:16px 0 10px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;font-weight:800}}
    article{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:13px;margin-bottom:10px;box-shadow:0 1px 0 rgba(23,23,23,.03)}}.meta{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}}
    .tag{{border-radius:999px;padding:3px 7px;font-size:11px;font-weight:720;background:#f1f5f9;color:#334155}}.tag.hot{{background:#ecfdf5;color:var(--green)}}.tag.retail{{background:#fff7ed;color:var(--orange)}}
    h2{{margin:0 0 7px;font-size:16px;line-height:1.3;letter-spacing:0}}h2 span{{display:block;margin-top:3px;color:#475569;font-size:13px;font-weight:680}}p{{margin:0 0 8px;color:#333;font-size:14px}}.en{{color:var(--muted);font-size:13px}}
    a{{display:inline-flex;max-width:100%;color:var(--blue);text-decoration:none;font-size:12px;font-weight:760;overflow-wrap:anywhere}}footer{{margin-top:14px;color:var(--muted);font-size:12px}}
  </style>
</head>
<body>
  <main>
    <header><h1>{TITLE}</h1><p class="sub">{scope}</p><div class="status">{status}</div></header>
    <div class="section-title">{HIGH_TITLE}</div>
    {high_html}
    <div class="section-title">{NORMAL_TITLE}</div>
    {normal_html}
    <footer>{FOOTER_PREFIX}{checked}</footer>
  </main>
</body>
</html>
"""


def main():
    now = datetime.now(SHANGHAI)
    data = normalize_data(load_data())
    existing = {item.get("sourceUrl", "").split("?")[0] for item in data.get("items", [])}
    additions = []
    for item in candidates(now):
        url_key = item["sourceUrl"].split("?")[0]
        if url_key not in existing:
            additions.append(item)
            existing.add(url_key)
        if len(additions) >= 4:
            break
    data["items"] = prune(additions + data.get("items", []), now)
    data["lastCheckedAt"] = now.strftime("%Y-%m-%d %H:%M")
    data["updatedAt"] = now.strftime("%Y-%m-%d")
    data["status"] = f"\u81ea\u52a8\u65b0\u589e {len(additions)} \u6761" if additions else "\u5df2\u81ea\u52a8\u68c0\u67e5\uff0c\u6682\u65e0\u65b0\u589e"
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    INDEX_PATH.write_text(render(data), encoding="utf-8")
    print(data["status"])


if __name__ == "__main__":
    main()
