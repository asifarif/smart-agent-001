# tools/web_scraper.py - Enhanced with stealth mode
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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]

    async def setup(self):
        """Initialize browser with stealth mode"""
        playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Faster loading
                '--disable-javascript',  # Disable JS to avoid detection scripts
            ]
        )
        
        # Create context with realistic settings
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
            }
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type((Exception,))
    )
    async def get_page_data(self, url: str) -> dict:
        """Scrape page with stealth mode and Cloudflare bypass"""
        if not self.context:
            await self.setup()
        
        page = await self.context.new_page()
        
        try:
            # Apply stealth mode
            await stealth_async(page)
            
            print(f"⏳ Loading page: {url}")
            
            # Navigate with extended timeout
            await page.goto(
                url, 
                wait_until="domcontentloaded",
                timeout=180000  # 3 minutes
            )
            
            # Wait for initial load
            await page.wait_for_timeout(3000)
            
            # Check for Cloudflare challenge
            content = await page.content()
            if self._is_cloudflare_challenge(content):
                print(f"🔄 Cloudflare challenge detected, waiting...")
                await self._handle_cloudflare_challenge(page)
                content = await page.content()
            
            # Check if we got blocked
            if self._is_blocked(content):
                print(f"❌ Page blocked or showing error for {url}")
                return None
            
            # Extract text content
            text_content = await page.evaluate('''() => {
                // Remove scripts and styles
                const scripts = document.querySelectorAll('script, style, noscript');
                scripts.forEach(el => el.remove());
                
                // Get clean text
                return document.body ? document.body.innerText : document.documentElement.innerText;
            }''')
            
            # Get page title
            title = await page.title()
            
            print(f"✅ Successfully scraped: {url} (text length: {len(text_content)})")
            
            return {
                "url": url,
                "title": title,
                "text": text_content.strip(),
                "html": content,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"❌ Failed to load page {url}: {str(e)}")
            return None
        finally:
            await page.close()

    def _is_cloudflare_challenge(self, html: str) -> bool:
        """Check if page shows Cloudflare challenge"""
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
        """Check if page is blocked or showing error"""
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
        """Handle Cloudflare challenge page"""
        try:
            # Wait for challenge to complete
            print("⏳ Waiting for Cloudflare challenge to complete...")
            
            # Wait up to 30 seconds for challenge to resolve
            for i in range(30):
                await page.wait_for_timeout(1000)
                content = await page.content()
                
                if not self._is_cloudflare_challenge(content):
                    print("✅ Cloudflare challenge completed")
                    return
                
                # Try clicking verification if present
                try:
                    verify_button = await page.query_selector('input[type="button"][value*="Verify"]')
                    if verify_button:
                        await verify_button.click()
                        await page.wait_for_timeout(2000)
                except:
                    pass
            
            print("⚠️ Cloudflare challenge timeout")
            
        except Exception as e:
            print(f"⚠️ Error handling Cloudflare challenge: {e}")

    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()