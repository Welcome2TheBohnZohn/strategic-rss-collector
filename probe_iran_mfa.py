import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TARGETS = [
    ("statements-show", "https://en.mfa.gov.ir/portal/NewsAgencyShow/699"),
    ("events-show", "https://en.mfa.gov.ir/portal/NewsAgencyShow/3180"),
    ("statements-archive", "https://en.mfa.ir/portal/newsarchive/699"),
    ("events-archive", "https://en.mfa.ir/portal/newsarchive/3180"),
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


def report_html(label, url, html):
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    matches = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        match = re.search(r"/portal/newsview/(\d+)", href, re.I)
        if not match:
            continue
        news_id = match.group(1)
        if news_id in seen:
            continue
        seen.add(news_id)
        matches.append((news_id, href, anchor))

    print(label, "UNIQUE NEWS LINKS", len(matches))
    print(label, "HTML NEWSVIEW OCCURRENCES", len(re.findall(r"newsview", html, re.I)))

    for news_id, href, anchor in matches[:3]:
        print("\n", label, "ID", news_id)
        print("HREF", href)
        print("TITLE", " ".join(anchor.stripped_strings)[:300])
        node = anchor
        for level in range(1, 6):
            node = node.parent
            if node is None:
                break
            text = " ".join(node.stripped_strings)
            print(
                "LEVEL", level,
                "TAG", node.name,
                "CLASS", node.get("class"),
                "TEXT", text[:1200],
            )

    return len(matches)


for label, url in TARGETS:
    print("\nSTATIC", label, url)
    try:
        response = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        print("STATUS", response.status_code, response.url, "LEN", len(response.text))
        report_html(label + " STATIC", response.url, response.text)
    except Exception as exc:
        print("STATIC ERROR", type(exc).__name__, exc)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(
        user_agent=HEADERS["User-Agent"],
        locale="en-US",
        viewport={"width": 1440, "height": 1100},
    )

    for label, url in TARGETS[:2]:
        print("\nBROWSER", label, url)
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        print("STATUS", response.status if response else None, page.url)
        report_html(label + " BROWSER", page.url, page.content())
        print("BODY", page.locator("body").inner_text()[:5000])
        page.close()

    context.close()
    browser.close()
