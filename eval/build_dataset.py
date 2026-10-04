"""
Collector Coverage Measurement Script.
Reads eval/volunteers.csv, runs live collectors for each volunteer profile,
and outputs profile coverage statistics.
"""
import asyncio
import csv
from pathlib import Path
from app.config import BASE_DIR
from app.parser import parse_query
from app.collectors.github import GitHubCollector
from app.collectors.scholar import ScholarCollector
from app.collectors.orcid import ORCIDCollector
from app.collectors.search_api import SearchAPICollector


async def build_and_evaluate_coverage():
    csv_path = BASE_DIR / "eval" / "volunteers.csv"
    if not csv_path.exists():
        print(f"File {csv_path} not found.")
        return

    collectors = [
        GitHubCollector(),
        ScholarCollector(),
        ORCIDCollector(),
        SearchAPICollector()
    ]

    total_true_profiles = 0
    found_true_profiles = 0

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip()
            college = row["college"].strip()
            keywords = [k.strip() for k in row["keywords"].split("|") if k.strip()]
            true_urls = [u.strip().rstrip("/").lower() for u in row["true_urls"].split("|") if u.strip()]

            total_true_profiles += len(true_urls)

            parsed_q = {
                "name": name,
                "college": college,
                "keywords": keywords
            }

            print(f"Evaluating coverage for volunteer: {name} ({college})...")
            tasks = [col.run(parsed_q) for col in collectors]
            results_nested = await asyncio.gather(*tasks, return_exceptions=True)

            discovered_urls = set()
            for res in results_nested:
                if isinstance(res, list):
                    for item in res:
                        u = item.get("url", "").strip().rstrip("/").lower()
                        if u:
                            discovered_urls.add(u)

            for target_url in true_urls:
                if target_url in discovered_urls or any(target_url in d or d in target_url for d in discovered_urls):
                    found_true_profiles += 1

    coverage_pct = (found_true_profiles / total_true_profiles * 100) if total_true_profiles > 0 else 0
    print("==================================================")
    print(f"Total Target Profiles Specified : {total_true_profiles}")
    print(f"Total Target Profiles Discovered: {found_true_profiles}")
    print(f"Collector Profile Coverage Rate : {coverage_pct:.2f}%")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(build_and_evaluate_coverage())
