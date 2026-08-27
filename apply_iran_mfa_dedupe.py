from pathlib import Path

path = Path("rss_builder.py")
text = path.read_text(encoding="utf-8")

old_diag = '''    diagnostics = {\n        "archives": [],\n        "detail_full_text": 0,\n        "archive_fallback": 0,\n    }\n'''
new_diag = '''    diagnostics = {\n        "archives": [],\n        "detail_full_text": 0,\n        "archive_fallback": 0,\n        "duplicate_content_skipped": 0,\n    }\n'''
if old_diag not in text:
    raise SystemExit("Iran MFA diagnostics anchor not found")
text = text.replace(old_diag, new_diag, 1)

old_articles = '''    articles = []\n\n    for record in records:\n'''
new_articles = '''    articles = []\n    seen_content_keys = set()\n\n    for record in records:\n'''
if old_articles not in text:
    raise SystemExit("Iran MFA articles anchor not found")
text = text.replace(old_articles, new_articles, 1)

old_append = '''        articles.append(\n            {\n                "title": title,\n                "url": record[\n                    "url"\n                ],\n'''
new_append = '''        content_key = (\n            normalize_text(title).casefold()\n            + "\\n"\n            + normalize_text(text_value).casefold()\n        )\n\n        if content_key in seen_content_keys:\n            diagnostics[\n                "duplicate_content_skipped"\n            ] += 1\n            continue\n\n        seen_content_keys.add(\n            content_key\n        )\n\n        articles.append(\n            {\n                "title": title,\n                "url": record[\n                    "url"\n                ],\n'''
if old_append not in text:
    raise SystemExit("Iran MFA append anchor not found")
text = text.replace(old_append, new_append, 1)

path.write_text(text, encoding="utf-8")
print("Added Iran MFA duplicate-content filtering")
