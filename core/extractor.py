# core/extractor.py - Fixed version
import os
import json
import httpx
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("MODEL", "llama3-8b-8192")  # Default model if not set

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
async def extract_admission_info(raw_input: str, url: str) -> list:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    
    if not raw_input or not raw_input.strip():
        print(f"⚠️ Empty or whitespace-only input for {url}")
        return []

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Enhanced system prompt with better instructions
    system_prompt = """You are an expert admission information extractor. Your task is to extract university program information from webpage content and return it as valid JSON."""

    user_prompt = f"""
Extract admission program information from this university webpage content.

URL: {url}

Return ONLY a valid JSON array of objects. Each object must have these exact fields:
- "program_name": string (full program name, e.g., "Bachelor of Science in Computer Science")
- "category": one of ["undergraduate", "masters", "phd", "certification", "diploma"]
- "admission_open": boolean (true if admissions are currently open)
- "application_deadline": string in "YYYY-MM-DD" format or null
- "link": string (application/program link if available, otherwise use source URL)
- "source_text": string (relevant text excerpt from webpage)
- "source_url": "{url}"

Classification rules:
- "undergraduate": BS, Bachelor, BSc, BA, BBA, Doctor of Physical Therapy, etc.
- "masters": MS, Master, MSc, MA, MBA, MPhil, etc.
- "phd": PhD, Doctorate programs
- "certification": Short courses, certificates
- "diploma": Diploma programs

Look for:
- Program names (BS, MS, MBA, etc.)
- Application deadlines or dates
- "Apply Now", "Admission Open", "Last Date" text
- Any indication of open admissions

If no programs found, return: []

Webpage content:
{raw_input[:6000]}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
        content = response.json()
        
        if "choices" not in content or not content["choices"]:
            print(f"⚠️ No choices in Groq response for {url}")
            return []
            
        refined_text = content["choices"][0]["message"]["content"].strip()
        print(f"ℹ️ Groq response for {url} (length: {len(refined_text)}): {refined_text[:200]}...")
        
        if not refined_text:
            print(f"⚠️ Empty response from Groq for {url}")
            return []
        
        # Clean the response - remove markdown code blocks if present
        if refined_text.startswith("```json"):
            refined_text = refined_text.replace("```json", "").replace("```", "").strip()
        elif refined_text.startswith("```"):
            refined_text = refined_text.replace("```", "").strip()
        
        # Try to find JSON array in the response
        json_match = re.search(r'\[.*\]', refined_text, re.DOTALL)
        if json_match:
            refined_text = json_match.group(0)
        
        try:
            extracted_data = json.loads(refined_text)
            if not isinstance(extracted_data, list):
                print(f"⚠️ Response is not a list for {url}: {type(extracted_data)}")
                return []
                
            print(f"✅ Successfully extracted {len(extracted_data)} programs from {url}")
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSONDecodeError for {url}: {e}")
            print(f"Raw response: {refined_text[:500]}...")
            return []
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            print(f"⚠️ Rate limit hit for {url}: {e}")
            raise
        print(f"⚠️ HTTP status error for {url}: {e}")
        return []
    except httpx.RequestError as e:
        print(f"⚠️ HTTP request error for {url}: {e}")
        return []
    except Exception as e:
        print(f"⚠️ Unexpected error extracting from {url}: {e}")
        return []
