# agents/iqra_agent.py
import os
import json
import asyncio
from bs4 import BeautifulSoup
from tools.university_scraper_agent import UniversityScraperAgent
from tools.web_scraper import WebScraper
from database.supabase_client import SupabaseClient

class IqraAgent(UniversityScraperAgent):
    name = "iqra_agent"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.known_programs = self.supabase_client.get_corrected_programs("Iqra University")
        self.visited = set(self.supabase_client.get_visited_urls("Iqra University"))
        self.scraper = WebScraper()
        self.start_urls = [
            "https://iqra.edu.pk/",
            "https://iqra.edu.pk/admissions/",
            "https://iqra.edu.pk/degree/under-graduate-program/"
        ]
        self.scraped_pages = []

    def load_corrected_data(self):
        """Load corrected output from previous runs."""
        try:
            with open("memory/iqra_agent/corrected.json", "r", encoding="utf-8") as f:
                corrected = json.load(f)
                return corrected
        except FileNotFoundError:
            return []

    def compare_outputs(self, agent_output, corrected_output):
        """Compare agent output with corrected output, update known_programs, and return differences."""
        differences = []
        for agent_item in agent_output:
            corrected_item = next((c for c in corrected_output if c["program_name"] == agent_item["program_name"]), None)
            if corrected_item and (
                agent_item["category"] != corrected_item["category"] or
                agent_item.get("deadlines", []) != corrected_item.get("deadlines", []) or
                agent_item.get("admission_open", False) != corrected_item.get("admission_open", False)
            ):
                differences.append({
                    "program_name": agent_item["program_name"],
                    "agent": agent_item,
                    "corrected": corrected_item
                })
                self.known_programs[agent_item["program_name"]] = {
                    "category": corrected_item["category"],
                    "deadlines": corrected_item.get("deadlines", []),
                    "admission_open": corrected_item.get("admission_open", False)
                }
        return differences

    async def extract_programs(self):
        await self.scraper.setup()

        # Load previous corrected data for learning
        corrected_output = self.load_corrected_data()

        for url in self.start_urls:
            if url in self.visited:
                continue
            page_data = await self.scraper.get_page_data(url)
            if page_data and page_data["url"] not in self.visited:
                self.scraped_pages.append(page_data)
                self.supabase_client.save_visited_url("Iqra University", page_data["url"])
                self.visited.add(page_data["url"])

                soup = BeautifulSoup(page_data["html"], "html.parser")
                internal_links = {
                    a["href"] if a["href"].startswith("http") else "https://iqra.edu.pk" + a["href"]
                    for a in soup.find_all("a", href=True)
                    if any(k in a["href"].lower() for k in ["program", "faculty", "admission"])
                }

                for link in internal_links:
                    if link not in self.visited:
                        try:
                            sub_page = await self.scraper.get_page_data(link)
                            if sub_page:
                                self.scraped_pages.append(sub_page)
                                self.supabase_client.save_visited_url("Iqra University", link)
                                self.visited.add(link)
                                await asyncio.sleep(1)
                        except Exception as e:
                            print(f"⚠️ Error fetching {link}: {e}")

        await self.scraper.close()

        # Save scraped pages for processing by main.py
        os.makedirs("memory/iqra_agent", exist_ok=True)
        with open("memory/iqra_agent/scraped_pages.json", "w", encoding="utf-8") as f:
            json.dump(self.scraped_pages, f, indent=2, ensure_ascii=False)

        print(f"✅ Scraped {len(self.scraped_pages)} pages for Iqra University.")

        # Note: Extraction is handled by main.py using extract_admission_info
        # For learning, assume main.py saves agent_output.json after extraction
        try:
            with open("memory/iqra_agent/agent_output.json", "r", encoding="utf-8") as f:
                agent_output = json.load(f)
                if corrected_output:
                    differences = self.compare_outputs(agent_output, corrected_output)
                    if differences:
                        print(f"📚 Learned from {len(differences)} differences in corrected output.")
                        # Update Supabase with corrected programs
                        for diff in differences:
                            corrected = diff["corrected"]
                            self.supabase_client.upsert_extracted_program(
                                university="Iqra University",
                                program_name=corrected["program_name"],
                                category=corrected["category"],
                                deadlines=corrected.get("deadlines", []),
                                admission_open=corrected.get("admission_open", False),
                                source_text=corrected.get("source_text", ""),
                                source_url=corrected.get("source_url", "")
                            )
        except FileNotFoundError:
            print("⚠️ No agent_output.json found, skipping comparison.")

        return self.scraped_pages