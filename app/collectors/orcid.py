"""
ORCID Public API Collector.
Searches public researcher profiles via open ORCID REST API.
"""
from typing import Dict, Any, List
import httpx
from app.collectors.base import BaseCollector


class ORCIDCollector(BaseCollector):
    name = "ORCID"

    async def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = query.get("name", "").strip()
        college = query.get("college")

        if not name:
            return []

        search_q = f'given-names:"{name}" OR family-name:"{name}" OR text:"{name}"'
        if college:
            search_q += f' AND text:"{college}"'

        url = "https://pub.orcid.org/v3.0/expanded-search/"
        params = {
            "q": search_q,
            "rows": 5
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "OTrace-Footprint-Analyzer/1.0"
        }

        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                expanded_results = data.get("expanded-result", [])
                if expanded_results:
                    for item in expanded_results:
                        orcid_id = item.get("orcid-id")
                        given = item.get("given-names", "")
                        family = item.get("family-names", "")
                        display_name = f"{given} {family}".strip() or name
                        inst = item.get("institution-name", [])
                        inst_str = ", ".join(inst) if isinstance(inst, list) else str(inst)

                        results.append({
                            "platform": "ORCID",
                            "username": orcid_id,
                            "display_name": display_name,
                            "url": f"https://orcid.org/{orcid_id}",
                            "snippet": f"ORCID iD: {orcid_id} | Institution: {inst_str}".strip(" |"),
                            "institution": inst_str if inst_str else None,
                            "location": None,
                            "cross_links": []
                        })
        return results
