import requests
from bs4 import BeautifulSoup

url = "https://en.mfa.gov.ir/portal/newsview/793300"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}
response = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
print("STATUS", response.status_code, response.url, "LEN", len(response.text))
response.raise_for_status()
soup = BeautifulSoup(response.text, "lxml")

needle = "According to Baqaei"
node = soup.find(string=lambda value: value and needle in value)
print("FOUND", bool(node))
if node:
    current = node.parent
    for level in range(1, 9):
        if current is None:
            break
        text = " ".join(current.stripped_strings)
        print(
            "LEVEL", level,
            "TAG", current.name,
            "ID", current.get("id"),
            "CLASS", current.get("class"),
            "TEXT", text[:3000],
        )
        current = current.parent

print("\nLIKELY CONTAINERS")
for tag in soup.find_all(["div", "article", "section"]):
    text = " ".join(tag.stripped_strings)
    if "Qatari PM FM to visit Tehran on Thursday" in text and "According to Baqaei" in text:
        print("TAG", tag.name, "ID", tag.get("id"), "CLASS", tag.get("class"), "LEN", len(text), "TEXT", text[:2500])
