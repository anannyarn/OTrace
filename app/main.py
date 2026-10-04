"""
OTrace FastAPI Main Application Server.
Provides API endpoints for parsing, footprint search, consent validation,
audit logging, rate limiting, feedback loops, and hosting the single-page frontend.
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import BRAVE_API_KEY, TAVILY_API_KEY, ANTHROPIC_API_KEY
from app.db import init_db, log_search_audit, save_feedback, get_all_feedback, clear_user_data
from app.parser import parse_query
from app.collectors.github import GitHubCollector
from app.collectors.scholar import ScholarCollector
from app.collectors.orcid import ORCIDCollector
from app.collectors.search_api import SearchAPICollector
from app.matching import score_candidate
from app.llm_judge import judge_top_candidates
from app.exposure import calculate_exposure_report

app = FastAPI(
    title="OTrace Digital Footprint Tool",
    description="Defensive digital footprint analyzer and identity resolution scoring system.",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple In-Memory Per-IP Rate Limiting (30 requests / minute)
IP_REQUEST_LOG: Dict[str, List[float]] = {}
RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 60.0


def check_rate_limit(ip: str):
    now = time.time()
    if ip not in IP_REQUEST_LOG:
        IP_REQUEST_LOG[ip] = []
    # Filter timestamps within window
    IP_REQUEST_LOG[ip] = [t for t in IP_REQUEST_LOG[ip] if now - t <= RATE_LIMIT_WINDOW]
    if len(IP_REQUEST_LOG[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a minute before making more requests."
        )
    IP_REQUEST_LOG[ip].append(now)


# Initialize SQLite DB schemas on module import
init_db()


# Pydantic Schemas
class SearchRequest(BaseModel):
    q: str
    consent: bool


class ParseRequest(BaseModel):
    q: str


class FeedbackRequest(BaseModel):
    query_name: str
    candidate_url: str
    candidate_platform: str
    is_same_person: bool
    features: Dict[str, Any]


# API Endpoints
@app.get("/health")
def health_check():
    has_search_key = bool(BRAVE_API_KEY or TAVILY_API_KEY)
    has_llm_key = bool(ANTHROPIC_API_KEY)
    return {
        "status": "ok",
        "collectors": ["GitHub", "Semantic Scholar", "ORCID", "SearchAPI"],
        "search_api_enabled": has_search_key,
        "llm_judge_enabled": has_llm_key
    }


@app.post("/parse")
def parse_endpoint(req: ParseRequest, request: Request):
    check_rate_limit(request.client.host if request.client else "127.0.0.1")
    parsed = parse_query(req.q)
    return parsed


@app.post("/search")
async def search_endpoint(req: SearchRequest, request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(ip)

    # 1. HARD RULE: Consent Verification
    if not req.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required to perform search. Please confirm you are searching for yourself or have consent."
        )

    raw_query = req.q.strip()
    if not raw_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )

    # 2. Parse Query
    parsed = parse_query(raw_query)
    name = parsed.get("name", "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract a valid name from the search text."
        )

    # 3. Run Collectors concurrently
    collectors = [
        GitHubCollector(),
        ScholarCollector(),
        ORCIDCollector(),
        SearchAPICollector()
    ]

    tasks = [col.run(parsed) for col in collectors]
    collector_results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    raw_candidates = []
    for res in collector_results_nested:
        if isinstance(res, list):
            raw_candidates.extend(res)

    # Deduplicate candidates by clean URL
    unique_candidates = []
    seen_urls = set()
    for c in raw_candidates:
        u = c.get("url", "").strip().rstrip("/")
        if u and u not in seen_urls:
            seen_urls.add(u)
            unique_candidates.append(c)

    # 4. Score Candidates using Matching Engine
    scored_candidates = []
    for cand in unique_candidates:
        score_res = score_candidate(parsed, cand)
        cand["confidence_score"] = score_res["confidence_score"]
        cand["band"] = score_res["band"]
        cand["features"] = score_res["features"]
        cand["evidence"] = score_res["evidence"]
        scored_candidates.append(cand)

    # Sort candidates by confidence descending
    scored_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
    top_results = scored_candidates[:40]

    # 5. Optional LLM Judge on top 5 candidates
    top_results, llm_used = await judge_top_candidates(parsed, top_results)

    # Re-sort after potential LLM adjustment
    top_results.sort(key=lambda x: x["confidence_score"], reverse=True)

    # 6. Compute Exposure Report
    exposure = calculate_exposure_report(parsed, top_results)

    # 7. Privacy Audit Log (Hashed Name Only)
    log_search_audit(name, ip, len(top_results))

    # Warnings for search configuration
    warnings = []
    if not (BRAVE_API_KEY or TAVILY_API_KEY):
        # Social media accounts are gathered via DDGS multi-engine search
        pass


    return {
        "parsed": parsed,
        "warnings": warnings,
        "results": top_results,
        "exposure": exposure,
        "method": "ML Classifier + Calibrated Fallback",
        "llm_used": llm_used
    }


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    save_feedback(
        req.query_name,
        req.candidate_url,
        req.candidate_platform,
        req.is_same_person,
        req.features
    )
    all_feedback = get_all_feedback()
    return {
        "status": "success",
        "message": "Feedback recorded.",
        "label_count": len(all_feedback)
    }


@app.get("/feedback/export")
def export_feedback():
    labels = get_all_feedback()
    return {
        "count": len(labels),
        "data": labels
    }


@app.delete("/data")
def delete_user_data():
    clear_user_data()
    return {"status": "success", "message": "All cached profiles, audit logs, and feedback labels cleared."}


# Serve static web interface
static_path = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse(static_path / "index.html")
