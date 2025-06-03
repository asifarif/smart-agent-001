# tools/classify_programs.py
import re

faculty_prefixes = re.compile(
    r"^(Mr|Ms|Mrs|Dr|Prof|Professor|Lecturer|Assistant Professor|Associate Professor|Engr)\b",
    re.IGNORECASE
)

# Define common name prefixes to filter out
def is_probably_faculty(text):
    text = text.strip()

    # Fix glued title+degree
    text = re.sub(r"(?i)\b(Lecturer|Professor|Assistant Professor|Associate Professor|Engr)(?=[A-Z])", r"\1 ", text)

    # Known faculty prefixes
    if faculty_prefixes.match(text):
        return True

    # Contains multiple degrees — likely a faculty bio
    #if len(re.findall(r'\b(PhD|MPhil|MS|ME|MSc|MA|MBA|BS|BSc|B\.Ed|B\.Com|MBBS|BDS)\b', text, flags=re.IGNORECASE)) >= 2:
    #    return True

    # Promotional/news phrases (not a program)
    if re.search(r"\b(hosts?|organized|conducted|celebrates?|sports day|event|seminar)\b", text, re.IGNORECASE):
        return True

    # Too short or suspicious
    if len(text.split()) <= 3:
        return True

    return False

def classify_programs(programs):
    cleaned = []
    seen = set()
    
    degree_patterns = {
        "undergraduate": re.compile(r"\b(Bachelor of [A-Za-z\s]+|BS\s?\([A-Za-z\s]+\)|Bachelors of [A-Za-z\s]|bachelors|bachelor|bs|bsc|ba|bba|pharm[\- ]?d|mbbs|bds|b\.?ed|b\.?com|BSc)\b", re.IGNORECASE),
        # "masters": re.compile(r"\b(Master of [A-Za-z\s]+|MS\s?\([A-Za-z\s]+\)|MSc\s?\([A-Za-z\s]+\))\b", re.IGNORECASE),
        # "phd": re.compile(r"\b(Ph\.?D\.?|Doctor of Philosophy)\b", re.IGNORECASE),
        "medical": re.compile(r"\b(MBBS|BDS|BSN|Pharm[\- ]?D)\b", re.IGNORECASE)
    }

    for prog in programs:
        text = prog.strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\-\&\(\)]", "", text)

        # Skip if it looks like faculty name or too short/long
        if is_probably_faculty(text):
            continue

        if len(text) < 6 or len(text) > 500:
            continue

        if text.lower() in seen:
            continue

        category = None
        for level, pattern in degree_patterns.items():
            if pattern.search(text):
                category = level
                break

        if category:
            cleaned.append({"program_name": text, "category": category})
            seen.add(text.lower())

    return cleaned
