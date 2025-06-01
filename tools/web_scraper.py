# tools/web_scraper.py
from playwright.sync_api import sync_playwright

class WebScraper:
    def __init__(self, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=["--start-maximized"]
        )
        self.page = self.browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        ))

    def get_page_text(self, url: str) -> str:
        try:
            print(f"⏳ Loading page: {url}")
            self.page.goto(url, timeout=120000, wait_until="load")
            self.page.wait_for_load_state("networkidle")
            html = self.page.content()

            with open("ziauddin_page.html", "w", encoding="utf-8") as f:
                f.write(html)

            print("✅ Page content saved to ziauddin_page.html")
            return html
        except Exception as e:
            print(f"❌ Failed to load page {url}: {e}")
            return ""

    def close(self):
        self.browser.close()
        self.playwright.stop()
