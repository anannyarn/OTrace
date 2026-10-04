"""
Smart Search Box Parser for OTrace.
Parses free-text input or labeled input into structured components:
{ "name": str, "college": str | None, "keywords": list[str] }
"""
import re
from typing import Dict, Any, Optional, List
from app.aliases import get_canonical_college, ALIAS_TO_CANONICAL


def parse_query(text: str) -> Dict[str, Any]:
    """
    Parses user input into name, college (if identified), and generic keywords.
    Handles:
    1. Key-value labeled formats: "name: Arun Nair, college: NITC, city: Kochi"
    2. Comma-separated format: "Arun Nair, NIT Calicut, CSE 2024, Infosys"
    3. Unseparated space format: "Arun Nair NIT Calicut CSE 2024" (first 2 words = name)
    """
    raw = text.strip()
    if not raw:
        return {"name": "", "college": None, "keywords": []}

    # 1. Check for labeled format (e.g., "name: ...", "college: ...")
    if ":" in raw and any(key in raw.lower() for key in ["name:", "college:", "company:", "city:", "work:"]):
        return _parse_labeled_query(raw)

    # 2. Check for comma-separated format
    if "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        name = parts[0]
        keywords: List[str] = []
        college: Optional[str] = None

        for part in parts[1:]:
            canon = get_canonical_college(part)
            if canon and not college:
                college = canon
            else:
                keywords.append(part)
        
        # Also check if college alias was embedded in the name string by accident
        name_canon = get_canonical_college(name)
        if name_canon and not college:
            college = name_canon

        return {
            "name": name,
            "college": college,
            "keywords": keywords
        }

    # 3. Unseparated space format: no commas
    tokens = raw.split()
    if len(tokens) <= 2:
        # 1 or 2 words total -> entire text is name
        canon = get_canonical_college(raw)
        return {
            "name": raw,
            "college": canon,
            "keywords": []
        }

    # Pull known college aliases out from tokens/subphrases first
    college: Optional[str] = get_canonical_college(raw)
    remaining_tokens: List[str] = []
    
    # Try finding multi-word or single-word college aliases in raw text
    matched_alias_str = None
    if college:
        # Find which specific alias matched
        raw_lower = raw.lower()
        for alias in sorted(ALIAS_TO_CANONICAL.keys(), key=len, reverse=True):
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, raw_lower):
                matched_alias_str = alias
                break

    if matched_alias_str:
        # Remove matched alias phrase from tokens
        pattern = re.compile(r'\b' + re.escape(matched_alias_str) + r'\b', re.IGNORECASE)
        clean_text = pattern.sub('', raw)
        clean_tokens = clean_text.split()
        if len(clean_tokens) >= 2:
            name = f"{clean_tokens[0]} {clean_tokens[1]}"
            keywords = clean_tokens[2:]
        elif len(clean_tokens) == 1:
            name = clean_tokens[0]
            keywords = []
        else:
            name = raw
            keywords = []
    else:
        # First two words = name, the rest are keywords
        name = f"{tokens[0]} {tokens[1]}"
        keywords = tokens[2:]
        # Check if any remaining keyword is a college alias
        for kw in keywords:
            canon = get_canonical_college(kw)
            if canon and not college:
                college = canon

    return {
        "name": name,
        "college": college,
        "keywords": keywords
    }


def _parse_labeled_query(raw: str) -> Dict[str, Any]:
    """Helper to parse key-value labeled strings."""
    # Pattern to match label: value pairs separated by commas or spaces
    # Example: "name: Arun Kumar Nair, college: NITC, city: Kochi"
    pattern = r'(name|college|company|city|work|institution|employer)\s*:\s*([^,:]+)'
    matches = re.findall(pattern, raw, re.IGNORECASE)

    name = ""
    college: Optional[str] = None
    keywords: List[str] = []

    for key, val in matches:
        k = key.lower()
        v = val.strip()
        if k == "name":
            name = v
        elif k in ["college", "institution"]:
            canon = get_canonical_college(v)
            college = canon if canon else v
        else:
            keywords.append(v)
            canon = get_canonical_college(v)
            if canon and not college:
                college = canon

    if not name:
        # Fallback if label 'name:' was omitted
        parts = raw.split(",")
        name = parts[0].strip()

    return {
        "name": name,
        "college": college,
        "keywords": keywords
    }
