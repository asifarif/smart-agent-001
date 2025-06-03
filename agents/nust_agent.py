# agents/nust_agent.py
import os
import json
import asyncio
from bs4 import BeautifulSoup
from tools.university_scraper_agent import UniversityScraperAgent
from tools.web_scraper import WebScraper
from database.supabase_client import SupabaseClient

class NustAgent(UniversityScraperAgent):
    name = "nust_agent"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.known_programs = self.supabase_client.get_corrected_programs("NUST")
        self.visited = set(self.supabase_client.get_visited_urls("NUST"))
        self.scraper = WebScraper()
        self.start_urls = [
            "https://ugadmissions.nust.edu.pk/",
            "https://nust.edu.pk/academics/undergraduate",
            "https://nust.edu.pk/admissions/undergraduates/list-of-ug-programmes-and-institutions/",
        ]
        self.scraped_pages = []

    async def extract_programs(self):
        await self.scraper.setup()

        for url in self.start_urls:
            if url in self.visited:
                continue
            page_data = await self.scraper.get_page_data(url)
            if page_data and page_data["url"] not in self.visited:
                self.scraped_pages.append(page_data)
                self.supabase_client.save_visited_url("NUST", page_data["url"])
                self.visited.add(page_data["url"])

                soup = BeautifulSoup(page_data["html"], "html.parser")
                internal_links = {
                    a["href"] if a["href"].startswith("http") else "https://nust.edu.pk" + a["href"]
                    for a in soup.find_all("a", href=True)
                    if any(k in a["href"].lower() for k in ["program", "faculty", "admission"])
                }

                for link in internal_links:
                    if link not in self.visited:
                        try:
                            sub_page = await self.scraper.get_page_data(link)
                            if sub_page:
                                self.scraped_pages.append(sub_page)
                                self.supabase_client.save_visited_url("NUST", link)
                                self.visited.add(link)
                                await asyncio.sleep(1)
                        except Exception as e:
                            print(f"⚠️ Error fetching {link}: {e}")

        await self.scraper.close()

        os.makedirs("memory/nust_agent", exist_ok=True)
        with open("memory/nust_agent/scraped_pages.json", "w", encoding="utf-8") as f:
            json.dump(self.scraped_pages, f, indent=2, ensure_ascii=False)

        print(f"✅ Scraped {len(self.scraped_pages)} pages for NUST.")
        return self.scraped_pages