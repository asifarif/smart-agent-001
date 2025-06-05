# core/extractor.py - Improved program extraction
import os
import json
import httpx
import re
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("MODEL", "llama3-8b-8192")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
async def extract_admission_info(html: str, url: str) -> list:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    
    if not html or not html.strip():
        print(f"⚠️ Empty or whitespace-only HTML input for {url}")
        return []

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    
    # Attempt to find program data in tables, lists, divs, or sections
    content_text = ""
    
    # Try finding a table with program data
    table = None
    for selector in ["table", "table.table", "table.programs-table", "table#program-table", "table.data-table"]:
        table = soup.select_one(selector)
        if table:
            break
    
    if not table:
        tables = soup.find_all("table")
        for t in tables:
            headers = [th.text.strip().lower() for th in t.find_all("th")]
            program_keywords = ["program", "course", "degree", "category", "admission", "deadline", "apply", "status"]
            if any(keyword in headers for keyword in program_keywords):
                table = t
                break
    
    if table:
        content_text = "\n".join([row.get_text(separator=" | ").strip() for row in table.find_all("tr") if row.get_text(strip=True)])
        print(f"ℹ️ Extracted table content for {url} (length: {len(content_text)}): {content_text[:200]}...")
    else:
        # Fallback: Look for lists
        ul_list = soup.find("ul", class_=re.compile(r"program|list|courses|degrees|admission", re.I))
        if ul_list:
            content_text = "\n".join([li.get_text(separator=" | ").strip() for li in ul_list.find_all("li") if li.get_text(strip=True)])
        else:
            # Fallback: Look for divs or sections with program-related classes
            divs = soup.find_all("div", class_=re.compile(r"program|course|degree|admission|entry", re.I))
            if divs:
                content_text = "\n".join([div.get_text(separator=" | ").strip() for div in divs if div.get_text(strip=True)])
            else:
                # Last resort: Look for any elements containing program keywords
                program_elements = soup.find_all(text=re.compile(r"(BS|BSc|BA|BBA|MS|MSc|MA|MBA|MPhil|PhD|Diploma|Certificate)\b", re.I))
                if program_elements:
                    parent_elements = [elem.parent for elem in program_elements]
                    content_text = "\n".join([elem.get_text(separator=" | ").strip() for elem in parent_elements if elem.get_text(strip=True)])
                else:
                    print(f"⚠️ No program content found in HTML for {url}")
                    return []

        print(f"ℹ️ Extracted fallback content for {url} (length: {len(content_text)}): {content_text[:200]}...")

    if not content_text:
        print(f"⚠️ No content extracted for {url}")
        return []

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """You are an expert admission information extractor. Your task is to extract university program information from webpage content and return it as valid JSON."""

    user_prompt = f"""
Extract admission program information from the following webpage content, where sections or rows may be separated by newlines and columns by "|":

{content_text[:8000]}

URL: {url}

Return a JSON array of objects. Each object must have these exact fields:
- "program_name": string (e.g., "Bachelor of Science in Computer Science")
- "category": one of ["undergraduate", "masters", "phd", "certification", "diploma"]
- "admission_open": boolean (true if admissions are currently open, infer from context like "Apply Now", "Open", "Admission Open")
- "application_deadline": string in "YYYY-MM-DD" format or null (parse from text like "Last Date: 31 Dec 2024" or "07-Jul-2025")
- "link": string (URL for the program if found, otherwise use "{url}")
- "source_text": string (relevant text excerpt from the content)

Classification rules:
- "undergraduate": BS, BSc, BA, BBA, Bachelor, Bachelors, Doctor of Physical Therapy, etc.
- "masters": MS, MSc, MA, MBA, MPhil, Master, etc.
- "phd": PhD, Doctorate
- "certification": Short courses, certificates
- "diploma": Diploma programs

Look for:
- Program names (BS, MS, MBA, etc.)
- Application deadlines or dates (e.g., "Last Date: 31 Dec 2024", "07-Jul-2025")
- Indicators of open admissions ("Apply Now", "Admission Open", "Open")
- Links to program pages (if available)

If no programs are found, return: []
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
        
        if refined_text.startswith("```json"):
            refined_text = refined_text.replace("```json", "").replace("```", "").strip()
        elif refined_text.startswith("```"):
            refined_text = refined_text.replace("```", "").strip()
        
        json_match = re.search(r'\[.*\]', refined_text, re.DOTALL)
        if json_match:
            refined_text = json_match.group(0)
        
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
        print(f"⚠️ HTTP status error for {url}: {e}")
        raise
    except httpx.RequestError as e:
        print(f"⚠️ HTTP request error for {url}: {e}")
        raise
    except Exception as e:
        print(f"⚠️ Unexpected error extracting from {url}: {e}")
        return []