# agents/pdf_agent.py

import os
from tools.pdf_extractor import extract_text_from_pdf
from tools.classify_programs import classify_programs

class PDFAgent:
    def __init__(self, file_path):
        self.file_path = file_path

    def extract_programs(self):
        print(f"📄 Extracting text from PDF: {self.file_path}")
        
        # File existence check
        if not os.path.exists(self.file_path):
            print("❌ PDF file not found.")
            return []

        # File extension check
        if not self.file_path.lower().endswith(".pdf"):
            print("⚠️ File is not a PDF.")
            return []

        try:
            raw_text = extract_text_from_pdf(self.file_path)
        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            return []

        lines = raw_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        print(f"📊 {len(cleaned_lines)} lines extracted from PDF.")

        structured_programs = classify_programs(cleaned_lines)

        print(f"✅ {len(structured_programs)} programs detected.")
        return structured_programs
