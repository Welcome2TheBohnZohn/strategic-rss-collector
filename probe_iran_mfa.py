import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ARCHIVES = [
    "https://en.mfa.ir/portal/newsarchive/699",
    "https://en.mfa.ir/portal/newsarchive/3180",
]

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        viewport={"width": 1440, "height": 1100},
    )

    for archive_url in ARCHIVES:
        print("\nARCHIVE", archive_url)
        page = context.new_page()
        response = page.goto(
            archive_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(5000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        print("STATUS", response.status if response else None, page.url)
        soup = BeautifulSoup(page.content(), "lxml")
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

        print("UNIQUE NEWS LINKS", len(matches))

        for news_id, href, anchor in matches[:4]:
            print("\nID", news_id)
            print("HREF", href)
            print("TITLE", " ".join(anchor.stripped_strings)[:300])
            node = anchor
            for level in range(1, 7):
                node = node.parent
                if node is None:
                    break
                text = " ".join(node.stripped_strings)
                print(
                    "LEVEL", level,
                    "TAG", node.name,
                    "CLASS", node.get("class"),
                    "TEXT", text[:1600],
                )

        page.close()

    context.close()
    browser.close()
