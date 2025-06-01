# database/supabase_client.py
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def store_programs(programs, university_name="Ziauddin University", university_id="ziauddin", source="ziauddin"):
    data = [{
        "program_name": p,
        "category": p["category"],
        "university_name": university_name,
        "university_id": university_id,
        "source": source
    } for p in programs]
    res = supabase.table("programs").insert(data).execute()
    print("✅ Data saved to Supabase:", res)