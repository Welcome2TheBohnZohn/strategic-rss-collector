from pathlib import Path

path = Path("rss_builder.py")
text = path.read_text(encoding="utf-8")

helper = r'''

def iran_mfa_detail_text(page_html):

    soup = BeautifulSoup(
        page_html,
        "lxml",
    )

    container = soup.select_one(
        ".news-text-full"
    )

    if container is None:
        return ""

    paragraphs = []

    for node in container.find_all(
        "p"
    ):

        value = normalize_text(
            node.get_text(
                " ",
                strip=True,
            )
        )

        if (
            value
            and value not in paragraphs
        ):
            paragraphs.append(
                value
            )

    if paragraphs:
        return normalize_text(
            "\n\n".join(
                paragraphs
            )
        )

    return ""
'''

anchor = "\n\ndef iran_mfa_archive_records(\n"
if "def iran_mfa_detail_text(page_html):" not in text:
    if anchor not in text:
        raise SystemExit("Iran MFA detail helper anchor not found")
    text = text.replace(
        anchor,
        helper + anchor,
        1,
    )

old = r'''        if detail.get(
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
'''

new = r'''        if detail.get(
            "ok"
        ):

            candidate_text = iran_mfa_detail_text(
                detail["text"]
            )

            word_count = len(
                candidate_text.split()
            )

            if (
                word_count >= 12
                and len(candidate_text) >= 80
            ):
                text_value = candidate_text
                diagnostics[
                    "detail_full_text"
                ] += 1
'''

if old not in text:
    raise SystemExit("Iran MFA old detail extraction block not found")

text = text.replace(
    old,
    new,
    1,
)

path.write_text(
    text,
    encoding="utf-8",
)

print("Added Iran MFA full-text detail extraction")
