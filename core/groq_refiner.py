# core/groq_refiner.py
import httpx
import os
from tools.classify_programs import classify_programs
from core.extractor import extract_possible_program_lines
import asyncio

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("MODEL")

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

async def refine_scraped_pages(scraped_pages):
    if not GROQ_API_KEY:
        raise ValueError("🚫 GROQ_API_KEY not found in environment variables.")

    # ✅ 1. Extract lines that might be program names
    all_lines = []
    for page in scraped_pages:
        text = page.get("text", "")
        lines = extract_possible_program_lines(text)
        all_lines.extend(lines)

    # ✅ 2. Filter lines to identify valid programs
    filtered_programs = classify_programs(all_lines)

    if not filtered_programs:
        print("⚠️ No valid programs found after classification.")
        return []

    # ✅ 3. Build prompt for Groq
    program_text_block = "\n".join([p["program_name"] for p in filtered_programs])

    system_prompt = (
        "You are an expert academic analyst. Given a list of academic program names, "
        "organize them into structured data grouped by faculty or department if possible. "
        "Each item should include: name, level (e.g., undergraduate), and groupings like 'Faculty of Engineering'."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": program_text_block}
    ]

    async with httpx.AsyncClient(timeout=100.0) as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.3
                }
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise RuntimeError(f"HTTP error during Groq request: {e}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP status error during Groq request: {e}")

    content = response.json()
    refined_text = content["choices"][0]["message"]["content"]

    try:
        import json
        return json.loads(refined_text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Groq output as JSON. Returning raw string.")
        return [{"raw_output": refined_text}]
