"""
Search API Collector for Social & Web Profiles (Brave Search API / Tavily API / DDGS Multi-Engine Fallback).
Extracts public social media and developer profile URLs (LinkedIn, Instagram, X/Twitter, Facebook,
YouTube, GitHub, Reddit, Medium, Threads, Pinterest, Quora, Kaggle, LeetCode, CodeChef, HackerRank, Dev.to, Substack)
while dropping posts, hashtags, feeds, and non-profile pages.
"""
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import httpx
from app.config import BRAVE_API_KEY, TAVILY_API_KEY
from app.collectors.base import BaseCollector

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

# Regex rules to validate and parse genuine user profile URLs across all major platforms
PROFILE_PATTERNS: List[Tuple[str, str, int]] = [
    ("LinkedIn", r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)', 1),
    ("Instagram", r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_\.-]+)', 1),
    ("X/Twitter", r'https?://(?:www\.)?(?:x|twitter)\.com/([a-zA-Z0-9_]+)', 1),
    ("Facebook", r'https?://(?:www\.)?facebook\.com/(?:people/[a-zA-Z0-9\.-]+/\d+|public/[a-zA-Z0-9\.-]+|([a-zA-Z0-9\.-]+))', 1),
    ("YouTube", r'https?://(?:www\.)?youtube\.com/(?:@|user/|c/|channel/)?([a-zA-Z0-9_.-]+)', 1),
    ("GitHub", r'https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)', 1),
    ("Reddit", r'https?://(?:www\.)?reddit\.com/(?:user|u)/([a-zA-Z0-9_-]+)', 1),
    ("Medium", r'https?://(?:www\.|[a-zA-Z0-9_-]+\.)?medium\.com/@?([a-zA-Z0-9_-]+)', 1),
    ("Threads", r'https?://(?:www\.)?threads\.net/@([a-zA-Z0-9_\.-]+)', 1),
    ("Pinterest", r'https?://(?:[a-z]{2,3}\.)?pinterest\.com/([a-zA-Z0-9_-]+)', 1),
    ("Quora", r'https?://(?:www\.)?quora\.com/profile/([a-zA-Z0-9_-]+)', 1),
    ("Kaggle", r'https?://(?:www\.)?kaggle\.com/([a-zA-Z0-9_-]+)', 1),
    ("LeetCode", r'https?://(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)', 1),
    ("CodeChef", r'https?://(?:www\.)?codechef\.com/users/([a-zA-Z0-9_-]+)', 1),
    ("HackerRank", r'https?://(?:www\.)?hackerrank\.com/(?:profile/)?([a-zA-Z0-9_-]+)', 1),
    ("Dev.to", r'https?://(?:www\.)?dev\.to/([a-zA-Z0-9_-]+)', 1),
    ("Substack", r'https?://(?:www\.|[a-zA-Z0-9_-]+\.)?substack\.com/@?([a-zA-Z0-9_-]+)', 1),
]

EXCLUDE_PATH_KEYWORDS = [
    "/status/", "/posts/", "/p/", "/reels/", "/explore/", "/stories/",
    "/groups/", "/events/", "/watch", "/playlist", "/shorts", "/jobs/",
    "/company/", "/pulse/", "/hashtag/", "/search/", "/photo.php",
    "/problems/", "/datasets/", "/competitions/", "/auth/", "/login/",
    "/articles/", "/discuss/", "/questions/", "/help/", "/about/"
]

IGNORED_USERNAMES = {
    "explore", "help", "about", "terms", "privacy", "settings", "login",
    "signup", "jobs", "popular", "reel", "reels", "p", "tv", "stories",
    "feed", "search", "hashtag", "topics", "groups", "events", "directory",
    "overview", "comments", "submitted", "saved", "upvoted", "downvoted",
    "datasets", "code", "discussion", "competitions", "learn", "work",
    "company", "organizations", "enterprise", "business", "blog", "press"
}


def parse_profile_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Validates if a URL is a clean personal profile page.
    Returns (Platform, Username) if valid, else None.
    """
    if not url:
        return None

    # Strip trailing query params for clean check
    url_clean = url.split("?")[0].rstrip("/")
    url_lower = url_clean.lower()

    for kw in EXCLUDE_PATH_KEYWORDS:
        if kw in url_lower:
            return None

    for platform, pattern, grp in PROFILE_PATTERNS:
        match = re.search(pattern, url_clean, re.IGNORECASE)
        if match:
            username = match.group(grp)
            if not username:
                continue
            if username.lower() in IGNORED_USERNAMES:
                return None
            return platform, username
    return None


class SearchAPICollector(BaseCollector):
    name = "SearchAPI"

    async def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = query.get("name", "").strip()
        college = query.get("college")
        keywords = query.get("keywords", [])

        if not name:
            return []

        results: List[Dict[str, Any]] = []

        # 1. API Keys (Brave / Tavily) if provided
        if BRAVE_API_KEY:
            brave_res = await self._fetch_brave(name, college, keywords)
            results.extend(brave_res)
        if TAVILY_API_KEY:
            tavily_res = await self._fetch_tavily(name, college, keywords)
            results.extend(tavily_res)

        # 2. Free Web Search (DDGS Multi-Engine per platform) - always runs to gather social accounts
        ddgs_res = await self._fetch_ddgs(name, college, keywords)
        results.extend(ddgs_res)

        # Deduplicate results by clean profile URL
        unique_results = []
        seen_urls = set()
        for r in results:
            u = r.get("url", "").strip().rstrip("/")
            if u and u not in seen_urls:
                seen_urls.add(u)
                unique_results.append(r)

        return unique_results

    async def _fetch_ddgs(self, name: str, college: Optional[str], keywords: List[str]) -> List[Dict[str, Any]]:
        """Multi-engine search for social & developer profiles using per-site queries."""
        if not HAS_DDGS:
            return []

        base_query = f"{name}"
        if college:
            base_query += f" {college}"
        if keywords:
            base_query += " " + " ".join(keywords[:2])

        target_sites = [
            "linkedin.com",
            "instagram.com",
            "x.com",
            "facebook.com",
            "github.com",
            "reddit.com",
            "medium.com",
            "youtube.com",
            "kaggle.com",
            "leetcode.com",
            "hackerrank.com",
            "codechef.com",
            "dev.to",
            "quora.com",
            "pinterest.com"
        ]

        def run_search_sync() -> List[Dict[str, Any]]:
            items = []
            try:
                ddgs = DDGS()
                for site in target_sites:
                    q = f"{base_query} site:{site}"
                    try:
                        res = list(ddgs.text(q, max_results=5))
                        items.extend(res)
                    except Exception:
                        pass
                # General search fallback for profiles
                try:
                    gen_q = f"{base_query} profile linkedin instagram twitter facebook github"
                    res = list(ddgs.text(gen_q, max_results=10))
                    items.extend(res)
                except Exception:
                    pass
            except Exception as e:
                print(f"DDGS search error: {e}")
            return items

        raw_items = await asyncio.to_thread(run_search_sync)

        results = []
        for item in raw_items:
            url = item.get("href") or item.get("url") or ""
            parsed = parse_profile_url(url)
            if parsed:
                platform, username = parsed
                title = item.get("title") or name
                snippet = item.get("body") or item.get("snippet") or f"Public {platform} profile for {name}."
                results.append({
                    "platform": platform,
                    "username": username,
                    "display_name": title,
                    "url": url,
                    "snippet": snippet,
                    "institution": college,
                    "location": None,
                    "cross_links": []
                })
        return results

    async def _fetch_brave(self, name: str, college: Optional[str], keywords: List[str]) -> List[Dict[str, Any]]:
        query_str = f"{name}"
        if college:
            query_str += f" {college}"
        if keywords:
            query_str += " " + " ".join(keywords[:2])

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }

        sites = [
            "site:linkedin.com/in",
            "site:instagram.com",
            "site:x.com",
            "site:facebook.com",
            "site:youtube.com",
            "site:github.com",
            "site:reddit.com",
            "site:medium.com"
        ]

        full_query = f"{query_str} ({' OR '.join(sites)})"

        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": full_query, "count": 20},
                    headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    web_results = data.get("web", {}).get("results", [])
                    for item in web_results:
                        url = item.get("url", "")
                        parsed = parse_profile_url(url)
                        if parsed:
                            platform, username = parsed
                            results.append({
                                "platform": platform,
                                "username": username,
                                "display_name": item.get("title", name),
                                "url": url,
                                "snippet": item.get("description", ""),
                                "institution": college,
                                "location": None,
                                "cross_links": []
                            })
        except Exception as e:
            print(f"Brave Search API error: {e}")
        return results

    async def _fetch_tavily(self, name: str, college: Optional[str], keywords: List[str]) -> List[Dict[str, Any]]:
        query_str = f"{name}"
        if college:
            query_str += f" {college}"
        if keywords:
            query_str += " " + " ".join(keywords[:2])

        payload = {
            "api_key": TAVILY_API_KEY,
            "query": f"{query_str} profile linkedin instagram twitter facebook github reddit medium kaggle leetcode",
            "search_depth": "basic",
            "max_results": 20
        }

        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.tavily.com/search", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("results", [])
                    for item in items:
                        url = item.get("url", "")
                        parsed = parse_profile_url(url)
                        if parsed:
                            platform, username = parsed
                            results.append({
                                "platform": platform,
                                "username": username,
                                "display_name": item.get("title", name),
                                "url": url,
                                "snippet": item.get("content", ""),
                                "institution": college,
                                "location": None,
                                "cross_links": []
                            })
        except Exception as e:
            print(f"Tavily Search API error: {e}")
        return results
