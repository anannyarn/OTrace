"""
Exposure Report Generator for OTrace.
Calculates overall exposure score (0-100), attacker intelligence synthesis,
and platform-specific privacy remediation steps.
"""
from typing import Dict, Any, List


def calculate_exposure_report(query: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes exposure score and risk insights based on strong (>=80%) and plausible (>=50%) matches.
    """
    valid_matches = [r for r in results if r.get("confidence_score", 0) >= 50]
    strong_matches = [r for r in results if r.get("confidence_score", 0) >= 80]

    if not valid_matches:
        return {
            "exposure_score": 10,
            "risk_level": "Low",
            "platforms_found": 0,
            "reused_usernames": [],
            "attacker_insights": [
                "Minimal public profile footprint found across monitored platforms."
            ],
            "recommendations": [
                {
                    "title": "Maintain Good Privacy Hygiene",
                    "platform": "General",
                    "impact": "Low",
                    "action": "Periodically audit your public search results to ensure no unintended personal details leak."
                }
            ]
        }

    platforms = list({m["platform"] for m in valid_matches})
    
    # Check handle reuse
    handles = [m["username"].lower() for m in valid_matches if m.get("username")]
    handle_counts = {}
    for h in handles:
        handle_counts[h] = handle_counts.get(h, 0) + 1
    reused_handles = [h for h, count in handle_counts.items() if count > 1]

    # Calculate exposure score components
    base_score = min(40, len(valid_matches) * 10)
    strong_bonus = min(30, len(strong_matches) * 15)
    reuse_bonus = min(20, len(reused_handles) * 10)

    # Public detail exposure
    has_institution = any(m.get("institution") for m in valid_matches) or bool(query.get("college"))
    detail_bonus = 10 if has_institution else 0

    total_exposure = min(100, base_score + strong_bonus + reuse_bonus + detail_bonus)

    risk_level = "Low"
    if total_exposure >= 75:
        risk_level = "High"
    elif total_exposure >= 45:
        risk_level = "Moderate"

    # Attacker intelligence insights
    insights = []
    if reused_handles:
        insights.append(
            f"Username Reuse Risk: Reusing handle(s) '{', '.join(reused_handles)}' across multiple platforms ({', '.join(platforms)}) makes cross-platform tracking effortless for attackers."
        )

    if "LinkedIn" in platforms and has_institution:
        insights.append(
            "Corporate Pretexting: Public employment details on LinkedIn combined with college history enable highly tailored spear-phishing or recruiter pretexting."
        )

    if "GitHub" in platforms and ("Instagram" in platforms or "X/Twitter" in platforms):
        insights.append(
            "Developer Identity Correlation: GitHub code activity combined with personal social profiles links technical projects directly to private social persona."
        )

    if query.get("keywords"):
        insights.append(
            f"Contextual Correlation: Search keywords ({', '.join(query['keywords'])}) matched across public snippets, allowing attackers to construct a timeline of your career & location."
        )

    if not insights:
        insights.append("Public profiles expose basic personal identity indicators that can be aggregated across search engines.")

    # Recommendations
    recs = []
    if reused_handles:
        recs.append({
            "title": "Decouple Reused Usernames",
            "platform": "Multi-platform",
            "impact": "High",
            "action": "Change usernames on personal/social accounts so they do not mirror your professional GitHub or LinkedIn handles."
        })

    if "LinkedIn" in platforms:
        recs.append({
            "title": "Restrict LinkedIn Public Visibility",
            "platform": "LinkedIn",
            "impact": "High",
            "action": "Go to Settings & Privacy > Edit your public profile > Limit off-site visibility for last name, connections, and detailed work history."
        })

    if "Instagram" in platforms or "Facebook" in platforms:
        recs.append({
            "title": "Set Personal Social Accounts to Private",
            "platform": "Social Media",
            "impact": "Medium",
            "action": "Switch Instagram/Facebook profile privacy settings to Private to prevent open-web search indexers from scraping profile titles."
        })

    if "GitHub" in platforms:
        recs.append({
            "title": "Sanitize Public GitHub Emails & Bios",
            "platform": "GitHub",
            "impact": "Medium",
            "action": "Enable 'Keep my email addresses private' in GitHub settings and use noreply commit email addresses."
        })

    recs.append({
        "title": "Opt-out from Search Engine Indices",
        "platform": "Search Engines",
        "impact": "Medium",
        "action": "Submit URL removal requests to Google & Bing Search Console for outdated cached profile pages."
    })

    return {
        "exposure_score": total_exposure,
        "risk_level": risk_level,
        "platforms_found": len(platforms),
        "reused_usernames": reused_handles,
        "attacker_insights": insights,
        "recommendations": recs
    }
