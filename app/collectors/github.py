"""
GitHub Public API Collector.
Searches public user accounts on GitHub using official open GitHub REST API.
"""
from typing import Dict, Any, List
import httpx
from app.collectors.base import BaseCollector


class GitHubCollector(BaseCollector):
    name = "GitHub"

    async def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = query.get("name", "").strip()
        keywords = query.get("keywords", [])
        college = query.get("college")

        if not name:
            return []

        search_q = f'"{name}" in:fullname'
        if keywords:
            search_q += " " + " ".join(keywords[:2])
        if college:
            search_q += f" {college}"

        url = f"https://api.github.com/search/users?q={httpx.URL(search_q).raw_path.decode('utf-8')}&per_page=5"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "OTrace-Footprint-Analyzer/1.0"
        }

        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                # Fallback to name search without in:fullname
                fallback_url = f"https://api.github.com/search/users?q={name}&per_page=5"
                resp = await client.get(fallback_url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                
                # Fetch detailed profile info for top 5 users
                for item in items[:5]:
                    user_url = item.get("url")
                    if user_url:
                        u_resp = await client.get(user_url, headers=headers)
                        if u_resp.status_code == 200:
                            u_data = u_resp.json()
                            cross_links = []
                            blog = u_data.get("blog")
                            if blog:
                                if not blog.startswith("http"):
                                    blog = "https://" + blog
                                cross_links.append(blog)

                            results.append({
                                "platform": "GitHub",
                                "username": u_data.get("login"),
                                "display_name": u_data.get("name") or u_data.get("login"),
                                "url": u_data.get("html_url"),
                                "snippet": f"{u_data.get('bio') or ''} | Company: {u_data.get('company') or ''} | Location: {u_data.get('location') or ''}".strip(" |"),
                                "institution": u_data.get("company"),
                                "location": u_data.get("location"),
                                "cross_links": cross_links
                            })
        return results
