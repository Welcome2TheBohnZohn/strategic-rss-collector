#!/usr/bin/env python3

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser


ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "sources.json"
FEEDS_DIR = ROOT / "feeds"
ARTICLES_DIR = ROOT / "articles"

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ET.register_namespace("content", CONTENT_NS)

MAX_ITEMS_PER_SOURCE = 12
REQUEST_TIMEOUT = 30

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
]

BAD_LINK_TEXT = {
    "home",
    "more",
    "more>>",
    "read more",
    "view all",
    "next",
    "previous",
    "首页",
    "更多",
    "查看全部",
    "下一页",
    "上一页",
    "返回",
    "网站地图",
}


def load_sources():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch(url, retries=2):
    last_error = ""

    for attempt in range(retries + 1):
        try:
            headers = {
                "User-Agent": USER_AGENTS[attempt % len(USER_AGENTS)],
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
                "Cache-Control": "no-cache",
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            response.raise_for_status()

            if not response.encoding or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"

            return {
                "ok": True,
                "url": response.url,
                "status": response.status_code,
                "text": response.text,
                "error": "",
            }

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

            if attempt < retries:
                time.sleep(2 * (attempt + 1))

    return {
        "ok": False,
        "url": url,
        "status": None,
        "text": "",
        "error": last_error,
    }


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def canonical_url(base_url, href):
    try:
        url = urljoin(base_url, href)
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        return parsed._replace(fragment="").geturl()

    except Exception:
        return ""


def same_domain(source_url, candidate_url):
    source_host = (urlparse(source_url).hostname or "").lower()
    candidate_host = (urlparse(candidate_url).hostname or "").lower()

    source_host = source_host.removeprefix("www.")
    candidate_host = candidate_host.removeprefix("www.")

    if not source_host or not candidate_host:
        return False

    return (
        candidate_host == source_host
        or candidate_host.endswith("." + source_host)
    )


def find_candidate_links(source, page_html, final_url):
    soup = BeautifulSoup(page_html, "lxml")

    include_pattern = re.compile(
        source.get("include_regex", ".*"),
        re.IGNORECASE,
    )

    exclude_pattern = re.compile(
        source.get("exclude_regex", r"$^"),
        re.IGNORECASE,
    )

    candidates = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = canonical_url(final_url, link.get("href", ""))

        if not href:
            continue

        if href in seen:
            continue

        seen.add(href)

        if not same_domain(source["source_url"], href):
            continue

        if exclude_pattern.search(href):
            continue

        if not include_pattern.search(href):
            continue

        anchor_text = clean_text(link.get_text(" ", strip=True))

        if len(anchor_text) < 4:
            continue

        if anchor_text.lower() in BAD_LINK_TEXT:
            continue

        score = 0

        if len(anchor_text) >= 10:
            score += 2

        if re.search(r"20\d{2}", href):
            score += 2

        if re.search(r"\d{6,}", href):
            score += 2

        if any(
            word in href.lower()
            for word in (
                "news",
                "article",
                "content",
                "detail",
                "press",
            )
        ):
            score += 2

        score += 5

        candidates.append(
            {
                "url": href,
                "anchor_title": anchor_text,
                "score": score,
            }
        )

    candidates.sort(
        key=lambda x: (
            -x["score"],
            -len(x["anchor_title"]),
        )
    )

    return candidates[:40]


def extract_title(soup, fallback="Untitled"):
    selectors = [
        "h1",
        ".article-title",
        ".article_title",
        ".news-title",
        ".news_title",
        ".title",
        "#title",
    ]

    for selector in selectors:
        node = soup.select_one(selector)

        if node:
            text = clean_text(node.get_text(" ", strip=True))

            if 4 <= len(text) <= 300:
                return text

    if soup.title:
        text = clean_text(soup.title.get_text(" ", strip=True))

        if text:
            return text

    return fallback


def try_parse_date(value):
    if not value:
        return None

    try:
        dt = dateparser.parse(value, fuzzy=True)

        if dt and 1990 <= dt.year <= 2100:
            return dt

    except Exception:
        pass

    return None


def extract_date(soup, page_text):
    meta_candidates = [
        ("property", "article:published_time"),
        ("property", "og:published_time"),
        ("name", "pubdate"),
        ("name", "publishdate"),
        ("name", "publish-date"),
        ("name", "date"),
        ("name", "DC.date"),
        ("itemprop", "datePublished"),
    ]

    for attribute, value in meta_candidates:
        node = soup.find("meta", attrs={attribute: value})

        if node and node.get("content"):
            parsed = try_parse_date(node.get("content"))

            if parsed:
                return parsed

    for time_node in soup.find_all("time"):
        candidate = (
            time_node.get("datetime")
            or time_node.get("content")
            or time_node.get_text(" ", strip=True)
        )

        parsed = try_parse_date(candidate)

        if parsed:
            return parsed

    common_selectors = [
        ".date",
        ".time",
        ".publish-time",
        ".publish_time",
        ".article-date",
        ".article_date",
        ".pubtime",
        ".source",
    ]

    for selector in common_selectors:
        node = soup.select_one(selector)

        if node:
            parsed = try_parse_date(
                clean_text(node.get_text(" ", strip=True))
            )

            if parsed:
                return parsed

    sample = page_text[:8000]

    patterns = [
        r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})",
        r"(20\d{2})年(\d{1,2})月(\d{1,2})日",
        r"(20\d{2})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, sample)

        if not match:
            continue

        try:
            groups = list(map(int, match.groups()))

            year = groups[0]
            month = groups[1]
            day = groups[2]

            hour = groups[3] if len(groups) > 3 else 0
            minute = groups[4] if len(groups) > 4 else 0

            return datetime(
                year,
                month,
                day,
                hour,
                minute,
            )

        except Exception:
            continue

    return None


def extract_article_text(soup):
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header",
            "form",
            "iframe",
            "svg",
        ]
    ):
        tag.decompose()

    selectors = [
        "article",
        "[itemprop='articleBody']",
        ".article-content",
        ".article_content",
        ".articleContent",
        ".news-content",
        ".news_content",
        ".detail-content",
        ".detail_content",
        ".content",
        ".TRS_Editor",
        ".pages_content",
        "#article",
        "#content",
        "#zoom",
        "main",
    ]

    candidates = []

    for selector in selectors:
        for node in soup.select(selector):
            text = clean_text(node.get_text("\n", strip=True))

            if len(text) >= 200:
                candidates.append(text)

    if candidates:
        return max(candidates, key=len)[:50000]

    paragraphs = []

    for p in soup.find_all("p"):
        text = clean_text(p.get_text(" ", strip=True))

        if len(text) >= 30:
            paragraphs.append(text)

    if paragraphs:
        text = "\n\n".join(paragraphs)

        if len(text) >= 200:
            return text[:50000]

    text = clean_text(soup.get_text("\n", strip=True))

    return text[:50000]


def extract_article(page_html, fallback_title):
    soup = BeautifulSoup(page_html, "lxml")

    title = extract_title(soup, fallback_title)

    visible_text = clean_text(
        soup.get_text("\n", strip=True)
    )

    published = extract_date(
        soup,
        visible_text,
    )

    article_text = extract_article_text(soup)

    return {
        "title": title,
        "text": article_text,
        "published": published,
    }


def safe_filename(title, url):
    title = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip(" ._")

    if not title:
        title = hashlib.sha1(
            url.encode("utf-8")
        ).hexdigest()[:12]

    return title[:120]


def save_article(source_slug, article):
    directory = ARTICLES_DIR / source_slug
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        safe_filename(
            article["title"],
            article["url"],
        )
        + ".md"
    )

    path = directory / filename

    if article["published"]:
        published_text = article[
            "published"
        ].strftime("%Y-%m-%d %H:%M:%S")
    else:
        published_text = "Unknown"

    contents = (
        f"# {article['title']}\n\n"
        f"Published: {published_text}\n\n"
        f"Source: {article['url']}\n\n"
        f"{article['text']}\n"
    )

    path.write_text(
        contents,
        encoding="utf-8",
    )


def normalize_datetime(dt):
    if not dt:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def build_rss(source, articles):
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = ET.SubElement(
        rss,
        "channel",
    )

    ET.SubElement(
        channel,
        "title",
    ).text = source["title"]

    ET.SubElement(
        channel,
        "link",
    ).text = source["source_url"]

    ET.SubElement(
        channel,
        "description",
    ).text = (
        f"Generated RSS feed for "
        f"{source['title']}"
    )

    ET.SubElement(
        channel,
        "language",
    ).text = source.get(
        "language",
        "en",
    )

    ET.SubElement(
        channel,
        "lastBuildDate",
    ).text = format_datetime(
        datetime.now(
            timezone.utc
        )
    )

    for article in articles:
        item = ET.SubElement(
            channel,
            "item",
        )

        ET.SubElement(
            item,
            "title",
        ).text = article["title"]

        ET.SubElement(
            item,
            "link",
        ).text = article["url"]

        guid = ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "true",
            },
        )

        guid.text = article["url"]

        published = normalize_datetime(
            article["published"]
        )

        if published:
            ET.SubElement(
                item,
                "pubDate",
            ).text = format_datetime(
                published
            )

        description = article[
            "text"
        ][:1500]

        ET.SubElement(
            item,
            "description",
        ).text = description

        content = ET.SubElement(
            item,
            f"{{{CONTENT_NS}}}encoded",
        )

        content.text = (
            "<p><strong>Original source:</strong> "
            + html.escape(
                article["url"]
            )
            + "</p>"
            + "<pre>"
            + html.escape(
                article["text"]
            )
            + "</pre>"
        )

    return ET.tostring(
        rss,
        encoding="utf-8",
        xml_declaration=True,
    )


def run_source(source):
    print(
        f"\n==> {source['slug']}: "
        f"{source['start_url']}",
        flush=True,
    )

    status = {
        "slug": source["slug"],
        "title": source["title"],
        "start_url": source["start_url"],
        "http_status": None,
        "candidate_links": 0,
        "attempted": 0,
        "articles_with_text": 0,
        "articles_with_date": 0,
        "feed_items": 0,
        "error": "",
    }

    listing = fetch(
        source["start_url"]
    )

    status[
        "http_status"
    ] = listing["status"]

    if not listing["ok"]:
        status["error"] = listing[
            "error"
        ]

        print(
            f"    FAILED: "
            f"{status['error']}"
        )

        return status

    candidates = find_candidate_links(
        source,
        listing["text"],
        listing["url"],
    )

    status[
        "candidate_links"
    ] = len(candidates)

    articles = []
    seen_urls = set()

    for candidate in candidates:
        if len(
            articles
        ) >= MAX_ITEMS_PER_SOURCE:
            break

        url = candidate["url"]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        status["attempted"] += 1

        page = fetch(
            url,
            retries=1,
        )

        if not page["ok"]:
            continue

        article = extract_article(
            page["text"],
            candidate[
                "anchor_title"
            ],
        )

        if len(
            article["text"]
        ) < 200:
            continue

        article["url"] = page["url"]

        status[
            "articles_with_text"
        ] += 1

        if article["published"]:
            status[
                "articles_with_date"
            ] += 1

        save_article(
            source["slug"],
            article,
        )

        articles.append(
            article
        )

    FEEDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    feed_path = (
        FEEDS_DIR
        / f"{source['slug']}.xml"
    )

    feed_path.write_bytes(
        build_rss(
            source,
            articles,
        )
    )

    status[
        "feed_items"
    ] = len(articles)

    print(
        "    "
        f"HTTP={status['http_status']} "
        f"candidates={status['candidate_links']} "
        f"attempted={status['attempted']} "
        f"text={status['articles_with_text']} "
        f"dated={status['articles_with_date']} "
        f"items={status['feed_items']}",
        flush=True,
    )

    return status


def write_status_report(statuses):
    FEEDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    lines = [
        "Strategic RSS Collector Status",
        f"Generated: {now}",
        "",
        (
            "Status meanings:"
        ),
        (
            "OK = Feed contains one or more items"
        ),
        (
            "FETCHED/NO ITEMS = Website loaded but no usable articles were extracted"
        ),
        (
            "FAILED = Website could not be retrieved"
        ),
        "",
    ]

    working = 0
    no_items = 0
    failed = 0

    for status in statuses:
        if status["feed_items"] > 0:
            state = "OK"
            working += 1

        elif status["http_status"]:
            state = "FETCHED/NO ITEMS"
            no_items += 1

        else:
            state = "FAILED"
            failed += 1

        lines.append(
            f"[{state}] "
            f"{status['slug']} - "
            f"{status['title']}"
        )

        lines.append(
            f"  Start URL: "
            f"{status['start_url']}"
        )

        lines.append(
            f"  HTTP: "
            f"{status['http_status']}"
        )

        lines.append(
            f"  Candidate links: "
            f"{status['candidate_links']}"
        )

        lines.append(
            f"  Attempted articles: "
            f"{status['attempted']}"
        )

        lines.append(
            f"  Articles with text: "
            f"{status['articles_with_text']}"
        )

        lines.append(
            f"  Articles with dates: "
            f"{status['articles_with_date']}"
        )

        lines.append(
            f"  RSS feed items: "
            f"{status['feed_items']}"
        )

        if status["error"]:
            lines.append(
                f"  Error: "
                f"{status['error']}"
            )

        lines.append("")

    lines.extend(
        [
            "SUMMARY",
            f"Working: {working}",
            f"Fetched but no items: {no_items}",
            f"Failed: {failed}",
            f"Total sources: {len(statuses)}",
            "",
        ]
    )

    report_path = (
        FEEDS_DIR
        / "status-report.txt"
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():
    FEEDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTICLES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sources = load_sources()

    print(
        f"Loaded {len(sources)} sources."
    )

    statuses = []

    for source in sources:
        try:
            status = run_source(
                source
            )

        except Exception as exc:
            print(
                f"    UNHANDLED ERROR: "
                f"{exc}"
            )

            status = {
                "slug": source[
                    "slug"
                ],
                "title": source[
                    "title"
                ],
                "start_url": source[
                    "start_url"
                ],
                "http_status": None,
                "candidate_links": 0,
                "attempted": 0,
                "articles_with_text": 0,
                "articles_with_date": 0,
                "feed_items": 0,
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

        statuses.append(
            status
        )

    write_status_report(
        statuses
    )

    print(
        "\nCollection complete."
    )

    print(
        "See feeds/status-report.txt "
        "for the full results."
    )


if __name__ == "__main__":
    main()
