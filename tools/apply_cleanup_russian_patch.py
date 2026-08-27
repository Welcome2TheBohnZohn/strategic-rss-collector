from pathlib import Path
import json
import xml.etree.ElementTree as ET

builder_path = Path("rss_builder.py")
text = builder_path.read_text(encoding="utf-8")

helper = r'''
def replace_saved_articles(
    source_slug,
    articles,
):

    # Only replace saved articles after a source produced usable
    # items. A temporary failure therefore does not erase the last
    # successful saved article set.
    if not articles:
        return

    folder = (
        ARTICLES_DIR
        / source_slug
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in folder.glob(
        "*.md"
    ):

        try:
            path.unlink()
        except Exception as exc:
            print(
                f"    Could not remove stale article {path}: {exc}",
                flush=True,
            )

    for article in articles:
        save_article(
            source_slug,
            article,
        )


'''

if "def replace_saved_articles(" not in text:
    anchor = "def write_feed(\n"
    assert text.count(anchor) == 1, "write_feed anchor changed"
    text = text.replace(anchor, helper + anchor, 1)

if "replace_saved_articles(\n        source[" not in text:
    old = '''def write_feed(\n    source,\n    articles,\n):\n\n    FEEDS_DIR.mkdir(\n'''
    new = '''def write_feed(\n    source,\n    articles,\n):\n\n    replace_saved_articles(\n        source[\n            "slug"\n        ],\n        articles,\n    )\n\n    FEEDS_DIR.mkdir(\n'''
    assert old in text, "write_feed body anchor changed"
    text = text.replace(old, new, 1)

telegram_code = r'''
# ============================================================
# TELEGRAM PUBLIC CHANNEL PREVIEWS
# ============================================================


def telegram_title(text):

    lines = [
        normalize_text(line)
        for line in str(text).splitlines()
        if normalize_text(line)
    ]

    if not lines:
        return "Telegram post"

    title = lines[0]

    if len(title) < 25 and len(lines) > 1:
        title = normalize_text(
            title + " " + lines[1]
        )

    return title[:240]


def run_telegram(source):

    print(
        "\n==> "
        + source["slug"]
        + " [TELEGRAM]: "
        + source["start_url"],
        flush=True,
    )

    status = base_status(source)
    status["source_type"] = "telegram"

    result = fetch_source(source)
    status["http_status"] = result["status"]
    status["resolved_url"] = result.get("url", "")

    if not result["ok"]:
        status["error"] = result["error"]
        return status

    soup = BeautifulSoup(
        result["text"],
        "lxml",
    )

    wraps = soup.select(
        ".tgme_widget_message_wrap"
    )

    status["all_links"] = len(
        soup.find_all("a", href=True)
    )
    status["candidate_links"] = len(wraps)

    articles = []
    seen = set()

    for wrap in wraps:

        status["attempted"] += 1

        message = wrap.select_one(
            ".tgme_widget_message"
        )
        text_node = wrap.select_one(
            ".tgme_widget_message_text"
        )

        if not message or not text_node:
            continue

        post_id = normalize_text(
            message.get("data-post", "")
        )
        text_value = normalize_text(
            text_node.get_text("\n", strip=True)
        )

        if len(text_value) < 10:
            continue

        link_node = wrap.select_one(
            "a.tgme_widget_message_date"
        )

        url = ""
        if link_node:
            url = canonical_url(
                result["url"],
                link_node.get("href", ""),
            )

        if not url and post_id:
            url = "https://t.me/" + post_id

        if not url or url in seen:
            continue

        seen.add(url)

        published = None
        time_node = wrap.select_one(
            "time[datetime]"
        )

        if time_node:
            published = try_parse_date(
                time_node.get("datetime", "")
            )

        articles.append(
            {
                "title": telegram_title(text_value),
                "url": url,
                "guid": url,
                "text": text_value[:50000],
                "published": published,
            }
        )

    articles.sort(
        key=lambda article: (
            normalize_datetime(article.get("published"))
            or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )

    articles = articles[:MAX_ITEMS_PER_SOURCE]

    populate_counts(status, articles)

    if not articles:
        status["error"] = (
            "Telegram public preview loaded, but no text posts were extracted."
        )
        save_raw(
            source,
            result["text"],
            "telegram-preview.html",
        )

    write_feed(source, articles)
    return status


'''

if "def run_telegram(source):" not in text:
    anchor = "def run_source(source):\n"
    assert text.count(anchor) == 1, "run_source anchor changed"
    text = text.replace(anchor, telegram_code + anchor, 1)

if 'if source_type == "telegram"' not in text:
    anchor = '''    if source_type == "rss":\n\n        return run_rss(\n            source\n        )\n\n'''
    branch = '''    if source_type == "telegram":\n\n        return run_telegram(\n            source\n        )\n\n'''
    assert anchor in text, "RSS branch anchor changed"
    text = text.replace(anchor, anchor + branch, 1)

builder_path.write_text(text, encoding="utf-8")

sources_path = Path("sources.json")
sources = json.loads(sources_path.read_text(encoding="utf-8"))

replacements = {
    "mil-ru-en": {
        "title": "Russian Ministry of Defence English - Official Telegram",
        "source_url": "https://t.me/mod_russia_en",
        "start_url": "https://t.me/s/mod_russia_en",
        "language": "en",
        "source_type": "telegram",
        "request_timeout": 20,
        "max_retries": 2,
        "retry_backoff": 2,
    },
    "mid-ru-en": {
        "title": "Russian Ministry of Foreign Affairs English - Official Telegram",
        "source_url": "https://t.me/MFARussia",
        "start_url": "https://t.me/s/MFARussia",
        "language": "en",
        "source_type": "telegram",
        "request_timeout": 20,
        "max_retries": 2,
        "retry_backoff": 2,
    },
}

for source in sources:
    slug = source.get("slug")
    if slug in replacements:
        replacement = {"slug": slug}
        replacement.update(replacements[slug])
        source.clear()
        source.update(replacement)

sources_path.write_text(
    json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

# One-time cleanup using the currently committed RSS XML. This removes
# files no longer represented in the current feed and collapses duplicate
# saved files that point to the same current item URL.
removed = 0
for feed_path in Path("feeds").glob("*.xml"):
    slug = feed_path.stem
    folder = Path("articles") / slug
    if not folder.is_dir():
        continue

    try:
        root = ET.parse(feed_path).getroot()
    except Exception:
        continue

    current_urls = {
        (node.text or "").strip()
        for node in root.findall("./channel/item/link")
        if (node.text or "").strip()
    }

    if not current_urls:
        continue

    by_url = {}
    for md in folder.glob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
        except Exception:
            continue

        source_url = ""
        for line in content.splitlines():
            if line.startswith("Source: "):
                source_url = line[8:].strip()
                break

        if source_url not in current_urls:
            md.unlink()
            removed += 1
            continue

        by_url.setdefault(source_url, []).append(md)

    for paths in by_url.values():
        if len(paths) <= 1:
            continue
        paths.sort(key=lambda item: (len(item.name), item.name))
        for duplicate in paths[1:]:
            duplicate.unlink()
            removed += 1

print(f"One-time stale article cleanup removed {removed} files")
print("Patched rss_builder.py and sources.json")
