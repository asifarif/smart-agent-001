# tools/university_scraper_agent.py
class UniversityScraperAgent:
    def __init__(self, supabase_client):
        self.supabase_client = supabase_client
        self.name = "base_agent"
        self.known_programs = []
        self.visited = set()
        self.scraped_pages = []

    def compare_outputs(self, structured_data: list):
        print(f"ℹ️ Comparing {len(structured_data)} extracted programs for {self.name}...")
        university = self.get_university_name()
        for program in structured_data:
            program["university"] = university
            # Apply corrections if available
            corrected = self.known_programs.get(program["program_name"])
            if corrected:
                for field in ["category", "admission_open", "deadlines"]:
                    if field in corrected:
                        print(f"ℹ️ Applying correction: {program['program_name']} {field} from {program[field]} to {corrected[field]}")
                        program[field] = corrected[field]
            self.supabase_client.upsert_extracted_program(program)
        print(f"✅ Upserted {len(structured_data)} programs to Supabase for {self.name}.")

    def get_university_name(self):
        if self.name == "ziauddin_agent":
            return "Ziauddin University"
        elif self.name == "iqra_agent":
            return "Iqra University"
        elif self.name == "nust_agent":
            return "NUST"
        return "Unknown University"