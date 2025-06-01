from tools.web_scraper import WebScraper
from dotenv import load_dotenv


def test_scrape():
    scraper = WebScraper()
    html = scraper.get_page_text("https://zu.edu.pk/")
    assert "Ziauddin University" in html
    scraper.close()

