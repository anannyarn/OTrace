"""
Matching Engine for OTrace.
Computes feature vectors, institution rules, name distances, and calibrated confidence scores.
"""
import os
import re
import joblib
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from rapidfuzz import distance, fuzz

from app.aliases import (
    GENERIC_COLLEGE_WORDS,
    get_canonical_college,
    normalize_name_token,
    COLLEGE_ALIASES
)
from app.config import MODEL_PATH

# Check for sentence_transformers availability
TRY_SENTENCE_TRANSFORMERS = False
try:
    from sentence_transformers import SentenceTransformer, util
    _st_model = SentenceTransformer('all-MiniLM-L6-v2')
    TRY_SENTENCE_TRANSFORMERS = True
except Exception:
    _st_model = None
    TRY_SENTENCE_TRANSFORMERS = False


FEATURE_NAMES = [
    "name_similarity",
    "institution_match",
    "semantic_similarity",
    "city_match",
    "username_fits_name",
    "cross_link_score",
    "keyword_hits"
]


def clean_display_name(raw_title: str, platform: str = "") -> str:
    """Strips platform-specific suffixes and search engine title junk to extract clean name."""
    if not raw_title:
        return ""
    t = raw_title.strip()

    # Remove common platform suffixes
    t = re.sub(
        r'\s*[\-|\|•·/]\s*(LinkedIn|Instagram|Twitter|X|Facebook|YouTube|GitHub|Reddit|Medium|Kaggle|LeetCode|HackerRank|CodeChef|Dev\.to|Substack).*$',
        '', t, flags=re.IGNORECASE
    )
    t = re.sub(r'\s*photos and videos.*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*Profile.*$', '', t, flags=re.IGNORECASE)

    # Handle GitHub style: 'username (Full Name)' -> 'Full Name'
    m_gh = re.search(r'^[a-zA-Z0-9_-]+\s*\(([^\)]+)\)', t)
    if m_gh:
        return m_gh.group(1).strip()

    # Handle handles in parens: 'Arun Nair (@arunnair99)' -> 'Arun Nair'
    t = re.sub(r'\s*\(@[^\)]+\)', '', t)

    # Handle Reddit style: 'Overview for u/username' -> 'username'
    m_red = re.search(r'Overview for u/([a-zA-Z0-9_-]+)', t, re.IGNORECASE)
    if m_red:
        return m_red.group(1)

    # Take first segment if still separated by dash or pipe
    if '-' in t:
        parts = [p.strip() for p in t.split('-') if p.strip()]
        if parts and 1 <= len(parts[0].split()) <= 4:
            t = parts[0]

    if '|' in t:
        parts = [p.strip() for p in t.split('|') if p.strip()]
        if parts and 1 <= len(parts[0].split()) <= 4:
            t = parts[0]

    return t.strip()


def extract_features(query: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, float]:
    """
    Extracts numerical features (0.0 to 1.0 scale) for a query and candidate pair.
    Enforces strict hard rules for generic words and known college mismatches.
    """
    q_name = query.get("name", "").strip()
    q_college = query.get("college")
    q_keywords = [kw.lower() for kw in query.get("keywords", [])]

    raw_display_name = candidate.get("display_name", "") or ""
    platform = candidate.get("platform", "") or ""
    c_display_name = clean_display_name(raw_display_name, platform) or raw_display_name

    c_username = candidate.get("username", "") or ""
    c_snippet = candidate.get("snippet", "") or ""
    c_inst = candidate.get("institution", "") or ""
    c_location = candidate.get("location", "") or ""
    c_cross_links = candidate.get("cross_links", []) or []

    # 1. Name Similarity (Jaro-Winkler + Token Sort + Token Set + Transliteration & Initial matching)
    name_sim = calculate_name_similarity(q_name, c_display_name, c_username, platform)

    # 2. Institution Match (with generic word stoplist and hard mismatch rule)
    inst_match = calculate_institution_match(q_college, c_inst, c_snippet)

    # 3. Semantic Similarity (Sentence Transformers or Token Overlap)
    sem_sim = calculate_semantic_similarity(
        f"{q_name} {q_college or ''} {' '.join(q_keywords)}",
        f"{c_display_name} {c_inst} {c_snippet}"
    )

    # 4. City / Location Match
    city_match = calculate_city_match(q_keywords, c_location, c_snippet)

    # 5. Username fits name
    username_fit = calculate_username_fits_name(q_name, c_username)

    # 6. Cross link score
    cross_link = 1.0 if c_cross_links else 0.0

    # 7. Keyword Hits (count of extra keywords appearing in candidate text)
    kw_hits = calculate_keyword_hits(q_keywords, f"{c_display_name} {c_inst} {c_snippet}")

    return {
        "name_similarity": round(float(name_sim), 4),
        "institution_match": round(float(inst_match), 4),
        "semantic_similarity": round(float(sem_sim), 4),
        "city_match": round(float(city_match), 4),
        "username_fits_name": round(float(username_fit), 4),
        "cross_link_score": round(float(cross_link), 4),
        "keyword_hits": round(float(kw_hits), 4)
    }


def calculate_name_similarity(query_name: str, candidate_name: str, candidate_username: str, platform: str = "") -> float:
    """Calculates robust name similarity metric."""
    if not query_name or not candidate_name:
        return 0.0

    clean_cand_name = clean_display_name(candidate_name, platform) or candidate_name

    # Normalize tokens with transliterations
    q_tokens = [normalize_name_token(t) for t in re.findall(r'\w+', query_name.lower())]
    c_tokens = [normalize_name_token(t) for t in re.findall(r'\w+', clean_cand_name.lower())]

    q_norm = " ".join(q_tokens)
    c_norm = " ".join(c_tokens)

    # Jaro-Winkler distance
    jw_score = distance.JaroWinkler.similarity(q_norm, c_norm)

    # Token sort ratio
    ts_score = fuzz.token_sort_ratio(q_norm, c_norm) / 100.0

    # Token set ratio
    tset_score = fuzz.token_set_ratio(q_norm, c_norm) / 100.0

    # Handle Initials matching (e.g. "A. Nair" vs "Arun Nair")
    initial_match = False
    if len(q_tokens) > 1 and len(c_tokens) > 1:
        if (len(q_tokens[0]) == 1 and q_tokens[0][0] == c_tokens[0][0] and q_tokens[1] == c_tokens[1]) or \
           (len(c_tokens[0]) == 1 and c_tokens[0][0] == q_tokens[0][0] and c_tokens[1] == q_tokens[1]):
            initial_match = True

    score = max(jw_score, ts_score, tset_score)
    if initial_match:
        score = max(score, 0.85)

    # Check username fallback if candidate_name was generic
    if candidate_username:
        u_score = calculate_username_fits_name(query_name, candidate_username)
        score = max(score, u_score * 0.9)

    return min(1.0, score)


def calculate_institution_match(query_college: Optional[str], candidate_inst: str, candidate_snippet: str) -> float:
    """
    Institution Match Logic:
    - HARD MISMATCH: If query college is known (e.g. 'NIT Calicut') and candidate mentions a DIFFERENT known college (e.g. 'MIT'), return 0.0.
    - Generic words ('institute', 'technology', 'university', 'college') DO NOT count as evidence.
    """
    if not query_college:
        return 0.0

    text_to_search = f"{candidate_inst} {candidate_snippet}".strip()
    if not text_to_search:
        return 0.0

    # Check canonical match first
    cand_canonical = get_canonical_college(text_to_search)
    if cand_canonical:
        if cand_canonical == query_college:
            return 1.0
        else:
            # HARD MISMATCH RULE!
            # Query specified a known college, candidate specified a DIFFERENT known college
            return 0.0

    # If candidate mentions generic words only, return 0.0
    tokens = [t.lower() for t in re.findall(r'\w+', text_to_search)]
    non_generic = [t for t in tokens if t not in GENERIC_COLLEGE_WORDS]
    if not non_generic:
        return 0.0

    # Fuzzy check with query college non-generic words
    q_tokens = [t.lower() for t in re.findall(r'\w+', query_college) if t.lower() not in GENERIC_COLLEGE_WORDS]
    if not q_tokens:
        return 0.0

    hits = sum(1 for qt in q_tokens if qt in non_generic)
    return hits / len(q_tokens)


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Computes semantic similarity via sentence-transformers or token overlap."""
    if _st_model is not None:
        try:
            emb1 = _st_model.encode(text1, convert_to_tensor=True)
            emb2 = _st_model.encode(text2, convert_to_tensor=True)
            cos_sim = util.cos_sim(emb1, emb2).item()
            return float(max(0.0, min(1.0, cos_sim)))
        except Exception:
            pass

    # Token overlap fallback
    t1 = set(re.findall(r'\w+', text1.lower()))
    t2 = set(re.findall(r'\w+', text2.lower()))
    if not t1 or not t2:
        return 0.0
    overlap = len(t1.intersection(t2))
    return overlap / max(len(t1), len(t2))


def calculate_city_match(keywords: List[str], candidate_location: str, candidate_snippet: str) -> float:
    """Checks if location keywords match candidate text."""
    combined = f"{candidate_location} {candidate_snippet}".lower()
    for kw in keywords:
        if len(kw) > 2 and kw in combined:
            return 1.0
    return 0.0


def calculate_username_fits_name(query_name: str, candidate_username: str) -> float:
    """Checks if candidate username resembles query name."""
    if not query_name or not candidate_username:
        return 0.0

    q_clean = re.sub(r'[^a-zA-Z0-9]', '', query_name.lower())
    u_clean = re.sub(r'[^a-zA-Z0-9]', '', candidate_username.lower())

    if not q_clean or not u_clean:
        return 0.0

    if q_clean in u_clean or u_clean in q_clean:
        return 1.0

    tokens = [t for t in re.findall(r'\w+', query_name.lower())]
    if len(tokens) >= 2:
        fn, ln = tokens[0], tokens[-1]
        combos = [f"{fn}{ln}", f"{ln}{fn}", f"{fn}_{ln}", f"{fn}.{ln}", f"{fn[0]}{ln}"]
        for c in combos:
            if c in u_clean:
                return 1.0

    sim = fuzz.ratio(q_clean, u_clean) / 100.0
    return float(sim)


def calculate_keyword_hits(keywords: List[str], text: str) -> float:
    """Calculates proportion of user keywords appearing in candidate text."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(1.0, hits / len(keywords))


def score_candidate(query: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scores a candidate profile using trained ML classifier if available,
    or hand-weighted calibrated fallback.
    """
    features = extract_features(query, candidate)
    feat_vector = np.array([[features[fn] for fn in FEATURE_NAMES]])

    has_college = bool(query.get("college"))

    score_val = 0.0
    if os.path.exists(MODEL_PATH) and has_college:
        try:
            model = joblib.load(MODEL_PATH)
            score_val = float(model.predict_proba(feat_vector)[0][1])
        except Exception:
            score_val = _hand_weighted_score(features, query)
    else:
        score_val = _hand_weighted_score(features, query)

    # Cap & Penalty checks for edge cases
    # 1. Common name / Name-only match with zero supporting evidence -> cap at 35%
    if features["name_similarity"] >= 0.7 and features["institution_match"] == 0.0 and features["city_match"] == 0.0 and features["keyword_hits"] == 0.0 and features["username_fits_name"] < 0.5:
        score_val = min(score_val, 0.35)

    # 2. Hard mismatch in college -> severe penalty
    if query.get("college") and features["institution_match"] == 0.0 and candidate.get("institution"):
        c_canon = get_canonical_college(candidate.get("institution") or "")
        if c_canon and c_canon != query.get("college"):
            score_val *= 0.2

    confidence = int(round(score_val * 100))
    confidence = max(5, min(99, confidence))

    band = "weak"
    if confidence >= 80:
        band = "strong"
    elif confidence >= 50:
        band = "plausible"

    evidence = _generate_evidence_breakdown(query, candidate, features)

    # Ensure display name returned is clean
    display_name_cleaned = clean_display_name(candidate.get("display_name", ""), candidate.get("platform", ""))
    if display_name_cleaned:
        candidate["display_name"] = display_name_cleaned

    return {
        "confidence_score": confidence,
        "band": band,
        "features": features,
        "evidence": evidence
    }


def _hand_weighted_score(features: Dict[str, float], query: Dict[str, Any]) -> float:
    """Heuristic hand-weighted scoring formula adapted to query parameters."""
    has_college = bool(query.get("college"))

    if has_college:
        weights = {
            "name_similarity": 0.40,
            "institution_match": 0.25,
            "semantic_similarity": 0.10,
            "username_fits_name": 0.15,
            "city_match": 0.05,
            "keyword_hits": 0.05
        }
    else:
        weights = {
            "name_similarity": 0.50,
            "username_fits_name": 0.25,
            "keyword_hits": 0.15,
            "semantic_similarity": 0.05,
            "city_match": 0.05,
            "institution_match": 0.0
        }

    score = sum(features[k] * w for k, w in weights.items())
    return float(score)



def _generate_evidence_breakdown(query: Dict[str, Any], candidate: Dict[str, Any], features: Dict[str, float]) -> Dict[str, List[str]]:
    """Generates human-understandable evidence points explaining the score."""
    supporting = []
    contradicting = []
    missing = []

    if features["name_similarity"] >= 0.8:
        supporting.append(f"Name match is strong ({int(features['name_similarity']*100)}% similarity)")
    elif features["name_similarity"] >= 0.6:
        supporting.append("Name is partially similar or transliteration match")
    else:
        contradicting.append("Name mismatch or low string similarity")

    if query.get("college"):
        if features["institution_match"] == 1.0:
            supporting.append(f"Matched institution '{query['college']}'")
        elif features["institution_match"] == 0.0 and candidate.get("institution"):
            c_canon = get_canonical_college(candidate.get("institution") or "")
            if c_canon and c_canon != query.get("college"):
                contradicting.append(f"Hard mismatch: candidate profile lists '{candidate['institution']}' instead of '{query['college']}'")
            else:
                missing.append(f"No match for college '{query['college']}'")
        else:
            missing.append(f"College '{query['college']}' not mentioned in candidate profile")

    if features["username_fits_name"] >= 0.8:
        supporting.append(f"Username '{candidate.get('username')}' closely matches name structure")

    if features["keyword_hits"] > 0:
        supporting.append("Matched extra context keywords in profile snippet")
    elif query.get("keywords"):
        missing.append("Candidate profile lacks typed contextual keywords")

    return {
        "supporting": supporting,
        "contradicting": contradicting,
        "missing": missing
    }
