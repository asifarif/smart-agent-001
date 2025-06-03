# main.py - Fixed version
import asyncio
import json
import os
from dotenv import load_dotenv
load_dotenv()
from core.agent_manager import AgentManager
from core.extractor import extract_admission_info
from agents.ziauddin_agent import ZiauddinAgent
from database.supabase_client import SupabaseClient

async def main():
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_client = SupabaseClient(supabase_url, supabase_key)

    # Initialize all agents
    agents = {
        "ziauddin_agent": ZiauddinAgent(supabase_client),
    }

    # Run agent scraping
    manager = AgentManager()
    await manager.run_all(force_scrape=True)

    agent_names = ["ziauddin_agent"]
    all_structured = []

    for name in agent_names:
        path = f"memory/{name}/scraped_pages.json"
        if not os.path.exists(path):
            print(f"⚠️ Missing {path}, skipping.")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                pages = json.load(f)
                print(f"ℹ️ Loaded {len(pages)} pages from {path}")
        except json.JSONDecodeError as e:
            print(f"⚠️ Invalid JSON in {path}: {e}")
            pages = []

        print(f"🔍 Extracting admission info from {len(pages)} pages for {name}...")
        structured = []
        
        for page in pages:
            try:
                page_structured = await extract_admission_info(page["text"], page["url"])
                print(f"ℹ️ Final extracted data for {page['url']}: {len(page_structured) if page_structured else 0} programs")
                
                if page_structured:
                    # Add university field to each program
                    for program in page_structured:
                        program["university"] = "Ziauddin University"
                    
                    structured.extend(page_structured)
                    print(f"ℹ️ Added {len(page_structured)} programs to structured data")
                else:
                    print(f"⚠️ No data extracted for {page['url']}")
                    
            except Exception as e:
                print(f"⚠️ Error extracting from {page['url']}: {e}")
                continue

        # Apply corrections from Supabase
        try:
            known_programs = supabase_client.get_corrected_programs("Ziauddin University")
            for item in structured:
                if item["program_name"] in known_programs:
                    corrected = known_programs[item["program_name"]]
                    item.update({
                        "category": corrected["category"],
                        "deadlines": corrected.get("deadlines", []),
                        "admission_open": corrected.get("admission_open", False)
                    })
        except Exception as e:
            print(f"⚠️ Error applying corrections: {e}")

        # Save to Supabase using the agent's compare_outputs method
        if structured:
            print(f"ℹ️ Saving {len(structured)} programs to Supabase...")
            agent = agents[name]
            agent.compare_outputs(structured)
        else:
            print("⚠️ No structured data to save to Supabase")

        all_structured.extend(structured)

        # Save to local files
        agent_output_path = f"memory/{name}/agent_output.json"
        os.makedirs(f"memory/{name}", exist_ok=True)
        with open(agent_output_path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(structured)} entries to {agent_output_path}")

        corrected_path = f"memory/{name}/corrected.json"
        with open(corrected_path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(structured)} entries to {corrected_path}")

    # Save combined results
    with open("corrected.json", "w", encoding="utf-8") as f:
        json.dump(all_structured, f, indent=2, ensure_ascii=False)
    print(f"💾 Final combined corrected.json with {len(all_structured)} total entries.")

if __name__ == "__main__":
    asyncio.run(main())