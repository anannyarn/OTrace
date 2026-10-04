"""
OTrace College Aliases, Generic Words, and Transliterations Table.
Designed to be easily extensible.
"""
import re
from typing import Dict, Set, List, Optional

# Generic words that must NOT count as individual college evidence
GENERIC_COLLEGE_WORDS = {
    "institute", "institutes", "technology", "university", "college", "colleges",
    "national", "indian", "science", "sciences", "and", "tech", "polytechnic",
    "school", "schools", "academy", "engineering", "state", "central"
}

# Standardized College Alias Dictionary
# Key: Canonical College Name
# Value: Set of normalized lower-case aliases (including acronyms and short names)
COLLEGE_ALIASES: Dict[str, Set[str]] = {
    "NIT Calicut": {
        "nitc", "nit calicut", "national institute of technology calicut",
        "calicut nit", "nitc calicut", "nit-calicut"
    },
    "CUSAT": {
        "cusat", "cochin university of science and technology",
        "cochin university", "cochin tech"
    },
    "IIT Madras": {
        "iit madras", "iitm", "indian institute of technology madras",
        "iit-madras", "iit chennai"
    },
    "IIT Bombay": {
        "iit bombay", "iitb", "indian institute of technology bombay",
        "iit-bombay", "iit mumbai"
    },
    "IIT Delhi": {
        "iit delhi", "iitd", "indian institute of technology delhi", "iit-delhi"
    },
    "IIT Kharagpur": {
        "iit kharagpur", "iitkgp", "indian institute of technology kharagpur", "iit-kgp"
    },
    "NIT Trichy": {
        "nitt", "nit trichy", "national institute of technology tiruchirappalli",
        "nit tiruchirappalli", "nittrichy"
    },
    "BITS Pilani": {
        "bits pilani", "bits", "birla institute of technology and science",
        "bits-pilani", "bits goa", "bits hyderabad"
    },
    "IISc Bangalore": {
        "iisc", "iisc bangalore", "indian institute of science", "iisc bengaluru"
    },
    "MIT": {
        "mit", "massachusetts institute of technology"
    },
    "Stanford University": {
        "stanford", "stanford university"
    },
    "Harvard University": {
        "harvard", "harvard university"
    },
    "Oxford University": {
        "oxford", "university of oxford", "oxford university"
    },
    "Cambridge University": {
        "cambridge", "university of cambridge", "cambridge university"
    },
    "Carnegie Mellon University": {
        "cmu", "carnegie mellon", "carnegie mellon university"
    },
    "UC Berkeley": {
        "ucb", "uc berkeley", "university of california berkeley", "berkeley"
    }
}

# Reverse lookup: Normalized token/phrase -> Canonical Name
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in COLLEGE_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical


def get_canonical_college(query_str: str) -> Optional[str]:
    """
    Given a query string or token, check if it matches a known college alias.
    Returns Canonical Name if matched, else None.
    """
    cleaned = re.sub(r'[^\w\s]', '', query_str.strip().lower())
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]
    
    # Try multi-word subphrase matching
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if len(alias) > 3:  # Only match non-trivial aliases in subphrases
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, cleaned):
                return canonical
        elif alias == cleaned:
            return canonical
    return None


# Name Transliterations & Equivalent Variations
TRANSLITERATION_GROUPS: List[List[str]] = [
    ["mohammed", "muhammad", "mohd", "muhammed", "mohamed", "mohamad"],
    ["ahmed", "ahmad"],
    ["nair", "nayar"],
    ["menon", "mainon"],
    ["kumar", "kumaar"],
    ["rao", "row", "raao"],
    ["singh", "singha"],
    ["patil", "patel"],
    ["chaterjee", "chatterjee", "chattopadhyay"],
    ["banerjee", "bandyopadhyay"],
    ["mukherjee", "mukhopadhyay"],
    ["sen", "sengupta"],
]

TRANSLITERATION_MAP: Dict[str, str] = {}
for group in TRANSLITERATION_GROUPS:
    canonical = group[0]
    for variant in group:
        TRANSLITERATION_MAP[variant] = canonical


def normalize_name_token(token: str) -> str:
    """Normalize a name token considering transliteration equivalents."""
    tok = token.strip().lower()
    return TRANSLITERATION_MAP.get(tok, tok)
