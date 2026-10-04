"""
Semantic Scholar Public API Collector.
Searches academic authors via Semantic Scholar Graph API.
"""
from typing import Dict, Any, List
import httpx
from app.collectors.base import BaseCollector


class ScholarCollector(BaseCollector):
    name = "Semantic Scholar"

    async def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = query.get("name", "").strip()
        college = query.get("college")
        keywords = query.get("keywords", [])

        if not name:
            return []

        search_q = name
        if college:
            search_q += f" {college}"

        url = "https://api.semanticscholar.org/graph/v1/author/search"
        params = {
            "query": search_q,
            "fields": "name,aliases,affiliations,homepage,paperCount",
            "limit": 5
        }
        headers = {
            "User-Agent": "OTrace-Footprint-Analyzer/1.0"
        }

        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                for item in items:
                    author_id = item.get("authorId")
                    author_name = item.get("name")
                    affiliations = item.get("affiliations") or []
                    aff_str = ", ".join(affiliations) if isinstance(affiliations, list) else str(affiliations)
                    homepage = item.get("homepage")
                    cross_links = [homepage] if homepage else []

                    profile_url = f"https://www.semanticscholar.org/author/{author_id}" if author_id else ""
                    paper_count = item.get("paperCount", 0)

                    results.append({
                        "platform": "Semantic Scholar",
                        "username": author_id,
                        "display_name": author_name,
                        "url": profile_url,
                        "snippet": f"Academic Author | Papers: {paper_count} | Affiliations: {aff_str}".strip(" |"),
                        "institution": aff_str if aff_str else None,
                        "location": None,
                        "cross_links": cross_links
                    })
        return results
