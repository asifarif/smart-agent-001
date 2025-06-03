# database/supabase_client.py - Fixed version
from supabase import create_client, Client
from datetime import datetime
from postgrest.exceptions import APIError
import os

class SupabaseClient:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be provided")
            
        self.client: Client = create_client(self.url, self.key)

    def get_visited_urls(self, university: str) -> set:
        try:
            response = self.client.table("visited_urls").select("url").eq("university", university).execute()
            return {row["url"] for row in response.data} if response.data else set()
        except APIError as e:
            print(f"⚠️ Supabase error getting visited URLs: {e}")
            return set()

    def save_visited_url(self, university: str, url: str):
        try:
            data = {
                "university": university, 
                "url": url, 
                "visited_at": datetime.utcnow().isoformat()
            }
            self.client.table("visited_urls").insert(data).execute()
            print(f"✅ Saved visited URL: {url}")
        except APIError as e:
            print(f"⚠️ Supabase error saving visited URL: {e}")

    def get_corrected_programs(self, university: str) -> dict:
        try:
            response = self.client.table("corrected_programs").select(
                "program_name, category, deadlines, admission_open"
            ).eq("university", university).execute()
            
            return {row["program_name"]: {
                "category": row["category"],
                "deadlines": row["deadlines"],
                "admission_open": row["admission_open"]
            } for row in response.data} if response.data else {}
        except APIError as e:
            print(f"⚠️ Supabase error getting corrected programs: {e}")
            return {}

    def upsert_extracted_program(self, program: dict):
        try:
            # Ensure required fields are present
            required_fields = ["university", "program_name", "category", "admission_open", "source_text", "source_url"]
            for field in required_fields:
                if field not in program:
                    print(f"⚠️ Missing required field '{field}' in program data")
                    return
            
            data = {
                "university": program["university"],
                "program_name": program["program_name"],
                "category": program["category"],
                "deadlines": program.get("deadlines", []),
                "admission_open": program["admission_open"],
                "source_text": program["source_text"],
                "source_url": program["source_url"],
                "extraction_date": datetime.utcnow().isoformat(),
                "application_deadline": program.get("application_deadline"),
                "link": program.get("link", program["source_url"])
            }
            
            response = self.client.table("extracted_programs").upsert(
                data, 
                on_conflict=["university", "program_name"]
            ).execute()
            
            print(f"✅ Upserted program '{program['program_name']}' for {program['university']}")
            return response.data
            
        except APIError as e:
            print(f"⚠️ Supabase error upserting program: {e}")
        except KeyError as e:
            print(f"⚠️ Missing key in program data: {e}")
            print(f"Program data: {program}")
