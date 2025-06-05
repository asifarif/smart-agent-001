# agents/ziauddin_agent.py - Fixed version combining best of both
import os
import json
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, List, Set
from tools.university_scraper_agent import UniversityScraperAgent
from tools.web_scraper import WebScraper
from database.supabase_client import SupabaseClient
import logging
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZiauddinAgent(UniversityScraperAgent):
    name = "ziauddin_agent"

    def __init__(
        self,
        supabase_client: SupabaseClient,
        max_internal_links: int = 3,
        min_text_length: int = 200,
        delay_min: float = 10.0,
        delay_max: float = 15.0
    ):
        """Initialize agent with configurable parameters."""
        self.supabase_client = supabase_client
        self.known_programs = self.supabase_client.get_corrected_programs("Ziauddin University")
        self.visited = set(self.supabase_client.get_visited_urls("Ziauddin University"))
        self.scraper = WebScraper()
        self.start_urls = [
            "https://zu.edu.pk/undergraduate-programmes/",
            "https://admission.zu.edu.pk/programs-list-table",
            "https://zu.edu.pk/",
        ]
        self.scraped_pages = []
        self.extracted_programs = []
        self.max_internal_links = max_internal_links
        self.min_text_length = min_text_length
        self.delay_min = delay_min
        self.delay_max = delay_max

    async def setup(self):
        """Initialize the scraper with setup logging."""
        try:
            await self.scraper.setup()
            logger.info("🚀 ZiauddinAgent setup complete")
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise

    async def close(self):
        """Close the scraper with cleanup logging."""
        try:
            await self.scraper.close()
            logger.info("🔒 ZiauddinAgent closed")
        except Exception as e:
            logger.error(f"❌ Close failed: {e}")
            raise

    def _extract_program_links(self, html: str, base_url: str) -> Set[str]:
        """Extract internal links with keyword filtering - simplified version."""
        soup = BeautifulSoup(html, "html.parser")
        internal_links = set()
        base_domain = "https://zu.edu.pk"
        
        # Use the working keyword list from old code
        program_keywords = [
            "program", "course", "degree", "bachelor", "master", "phd", "diploma",
            "undergraduate", "graduate", "postgraduate", "admission", "faculty",
            "department", "school", "college", "bs", "ms", "mba", "bba", "programmes"
        ]
        
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text().strip().lower()
            
            # Check if URL or text contains program keywords
            if any(keyword in href.lower() or keyword in text for keyword in program_keywords):
                if href.startswith("http"):
                    if "zu.edu.pk" in href:
                        internal_links.add(href)
                elif href.startswith("/"):
                    internal_links.add(base_domain + href)
                elif not href.startswith("#") and not href.startswith("mailto:"):
                    internal_links.add(base_domain + "/" + href)
        
        logger.info(f"🔗 Found {len(internal_links)} program-related links from {base_url}")
        return internal_links

    async def extract_programs(self, force_scrape: bool = False) -> List[Dict]:
        """Extract programs from all start URLs - simplified approach."""
        try:
            await self.setup()
            logger.info(f"🚀 Starting extraction for {len(self.start_urls)} URLs")

            if not force_scrape:
                self.visited = set(self.supabase_client.get_visited_urls("Ziauddin University"))
                logger.info(f"📂 Loaded {len(self.visited)} previously visited URLs")

            for i, url in enumerate(self.start_urls):
                logger.info(f"📍 Processing URL {i+1}/{len(self.start_urls)}: {url}")
                
                if url in self.visited and not force_scrape:
                    logger.info(f"ℹ️ Skipping already visited URL: {url}")
                    continue
                    
                try:
                    logger.info(f"🔍 Scraping: {url}")
                    page_data = await self.scraper.get_page_data(url)
                    
                    if page_data and page_data.get("text", "").strip():
                        text_length = len(page_data['text'])
                        logger.info(f"✅ Successfully scraped: {url} (text length: {text_length})")
                        
                        if text_length > self.min_text_length:
                            self.scraped_pages.append(page_data)
                            
                            if url not in self.visited:
                                self.supabase_client.save_visited_url("Ziauddin University", page_data["url"])
                                self.visited.add(page_data["url"])

                            # Extract and process internal links
                            if page_data.get("html"):
                                internal_links = self._extract_program_links(page_data["html"], url)
                                
                                for j, link in enumerate(list(internal_links)[:self.max_internal_links]):
                                    if link not in self.visited or force_scrape:
                                        try:
                                            logger.info(f"🔍 Scraping internal link {j+1}/{min(len(internal_links), self.max_internal_links)}: {link}")
                                            sub_page = await self.scraper.get_page_data(link)
                                            
                                            if sub_page and len(sub_page.get("text", "")) > self.min_text_length:
                                                logger.info(f"✅ Successfully scraped internal link: {link}")
                                                self.scraped_pages.append(sub_page)
                                                if link not in self.visited:
                                                    self.supabase_client.save_visited_url("Ziauddin University", link)
                                                    self.visited.add(link)
                                            
                                            # Dynamic delay based on load time
                                            load_time = sub_page.get("load_time", self.delay_min) if sub_page else self.delay_min
                                            delay = max(self.delay_min, min(self.delay_max, load_time * 2))
                                            logger.info(f"⏳ Delaying for {delay:.2f}s")
                                            await asyncio.sleep(delay)
                                            
                                        except Exception as e:
                                            logger.error(f"⚠️ Error fetching internal link {link}: {e}")
                                            continue
                        else:
                            logger.warning(f"⚠️ Content too short from: {url} (length: {text_length})")
                    else:
                        logger.warning(f"⚠️ No data retrieved from: {url}")
                        
                except Exception as e:
                    logger.error(f"⚠️ Error scraping {url}: {e}")
                    continue
                    
                # Delay between main URLs
                if i < len(self.start_urls) - 1:
                    load_time = page_data.get("load_time", self.delay_min) if page_data else self.delay_min
                    delay = max(self.delay_max, load_time * 1.5)
                    logger.info(f"⏳ Delaying for {delay:.2f}s before next start URL")
                    await asyncio.sleep(delay)

            # Save data to separate files
            os.makedirs(f"memory/{self.name}", exist_ok=True)
            pages_file = f"memory/{self.name}/scraped_pages.json"
            with open(pages_file, "w", encoding="utf-8") as f:
                json.dump(self.scraped_pages, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved {len(self.scraped_pages)} pages to {pages_file}")

            visited_file = f"memory/{self.name}/visited_urls.json"
            with open(visited_file, "w", encoding="utf-8") as f:
                json.dump(list(self.visited), f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved {len(self.visited)} visited URLs to {visited_file}")

            logger.info(f"✅ Total scraped pages: {len(self.scraped_pages)}")
            return self.scraped_pages

        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            raise
        finally:
            await self.close()

    def compare_outputs(self, structured_data: List[Dict]):
        """Compare and save extracted programs to Supabase with error handling."""
        if not structured_data:
            logger.warning("⚠️ No structured data to save")
            return

        logger.info(f"💾 Saving {len(structured_data)} programs to Supabase...")
        success_count = 0
        for program in structured_data:
            try:
                self.supabase_client.upsert_extracted_program(program)
                success_count += 1
            except Exception as e:
                logger.error(f"⚠️ Error saving program {program.get('program_name', 'Unknown')}: {e}")
                continue

        logger.info(f"✅ Successfully saved {success_count}/{len(structured_data)} programs to Supabase")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_client = SupabaseClient(supabase_url, supabase_key)
    agent = ZiauddinAgent(supabase_client)
    asyncio.run(agent.extract_programs(force_scrape=True))