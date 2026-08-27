import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}
ARCHIVES = [
    "https://en.mfa.ir/portal/newsarchive/699",
    "https://en.mfa.ir/portal/newsarchive/3180",
]

for archive_url in ARCHIVES:
    print("\nARCHIVE", archive_url)
    response = requests.get(archive_url, headers=HEADERS, timeout=20)
    print("STATUS", response.status_code, response.url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        match = re.search(r"/portal/newsview/(\d+)", href, re.I)
        if not match:
            continue
        news_id = match.group(1)
        if news_id in seen:
            continue
        seen.add(news_id)
        print("\nID", news_id)
        print("HREF", href)
        print("TITLE", " ".join(anchor.stripped_strings)[:300])
        node = anchor
        for level in range(1, 6):
            node = node.parent
            if node is None:
                break
            text = " ".join(node.stripped_strings)
            print("LEVEL", level, "TAG", node.name, "CLASS", node.get("class"), "TEXT", text[:1200])
        if len(seen) >= 4:
            break
