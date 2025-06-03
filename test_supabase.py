# test_supabase.py
import os
from supabase import create_client, Client
from datetime import datetime

# Load environment variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase_client = create_client(supabase_url, supabase_key)

# Test data
test_program = {
    "university": "Ziauddin University",
    "program_name": "Bachelor of Science Clinical Psychology",  # Existing record
    "category": "undergraduate",
    "admission_open": False,  # Change to test update
    "application_deadline": "2025-07-14",
    "link": "https://admission.zu.edu.pk/programs-list-table",
    "source_text": "BS CLI PSY BS CLINICAL PSYCHOLOGY Psychology,clinical,clinic,therapy,therapist,social science,counselling,counselor,health,wellbeing,Mental health,behaviour,disorder,neuro,neurology,neuropsychology,cognitive,cognition,child psychology,Clifton Under Graduate 07-Jul-2025 Apply Now",
    "source_url": "https://admission.zu.edu.pk/programs-list-table",
    "extraction_date": datetime.utcnow().isoformat()
}

# Check if record exists, then update or insert
try:
    # Check if the record exists
    response = supabase_client.table("extracted_programs").select("*").eq("university", test_program["university"]).eq("program_name", test_program["program_name"]).execute()
    if response.data:
        # Update existing record
        update_response = supabase_client.table("extracted_programs").update(test_program).eq("university", test_program["university"]).eq("program_name", test_program["program_name"]).execute()
        print(f"✅ Successfully updated program: {update_response.data}")
    else:
        # Insert new record
        insert_response = supabase_client.table("extracted_programs").insert(test_program).execute()
        print(f"✅ Successfully inserted program: {insert_response.data}")
except Exception as e:
    print(f"⚠️ Error upserting program: {e}")