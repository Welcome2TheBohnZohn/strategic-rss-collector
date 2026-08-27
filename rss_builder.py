#!/usr/bin/env python3

import hashlib
import html
import io
import json
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone
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

DEFAULT_REQUEST_TIMEOUT = 12
DEFAULT_MAX_RETRIES = 1
DEFAULT_RETRY_BACKOFF = 1
DEFAULT_BROWSER_TIMEOUT_MS = 25000

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

    text = (
        text.replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
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


def source_timeout(source):

    try:

        return max(
            1,
            int(
                source.get(
                    "request_timeout",
                    DEFAULT_REQUEST_TIMEOUT,
                )
            ),
        )

    except Exception:

        return DEFAULT_REQUEST_TIMEOUT


def source_max_retries(source):

    try:

        return max(
            0,
            int(
                source.get(
                    "max_retries",
                    DEFAULT_MAX_RETRIES,
                )
            ),
        )

    except Exception:

        return DEFAULT_MAX_RETRIES


def source_retry_backoff(source):

    try:

        return max(
            0,
            int(
                source.get(
                    "retry_backoff",
                    DEFAULT_RETRY_BACKOFF,
                )
            ),
        )

    except Exception:

        return DEFAULT_RETRY_BACKOFF


def source_browser_timeout_ms(source):

    return max(
        DEFAULT_BROWSER_TIMEOUT_MS,
        source_timeout(source) * 1000,
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


def request_headers(
    json_content=False,
):

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/rss+xml,"
            "application/atom+xml,"
            "application/json,"
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

    if json_content:

        headers[
            "Content-Type"
        ] = (
            "application/json;"
            "charset=utf-8"
        )

    return headers


def fetch(
    url,
    *,
    timeout=DEFAULT_REQUEST_TIMEOUT,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_backoff=DEFAULT_RETRY_BACKOFF,
    verify_ssl=True,
    params=None,
):

    if not verify_ssl:

        urllib3.disable_warnings(
            urllib3.exceptions.InsecureRequestWarning
        )

    last_error = ""

    total_attempts = (
        max_retries + 1
    )

    for attempt_index in range(
        total_attempts
    ):

        attempt_number = (
            attempt_index + 1
        )

        try:

            print(
                f"    Request "
                f"{attempt_number}/"
                f"{total_attempts}: "
                f"{url}",
                flush=True,
            )

            response = requests.get(
                url,
                headers=request_headers(),
                params=params,
                timeout=timeout,
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
                "response": response,
            }

        except Exception as exc:

            last_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                f"    Request failed: "
                f"{last_error}",
                flush=True,
            )

            if (
                attempt_index
                < total_attempts - 1
            ):

                wait_seconds = (
                    retry_backoff
                    * attempt_number
                )

                if wait_seconds > 0:

                    print(
                        f"    Retrying in "
                        f"{wait_seconds} "
                        f"seconds...",
                        flush=True,
                    )

                    time.sleep(
                        wait_seconds
                    )

    return {
        "ok": False,
        "url": url,
        "status": None,
        "text": "",
        "content": b"",
        "error": last_error,
        "response": None,
    }


def post_json(
    url,
    payload,
    *,
    timeout=DEFAULT_REQUEST_TIMEOUT,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_backoff=DEFAULT_RETRY_BACKOFF,
    verify_ssl=True,
):

    if not verify_ssl:

        urllib3.disable_warnings(
            urllib3.exceptions.InsecureRequestWarning
        )

    last_error = ""

    total_attempts = (
        max_retries + 1
    )

    for attempt_index in range(
        total_attempts
    ):

        attempt_number = (
            attempt_index + 1
        )

        try:

            print(
                f"    JSON POST "
                f"{attempt_number}/"
                f"{total_attempts}: "
                f"{url}",
                flush=True,
            )

            response = requests.post(
                url,
                headers=request_headers(
                    json_content=True,
                ),
                json=payload,
                timeout=timeout,
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
                "response": response,
            }

        except Exception as exc:

            last_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                f"    JSON POST failed: "
                f"{last_error}",
                flush=True,
            )

            if (
                attempt_index
                < total_attempts - 1
            ):

                wait_seconds = (
                    retry_backoff
                    * attempt_number
                )

                if wait_seconds > 0:

                    print(
                        f"    Retrying "
                        f"JSON POST in "
                        f"{wait_seconds} "
                        f"seconds...",
                        flush=True,
                    )

                    time.sleep(
                        wait_seconds
                    )

    return {
        "ok": False,
        "url": url,
        "status": None,
        "text": "",
        "content": b"",
        "error": last_error,
        "response": None,
    }


def fetch_for_source(
    source,
    url,
    *,
    params=None,
    override_retries=None,
):

    if override_retries is None:

        retries = (
            source_max_retries(
                source
            )
        )

    else:

        retries = max(
            0,
            int(
                override_retries
            ),
        )

    return fetch(
        url,
        timeout=source_timeout(
            source
        ),
        max_retries=retries,
        retry_backoff=(
            source_retry_backoff(
                source
            )
        ),
        verify_ssl=source.get(
            "verify_ssl",
            True,
        ),
        params=params,
    )


def post_json_for_source(
    source,
    url,
    payload,
    *,
    override_retries=None,
):

    if override_retries is None:

        retries = (
            source_max_retries(
                source
            )
        )

    else:

        retries = max(
            0,
            int(
                override_retries
            ),
        )

    return post_json(
        url,
        payload,
        timeout=source_timeout(
            source
        ),
        max_retries=retries,
        retry_backoff=(
            source_retry_backoff(
                source
            )
        ),
        verify_ssl=source.get(
            "verify_ssl",
            True,
        ),
    )


def fetch_source(source):

    errors = []

    for url in start_urls(
        source
    ):

        result = fetch_for_source(
            source,
            url,
        )

        if result[
            "ok"
        ]:

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
        "response": None,
    }


def response_json(result):

    if not result.get(
        "ok"
    ):

        return None

    response = result.get(
        "response"
    )

    if response is not None:

        try:

            return response.json()

        except Exception:

            pass

    try:

        return json.loads(
            result.get(
                "text",
                "",
            )
        )

    except Exception:

        return None


def canonical_url(
    base_url,
    href,
):

    try:

        # Some source pages publish href values with stray leading
        # or trailing whitespace. Strip that before urljoin so a
        # valid URL does not become a request ending in %20/%20%20.
        clean_base = str(
            base_url
            or ""
        ).strip()

        clean_href = str(
            href
            or ""
        ).strip()

        if not clean_href:

            return ""

        url = urljoin(
            clean_base,
            clean_href,
        ).strip()

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
        ).geturl().strip()

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
        or first.endswith(
            "." + second
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
                not found[
                    url
                ]
                and text
            )
        ):

            found[
                url
            ] = text

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
            match.group(
                1
            ),
        )

        if (
            url
            and url not in found
        ):

            found[
                url
            ] = ""

    return [
        {
            "url": url,
            "text": text,
        }
        for url, text
        in found.items()
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

        if len(
            text
        ) < 4:

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

        if len(
            text
        ) >= 10:

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
            keyword
            in url.lower()
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

        (
            year,
            month,
            day,
            hour,
            minute,
        ) = (
            chinese_match.groups()
        )

        try:

            return datetime(
                int(
                    year
                ),
                int(
                    month
                ),
                int(
                    day
                ),
                int(
                    hour
                    or 0
                ),
                int(
                    minute
                    or 0
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
                    match.group(
                        1
                    )
                ),
                int(
                    match.group(
                        2
                    )
                ),
                int(
                    match.group(
                        3
                    )
                ),
            )

        compact_match = re.search(
            r"/(20\d{2})"
            r"(\d{2})"
            r"(\d{2})/",
            url,
        )

        if compact_match:

            return datetime(
                int(
                    compact_match.group(
                        1
                    )
                ),
                int(
                    compact_match.group(
                        2
                    )
                ),
                int(
                    compact_match.group(
                        3
                    )
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

    for (
        attribute,
        value,
    ) in meta_candidates:

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

        (
            year,
            month,
            day,
            hour,
            minute,
        ) = match.groups()

        try:

            return datetime(
                int(
                    year
                ),
                int(
                    month
                ),
                int(
                    day
                ),
                int(
                    hour
                    or 0
                ),
                int(
                    minute
                    or 0
                ),
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
            <= len(
                text
            )
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


def norinco_article_title(
    page_html,
    fallback_title,
    extracted_title,
):

    generic_titles = {
        "新闻中心",
        "首页",
        "中国兵器工业集团有限公司",
        "NORINCO Group",
    }

    current = normalize_text(
        extracted_title
    )

    if (
        current
        and current not in generic_titles
    ):

        return current

    soup = BeautifulSoup(
        page_html,
        "lxml",
    )

    # NORINCO article pages often expose a generic H1/page title,
    # while the actual story headline appears in another heading
    # or metadata field. Prefer those before falling back to the
    # listing-page anchor text.
    meta_checks = [
        (
            "property",
            "og:title",
        ),
        (
            "name",
            "ArticleTitle",
        ),
        (
            "name",
            "articleTitle",
        ),
        (
            "name",
            "title",
        ),
    ]

    for attribute, value in meta_checks:

        node = soup.find(
            "meta",
            attrs={
                attribute: value
            },
        )

        if not node:

            continue

        title_text = normalize_text(
            node.get(
                "content",
                "",
            )
        )

        if (
            4 <= len(
                title_text
            ) <= 300
            and title_text not in generic_titles
        ):

            return title_text

    fallback = normalize_text(
        fallback_title
    )

    fallback_prefix = re.sub(
        r"(?:\.{3,}|…+)$",
        "",
        fallback,
    ).strip()

    heading_candidates = []

    for node in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
        ]
    ):

        title_text = normalize_text(
            node.get_text(
                " ",
                strip=True,
            )
        )

        if (
            4 <= len(
                title_text
            ) <= 300
            and title_text not in generic_titles
        ):

            heading_candidates.append(
                title_text
            )

    if (
        fallback_prefix
        and len(
            fallback_prefix
        ) >= 6
    ):

        for title_text in heading_candidates:

            if title_text.startswith(
                fallback_prefix
            ):

                return title_text

    if heading_candidates:

        return heading_candidates[
            0
        ]

    if (
        fallback
        and fallback not in generic_titles
    ):

        return fallback

    return (
        current
        or fallback
        or "Untitled"
    )


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

            if len(
                text
            ) >= 200:

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

        if len(
            text
        ) >= 30:

            paragraphs.append(
                text
            )

    if paragraphs:

        text = "\n\n".join(
            paragraphs
        )

        if len(
            text
        ) >= 200:

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

    base_name = safe_filename(
        article[
            "title"
        ],
        article[
            "url"
        ],
    )

    path = (
        folder
        / (
            base_name
            + ".md"
        )
    )

    # Preserve human-readable title filenames, but do not let
    # two different articles with the same title overwrite one
    # another. If the existing file already belongs to this URL,
    # reuse it. Otherwise append a deterministic short URL hash.
    if path.exists():

        existing_text = ""

        try:

            existing_text = path.read_text(
                encoding="utf-8"
            )

        except Exception:

            pass

        source_marker = (
            "Source: "
            + article[
                "url"
            ]
        )

        if source_marker not in existing_text:

            url_hash = hashlib.sha1(
                article[
                    "url"
                ].encode(
                    "utf-8"
                )
            ).hexdigest()[
                :8
            ]

            path = (
                folder
                / (
                    base_name
                    + "_"
                    + url_hash
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
        "=== MATCHED CANDIDATES ===",
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
        str(
            text
        )[
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

    # RSS readers often apply their own date sorting, but the feed
    # itself should still be deterministic and newest-first. Items
    # without a publication date are placed after all dated items.
    sorted_articles = sorted(
        articles,
        key=lambda article: (
            normalize_datetime(
                article.get(
                    "published"
                )
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )

    for article in sorted_articles:

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

        published = (
            normalize_datetime(
                article.get(
                    "published"
                )
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
        "request_timeout": (
            source_timeout(
                source
            )
        ),
        "max_retries": (
            source_max_retries(
                source
            )
        ),
        "retry_backoff": (
            source_retry_backoff(
                source
            )
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
        for article
        in articles
        if article.get(
            "text"
        )
    )

    status[
        "articles_with_date"
    ] = sum(
        1
        for article
        in articles
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
        source
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
                for part
                in entry[
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

            if value:

                try:

                    published = datetime(
                        *value[
                            :6
                        ],
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

    candidates, links = (
        find_candidates(
            source,
            listing_html,
            listing_url,
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
            len(
                articles
            )
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
                        source_browser_timeout_ms(
                            source
                        )
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

                page_html = (
                    browser_page.content()
                )

                final_url = (
                    browser_page.url
                )

            else:

                page = fetch_for_source(
                    source,
                    url,
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

            if source.get(
                "slug"
            ) == "norinco-cn":

                article[
                    "title"
                ] = norinco_article_title(
                    page_html,
                    candidate[
                        "anchor_title"
                    ],
                    article.get(
                        "title",
                        "",
                    ),
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

        except Exception as exc:

            print(
                f"    Article failed: "
                f"{url} -> "
                f"{type(exc).__name__}: "
                f"{exc}",
                flush=True,
            )

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
        source
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

    browser = (
        playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
    )

    context = (
        browser.new_context(
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

    browser_timeout = (
        source_browser_timeout_ms(
            source
        )
    )

    for url in start_urls(
        source
    ):

        attempts = (
            source_max_retries(
                source
            )
            + 1
        )

        for attempt_index in range(
            attempts
        ):

            attempt_number = (
                attempt_index + 1
            )

            try:

                print(
                    f"    Browser "
                    f"{attempt_number}/"
                    f"{attempts}: "
                    f"{url}",
                    flush=True,
                )

                response = page.goto(
                    url,
                    wait_until=(
                        "domcontentloaded"
                    ),
                    timeout=(
                        browser_timeout
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

                content = (
                    page.content()
                )

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

                    content = (
                        page.content()
                    )

                status_code = (
                    response.status
                    if response
                    else 200
                )

                if status_code < 400:

                    return {
                        "ok": True,
                        "url": page.url,
                        "status": (
                            status_code
                        ),
                        "text": content,
                        "error": "",
                    }

                error_message = (
                    f"{url} -> "
                    f"HTTP "
                    f"{status_code}"
                )

            except Exception as exc:

                error_message = (
                    f"{url} -> "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            errors.append(
                error_message
            )

            if (
                attempt_index
                < attempts - 1
            ):

                wait_seconds = (
                    source_retry_backoff(
                        source
                    )
                    * attempt_number
                )

                if wait_seconds > 0:

                    print(
                        f"    Browser "
                        f"retry in "
                        f"{wait_seconds} "
                        f"seconds...",
                        flush=True,
                    )

                    time.sleep(
                        wait_seconds
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

            browser, context = (
                browser_context(
                    playwright,
                    source,
                )
            )

            page = (
                context.new_page()
            )

            page.set_default_timeout(
                source_browser_timeout_ms(
                    source
                )
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


# ============================================================
# NPC NATIONAL LAWS AND REGULATIONS DATABASE
# ============================================================


def npc_fetch_category_map(source):

    result = fetch_for_source(
        source,
        source[
            "npc_enum_url"
        ],
    )

    if not result[
        "ok"
    ]:

        return (
            None,
            result[
                "error"
            ],
            result,
        )

    payload = response_json(
        result
    )

    try:

        children = (
            payload[
                "data"
            ][
                "flfgfl"
            ][
                "children"
            ]
        )

    except Exception:

        return (
            None,
            (
                "NPC enumData response "
                "did not contain "
                "data.flfgfl.children"
            ),
            result,
        )

    mapping = {}

    for node in children:

        name = normalize_text(
            node.get(
                "name",
                "",
            )
        )

        codes = [
            code
            for code
            in node.get(
                "codeIdList",
                [],
            )
            if code is not None
        ]

        if (
            name
            and codes
        ):

            mapping[
                name
            ] = codes

    return (
        mapping,
        "",
        result,
    )


def npc_search_page(
    source,
    codes,
    page_num,
    page_size,
):

    payload = {
        "searchRange": 1,
        "sxrq": [],
        "gbrq": [],
        "searchType": 2,
        "sxx": [],
        "gbrqYear": [],
        "flfgCodeId": codes,
        "zdjgCodeId": [],
        "searchContent": "",
        "orderByParam": {
            "order": "-1",
            "sort": "",
        },
        "pageNum": page_num,
        "pageSize": page_size,
    }

    result = post_json_for_source(
        source,
        source[
            "npc_search_url"
        ],
        payload,
    )

    data = response_json(
        result
    )

    if not result[
        "ok"
    ]:

        return (
            None,
            result[
                "error"
            ],
            result,
            payload,
        )

    if not isinstance(
        data,
        dict,
    ):

        return (
            None,
            (
                "NPC search response "
                "was not JSON"
            ),
            result,
            payload,
        )

    if data.get(
        "code"
    ) != 200:

        return (
            None,
            (
                "NPC search API "
                "returned code="
                + str(
                    data.get(
                        "code"
                    )
                )
                + ": "
                + str(
                    data.get(
                        "message"
                    )
                    or data
                )
            ),
            result,
            payload,
        )

    return (
        data,
        "",
        result,
        payload,
    )


def npc_matches_keywords(
    record,
    keywords,
):

    haystack = normalize_text(
        " ".join(
            [
                str(
                    record.get(
                        "title",
                        "",
                    )
                ),
                str(
                    record.get(
                        "zdjgName",
                        "",
                    )
                ),
                str(
                    record.get(
                        "flxz",
                        "",
                    )
                ),
            ]
        )
    )

    return any(
        keyword in haystack
        for keyword
        in keywords
    )


def npc_record_date(record):

    return (
        try_parse_date(
            record.get(
                "gbrq"
            )
        )
        or datetime(
            1900,
            1,
            1,
        )
    )


def npc_record_text(
    record,
    law_text="",
):

    lines = [
        normalize_text(
            record.get(
                "title",
                "",
            )
        )
    ]

    fields = [
        (
            "发布机关",
            record.get(
                "zdjgName"
            ),
        ),
        (
            "法律性质",
            record.get(
                "flxz"
            ),
        ),
        (
            "公布日期",
            record.get(
                "gbrq"
            ),
        ),
        (
            "施行日期",
            record.get(
                "sxrq"
            ),
        ),
        (
            "状态",
            record.get(
                "sxx"
            ),
        ),
        (
            "数据库标识",
            record.get(
                "bbbs"
            ),
        ),
    ]

    for (
        label,
        value,
    ) in fields:

        value = normalize_text(
            value
        )

        if value:

            lines.append(
                f"{label}: "
                f"{value}"
            )

    metadata = "\n".join(
        line
        for line in lines
        if line
    )

    if law_text:

        return normalize_text(
            metadata
            + "\n\n"
            + law_text
        )[:50000]

    return metadata[
        :50000
    ]


def npc_extract_docx_text(content):

    try:

        with zipfile.ZipFile(
            io.BytesIO(
                content
            )
        ) as archive:

            xml_bytes = archive.read(
                "word/document.xml"
            )

        root = ET.fromstring(
            xml_bytes
        )

        namespace = (
            "{http://schemas.openxmlformats.org/"
            "wordprocessingml/2006/main}"
        )

        paragraphs = []

        for paragraph in root.iter(
            namespace
            + "p"
        ):

            parts = []

            for node in paragraph.iter(
                namespace
                + "t"
            ):

                if node.text:

                    parts.append(
                        node.text
                    )

            text = normalize_text(
                "".join(
                    parts
                )
            )

            if text:

                paragraphs.append(
                    text
                )

        return normalize_text(
            "\n\n".join(
                paragraphs
            )
        )[:50000]

    except Exception:

        return ""


def npc_batch_download_urls(
    source,
    records,
):

    bbbs_records = [
        record
        for record in records
        if record.get(
            "bbbs"
        )
    ]

    if not bbbs_records:

        return {}

    endpoint = (
        source.get(
            "npc_batch_url"
        )
        or (
            "https://flk.npc.gov.cn/"
            "law-search/download/batch"
        )
    )

    payload = [
        {
            "bbbs": record[
                "bbbs"
            ],
            "format": "docx",
        }
        for record
        in bbbs_records
    ]

    result = post_json_for_source(
        source,
        endpoint,
        payload,
    )

    data = response_json(
        result
    )

    if (
        not result[
            "ok"
        ]
        or not isinstance(
            data,
            dict,
        )
        or data.get(
            "code"
        ) != 200
    ):

        return {}

    items = (
        data.get(
            "data"
        )
        or []
    )

    output = {}

    if len(
        items
    ) == len(
        bbbs_records
    ):

        for (
            record,
            item,
        ) in zip(
            bbbs_records,
            items,
        ):

            if (
                isinstance(
                    item,
                    dict,
                )
                and item.get(
                    "url"
                )
            ):

                output[
                    record[
                        "bbbs"
                    ]
                ] = item[
                    "url"
                ]

        return output

    for item in items:

        if (
            not isinstance(
                item,
                dict,
            )
            or not item.get(
                "url"
            )
        ):

            continue

        bbbs = item.get(
            "bbbs"
        )

        if bbbs:

            output[
                bbbs
            ] = item[
                "url"
            ]

    return output


def run_npc(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [NPC LAW-SEARCH API]: "
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
    ] = "npc"

    (
        category_map,
        enum_error,
        enum_result,
    ) = npc_fetch_category_map(
        source
    )

    status[
        "resolved_url"
    ] = source.get(
        "npc_enum_url",
        source[
            "start_url"
        ],
    )

    status[
        "http_status"
    ] = (
        enum_result.get(
            "status"
        )
        if enum_result
        else None
    )

    diagnostic = {
        "enum_url": source.get(
            "npc_enum_url"
        ),
        "search_url": source.get(
            "npc_search_url"
        ),
        "requested_categories": (
            source.get(
                "npc_categories",
                [],
            )
        ),
        "keywords": source.get(
            "npc_keywords",
            [],
        ),
        "category_map": (
            category_map
            or {}
        ),
        "pages": [],
        "matched_records": [],
    }

    if not category_map:

        status[
            "error"
        ] = (
            enum_error
            or (
                "NPC category map "
                "could not be loaded."
            )
        )

        save_raw(
            source,
            json.dumps(
                diagnostic,
                ensure_ascii=False,
                indent=2,
            ),
            "law-search-diagnostic.json",
        )

        return status

    categories = source.get(
        "npc_categories",
        [
            "法律",
            "行政法规",
        ],
    )

    keywords = source.get(
        "npc_keywords",
        [],
    )

    page_size = int(
        source.get(
            "npc_page_size",
            100,
        )
    )

    max_pages = int(
        source.get(
            "npc_max_pages_per_category",
            10,
        )
    )

    records_by_id = {}

    total_rows_seen = 0
    successful_pages = 0

    for category in categories:

        codes = category_map.get(
            category
        )

        if not codes:

            diagnostic[
                "pages"
            ].append(
                {
                    "category": (
                        category
                    ),
                    "error": (
                        "Category not "
                        "found in enumData"
                    ),
                }
            )

            continue

        page_num = 1
        category_seen = 0
        category_total = None

        while (
            page_num
            <= max_pages
        ):

            (
                page,
                error,
                result,
                request_payload,
            ) = npc_search_page(
                source,
                codes,
                page_num,
                page_size,
            )

            page_diag = {
                "category": category,
                "page": page_num,
                "status": (
                    result.get(
                        "status"
                    )
                    if result
                    else None
                ),
                "request": request_payload,
                "error": error,
                "rows": 0,
                "total": None,
                "matches": 0,
            }

            if page is None:

                diagnostic[
                    "pages"
                ].append(
                    page_diag
                )

                break

            successful_pages += 1

            rows = (
                page.get(
                    "rows",
                    [],
                )
                or []
            )

            total = page.get(
                "total",
                len(
                    rows
                ),
            )

            category_total = total

            page_diag[
                "rows"
            ] = len(
                rows
            )

            page_diag[
                "total"
            ] = total

            total_rows_seen += len(
                rows
            )

            category_seen += len(
                rows
            )

            for row in rows:

                if not isinstance(
                    row,
                    dict,
                ):

                    continue

                if (
                    keywords
                    and not npc_matches_keywords(
                        row,
                        keywords,
                    )
                ):

                    continue

                key = (
                    row.get(
                        "bbbs"
                    )
                    or row.get(
                        "id"
                    )
                    or (
                        normalize_text(
                            row.get(
                                "title",
                                "",
                            )
                        )
                        + str(
                            row.get(
                                "gbrq",
                                "",
                            )
                        )
                    )
                )

                if not key:

                    continue

                records_by_id.setdefault(
                    key,
                    row,
                )

                page_diag[
                    "matches"
                ] += 1

            diagnostic[
                "pages"
            ].append(
                page_diag
            )

            if (
                not rows
                or category_seen
                >= (
                    category_total
                    or 0
                )
            ):

                break

            page_num += 1

    records = sorted(
        records_by_id.values(),
        key=npc_record_date,
        reverse=True,
    )

    diagnostic[
        "matched_records"
    ] = records[
        :100
    ]

    status[
        "all_links"
    ] = total_rows_seen

    status[
        "candidate_links"
    ] = len(
        records
    )

    if successful_pages == 0:

        status[
            "error"
        ] = (
            "NPC enumData loaded, "
            "but no law-search pages "
            "could be retrieved."
        )

        save_raw(
            source,
            json.dumps(
                diagnostic,
                ensure_ascii=False,
                indent=2,
            ),
            "law-search-diagnostic.json",
        )

        return status

    status[
        "http_status"
    ] = 200

    status[
        "resolved_url"
    ] = source[
        "npc_search_url"
    ]

    selected = records[
        :MAX_ITEMS_PER_SOURCE
    ]

    download_urls = (
        npc_batch_download_urls(
            source,
            selected,
        )
    )

    articles = []

    for record in selected:

        status[
            "attempted"
        ] += 1

        bbbs = (
            record.get(
                "bbbs"
            )
            or ""
        )

        title = (
            normalize_text(
                record.get(
                    "title",
                    "",
                )
            )
            or "Untitled"
        )

        published = try_parse_date(
            record.get(
                "gbrq"
            )
        )

        law_text = ""

        download_url = (
            download_urls.get(
                bbbs
            )
        )

        if download_url:

            doc_result = (
                fetch_for_source(
                    source,
                    download_url,
                    override_retries=0,
                )
            )

            if doc_result[
                "ok"
            ]:

                law_text = (
                    npc_extract_docx_text(
                        doc_result[
                            "content"
                        ]
                    )
                )

        article_url = source[
            "source_url"
        ]

        if bbbs:

            article_url = (
                source[
                    "source_url"
                ].rstrip("/")
                + "?bbbs="
                + str(
                    bbbs
                )
            )

        article = {
            "title": title,
            "url": article_url,
            "guid": (
                bbbs
                or article_url
            ),
            "text": (
                npc_record_text(
                    record,
                    law_text,
                )
            ),
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

    populate_counts(
        status,
        articles,
    )

    write_feed(
        source,
        articles,
    )

    save_raw(
        source,
        json.dumps(
            diagnostic,
            ensure_ascii=False,
            indent=2,
        ),
        "law-search-diagnostic.json",
    )

    return status



# ============================================================
# CHINA NATIONAL DEFENSE NEWS DIGITAL NEWSPAPER
# ============================================================


def newspaper_issue_url(
    source,
    issue_date,
    paper_number,
):

    base_url = source[
        "start_url"
    ].split(
        "?",
        1,
    )[0]

    paper_name = source.get(
        "paper_name",
        "zggfb",
    )

    return (
        base_url
        + "?paperDate="
        + issue_date
        + "&paperName="
        + paper_name
        + "&paperNumber="
        + paper_number
    )


def newspaper_article_links(
    source,
    links,
    issue_date,
):

    paper_name = source.get(
        "paper_name",
        "zggfb",
    )

    ignored_titles = {
        "图片",
        "启事",
        "广告",
        "PDF版下载",
        "上一版",
        "下一版",
    }

    output = []

    for item in links:

        url = item.get(
            "url",
            "",
        )

        title = normalize_text(
            item.get(
                "text",
                "",
            )
        )

        try:

            parsed = urlparse(
                url
            )

            query = parse_qs(
                parsed.query
            )

        except Exception:

            continue

        if (
            "/szb_223187/gfbszbxq/"
            not in parsed.path
        ):

            continue

        if (
            query.get(
                "paperName",
                [
                    ""
                ],
            )[0]
            != paper_name
        ):

            continue

        if (
            query.get(
                "paperDate",
                [
                    ""
                ],
            )[0]
            != issue_date
        ):

            continue

        if not query.get(
            "articleid"
        ):

            continue

        if (
            not title
            or title in ignored_titles
        ):

            continue

        output.append(
            {
                "url": url,
                "anchor_title": title,
            }
        )

    return output


def run_newspaper(source):

    print(
        "\n==> "
        + source[
            "slug"
        ]
        + " [NEWSPAPER]: "
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
    ] = "newspaper"

    lookback_days = max(
        1,
        int(
            source.get(
                "newspaper_lookback_days",
                14,
            )
        ),
    )

    paper_pages = source.get(
        "paper_pages",
        [
            "01",
            "02",
            "03",
            "04",
        ],
    )

    diagnostics = {
        "issue_date": None,
        "issue_pages": [],
        "candidates": [],
    }

    try:

        with sync_playwright() as playwright:

            browser, context = (
                browser_context(
                    playwright,
                    source,
                )
            )

            page = context.new_page()

            page.set_default_timeout(
                source_browser_timeout_ms(
                    source
                )
            )

            latest_date = None
            first_page_links = None
            first_page_url = ""
            last_http_status = None

            china_today = (
                datetime.now(
                    timezone.utc
                )
                + timedelta(
                    hours=8
                )
            ).date()

            for day_offset in range(
                lookback_days
            ):

                issue_date = (
                    china_today
                    - timedelta(
                        days=day_offset
                    )
                ).isoformat()

                issue_url = (
                    newspaper_issue_url(
                        source,
                        issue_date,
                        "01",
                    )
                )

                try:

                    response = page.goto(
                        issue_url,
                        wait_until=(
                            "domcontentloaded"
                        ),
                        timeout=(
                            source_browser_timeout_ms(
                                source
                            )
                        ),
                    )

                    page.wait_for_timeout(
                        3000
                    )

                    try:

                        page.wait_for_load_state(
                            "networkidle",
                            timeout=3500,
                        )

                    except PlaywrightTimeoutError:

                        pass

                    last_http_status = (
                        response.status
                        if response
                        else 200
                    )

                    links = collect_links(
                        page.content(),
                        page.url,
                    )

                    candidates = (
                        newspaper_article_links(
                            source,
                            links,
                            issue_date,
                        )
                    )

                    if candidates:

                        latest_date = (
                            issue_date
                        )

                        first_page_links = (
                            links
                        )

                        first_page_url = (
                            page.url
                        )

                        break

                except Exception as exc:

                    print(
                        "    Newspaper issue "
                        f"probe failed: "
                        f"{issue_url} -> "
                        f"{type(exc).__name__}: "
                        f"{exc}",
                        flush=True,
                    )

            status[
                "http_status"
            ] = last_http_status

            if not latest_date:

                status[
                    "error"
                ] = (
                    "No rendered China "
                    "National Defense News "
                    "issue with article links "
                    f"was found in the last "
                    f"{lookback_days} days."
                )

                save_raw(
                    source,
                    json.dumps(
                        diagnostics,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    (
                        "newspaper-"
                        "diagnostic.json"
                    ),
                )

                write_feed(
                    source,
                    [],
                )

                context.close()
                browser.close()

                return status

            diagnostics[
                "issue_date"
            ] = latest_date

            status[
                "resolved_url"
            ] = first_page_url

            candidate_map = {}
            total_links = 0

            for paper_number in paper_pages:

                if (
                    paper_number == "01"
                    and first_page_links
                    is not None
                ):

                    links = (
                        first_page_links
                    )

                    page_url = (
                        first_page_url
                    )

                else:

                    page_url = (
                        newspaper_issue_url(
                            source,
                            latest_date,
                            paper_number,
                        )
                    )

                    try:

                        response = page.goto(
                            page_url,
                            wait_until=(
                                "domcontentloaded"
                            ),
                            timeout=(
                                source_browser_timeout_ms(
                                    source
                                )
                            ),
                        )

                        page.wait_for_timeout(
                            2500
                        )

                        try:

                            page.wait_for_load_state(
                                "networkidle",
                                timeout=3000,
                            )

                        except PlaywrightTimeoutError:

                            pass

                        if response:

                            status[
                                "http_status"
                            ] = response.status

                        links = collect_links(
                            page.content(),
                            page.url,
                        )

                        page_url = page.url

                    except Exception as exc:

                        diagnostics[
                            "issue_pages"
                        ].append(
                            {
                                "paper_number": (
                                    paper_number
                                ),
                                "url": page_url,
                                "error": (
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                            }
                        )

                        continue

                total_links += len(
                    links
                )

                page_candidates = (
                    newspaper_article_links(
                        source,
                        links,
                        latest_date,
                    )
                )

                diagnostics[
                    "issue_pages"
                ].append(
                    {
                        "paper_number": (
                            paper_number
                        ),
                        "url": page_url,
                        "links": len(
                            links
                        ),
                        "article_links": len(
                            page_candidates
                        ),
                    }
                )

                for candidate in (
                    page_candidates
                ):

                    candidate_map.setdefault(
                        candidate[
                            "url"
                        ],
                        candidate,
                    )

            candidates = list(
                candidate_map.values()
            )

            diagnostics[
                "candidates"
            ] = candidates

            status[
                "all_links"
            ] = total_links

            status[
                "candidate_links"
            ] = len(
                candidates
            )

            articles = []

            issue_published = (
                datetime.fromisoformat(
                    latest_date
                )
            )

            for candidate in candidates:

                if len(
                    articles
                ) >= MAX_ITEMS_PER_SOURCE:

                    break

                status[
                    "attempted"
                ] += 1

                try:

                    response = page.goto(
                        candidate[
                            "url"
                        ],
                        wait_until=(
                            "domcontentloaded"
                        ),
                        timeout=(
                            source_browser_timeout_ms(
                                source
                            )
                        ),
                    )

                    page.wait_for_timeout(
                        1200
                    )

                    if response:

                        status[
                            "http_status"
                        ] = response.status

                    article = extract_article(
                        page.content(),
                        candidate[
                            "anchor_title"
                        ],
                        page.url,
                    )

                    if len(
                        article[
                            "text"
                        ]
                    ) < 200:

                        continue

                    generic_titles = {
                        "中国国防报",
                        "中国军网",
                        "数字报刊",
                    }

                    if (
                        not article.get(
                            "title"
                        )
                        or article[
                            "title"
                        ] in generic_titles
                    ):

                        article[
                            "title"
                        ] = candidate[
                            "anchor_title"
                        ]

                    article[
                        "url"
                    ] = page.url

                    article[
                        "guid"
                    ] = page.url

                    article[
                        "published"
                    ] = issue_published

                    save_article(
                        source[
                            "slug"
                        ],
                        article,
                    )

                    articles.append(
                        article
                    )

                except Exception as exc:

                    print(
                        "    Newspaper article "
                        f"failed: "
                        f"{candidate['url']} -> "
                        f"{type(exc).__name__}: "
                        f"{exc}",
                        flush=True,
                    )

            populate_counts(
                status,
                articles,
            )

            write_feed(
                source,
                articles,
            )

            save_raw(
                source,
                json.dumps(
                    diagnostics,
                    ensure_ascii=False,
                    indent=2,
                ),
                (
                    "newspaper-"
                    "diagnostic.json"
                ),
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


# ============================================================
# CNNVD
# ============================================================


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
        for line
        in segment.splitlines()
    ]

    lines = [
        line
        for line
        in lines
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
                r"^(超危|高危|"
                r"中危|低危|"
                r"未知|严重)\s*",
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

        if len(
            line
        ) >= 4:

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

    for (
        index,
        match,
    ) in enumerate(
        matches
    ):

        cnnvd_id = (
            match.group(
                0
            ).upper()
        )

        if cnnvd_id in seen:

            continue

        seen.add(
            cnnvd_id
        )

        start = max(
            0,
            match.start()
            - 80,
        )

        next_start = (
            matches[
                index + 1
            ].start()
            if (
                index + 1
                < len(
                    matches
                )
            )
            else len(
                text
            )
        )

        end = min(
            next_start,
            match.end()
            + 700,
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
                if title
                != cnnvd_id
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
            len(
                articles
            )
            >= MAX_ITEMS_PER_SOURCE
        ):

            break

    return articles



def parse_cnnvd_dom(
    rendered_html,
    rendered_text,
    source,
):

    soup = BeautifulSoup(
        rendered_html,
        "lxml",
    )

    articles = []
    seen = set()

    for row in soup.select(
        "div.el-row.content-center"
    ):

        title_node = row.select_one(
            ".item-content-title-content"
        )

        code_node = row.select_one(
            ".content-code"
        )

        if (
            not title_node
            or not code_node
        ):

            continue

        code_text = normalize_text(
            code_node.get_text(
                " ",
                strip=True,
            )
        )

        id_match = re.search(
            r"CNNVD-\d{4,6}-\d+",
            code_text,
            re.IGNORECASE,
        )

        if not id_match:

            continue

        cnnvd_id = (
            id_match.group(
                0
            ).upper()
        )

        if cnnvd_id in seen:

            continue

        title = normalize_text(
            title_node.get(
                "title"
            )
            or title_node.get_text(
                " ",
                strip=True,
            )
        )

        if not title:

            continue

        seen.add(
            cnnvd_id
        )

        severity_node = row.select_one(
            ".show-but span"
        )

        severity = normalize_text(
            severity_node.get_text(
                " ",
                strip=True,
            )
            if severity_node
            else ""
        )

        detail_node = row.select_one(
            ".content-detail"
        )

        detail_text = normalize_text(
            detail_node.get_text(
                " ",
                strip=True,
            )
            if detail_node
            else ""
        )

        published = None

        date_match = re.search(
            r"收录时间[：:]\s*"
            r"(20\d{2}[-/.]"
            r"\d{1,2}[-/.]"
            r"\d{1,2})",
            detail_text,
        )

        if date_match:

            published = try_parse_date(
                date_match.group(
                    1
                )
            )

        text_parts = [
            title
        ]

        if severity:

            text_parts.append(
                "危害等级: "
                + severity
            )

        if detail_text:

            text_parts.append(
                detail_text
            )

        text_parts.append(
            "CNNVD编号: "
            + cnnvd_id
        )

        item_url = (
            source[
                "source_url"
            ].rstrip("/")
            + "/home/globalSearch?keyword="
            + cnnvd_id
        )

        articles.append(
            {
                "title": (
                    f"{cnnvd_id} - "
                    f"{title}"
                ),
                "url": item_url,
                "guid": item_url,
                "text": "\n".join(
                    text_parts
                ),
                "published": published,
            }
        )

        if len(
            articles
        ) >= MAX_ITEMS_PER_SOURCE:

            break

    if articles:

        return articles

    # Preserve the prior parser as a fallback if CNNVD changes
    # its rendered DOM structure in the future.
    return parse_cnnvd_list(
        rendered_text,
        source,
    )

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

            browser, context = (
                browser_context(
                    playwright,
                    source,
                )
            )

            page = (
                context.new_page()
            )

            page.set_default_timeout(
                source_browser_timeout_ms(
                    source
                )
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
                    )
                    .inner_text(
                        timeout=5000
                    )
                )

            except Exception:

                body_text = (
                    BeautifulSoup(
                        page.content(),
                        "lxml",
                    )
                    .get_text(
                        "\n",
                        strip=True,
                    )
                )

            links = collect_links(
                page.content(),
                page.url,
            )

            rendered_html = (
                page.content()
            )

            articles = (
                parse_cnnvd_dom(
                    rendered_html,
                    body_text,
                    source,
                )
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

    if source_type == "npc":

        return run_npc(
            source
        )

    if source_type == "cnnvd":

        return run_cnnvd(
            source
        )

    if source_type == "newspaper":

        return run_newspaper(
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
            "npc",
            "cnnvd",
            "newspaper",
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
                (
                    "  Request timeout: "
                    + str(
                        status[
                            "request_timeout"
                        ]
                    )
                    + "s"
                ),
                (
                    "  Max retries: "
                    + str(
                        status[
                            "max_retries"
                        ]
                    )
                ),
                (
                    "  Retry backoff: "
                    + str(
                        status[
                            "retry_backoff"
                        ]
                    )
                    + "s"
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
        f"{len(sources)} "
        f"sources.",
        flush=True,
    )

    print(
        (
            "Default HTTP timeout: "
            f"{DEFAULT_REQUEST_TIMEOUT} "
            "seconds."
        ),
        flush=True,
    )

    print(
        (
            "Default retries: "
            f"{DEFAULT_MAX_RETRIES}."
        ),
        flush=True,
    )

    print(
        (
            "Per-source timeout/retry "
            "overrides are enabled."
        ),
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
