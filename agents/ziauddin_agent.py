# agents/ziauddin_agent.py
from tools.web_scraper import WebScraper
from bs4 import BeautifulSoup
from pprint import pprint
import time
import re


class ZiauddinAgent:
    def __init__(self):
        self.scraper = WebScraper()
        self.visited = set()

    def clean_programs(self, programs):
        cleaned = set()
        for prog in programs:
            prog = re.sub(r"\s+", " ", prog).strip()
            prog = re.sub(r"[^\w\s\-\&\(\)]", "", prog)  # remove most punctuation
            if 5 < len(prog) < 100:
                cleaned.add(prog)
        return sorted(cleaned)

    def extract_programs(self):
        base_url = "https://zu.edu.pk"
        html = self.scraper.get_page_text(base_url)
        soup = BeautifulSoup(html, "html.parser")

        internal_links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/") or base_url in href:
                full_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
                if full_url not in self.visited:
                    self.visited.add(full_url)
                    if any(keyword in full_url.lower() for keyword in ["program", "faculty", "department", "admission"]):
                        internal_links.add(full_url)

        print(f"🔗 Found {len(internal_links)} candidate pages to explore...\n")

        programs = []

        for url in internal_links:
            print(f"🌐 Visiting: {url}")
            try:
                sub_html = self.scraper.get_page_text(url)
                sub_soup = BeautifulSoup(sub_html, "html.parser")
                time.sleep(1)

                for tag in sub_soup.find_all(["h2", "h3", "a", "li", "p", "div"]):
                    text = tag.get_text(strip=True)
                    if any(kw in text.lower() for kw in ["bs", "ms", "mbbs", "bds", "pharm", "degree", "program"]):
                        if 5 < len(text) < 100 and text not in programs:
                            programs.append(text)

            except Exception as e:
                print(f"⚠️ Failed to fetch {url}: {e}")
                continue

        self.scraper.close()

        cleaned_programs = self.clean_programs(programs)
        print("\n📘 Cleaned Programs Extracted:\n")
        pprint(cleaned_programs)

        return cleaned_programs
