from pathlib import Path

path = Path("rss_builder.py")
text = path.read_text(encoding="utf-8")

start = text.index("def telegram_title(text):")
end = text.index("\n\ndef run_telegram(source):", start)

replacement = r'''def telegram_title(text):

    lines = [
        normalize_text(line)
        for line in str(text).splitlines()
        if normalize_text(line)
    ]

    if not lines:
        return "Telegram post"

    decorative_prefix = ""
    substantive = []

    for line in lines:

        if re.search(
            r"[A-Za-z0-9]",
            line,
        ):
            substantive.append(line)
        elif not decorative_prefix:
            decorative_prefix = line

    if not substantive:
        return normalize_text(
            " ".join(lines)
        )[:180]

    parts = []

    for line in substantive:
        parts.append(line)

        if len(
            normalize_text(
                " ".join(parts)
            )
        ) >= 80:
            break

    title = normalize_text(
        " ".join(parts)
    )

    if decorative_prefix:
        title = normalize_text(
            decorative_prefix
            + " "
            + title
        )

    return title[:180]
'''

text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
print("Improved Telegram title generation")
