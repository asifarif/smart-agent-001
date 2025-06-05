# tools/web_scraper.py - Enhanced noise removal and stealth
import asyncio
import random
import json
from playwright.async_api import async_playwright, Browser, Page
from playwright_stealth import stealth_async
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from bs4 import BeautifulSoup
import time

class WebScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]

    async def setup(self):
        """Initialize browser with improved stealth mode"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.user_agents),
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
            },
            java_script_enabled=True,  # Enable JavaScript for Cloudflare and dynamic content
            bypass_csp=True,
            locale='en-US',
            timezone_id='Asia/Karachi',
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type((Exception,))
    )
    async def get_page_data(self, url: str) -> dict:
        """Scrape page with improved stealth and advanced HTML cleaning"""
        if not self.context:
            await self.setup()
        
        page = await self.context.new_page()
        
        try:
            await stealth_async(page)
            
            print(f"⏳ Loading page: {url}")
            start_time = time.time()
            
            await page.goto(
                url, 
                wait_until="networkidle",  # Wait for all content to load
                timeout=180000
            )
            
            await page.wait_for_timeout(5000)  # Extra wait for dynamic content
            
            content = await page.content()
            if self._is_cloudflare_challenge(content):
                print(f"🔄 Cloudflare challenge detected, waiting...")
                await self._handle_cloudflare_challenge(page)
                content = await page.content()
            
            if self._is_blocked(content):
                print(f"❌ Page blocked or showing error for {url}")
                return None
            
            # Clean the HTML with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            # Remove Elementor-specific and other noisy elements
            for elem in soup(["script", "style", "noscript", "iframe", "link", "meta", "header", "footer", 
                              "nav", "aside", "form", "button", "input", 
                              "div.elementor-widget-container", "div.elementor-column-gap-default"]):
                elem.decompose()
            # Remove empty or irrelevant elements
            for elem in soup.find_all():
                text = elem.get_text(strip=True)
                if not text or len(text) < 10 or "elementor" in elem.get("class", []):
                    elem.decompose()
            cleaned_html = str(soup)
            
            # Extract text content
            text_content = soup.get_text(separator=" | ", strip=True)
            
            title = await page.title()
            load_time = time.time() - start_time
            
            print(f"✅ Successfully scraped: {url} (text length: {len(text_content)}, load time: {load_time:.2f}s)")
            
            return {
                "url": url,
                "title": title,
                "text": text_content,
                "html": cleaned_html,
                "timestamp": time.time(),
                "load_time": load_time
            }
            
        except Exception as e:
            print(f"❌ Failed to load page {url}: {str(e)}")
            return None
        finally:
            await page.close()

    def _is_cloudflare_challenge(self, html: str) -> bool:
        indicators = [
            "Verify you are human",
            "cf-challenge",
            "cf-browser-verification",
            "Just a moment",
            "cloudflare",
            "Ray ID:",
            "Enable JavaScript and cookies to continue"
        ]
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in indicators)

    def _is_blocked(self, html: str) -> bool:
        error_indicators = [
            "403 Forbidden",
            "Access Denied",
            "Blocked",
            "Not Found",
            "Page Not Found",
            "Server Error"
        ]
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in error_indicators)

    async def _handle_cloudflare_challenge(self, page: Page):
        try:
            print("⏳ Waiting for Cloudflare challenge to complete...")
            
            for i in range(60):  # Extend timeout to 60 seconds
                await page.wait_for_timeout(1000)
                content = await page.content()
                
                if not self._is_cloudflare_challenge(content):
                    print("✅ Cloudflare challenge completed")
                    return
                
                try:
                    verify_button = await page.query_selector('input[type="checkbox"], input[type="button"][value*="Verify"]')
                    if verify_button:
                        await verify_button.click()
                        await page.wait_for_timeout(3000)
                except:
                    pass
            
            print("⚠️ Cloudflare challenge timeout")
            
        except Exception as e:
            print(f"⚠️ Error handling Cloudflare challenge: {e}")

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()