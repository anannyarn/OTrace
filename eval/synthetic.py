"""
Synthetic Labelled Dataset Generator for OTrace.
Generates realistic identity resolution evaluation data with:
- Same-name-different-college distractors (Hard negative)
- Transliteration variants and initials (True positive)
- Missing fields and partial keyword matches
- Cross-linked profiles
Split by person query ID to prevent data leakage.
"""
import random
from typing import List, Dict, Any, Tuple
from app.matching import extract_features, FEATURE_NAMES

NAMES = [
    ("Arun Nair", ["Arun Nayar", "A. Nair", "Arun Kumar Nair"]),
    ("Mohammed Ahmed", ["Muhammed Ahmad", "M. Ahmed", "Mohd Ahmed"]),
    ("Ananya Sharma", ["Ananya S.", "A. Sharma"]),
    ("Rahul Verma", ["Rahul V.", "R. Verma"]),
    ("Priya Patel", ["Priya Patil", "P. Patel"])
]

COLLEGES = [
    ("NIT Calicut", "nitc"),
    ("IIT Madras", "iitm"),
    ("CUSAT", "cusat"),
    ("BITS Pilani", "bits"),
    ("MIT", "mit")
]

EMPLOYERS = ["Infosys", "TCS", "Wipro", "Google", "Microsoft"]
CITIES = ["Kochi", "Bangalore", "Chennai", "Mumbai", "Delhi"]


def generate_synthetic_dataset(num_persons: int = 40) -> List[Dict[str, Any]]:
    """
    Generates synthetic samples.
    Each sample:
    {
        "person_id": int,
        "query": dict,
        "candidate": dict,
        "is_same_person": int (1 or 0),
        "features": dict
    }
    """
    dataset = []

    for person_id in range(num_persons):
        name_tuple = random.choice(NAMES)
        canonical_name, name_variants = name_tuple

        college_tuple = random.choice(COLLEGES)
        canonical_college, college_alias = college_tuple

        employer = random.choice(EMPLOYERS)
        city = random.choice(CITIES)

        query = {
            "name": canonical_name,
            "college": canonical_college,
            "keywords": [employer, city]
        }

        # 1. True Positive: Matching Profile with same college & employer
        tp_cand = {
            "platform": "GitHub",
            "username": canonical_name.lower().replace(" ", "_"),
            "display_name": random.choice(name_variants),
            "url": f"https://github.com/{canonical_name.lower().replace(' ', '_')}",
            "snippet": f"Software Engineer at {employer}. Alumnus of {canonical_college}.",
            "institution": canonical_college,
            "location": city,
            "cross_links": [f"https://linkedin.com/in/{canonical_name.lower().replace(' ', '')}"]
        }

        feats_tp = extract_features(query, tp_cand)
        dataset.append({
            "person_id": person_id,
            "query": query,
            "candidate": tp_cand,
            "is_same_person": 1,
            "features": feats_tp
        })

        # 2. Hard Negative: Same Name, DIFFERENT Known College (Distractor)
        other_colleges = [c for c in COLLEGES if c[0] != canonical_college]
        distractor_college, _ = random.choice(other_colleges)

        hn_cand = {
            "platform": "LinkedIn",
            "username": canonical_name.lower().replace(" ", ""),
            "display_name": canonical_name,
            "url": f"https://linkedin.com/in/{canonical_name.lower().replace(' ', '')}",
            "snippet": f"Student at {distractor_college}.",
            "institution": distractor_college,
            "location": "Different City",
            "cross_links": []
        }

        feats_hn = extract_features(query, hn_cand)
        dataset.append({
            "person_id": person_id,
            "query": query,
            "candidate": hn_cand,
            "is_same_person": 0,
            "features": feats_hn
        })

        # 3. Easy Negative: Random Name & Random College
        en_cand = {
            "platform": "X/Twitter",
            "username": "random_user_99",
            "display_name": "Vikram Seth",
            "url": "https://x.com/random_user_99",
            "snippet": f"Designer based in {random.choice(CITIES)}",
            "institution": "Other Institute",
            "location": random.choice(CITIES),
            "cross_links": []
        }

        feats_en = extract_features(query, en_cand)
        dataset.append({
            "person_id": person_id,
            "query": query,
            "candidate": en_cand,
            "is_same_person": 0,
            "features": feats_en
        })

    return dataset


if __name__ == "__main__":
    data = generate_synthetic_dataset(10)
    print(f"Generated {len(data)} synthetic evaluation samples.")
