# core/agent_manager.py - Fixed version
import asyncio
import logging
from agents.ziauddin_agent import ZiauddinAgent
from database.supabase_client import SupabaseClient
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
            
        self.supabase_client = SupabaseClient(supabase_url, supabase_key)
        self.agents = [
            ZiauddinAgent(self.supabase_client),
        ]

    async def run_all(self, force_scrape: bool = False):
        for agent in self.agents:
            logger.info(f"🚀 Running {agent.name}...")
            try:
                scraped_pages = await agent.extract_programs(force_scrape=force_scrape)
                logger.info(f"✅ {agent.name} completed successfully. Scraped {len(scraped_pages)} pages.")
            except Exception as e:
                logger.error(f"⚠️ Error running {agent.name}: {e}")
