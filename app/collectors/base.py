"""
Base Collector Interface & Utilities.
"""
from typing import Dict, Any, List, Optional
import httpx
from app.db import get_cache, set_cache


class BaseCollector:
    name: str = "Base"

    async def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch profiles matching query."""
        raise NotImplementedError

    def get_cache_key(self, query: Dict[str, Any]) -> str:
        name = query.get("name", "").strip().lower()
        college = (query.get("college") or "").strip().lower()
        keywords = "-".join(sorted(query.get("keywords", []))).lower()
        return f"{self.name.lower()}:{name}:{college}:{keywords}"

    async def run(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        cache_key = self.get_cache_key(query)
        cached = get_cache(cache_key)
        if cached is not None and len(cached) > 0:
            return cached

        try:
            results = await self.fetch(query)
            if results:
                set_cache(cache_key, results)
            return results
        except Exception as e:
            print(f"Error running collector {self.name}: {e}")
            return []

