#!/usr/bin/env python3
import html
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
FOOTER_PREFIX = "\u6bcf\u5929\u5317\u4eac\u65f6\u95f4 10:00 \u7531 GitHub Actions \u81ea\u52a8\u66f4\u65b0\u3002\u6700\u8fd1\u68c0\u67e5\uff1a"
DEFAULT_VALUE = "\u53ef\u4f5c\u4e3a CPG \u5ba2\u6237\u5207\u5165\u70b9\uff1a\u91cd\u70b9\u89c2\u5bdf\u5b83\u662f\u5426\u80fd\u63d0\u5347\u65b0\u54c1\u79cd\u8349\u3001\u8fbe\u4eba\u8f6c\u5316\u3001\u5546\u54c1\u627f\u63a5\u6216\u81ea\u52a8\u5316\u6295\u653e\u6548\u7387\u3002"
AI_CATEGORY = "AI/\u81ea\u52a8\u5316"
PLAY_CATEGORY = "\u5e7f\u544a\u73a9\u6cd5"


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
                "summary": f"\u65b0\u62a5\u9053\u63d0\u5230 {platform} \u76f8\u5173\u5e7f\u544a/\u8425\u9500\u52a8\u4f5c\uff1a{title[:120]}",
                "value": DEFAULT_VALUE,
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
    return (
        "<article>"
        f"<div class=\"meta\"><span class=\"tag{hot}\">{html.escape(item.get('platform', ''))}</span>"
        f"<span class=\"tag{hot}\">{html.escape(item.get('date', ''))}</span>"
        f"<span class=\"tag retail\">{html.escape(item.get('category', ''))}</span></div>"
        f"<h2>{html.escape(item.get('title', ''))}</h2>"
        f"<p>{html.escape(item.get('summary', ''))}</p>"
        f"<p class=\"why\">{html.escape(item.get('value', ''))}</p>"
        f"<a href=\"{html.escape(item.get('sourceUrl', ''))}\">{SOURCE_PREFIX}{html.escape(item.get('sourceLabel', ''))}</a>"
        "</article>"
    )


def render(data):
    high = [item for item in data["items"] if item.get("priority") == "high"][:8]
    normal = [item for item in data["items"] if item.get("priority") != "high"][:10]
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
    h2{{margin:0 0 7px;font-size:16px;line-height:1.3;letter-spacing:0}}p{{margin:0 0 8px;color:#333;font-size:14px}}.why{{border-left:3px solid #cbd5e1;padding-left:9px;color:var(--muted)}}
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
    data = load_data()
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
