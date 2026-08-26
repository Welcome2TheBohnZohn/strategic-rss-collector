#!/usr/bin/env python3

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
from xml.etree import ElementTree as ET

import feedparser
import requests
import urllib3
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "sources.json"

FEEDS_DIR = ROOT / "feeds"
ARTICLES_DIR = ROOT / "articles"
DIAGNOSTICS_DIR = ROOT / "diagnostics"

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ET.register_namespace("content", CONTENT_NS)

REQUEST_TIMEOUT = 10
BROWSER_TIMEOUT_MS = 20000
MAX_ITEMS_PER_SOURCE = 12
MAX_CANDIDATES = 50


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
    "english",
    "中文",
}


def load_sources():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text):
    if not text:
        return ""

    text = re.sub(r"\r\n?", "\n", str(text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def strip_html(value):
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "lxml")

    return normalize_text(
        soup.get_text("\n", strip=True)
    )


def fetch(url, retries=1, verify_ssl=True):

    last_error = ""

    for attempt in range(retries + 1):

        try:

            headers = {
                "User-Agent": USER_AGENTS[
                    attempt % len(USER_AGENTS)
                ],
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/rss+xml,"
                    "application/atom+xml,"
                    "application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": (
                    "en-US,en;q=0.9,"
                    "zh-CN;q=0.8,"
                    "zh;q=0.7"
                ),
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "close",
            }

            if not verify_ssl:

                urllib3.disable_warnings(
                    urllib3.exceptions.InsecureRequestWarning
                )

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=verify_ssl,
            )

            response.raise_for_status()

            if (
                not response.encoding
                or response.encoding.lower()
                == "iso-8859-1"
            ):
                response.encoding = (
                    response.apparent_encoding
                    or "utf-8"
                )

            return {
                "ok": True,
                "url": response.url,
                "status": response.status_code,
                "text": response.text,
                "content": response.content,
                "error": "",
            }

        except Exception as exc:

            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

            if attempt < retries:
                time.sleep(1)

    return {
        "ok": False,
        "url": url,
        "status": None,
        "text": "",
        "content": b"",
        "error": last_error,
    }


def canonical_url(base_url, href):

    try:

        url = urljoin(
            base_url,
            href,
        )

        parsed = urlparse(url)

        if parsed.scheme not in (
            "http",
            "https",
        ):
            return ""

        return parsed._replace(
            fragment=""
        ).geturl()

    except Exception:

        return ""


def normalized_host(url):

    return (
        urlparse(url).hostname
        or ""
    ).lower().removeprefix(
        "www."
    )


def same_domain(
    source_url,
    candidate_url,
):

    source_host = normalized_host(
        source_url
    )

    candidate_host = normalized_host(
        candidate_url
    )

    if not source_host or not candidate_host:
        return False

    return (
        candidate_host == source_host
        or candidate_host.endswith(
            "." + source_host
        )
    )


def collect_all_links(
    page_html,
    final_url,
):

    soup = BeautifulSoup(
        page_html,
        "lxml",
    )

    found = {}

    for link in soup.find_all(
        "a",
        href=True,
    ):

        url = canonical_url(
            final_url,
            link.get("href", ""),
        )

        if not url:
            continue

        text = normalize_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if (
            url not in found
            or (
                not found[url]
                and text
            )
        ):
            found[url] = text

    quoted_pattern = re.compile(
        r"[\"']"
        r"((?:https?://[^\"'<> ]+"
        r"|/[^\"'<> ]+))"
        r"[\"']",
        re.IGNORECASE,
    )

    for match in quoted_pattern.finditer(
        page_html
    ):

        url = canonical_url(
            final_url,
            match.group(1),
        )

        if (
            url
            and url not in found
        ):
            found[url] = ""

    return [
        {
            "url": url,
            "text": text,
        }
        for url, text in found.items()
    ]


def find_candidate_links(
    source,
    page_html,
    final_url,
):

    all_links = collect_all_links(
        page_html,
        final_url,
    )

    include_pattern = re.compile(
        source.get(
            "include_regex",
            ".*",
        ),
        re.IGNORECASE,
    )

    exclude_pattern = re.compile(
        source.get(
            "exclude_regex",
            r"$^",
        ),
        re.IGNORECASE,
    )

    candidates = []
    seen = set()

    for item in all_links:

        href = item["url"]
        anchor_text = item["text"]

        if href in seen:
            continue

        seen.add(href)

        if not same_domain(
            source["source_url"],
            href,
        ):
            continue

        if exclude_pattern.search(
            href
        ):
            continue

        if not include_pattern.search(
            href
        ):
            continue

        if len(anchor_text) < 4:

            anchor_text = (
                urlparse(href)
                .path
                .rstrip("/")
                .split("/")[-1]
                or "Article"
            )

        if (
            anchor_text.lower()
            in BAD_LINK_TEXT
        ):
            continue

        score = 5

        if len(anchor_text) >= 10:
            score += 2

        if re.search(
            r"20\d{2}",
            href,
        ):
            score += 2

        if re.search(
            r"\d{6,}",
            href,
        ):
            score += 2

        if any(
            keyword in href.lower()
            for keyword in (
                "news",
                "article",
                "content",
                "detail",
                "press",
                "newsview",
                "show",
                "flaw",
            )
        ):
            score += 2

        candidates.append(
            {
                "url": href,
                "anchor_title": anchor_text,
                "score": score,
            }
        )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            -len(
                item[
                    "anchor_title"
                ]
            ),
        )
    )

    return (
        candidates[
            :MAX_CANDIDATES
        ],
        all_links,
    )


def extract_title(
    soup,
    fallback="Untitled",
):

    selectors = [
        "h1",
        ".article-title",
        ".article_title",
        ".articleTitle",
        ".news-title",
        ".news_title",
        ".newsTitle",
        ".title",
        ".title1",
        "#title",
    ]

    for selector in selectors:

        node = soup.select_one(
            selector
        )

        if not node:
            continue

        text = normalize_text(
            node.get_text(
                " ",
                strip=True,
            )
        )

        if 4 <= len(text) <= 300:
            return text

    if soup.title:

        text = normalize_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            return text

    return fallback


def try_parse_date(value):

    if not value:
        return None

    value = normalize_text(value)

    match = re.search(
        r"(20\d{2})年\s*"
        r"(\d{1,2})月\s*"
        r"(\d{1,2})日"
        r"(?:\s*(\d{1,2})"
        r"[:：](\d{1,2}))?",
        value,
    )

    if match:

        groups = match.groups()

        try:

            return datetime(
                int(groups[0]),
                int(groups[1]),
                int(groups[2]),
                (
                    int(groups[3])
                    if groups[3]
                    else 0
                ),
                (
                    int(groups[4])
                    if groups[4]
                    else 0
                ),
            )

        except Exception:
            pass

    try:

        dt = dateparser.parse(
            value,
            fuzzy=True,
        )

        if (
            dt
            and 1990
            <= dt.year
            <= 2100
        ):
            return dt

    except Exception:
        pass

    return None


def extract_date_from_url(url):

    try:

        parsed = urlparse(url)

        query = parse_qs(
            parsed.query
        )

        for key in (
            "paperDate",
            "date",
            "pubDate",
            "publishDate",
        ):

            for value in query.get(
                key,
                [],
            ):

                dt = try_parse_date(
                    value
                )

                if dt:
                    return dt

        match = re.search(
            r"(20\d{2})[-_/]"
            r"(\d{1,2})[-_/]"
            r"(\d{1,2})",
            url,
        )

        if match:

            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )

    except Exception:
        pass

    return None


def extract_date(
    soup,
    page_text,
):

    meta_candidates = [
        (
            "property",
            "article:published_time",
        ),
        (
            "property",
            "og:published_time",
        ),
        (
            "name",
            "pubdate",
        ),
        (
            "name",
            "publishdate",
        ),
        (
            "name",
            "publish-date",
        ),
        (
            "name",
            "date",
        ),
        (
            "name",
            "DC.date",
        ),
        (
            "name",
            "PubDate",
        ),
        (
            "itemprop",
            "datePublished",
        ),
    ]

    for attribute, value in meta_candidates:

        node = soup.find(
            "meta",
            attrs={
                attribute: value
            },
        )

        if (
            node
            and node.get(
                "content"
            )
        ):

            dt = try_parse_date(
                node.get(
                    "content"
                )
            )

            if dt:
                return dt

    for node in soup.find_all(
        "time"
    ):

        dt = try_parse_date(
            node.get(
                "datetime"
            )
            or node.get(
                "content"
            )
            or node.get_text(
                " ",
                strip=True,
            )
        )

        if dt:
            return dt

    selectors = [
        ".date",
        ".time",
        ".publish-time",
        ".publish_time",
        ".publishTime",
        ".article-date",
        ".article_date",
        ".articleDate",
        ".pubtime",
        ".pub-time",
        ".pub_time",
        ".info",
        ".source",
        ".origin",
        ".message",
        ".time-source",
        ".article-info",
    ]

    for selector in selectors:

        for node in soup.select(
            selector
        ):

            dt = try_parse_date(
                node.get_text(
                    " ",
                    strip=True,
                )
            )

            if dt:
                return dt

    sample = page_text[
        :16000
    ]

    patterns = [
        (
            r"(20\d{2})[-/.]"
            r"(\d{1,2})[-/.]"
            r"(\d{1,2})"
            r"(?:\s+"
            r"(\d{1,2})"
            r"[:：](\d{1,2}))?"
        ),
        (
            r"(20\d{2})年\s*"
            r"(\d{1,2})月\s*"
            r"(\d{1,2})日"
            r"(?:\s*"
            r"(\d{1,2})"
            r"[:：](\d{1,2}))?"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            sample,
        )

        if not match:
            continue

        groups = match.groups()

        try:

            return datetime(
                int(groups[0]),
                int(groups[1]),
                int(groups[2]),
                (
                    int(groups[3])
                    if (
                        len(groups) > 3
                        and groups[3]
                    )
                    else 0
                ),
                (
                    int(groups[4])
                    if (
                        len(groups) > 4
                        and groups[4]
                    )
                    else 0
                ),
            )

        except Exception:
            pass

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
            "aside",
        ]
    ):
        tag.decompose()

    selectors = [
        "article",
        "[itemprop='articleBody']",
        ".article-content",
        ".article_content",
        ".articleContent",
        ".article-body",
        ".article_body",
        ".news-content",
        ".news_content",
        ".newsContent",
        ".detail-content",
        ".detail_content",
        ".content",
        ".TRS_Editor",
        ".pages_content",
        ".editor",
        ".text",
        "#article",
        "#content",
        "#zoom",
        "main",
    ]

    candidates = []

    for selector in selectors:

        for node in soup.select(
            selector
        ):

            text = normalize_text(
                node.get_text(
                    "\n",
                    strip=True,
                )
            )

            if len(text) >= 200:

                candidates.append(
                    text
                )

    if candidates:

        return max(
            candidates,
            key=len,
        )[:50000]

    paragraphs = []

    for paragraph in soup.find_all(
        "p"
    ):

        text = normalize_text(
            paragraph.get_text(
                " ",
                strip=True,
            )
        )

        if len(text) >= 30:

            paragraphs.append(
                text
            )

    if paragraphs:

        text = "\n\n".join(
            paragraphs
        )

        if len(text) >= 200:

            return text[
                :50000
            ]

    return normalize_text(
        soup.get_text(
            "\n",
            strip=True,
        )
    )[:50000]


def extract_article(
    page_html,
    fallback_title,
    article_url="",
):

    soup = BeautifulSoup(
        page_html,
        "lxml",
    )

    title = extract_title(
        soup,
        fallback_title,
    )

    visible_text = normalize_text(
        soup.get_text(
            "\n",
            strip=True,
        )
    )

    published = extract_date(
        soup,
        visible_text,
    )

    if (
        not published
        and article_url
    ):

        published = (
            extract_date_from_url(
                article_url
            )
        )

    return {
        "title": title,
        "text": extract_article_text(
            soup
        ),
        "published": published,
    }


def safe_filename(
    title,
    url,
):

    title = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip(
        " ._"
    )

    if not title:

        title = hashlib.sha1(
            url.encode(
                "utf-8"
            )
        ).hexdigest()[:12]

    return title[:120]


def save_article(
    source_slug,
    article,
):

    directory = (
        ARTICLES_DIR
        / source_slug
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        directory
        / (
            safe_filename(
                article["title"],
                article["url"],
            )
            + ".md"
        )
    )

    published_text = (
        article[
            "published"
        ].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if article[
            "published"
        ]
        else "Unknown"
    )

    path.write_text(
        f"# {article['title']}\n\n"
        f"Published: "
        f"{published_text}\n\n"
        f"Source: "
        f"{article['url']}\n\n"
        f"{article['text']}\n",
        encoding="utf-8",
    )


def save_diagnostics(
    source,
    all_links,
    candidates,
):

    DIAGNOSTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        DIAGNOSTICS_DIR
        / (
            source["slug"]
            + ".txt"
        )
    )

    lines = [
        (
            "Diagnostic link report for "
            + source["title"]
        ),
        "",
        (
            "Start URL: "
            + source[
                "start_url"
            ]
        ),
        (
            "Source type: "
            + source.get(
                "source_type",
                "html",
            )
        ),
        (
            "Include regex: "
            + source.get(
                "include_regex",
                "",
            )
        ),
        "",
        (
            f"Candidate links: "
            f"{len(candidates)}"
        ),
        (
            f"All links discovered: "
            f"{len(all_links)}"
        ),
        "",
        (
            "=== MATCHED "
            "CANDIDATES ==="
        ),
        "",
    ]

    for item in candidates:

        lines.append(
            item["url"]
        )

        lines.append(
            "  "
            + item[
                "anchor_title"
            ]
        )

    lines.extend(
        [
            "",
            (
                "=== ALL DISCOVERED "
                "LINKS ==="
            ),
            "",
        ]
    )

    for item in all_links:

        lines.append(
            item["url"]
        )

        if item["text"]:

            lines.append(
                "  "
                + item["text"]
            )

    path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )


def save_raw_response(
    source,
    text,
    suffix="raw.html",
):

    DIAGNOSTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        DIAGNOSTICS_DIR
        / (
            source["slug"]
            + "-"
            + suffix
        )
    )

    path.write_text(
        text[:150000],
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


def build_rss(
    source,
    articles,
):

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
    ).text = source[
        "title"
    ]

    ET.SubElement(
        channel,
        "link",
    ).text = source[
        "source_url"
    ]

    ET.SubElement(
        channel,
        "description",
    ).text = (
        "Generated RSS feed for "
        + source["title"]
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
        ).text = article[
            "title"
        ]

        ET.SubElement(
            item,
            "link",
        ).text = article[
            "url"
        ]

        guid = ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink":
                "true",
            },
        )

        guid.text = article[
            "url"
        ]

        published = (
            normalize_datetime(
                article[
                    "published"
                ]
            )
        )

        if published:

            ET.SubElement(
                item,
                "pubDate",
            ).text = (
                format_datetime(
                    published
                )
            )

        ET.SubElement(
            item,
            "description",
        ).text = article[
            "text"
        ][:1500]

        content = ET.SubElement(
            item,
            (
                "{"
                + CONTENT_NS
                + "}encoded"
            ),
        )

        content.text = (
            "<p><strong>"
            "Original source:"
            "</strong> "
            + html.escape(
                article[
                    "url"
                ]
            )
            + "</p><pre>"
            + html.escape(
                article[
                    "text"
                ]
            )
            + "</pre>"
        )

    return ET.tostring(
        rss,
        encoding="utf-8",
        xml_declaration=True,
    )


def write_feed_file(
    source,
    articles,
):

    FEEDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        FEEDS_DIR
        / (
            source["slug"]
            + ".xml"
        )
    ).write_bytes(
        build_rss(
            source,
            articles,
        )
    )


def feed_entry_datetime(entry):

    for key in (
        "published_parsed",
        "updated_parsed",
        "created_parsed",
    ):

        value = entry.get(
            key
        )

        if value:

            try:

                return datetime(
                    *value[:6],
                    tzinfo=timezone.utc,
                )

            except Exception:
                pass

    for key in (
        "published",
        "updated",
        "created",
    ):

        dt = try_parse_date(
            entry.get(
                key
            )
        )

        if dt:
            return dt

    return None


def feed_entry_text(entry):

    contents = entry.get(
        "content",
        [],
    )

    if contents:

        pieces = [
            strip_html(
                item.get(
                    "value",
                    "",
                )
            )
            for item in contents
            if item.get(
                "value"
            )
        ]

        text = "\n\n".join(
            piece
            for piece in pieces
            if piece
        )

        if text:

            return text[
                :50000
            ]

    for key in (
        "summary",
        "description",
    ):

        if entry.get(key):

            text = strip_html(
                entry.get(
                    key
                )
            )

            if text:

                return text[
                    :50000
                ]

    return ""


def base_status(
    source,
    verify_ssl,
):

    return {
        "slug": source["slug"],
        "title": source["title"],
        "start_url": source[
            "start_url"
        ],
        "source_type": source.get(
            "source_type",
            "html",
        ),
        "http_status": None,
        "candidate_links": 0,
        "all_links": 0,
        "attempted": 0,
        "articles_with_text": 0,
        "articles_with_date": 0,
        "feed_items": 0,
        "ssl_verified": verify_ssl,
        "error": "",
    }


def run_rss_source(source):

    print(
        "\n==> "
        + source["slug"]
        + " [RSS]: "
        + source["start_url"],
        flush=True,
    )

    verify_ssl = source.get(
        "verify_ssl",
        True,
    )

    status = base_status(
        source,
        verify_ssl,
    )

    response = fetch(
        source["start_url"],
        retries=1,
        verify_ssl=verify_ssl,
    )

    status[
        "http_status"
    ] = response[
        "status"
    ]

    if not response[
        "ok"
    ]:

        status[
            "error"
        ] = response[
            "error"
        ]

        print(
            "    FAILED: "
            + status[
                "error"
            ],
            flush=True,
        )

        return status

    parsed = feedparser.parse(
        response[
            "content"
        ]
    )

    articles = []

    for entry in parsed.entries[
        :MAX_ITEMS_PER_SOURCE
    ]:

        title = (
            strip_html(
                entry.get(
                    "title",
                    "",
                )
            )
            or "Untitled"
        )

        url = (
            entry.get(
                "link"
            )
            or entry.get(
                "id"
            )
            or source[
                "source_url"
            ]
        )

        text = feed_entry_text(
            entry
        )

        published = (
            feed_entry_datetime(
                entry
            )
            or extract_date_from_url(
                url
            )
        )

        article = {
            "title": title,
            "url": url,
            "text": text,
            "published": published,
        }

        save_article(
            source[
                "slug"
            ],
            article,
        )

        articles.append(
            article
        )

    status[
        "attempted"
    ] = len(
        parsed.entries
    )

    status[
        "articles_with_text"
    ] = sum(
        1
        for article in articles
        if article[
            "text"
        ]
    )

    status[
        "articles_with_date"
    ] = sum(
        1
        for article in articles
        if article[
            "published"
        ]
    )

    status[
        "feed_items"
    ] = len(
        articles
    )

    if not articles:

        save_raw_response(
            source,
            response[
                "text"
            ],
            "rss-response.txt",
        )

    write_feed_file(
        source,
        articles,
    )

    return status


def run_html_source(source):

    print(
        "\n==> "
        + source["slug"]
        + " [HTML]: "
        + source["start_url"],
        flush=True,
    )

    verify_ssl = source.get(
        "verify_ssl",
        True,
    )

    status = base_status(
        source,
        verify_ssl,
    )

    listing = fetch(
        source["start_url"],
        retries=1,
        verify_ssl=verify_ssl,
    )

    status[
        "http_status"
    ] = listing[
        "status"
    ]

    if not listing[
        "ok"
    ]:

        status[
            "error"
        ] = listing[
            "error"
        ]

        return status

    candidates, all_links = (
        find_candidate_links(
            source,
            listing[
                "text"
            ],
            listing[
                "url"
            ],
        )
    )

    status[
        "candidate_links"
    ] = len(
        candidates
    )

    status[
        "all_links"
    ] = len(
        all_links
    )

    if not all_links:

        save_raw_response(
            source,
            listing[
                "text"
            ],
            "raw.html",
        )

    save_diagnostics(
        source,
        all_links,
        candidates,
    )

    articles = []
    seen_urls = set()

    for candidate in candidates:

        if (
            len(articles)
            >= MAX_ITEMS_PER_SOURCE
        ):
            break

        url = candidate[
            "url"
        ]

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        status[
            "attempted"
        ] += 1

        page = fetch(
            url,
            retries=0,
            verify_ssl=verify_ssl,
        )

        if not page[
            "ok"
        ]:
            continue

        article = extract_article(
            page[
                "text"
            ],
            candidate[
                "anchor_title"
            ],
            page[
                "url"
            ],
        )

        if len(
            article[
                "text"
            ]
        ) < 200:
            continue

        article[
            "url"
        ] = page[
            "url"
        ]

        status[
            "articles_with_text"
        ] += 1

        if article[
            "published"
        ]:

            status[
                "articles_with_date"
            ] += 1

        save_article(
            source[
                "slug"
            ],
            article,
        )

        articles.append(
            article
        )

    status[
        "feed_items"
    ] = len(
        articles
    )

    write_feed_file(
        source,
        articles,
    )

    return status


def wait_for_browser_page(page):

    page.wait_for_timeout(
        5000
    )

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=5000,
        )

    except PlaywrightTimeoutError:
        pass

    content = page.content()

    challenge_markers = (
        (
            "Please enable JavaScript "
            "to view the page content"
        ),
        "/TSPD/",
        (
            "Transferring "
            "to the website"
        ),
        "__arcsjs",
    )

    if any(
        marker in content
        for marker in challenge_markers
    ):

        page.wait_for_timeout(
            8000
        )

        try:

            page.wait_for_load_state(
                "networkidle",
                timeout=5000,
            )

        except PlaywrightTimeoutError:
            pass

    return page.content()


def run_browser_source(source):

    print(
        "\n==> "
        + source["slug"]
        + " [BROWSER]: "
        + source["start_url"],
        flush=True,
    )

    verify_ssl = source.get(
        "verify_ssl",
        True,
    )

    status = base_status(
        source,
        verify_ssl,
    )

    articles = []

    try:

        with sync_playwright() as playwright:

            browser = (
                playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        (
                            "--disable-"
                            "dev-shm-usage"
                        ),
                    ],
                )
            )

            context = (
                browser.new_context(
                    user_agent=(
                        USER_AGENTS[0]
                    ),
                    locale="en-US",
                    viewport={
                        "width": 1440,
                        "height": 1000,
                    },
                    ignore_https_errors=(
                        not verify_ssl
                    ),
                )
            )

            page = context.new_page()

            page.set_default_timeout(
                BROWSER_TIMEOUT_MS
            )

            response = page.goto(
                source[
                    "start_url"
                ],
                wait_until=(
                    "domcontentloaded"
                ),
                timeout=(
                    BROWSER_TIMEOUT_MS
                ),
            )

            listing_html = (
                wait_for_browser_page(
                    page
                )
            )

            final_url = page.url

            status[
                "http_status"
            ] = (
                response.status
                if response
                else 200
            )

            candidates, all_links = (
                find_candidate_links(
                    source,
                    listing_html,
                    final_url,
                )
            )

            status[
                "candidate_links"
            ] = len(
                candidates
            )

            status[
                "all_links"
            ] = len(
                all_links
            )

            save_diagnostics(
                source,
                all_links,
                candidates,
            )

            if not candidates:

                save_raw_response(
                    source,
                    listing_html,
                    (
                        "browser-"
                        "rendered.html"
                    ),
                )

            seen_urls = set()

            for candidate in candidates:

                if (
                    len(articles)
                    >= MAX_ITEMS_PER_SOURCE
                ):
                    break

                url = candidate[
                    "url"
                ]

                if url in seen_urls:
                    continue

                seen_urls.add(
                    url
                )

                status[
                    "attempted"
                ] += 1

                try:

                    page.goto(
                        url,
                        wait_until=(
                            "domcontentloaded"
                        ),
                        timeout=(
                            BROWSER_TIMEOUT_MS
                        ),
                    )

                    page.wait_for_timeout(
                        1500
                    )

                    try:

                        page.wait_for_load_state(
                            "networkidle",
                            timeout=3000,
                        )

                    except PlaywrightTimeoutError:
                        pass

                    article_html = (
                        page.content()
                    )

                    article_url = (
                        page.url
                    )

                    article = (
                        extract_article(
                            article_html,
                            candidate[
                                "anchor_title"
                            ],
                            article_url,
                        )
                    )

                    if len(
                        article[
                            "text"
                        ]
                    ) < 200:
                        continue

                    article[
                        "url"
                    ] = article_url

                    status[
                        "articles_with_text"
                    ] += 1

                    if article[
                        "published"
                    ]:

                        status[
                            "articles_with_date"
                        ] += 1

                    save_article(
                        source[
                            "slug"
                        ],
                        article,
                    )

                    articles.append(
                        article
                    )

                except Exception:
                    continue

            context.close()
            browser.close()

    except Exception as exc:

        status[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        if status[
            "http_status"
        ] is None:

            return status

    status[
        "feed_items"
    ] = len(
        articles
    )

    write_feed_file(
        source,
        articles,
    )

    return status


def run_source(source):

    source_type = source.get(
        "source_type",
        "html",
    ).lower()

    if source_type == "rss":

        return run_rss_source(
            source
        )

    if source_type == "browser":

        return run_browser_source(
            source
        )

    return run_html_source(
        source
    )


def write_status_report(
    statuses,
):

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
        "Status meanings:",
        (
            "OK = Feed contains "
            "one or more items"
        ),
        (
            "FETCHED/NO ITEMS = "
            "Source loaded but no "
            "usable items were extracted"
        ),
        (
            "FAILED = Source could "
            "not be retrieved"
        ),
        "",
    ]

    working = 0
    no_items = 0
    failed = 0

    for status in statuses:

        if status[
            "feed_items"
        ] > 0:

            state = "OK"
            working += 1

        elif status[
            "http_status"
        ]:

            state = (
                "FETCHED/NO ITEMS"
            )

            no_items += 1

        else:

            state = "FAILED"
            failed += 1

        lines.extend(
            [
                (
                    f"[{state}] "
                    f"{status['slug']} - "
                    f"{status['title']}"
                ),
                (
                    "  Source type: "
                    + status[
                        "source_type"
                    ]
                ),
                (
                    "  Start URL: "
                    + status[
                        "start_url"
                    ]
                ),
                (
                    "  HTTP: "
                    + str(
                        status[
                            "http_status"
                        ]
                    )
                ),
            ]
        )

        if status[
            "source_type"
        ] in (
            "html",
            "browser",
        ):

            lines.extend(
                [
                    (
                        "  Links discovered: "
                        + str(
                            status[
                                "all_links"
                            ]
                        )
                    ),
                    (
                        "  Candidate links: "
                        + str(
                            status[
                                "candidate_links"
                            ]
                        )
                    ),
                ]
            )

        lines.extend(
            [
                (
                    "  Attempted "
                    "items/articles: "
                    + str(
                        status[
                            "attempted"
                        ]
                    )
                ),
                (
                    "  Items/articles "
                    "with text: "
                    + str(
                        status[
                            "articles_with_text"
                        ]
                    )
                ),
                (
                    "  Items/articles "
                    "with dates: "
                    + str(
                        status[
                            "articles_with_date"
                        ]
                    )
                ),
                (
                    "  RSS feed items: "
                    + str(
                        status[
                            "feed_items"
                        ]
                    )
                ),
                (
                    "  SSL verification: "
                    + (
                        "ON"
                        if status[
                            "ssl_verified"
                        ]
                        else "OFF"
                    )
                ),
            ]
        )

        if status[
            "error"
        ]:

            lines.append(
                "  Error: "
                + status[
                    "error"
                ]
            )

        lines.append("")

    lines.extend(
        [
            "SUMMARY",
            (
                f"Working: "
                f"{working}"
            ),
            (
                "Fetched but no items: "
                f"{no_items}"
            ),
            (
                f"Failed: "
                f"{failed}"
            ),
            (
                "Total sources: "
                f"{len(statuses)}"
            ),
            "",
        ]
    )

    (
        FEEDS_DIR
        / "status-report.txt"
    ).write_text(
        "\n".join(
            lines
        ),
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

    DIAGNOSTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sources = load_sources()

    print(
        f"Loaded "
        f"{len(sources)} sources.",
        flush=True,
    )

    statuses = []

    for source in sources:

        try:

            status = run_source(
                source
            )

        except Exception as exc:

            status = base_status(
                source,
                source.get(
                    "verify_ssl",
                    True,
                ),
            )

            status[
                "error"
            ] = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        statuses.append(
            status
        )

    write_status_report(
        statuses
    )

    print(
        "\nCollection complete.",
        flush=True,
    )

    print(
        (
            "See feeds/"
            "status-report.txt "
            "for results."
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
