# agents/ziauddin_agent.py - Fixed URL issue
import os
import json
import asyncio
from bs4 import BeautifulSoup
from tools.university_scraper_agent import UniversityScraperAgent
from tools.web_scraper import WebScraper
from database.supabase_client import SupabaseClient

class ZiauddinAgent(UniversityScraperAgent):
    name = "ziauddin_agent"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.known_programs = self.supabase_client.get_corrected_programs("Ziauddin University")
        self.visited = set(self.supabase_client.get_visited_urls("Ziauddin University"))
        self.scraper = WebScraper()
        
        # Fixed URLs - removed the duplicate domain issue
        self.start_urls = [
            "https://zu.edu.pk/undergraduate-programmes/",
            "https://admission.zu.edu.pk/programs-list-table",
            "https://zu.edu.pk/",
        ]
        self.scraped_pages = []

    async def extract_programs(self, force_scrape: bool = False):
        await self.scraper.setup()
        print(f"🚀 Starting extraction for {len(self.start_urls)} URLs")

        # Try alternative URLs if main ones fail

        all_urls = self.start_urls

        for url in all_urls:
            if url in self.visited and not force_scrape:
                print(f"ℹ️ Skipping already visited URL: {url}")
                continue
                
            try:
                print(f"🔍 Scraping: {url}")
                page_data = await self.scraper.get_page_data(url)
                
                if page_data and page_data.get("text", "").strip():
                    text_length = len(page_data['text'])
                    print(f"✅ Successfully scraped: {url} (text length: {text_length})")
                    
                    # Only add if we got substantial content
                    if text_length > 200:  # Minimum content threshold
                        self.scraped_pages.append(page_data)
                        
                        if url not in self.visited:
                            self.supabase_client.save_visited_url("Ziauddin University", page_data["url"])
                            self.visited.add(page_data["url"])

                        # Extract internal links for additional scraping
                        if page_data.get("html"):
                            internal_links = self._extract_program_links(page_data["html"], url)
                            
                            # Limit internal links to avoid too many requests
                            for i, link in enumerate(list(internal_links)[:3]):  # Only top 3 links
                                if link not in self.visited or force_scrape:
                                    try:
                                        print(f"🔍 Scraping internal link {i+1}/3: {link}")
                                        sub_page = await self.scraper.get_page_data(link)
                                        if sub_page and len(sub_page.get("text", "")) > 200:
                                            print(f"✅ Successfully scraped internal link: {link}")
                                            self.scraped_pages.append(sub_page)
                                            if link not in self.visited:
                                                self.supabase_client.save_visited_url("Ziauddin University", link)
                                                self.visited.add(link)
                                        await asyncio.sleep(3)  # Longer delay for internal links
                                    except Exception as e:
                                        print(f"⚠️ Error fetching internal link {link}: {e}")
                    else:
                        print(f"⚠️ Content too short from: {url} (length: {text_length})")
                else:
                    print(f"⚠️ No data retrieved from: {url}")
                    
            except Exception as e:
                print(f"⚠️ Error scraping {url}: {e}")
                continue
                
            await asyncio.sleep(5)  # Longer delay between main URLs to avoid rate limiting

        await self.scraper.close()

        # Save scraped pages
        os.makedirs("memory/ziauddin_agent", exist_ok=True)
        with open("memory/ziauddin_agent/scraped_pages.json", "w", encoding="utf-8") as f:
            json.dump(self.scraped_pages, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(self.scraped_pages)} pages to memory/ziauddin_agent/scraped_pages.json")
        print(f"✅ Total scraped pages: {len(self.scraped_pages)}")
        
        return self.scraped_pages

    def _extract_program_links(self, html: str, base_url: str) -> set:
        """Extract program-related links from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        internal_links = set()
        base_domain = "https://zu.edu.pk"
        
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text().strip().lower()
            
            # Look for program-related keywords in link text or href
            program_keywords = [
                "program", "course", "degree", "bachelor", "master", "phd", "diploma",
                "undergraduate", "graduate", "postgraduate", "admission", "faculty",
                "department", "school", "college", "bs", "ms", "mba", "bba"
            ]
            
            if any(keyword in href.lower() or keyword in text for keyword in program_keywords):
                if href.startswith("http"):
                    if "zu.edu.pk" in href:  # Only ZU links
                        internal_links.add(href)
                elif href.startswith("/"):
                    internal_links.add(base_domain + href)
                elif not href.startswith("#") and not href.startswith("mailto:"):
                    internal_links.add(base_domain + "/" + href)
        
        print(f"🔗 Found {len(internal_links)} program-related links")
        return internal_links

    def compare_outputs(self, structured_data: list):
        """Save structured data to Supabase"""
        if not structured_data:
            print("⚠️ No structured data to save")
            return
            
        print(f"💾 Saving {len(structured_data)} programs to Supabase...")
        
        success_count = 0
        for program in structured_data:
            try:
                self.supabase_client.upsert_extracted_program(program)
                success_count += 1
            except Exception as e:
                print(f"⚠️ Error saving program {program.get('program_name', 'Unknown')}: {e}")
        
        print(f"✅ Successfully saved {success_count}/{len(structured_data)} programs to Supabase")
