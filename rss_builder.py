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

REQUEST_TIMEOUT = 12
BROWSER_TIMEOUT_MS = 25000

MAX_ITEMS_PER_SOURCE = 12
MAX_CANDIDATES = 50


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)


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

    return json.loads(
        SOURCES_FILE.read_text(
            encoding="utf-8"
        )
    )


def normalize_text(value):

    if not value:
        return ""

    text = str(value)

    text = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def strip_html(value):

    if not value:
        return ""

    soup = BeautifulSoup(
        str(value),
        "lxml",
    )

    return normalize_text(
        soup.get_text(
            "\n",
            strip=True,
        )
    )


def start_urls(source):

    values = [
        source["start_url"]
    ]

    values.extend(
        source.get(
            "fallback_urls",
            [],
        )
    )

    output = []

    for value in values:

        if (
            value
            and value not in output
        ):
            output.append(
                value
            )

    return output


def request_headers():

    return {
        "User-Agent": USER_AGENT,
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


def fetch(
    url,
    retries=1,
    verify_ssl=True,
):

    if not verify_ssl:

        urllib3.disable_warnings(
            urllib3.exceptions.InsecureRequestWarning
        )

    last_error = ""

    for attempt in range(
        retries + 1
    ):

        try:

            response = requests.get(
                url,
                headers=request_headers(),
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
                "status": (
                    response.status_code
                ),
                "text": response.text,
                "content": response.content,
                "error": "",
            }

        except Exception as exc:

            last_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
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


def fetch_source(
    source,
    retries=1,
):

    verify_ssl = source.get(
        "verify_ssl",
        True,
    )

    errors = []

    for url in start_urls(
        source
    ):

        result = fetch(
            url,
            retries=retries,
            verify_ssl=verify_ssl,
        )

        if result["ok"]:

            return result

        errors.append(
            f"{url} -> "
            f"{result['error']}"
        )

    return {
        "ok": False,
        "url": source[
            "start_url"
        ],
        "status": None,
        "text": "",
        "content": b"",
        "error": " | ".join(
            errors
        ),
    }


def canonical_url(
    base_url,
    href,
):

    try:

        url = urljoin(
            base_url,
            href,
        )

        parsed = urlparse(
            url
        )

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
        urlparse(
            url
        ).hostname
        or ""
    ).lower().removeprefix(
        "www."
    )


def same_domain(
    source_url,
    candidate_url,
):

    first = normalized_host(
        source_url
    )

    second = normalized_host(
        candidate_url
    )

    if (
        not first
        or not second
    ):

        return False

    return (
        first == second
        or second.endswith(
            "." + first
        )
    )


def collect_links(
    page_html,
    final_url,
):

    soup = BeautifulSoup(
        page_html,
        "lxml",
    )

    found = {}

    for node in soup.find_all(
        "a",
        href=True,
    ):

        url = canonical_url(
            final_url,
            node.get(
                "href",
                "",
            ),
        )

        if not url:

            continue

        text = normalize_text(
            node.get_text(
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


def find_candidates(
    source,
    page_html,
    final_url,
):

    links = collect_links(
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

    text_pattern = None

    if source.get(
        "include_text_regex"
    ):

        text_pattern = re.compile(
            source[
                "include_text_regex"
            ],
            re.IGNORECASE,
        )

    candidates = []
    seen = set()

    for item in links:

        url = item[
            "url"
        ]

        text = item[
            "text"
        ]

        if url in seen:

            continue

        seen.add(
            url
        )

        if not same_domain(
            source[
                "source_url"
            ],
            url,
        ):

            continue

        if exclude_pattern.search(
            url
        ):

            continue

        if not include_pattern.search(
            url
        ):

            continue

        if (
            text_pattern
            and not text_pattern.search(
                text
            )
        ):

            continue

        if len(text) < 4:

            text = (
                urlparse(
                    url
                )
                .path
                .rstrip("/")
                .split("/")[-1]
                or "Article"
            )

        if (
            text.lower()
            in BAD_LINK_TEXT
        ):

            continue

        score = 5

        if len(text) >= 10:

            score += 2

        if re.search(
            r"20\d{2}",
            url,
        ):

            score += 2

        if re.search(
            r"\d{6,}",
            url,
        ):

            score += 2

        if any(
            keyword in url.lower()
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
                "url": url,
                "anchor_title": text,
                "score": score,
            }
        )

    candidates.sort(
        key=lambda item: (
            -item[
                "score"
            ],
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
        links,
    )


def try_parse_date(value):

    if not value:

        return None

    value = normalize_text(
        value
    )

    chinese_match = re.search(
        r"(20\d{2})年\s*"
        r"(\d{1,2})月\s*"
        r"(\d{1,2})日"
        r"(?:\s*(\d{1,2})"
        r"[:：](\d{1,2}))?",
        value,
    )

    if chinese_match:

        year, month, day, hour, minute = (
            chinese_match.groups()
        )

        try:

            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour or 0),
                int(minute or 0),
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


def date_from_url(url):

    try:

        parsed = urlparse(
            url
        )

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
                int(
                    match.group(1)
                ),
                int(
                    match.group(2)
                ),
                int(
                    match.group(3)
                ),
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

        year, month, day, hour, minute = (
            match.groups()
        )

        try:

            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour or 0),
                int(minute or 0),
            )

        except Exception:

            pass

    return None


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

        if (
            4
            <= len(text)
            <= 300
        ):

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

        published = date_from_url(
            article_url
        )

    return {
        "title": extract_title(
            soup,
            fallback_title,
        ),
        "text": extract_article_text(
            soup
        ),
        "published": published,
    }


def safe_filename(
    title,
    url,
):

    value = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        title,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip(
        " ._"
    )

    if not value:

        value = hashlib.sha1(
            url.encode(
                "utf-8"
            )
        ).hexdigest()[
            :12
        ]

    return value[
        :120
    ]


def save_article(
    source_slug,
    article,
):

    folder = (
        ARTICLES_DIR
        / source_slug
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        folder
        / (
            safe_filename(
                article[
                    "title"
                ],
                article[
                    "url"
                ],
            )
            + ".md"
        )
    )

    published = article.get(
        "published"
    )

    published_text = (
        published.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if published
        else "Unknown"
    )

    path.write_text(
        f"# {article['title']}\n\n"
        f"Published: "
        f"{published_text}\n\n"
        f"Source: "
        f"{article['url']}\n\n"
        f"{article.get('text', '')}\n",
        encoding="utf-8",
    )


def save_diagnostics(
    source,
    links,
    candidates,
):

    DIAGNOSTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        DIAGNOSTICS_DIR
        / (
            source[
                "slug"
            ]
            + ".txt"
        )
    )

    lines = [
        (
            "Diagnostic link report for "
            + source[
                "title"
            ]
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
        (
            "Include text regex: "
            + source.get(
                "include_text_regex",
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
            f"{len(links)}"
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
            item[
                "url"
            ]
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

    for item in links:

        lines.append(
            item[
                "url"
            ]
        )

        if item[
            "text"
        ]:

            lines.append(
                "  "
                + item[
                    "text"
                ]
            )

    path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )


def save_raw(
    source,
    text,
    suffix,
):

    DIAGNOSTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        DIAGNOSTICS_DIR
        / (
            source[
                "slug"
            ]
            + "-"
            + suffix
        )
    )

    path.write_text(
        str(text)[
            :200000
        ],
        encoding="utf-8",
    )


def normalize_datetime(value):

    if not value:

        return None

    if value.tzinfo is None:

        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def build_rss(
    source,
    articles,
):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0"
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
        + source[
            "title"
        ]
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
                "false"
            },
        )

        guid.text = (
            article.get(
                "guid"
            )
            or article[
                "url"
            ]
        )

        published = normalize_datetime(
            article.get(
                "published"
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

        text = article.get(
            "text",
            "",
        )

        ET.SubElement(
            item,
            "description",
        ).text = text[
            :1500
        ]

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
                text
            )
            + "</pre>"
        )

    return ET.tostring(
        rss,
        encoding="utf-8",
        xml_declaration=True,
    )


def write_feed(
    source,
    articles,
):

    FEEDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        FEEDS_DIR
        / (
            source[
                "slug"
            ]
            + ".xml"
        )
    )

    path.write_bytes(
        build_rss(
            source,
            articles,
        )
    )


def base_status(source):

    return {
        "slug": source[
            "slug"
        ],
        "title": source[
            "title"
        ],
        "start_url": source[
            "start_url"
        ],
        "resolved_url": "",
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
        "ssl_verified": source.get(
            "verify_ssl",
            True,
        ),
        "error": "",
    }


def populate_counts(
    status,
    articles,
):

    status[
        "articles_with_text"
    ] = sum(
        1
        for article in articles
        if article.get(
            "text"
        )
    )

    status[
        "articles_with_date"
    ] = sum(
        1
        for article in articles
        if article.get(
            "published"
        )
    )

    status[
        "feed_items"
    ] = len(
        articles
    )


def run_rss(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [RSS]: "
        + source[
            "start_url"
        ],
        flush=True,
    )

    status = base_status(
        source
    )

    result = fetch_source(
        source,
        retries=1,
    )

    status[
        "http_status"
    ] = result[
        "status"
    ]

    status[
        "resolved_url"
    ] = result.get(
        "url",
        "",
    )

    if not result[
        "ok"
    ]:

        status[
            "error"
        ] = result[
            "error"
        ]

        return status

    parsed = feedparser.parse(
        result[
            "content"
        ]
    )

    articles = []

    for entry in parsed.entries[
        :MAX_ITEMS_PER_SOURCE
    ]:

        title = strip_html(
            entry.get(
                "title",
                "",
            )
        )

        if not title:

            title = "Untitled"

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

        text = ""

        if entry.get(
            "content"
        ):

            text = "\n\n".join(
                strip_html(
                    part.get(
                        "value",
                        "",
                    )
                )
                for part in entry[
                    "content"
                ]
                if part.get(
                    "value"
                )
            )

        if not text:

            text = strip_html(
                entry.get(
                    "summary"
                )
                or entry.get(
                    "description"
                )
                or ""
            )

        published = None

        for key in (
            "published_parsed",
            "updated_parsed",
            "created_parsed",
        ):

            value = entry.get(
                key
            )

            if not value:

                continue

            try:

                published = datetime(
                    *value[:6],
                    tzinfo=timezone.utc,
                )

                break

            except Exception:

                pass

        if not published:

            for key in (
                "published",
                "updated",
                "created",
            ):

                published = try_parse_date(
                    entry.get(
                        key
                    )
                )

                if published:

                    break

        if not published:

            published = date_from_url(
                url
            )

        article = {
            "title": title,
            "url": url,
            "guid": (
                entry.get(
                    "id"
                )
                or url
            ),
            "text": text[
                :50000
            ],
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

    populate_counts(
        status,
        articles,
    )

    if not articles:

        save_raw(
            source,
            result[
                "text"
            ],
            "rss-response.txt",
        )

        if getattr(
            parsed,
            "bozo",
            False,
        ):

            status[
                "error"
            ] = (
                "RSS parse warning: "
                + str(
                    getattr(
                        parsed,
                        "bozo_exception",
                        "unknown",
                    )
                )
            )

    write_feed(
        source,
        articles,
    )

    return status


def collect_html_articles(
    source,
    listing_html,
    listing_url,
    status,
    browser_page=None,
):

    candidates, links = find_candidates(
        source,
        listing_html,
        listing_url,
    )

    status[
        "candidate_links"
    ] = len(
        candidates
    )

    status[
        "all_links"
    ] = len(
        links
    )

    save_diagnostics(
        source,
        links,
        candidates,
    )

    if not candidates:

        save_raw(
            source,
            listing_html,
            (
                "rendered.html"
                if browser_page
                else "raw.html"
            ),
        )

    articles = []
    seen = set()

    for candidate in candidates:

        if (
            len(articles)
            >= MAX_ITEMS_PER_SOURCE
        ):

            break

        url = candidate[
            "url"
        ]

        if url in seen:

            continue

        seen.add(
            url
        )

        status[
            "attempted"
        ] += 1

        try:

            if browser_page:

                browser_page.goto(
                    url,
                    wait_until=(
                        "domcontentloaded"
                    ),
                    timeout=(
                        BROWSER_TIMEOUT_MS
                    ),
                )

                browser_page.wait_for_timeout(
                    1500
                )

                try:

                    browser_page.wait_for_load_state(
                        "networkidle",
                        timeout=4000,
                    )

                except PlaywrightTimeoutError:

                    pass

                page_html = browser_page.content()

                final_url = browser_page.url

            else:

                page = fetch(
                    url,
                    retries=0,
                    verify_ssl=(
                        source.get(
                            "verify_ssl",
                            True,
                        )
                    ),
                )

                if not page[
                    "ok"
                ]:

                    continue

                page_html = page[
                    "text"
                ]

                final_url = page[
                    "url"
                ]

            article = extract_article(
                page_html,
                candidate[
                    "anchor_title"
                ],
                final_url,
            )

            if len(
                article[
                    "text"
                ]
            ) < 200:

                continue

            article[
                "url"
            ] = final_url

            article[
                "guid"
            ] = final_url

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

    populate_counts(
        status,
        articles,
    )

    write_feed(
        source,
        articles,
    )

    return status


def run_html(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [HTML]: "
        + source[
            "start_url"
        ],
        flush=True,
    )

    status = base_status(
        source
    )

    listing = fetch_source(
        source,
        retries=1,
    )

    status[
        "http_status"
    ] = listing[
        "status"
    ]

    status[
        "resolved_url"
    ] = listing.get(
        "url",
        "",
    )

    if not listing[
        "ok"
    ]:

        status[
            "error"
        ] = listing[
            "error"
        ]

        return status

    return collect_html_articles(
        source,
        listing[
            "text"
        ],
        listing[
            "url"
        ],
        status,
    )


def browser_context(
    playwright,
    source,
):

    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    context = browser.new_context(
        user_agent=USER_AGENT,
        locale=source.get(
            "browser_locale",
            "en-US",
        ),
        viewport={
            "width": 1440,
            "height": 1100,
        },
        ignore_https_errors=(
            not source.get(
                "verify_ssl",
                True,
            )
        ),
    )

    return (
        browser,
        context,
    )


def browser_open(
    page,
    source,
):

    errors = []

    for url in start_urls(
        source
    ):

        try:

            response = page.goto(
                url,
                wait_until=(
                    "domcontentloaded"
                ),
                timeout=(
                    BROWSER_TIMEOUT_MS
                ),
            )

            page.wait_for_timeout(
                4000
            )

            try:

                page.wait_for_load_state(
                    "networkidle",
                    timeout=5000,
                )

            except PlaywrightTimeoutError:

                pass

            content = page.content()

            challenge_markers = [
                (
                    "Please enable "
                    "JavaScript to view "
                    "the page content"
                ),
                "/TSPD/",
                (
                    "Transferring "
                    "to the website"
                ),
                "__arcsjs",
            ]

            if any(
                marker in content
                for marker
                in challenge_markers
            ):

                page.wait_for_timeout(
                    8000
                )

                content = page.content()

            status_code = (
                response.status
                if response
                else 200
            )

            if status_code < 400:

                return {
                    "ok": True,
                    "url": page.url,
                    "status": status_code,
                    "text": content,
                    "error": "",
                }

            errors.append(
                f"{url} -> "
                f"HTTP "
                f"{status_code}"
            )

        except Exception as exc:

            errors.append(
                f"{url} -> "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    return {
        "ok": False,
        "url": source[
            "start_url"
        ],
        "status": None,
        "text": "",
        "error": " | ".join(
            errors
        ),
    }


def run_browser(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [BROWSER]: "
        + source[
            "start_url"
        ],
        flush=True,
    )

    status = base_status(
        source
    )

    try:

        with sync_playwright() as playwright:

            browser, context = browser_context(
                playwright,
                source,
            )

            page = context.new_page()

            page.set_default_timeout(
                BROWSER_TIMEOUT_MS
            )

            listing = browser_open(
                page,
                source,
            )

            status[
                "http_status"
            ] = listing[
                "status"
            ]

            status[
                "resolved_url"
            ] = listing.get(
                "url",
                "",
            )

            if not listing[
                "ok"
            ]:

                status[
                    "error"
                ] = listing[
                    "error"
                ]

                context.close()
                browser.close()

                return status

            result = collect_html_articles(
                source,
                listing[
                    "text"
                ],
                listing[
                    "url"
                ],
                status,
                browser_page=page,
            )

            context.close()
            browser.close()

            return result

    except Exception as exc:

        status[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return status


def cnnvd_title(
    cnnvd_id,
    segment,
):

    ignore = {
        cnnvd_id,
        "超危",
        "高危",
        "中危",
        "低危",
        "未知",
        "严重",
        "更多",
    }

    lines = [
        normalize_text(
            line
        )
        for line in segment.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    for line in lines:

        if line in ignore:

            continue

        if cnnvd_id in line:

            remainder = normalize_text(
                line.replace(
                    cnnvd_id,
                    "",
                )
            )

            remainder = re.sub(
                r"^(超危|高危|中危|"
                r"低危|未知|严重)\s*",
                "",
                remainder,
            )

            if len(
                remainder
            ) >= 4:

                return remainder[
                    :240
                ]

            continue

        if re.fullmatch(
            r"20\d{2}[-/.]"
            r"\d{1,2}[-/.]"
            r"\d{1,2}",
            line,
        ):

            continue

        if len(line) >= 4:

            return line[
                :240
            ]

    return cnnvd_id


def parse_cnnvd_list(
    rendered_text,
    source,
):

    text = normalize_text(
        rendered_text
    )

    matches = list(
        re.finditer(
            r"CNNVD-\d{4,6}-\d+",
            text,
            re.IGNORECASE,
        )
    )

    articles = []
    seen = set()

    for index, match in enumerate(
        matches
    ):

        cnnvd_id = (
            match.group(0)
            .upper()
        )

        if cnnvd_id in seen:

            continue

        seen.add(
            cnnvd_id
        )

        start = max(
            0,
            match.start() - 80,
        )

        next_start = (
            matches[
                index + 1
            ].start()
            if (
                index + 1
                < len(matches)
            )
            else len(text)
        )

        end = min(
            next_start,
            match.end() + 700,
        )

        segment = normalize_text(
            text[
                start:end
            ]
        )

        title = cnnvd_title(
            cnnvd_id,
            segment,
        )

        published = None

        date_match = re.search(
            r"(20\d{2})[-/.]"
            r"(\d{1,2})[-/.]"
            r"(\d{1,2})",
            segment,
        )

        if date_match:

            try:

                published = datetime(
                    int(
                        date_match.group(
                            1
                        )
                    ),
                    int(
                        date_match.group(
                            2
                        )
                    ),
                    int(
                        date_match.group(
                            3
                        )
                    ),
                )

            except Exception:

                pass

        article = {
            "title": (
                f"{cnnvd_id} - "
                f"{title}"
                if title != cnnvd_id
                else cnnvd_id
            ),
            "url": source[
                "start_url"
            ],
            "guid": (
                source[
                    "source_url"
                ].rstrip("/")
                + "/#"
                + cnnvd_id
            ),
            "text": segment[
                :3000
            ],
            "published": published,
        }

        articles.append(
            article
        )

        if (
            len(articles)
            >= MAX_ITEMS_PER_SOURCE
        ):

            break

    return articles


def run_cnnvd(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [CNNVD]: "
        + source[
            "start_url"
        ],
        flush=True,
    )

    status = base_status(
        source
    )

    status[
        "source_type"
    ] = "cnnvd"

    try:

        with sync_playwright() as playwright:

            browser, context = browser_context(
                playwright,
                source,
            )

            page = context.new_page()

            page.set_default_timeout(
                BROWSER_TIMEOUT_MS
            )

            listing = browser_open(
                page,
                source,
            )

            status[
                "http_status"
            ] = listing[
                "status"
            ]

            status[
                "resolved_url"
            ] = listing.get(
                "url",
                "",
            )

            if not listing[
                "ok"
            ]:

                status[
                    "error"
                ] = listing[
                    "error"
                ]

                context.close()
                browser.close()

                return status

            page.wait_for_timeout(
                3500
            )

            try:

                body_text = (
                    page.locator(
                        "body"
                    ).inner_text(
                        timeout=5000
                    )
                )

            except Exception:

                body_text = BeautifulSoup(
                    page.content(),
                    "lxml",
                ).get_text(
                    "\n",
                    strip=True,
                )

            links = collect_links(
                page.content(),
                page.url,
            )

            articles = parse_cnnvd_list(
                body_text,
                source,
            )

            status[
                "all_links"
            ] = len(
                links
            )

            status[
                "candidate_links"
            ] = len(
                articles
            )

            status[
                "attempted"
            ] = len(
                articles
            )

            populate_counts(
                status,
                articles,
            )

            save_raw(
                source,
                body_text,
                "browser-text.txt",
            )

            for article in articles:

                save_article(
                    source[
                        "slug"
                    ],
                    article,
                )

            write_feed(
                source,
                articles,
            )

            context.close()
            browser.close()

            return status

    except Exception as exc:

        status[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return status


def run_source(source):

    source_type = source.get(
        "source_type",
        "html",
    ).lower()

    if source_type == "rss":

        return run_rss(
            source
        )

    if source_type == "browser":

        return run_browser(
            source
        )

    if source_type == "cnnvd":

        return run_cnnvd(
            source
        )

    return run_html(
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

        if (
            status[
                "feed_items"
            ] > 0
        ):

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
                    "  Resolved URL: "
                    + (
                        status[
                            "resolved_url"
                        ]
                        or "None"
                    )
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
            "cnnvd",
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
                        "  Candidate "
                        "links/items: "
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

        lines.append(
            ""
        )

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

    report_path = (
        FEEDS_DIR
        / "status-report.txt"
    )

    report_path.write_text(
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

    print(
        f"HTTP timeout: "
        f"{REQUEST_TIMEOUT} seconds.",
        flush=True,
    )

    print(
        f"Browser timeout: "
        f"{BROWSER_TIMEOUT_MS} ms.",
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
                source
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
