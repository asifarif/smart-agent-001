from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def save_programs(university: str, programs: list):
    data = [{"university": university, "program": p} for p in programs]
    response = supabase.table("programs").insert(data).execute()
    return response
