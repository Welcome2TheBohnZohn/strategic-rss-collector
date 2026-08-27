from pathlib import Path
import json

builder_path = Path("rss_builder.py")
text = builder_path.read_text(encoding="utf-8")

block = r'''

# ============================================================
# IRAN MINISTRY OF FOREIGN AFFAIRS
# ============================================================


def iran_mfa_clean_title(value):

    title = normalize_text(value)

    title = re.sub(
        r"^Ministry of Foreign Affairs of the Islamic Republic of Iran\s*[-–—:]\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )

    return title.strip() or "Iran MFA update"


def iran_mfa_archive_records(
    archive_html,
    archive_url,
):

    soup = BeautifulSoup(
        archive_html,
        "lxml",
    )

    records = []
    seen_ids = set()

    category = (
        "Statements"
        if archive_url.rstrip("/").endswith("/699")
        else "Events"
    )

    for item in soup.select(
        ".news-arch-item"
    ):

        news_id = ""
        matching_links = []

        for anchor in item.find_all(
            "a",
            href=True,
        ):

            href = anchor.get(
                "href",
                "",
            )

            match = re.search(
                r"/portal/newsview/(\d+)",
                href,
                re.IGNORECASE,
            )

            if not match:
                continue

            candidate_id = match.group(
                1
            )

            if not news_id:
                news_id = candidate_id

            if candidate_id == news_id:
                matching_links.append(
                    anchor
                )

        if (
            not news_id
            or news_id in seen_ids
        ):
            continue

        seen_ids.add(
            news_id
        )

        text_values = []

        for anchor in matching_links:

            value = normalize_text(
                anchor.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                value
                and value not in text_values
            ):
                text_values.append(
                    value
                )

        container_lines = [
            normalize_text(line)
            for line in item.get_text(
                "\n",
                strip=True,
            ).splitlines()
            if normalize_text(line)
        ]

        date_match = re.search(
            r"(20\d{2})/(\d{1,2})/(\d{1,2})",
            " ".join(
                container_lines
            ),
        )

        published = None

        if date_match:
            try:
                published = datetime(
                    int(date_match.group(1)),
                    int(date_match.group(2)),
                    int(date_match.group(3)),
                    tzinfo=timezone.utc,
                )
            except Exception:
                published = None

        title = (
            iran_mfa_clean_title(
                text_values[0]
            )
            if text_values
            else ""
        )

        if not title:

            for line in container_lines:

                if re.fullmatch(
                    r"20\d{2}/\d{1,2}/\d{1,2}",
                    line,
                ):
                    continue

                title = iran_mfa_clean_title(
                    line
                )
                break

        summary = ""

        for value in text_values[1:]:

            candidate = normalize_text(
                value
            )

            if (
                candidate
                and candidate != title
            ):
                summary = candidate
                break

        if not summary:

            for line in container_lines:

                if line == title:
                    continue

                if re.fullmatch(
                    r"20\d{2}/\d{1,2}/\d{1,2}",
                    line,
                ):
                    continue

                if line in (
                    ".",
                    "...",
                ):
                    continue

                if len(line) >= 20:
                    summary = line
                    break

        records.append(
            {
                "news_id": news_id,
                "title": title,
                "summary": summary,
                "published": published,
                "category": category,
                "url": (
                    "https://en.mfa.gov.ir/portal/newsview/"
                    + news_id
                ),
            }
        )

    return records


def run_iran_mfa(source):

    print(
        "\n==> "
        + source["slug"]
        + " [IRAN MFA]: "
        + source["start_url"],
        flush=True,
    )

    status = base_status(
        source
    )
    status["source_type"] = "iran_mfa"

    archive_urls = source.get(
        "iran_mfa_archive_urls",
        [source["start_url"]],
    )

    records_by_id = {}
    diagnostics = {
        "archives": [],
        "detail_full_text": 0,
        "archive_fallback": 0,
    }

    first_success_url = ""

    for archive_url in archive_urls:

        result = fetch_for_source(
            source,
            archive_url,
        )

        archive_info = {
            "url": archive_url,
            "http_status": result.get(
                "status"
            ),
            "error": result.get(
                "error",
                "",
            ),
            "records": 0,
        }

        diagnostics[
            "archives"
        ].append(
            archive_info
        )

        if not result.get(
            "ok"
        ):
            continue

        if not first_success_url:
            first_success_url = result.get(
                "url",
                archive_url,
            )
            status["http_status"] = result.get(
                "status"
            )

        soup = BeautifulSoup(
            result["text"],
            "lxml",
        )

        status["all_links"] += len(
            soup.find_all(
                "a",
                href=True,
            )
        )

        records = iran_mfa_archive_records(
            result["text"],
            result.get(
                "url",
                archive_url,
            ),
        )

        archive_info[
            "records"
        ] = len(
            records
        )

        for record in records:

            news_id = record[
                "news_id"
            ]

            if news_id not in records_by_id:
                records_by_id[
                    news_id
                ] = record

    status["resolved_url"] = (
        first_success_url
        or source["start_url"]
    )

    records = list(
        records_by_id.values()
    )

    records.sort(
        key=lambda record: (
            normalize_datetime(
                record.get(
                    "published"
                )
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            ),
            int(
                record.get(
                    "news_id",
                    "0",
                )
                or 0
            ),
        ),
        reverse=True,
    )

    status["candidate_links"] = len(
        records
    )

    articles = []

    for record in records:

        if len(
            articles
        ) >= MAX_ITEMS_PER_SOURCE:
            break

        status["attempted"] += 1

        title = iran_mfa_clean_title(
            record.get(
                "title",
                "",
            )
        )

        summary = normalize_text(
            record.get(
                "summary",
                "",
            )
        )

        text_value = ""

        detail = fetch_for_source(
            source,
            record["url"],
            override_retries=0,
        )

        if detail.get(
            "ok"
        ):

            extracted = extract_article(
                detail["text"],
                title,
                detail.get(
                    "url",
                    record["url"],
                ),
            )

            candidate_text = normalize_text(
                extracted.get(
                    "text",
                    "",
                )
            )

            word_count = len(
                candidate_text.split()
            )

            if (
                word_count >= 40
                and len(candidate_text)
                >= max(
                    300,
                    len(title) + 120,
                )
            ):
                text_value = candidate_text
                diagnostics[
                    "detail_full_text"
                ] += 1

        if not text_value:

            diagnostics[
                "archive_fallback"
            ] += 1

            if (
                summary
                and summary not in (
                    ".",
                    "...",
                )
            ):
                text_value = summary
            else:
                text_value = title

        articles.append(
            {
                "title": title,
                "url": record[
                    "url"
                ],
                "guid": (
                    "iran-mfa:"
                    + record[
                        "news_id"
                    ]
                ),
                "text": text_value[
                    :50000
                ],
                "published": record.get(
                    "published"
                ),
            }
        )

    populate_counts(
        status,
        articles,
    )

    if not articles:
        status["error"] = (
            "Iran MFA archive endpoints loaded but no usable news records were extracted."
            if status.get("http_status")
            else "Iran MFA archive endpoints could not be retrieved."
        )

    diagnostics[
        "unique_records"
    ] = len(
        records
    )
    diagnostics[
        "feed_items"
    ] = len(
        articles
    )

    save_raw(
        source,
        json.dumps(
            diagnostics,
            ensure_ascii=False,
            indent=2,
        ),
        "archive-diagnostic.json",
    )

    write_feed(
        source,
        articles,
    )

    return status
'''

anchor = "\n\n# ============================================================\n# TELEGRAM PUBLIC CHANNEL PREVIEWS\n# ============================================================\n"
if "def run_iran_mfa(source):" not in text:
    if anchor not in text:
        raise SystemExit("Iran MFA insertion anchor not found")
    text = text.replace(anchor, block + anchor, 1)

old_dispatch = '''    if source_type == "telegram":\n\n        return run_telegram(\n            source\n        )\n'''
new_dispatch = '''    if source_type == "iran_mfa":\n\n        return run_iran_mfa(\n            source\n        )\n\n    if source_type == "telegram":\n\n        return run_telegram(\n            source\n        )\n'''
if 'source_type == "iran_mfa"' not in text:
    if old_dispatch not in text:
        raise SystemExit("run_source dispatch anchor not found")
    text = text.replace(old_dispatch, new_dispatch, 1)

builder_path.write_text(text, encoding="utf-8")

sources_path = Path("sources.json")
sources = json.loads(sources_path.read_text(encoding="utf-8"))

found = False
for source in sources:
    if source.get("slug") != "iran-mfa-en":
        continue
    found = True
    source.clear()
    source.update(
        {
            "slug": "iran-mfa-en",
            "title": "Iran Ministry of Foreign Affairs English",
            "source_url": "https://en.mfa.gov.ir/",
            "start_url": "https://en.mfa.gov.ir/portal/NewsAgencyShow/699",
            "language": "en",
            "source_type": "iran_mfa",
            "iran_mfa_archive_urls": [
                "https://en.mfa.gov.ir/portal/NewsAgencyShow/699",
                "https://en.mfa.gov.ir/portal/NewsAgencyShow/3180",
            ],
            "request_timeout": 20,
            "max_retries": 2,
            "retry_backoff": 2,
        }
    )
    break

if not found:
    raise SystemExit("iran-mfa-en source not found")

sources_path.write_text(
    json.dumps(
        sources,
        ensure_ascii=False,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)

print("Patched Iran MFA collector and source config")
