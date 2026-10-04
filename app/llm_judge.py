"""
Optional LLM Judge for top candidates.
Uses Anthropic API to evaluate profile identity matching if ANTHROPIC_API_KEY is configured.
Degrades silently if unavailable.
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from app.config import ANTHROPIC_API_KEY

TRY_ANTHROPIC = False
if ANTHROPIC_API_KEY:
    try:
        import anthropic
        TRY_ANTHROPIC = True
    except ImportError:
        TRY_ANTHROPIC = False


async def judge_top_candidates(query: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Evaluates top candidates using Anthropic Claude LLM judge if key is present.
    Blends score: 60% ML model + 40% LLM judge.
    Returns (evaluated_candidates, llm_used_boolean).
    """
    if not ANTHROPIC_API_KEY or not TRY_ANTHROPIC or not candidates:
        return candidates, False

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        top_cands = candidates[:5]

        prompt_payload = {
            "query": query,
            "candidates": [
                {
                    "index": i,
                    "platform": c.get("platform"),
                    "display_name": c.get("display_name"),
                    "username": c.get("username"),
                    "url": c.get("url"),
                    "snippet": c.get("snippet"),
                    "institution": c.get("institution")
                }
                for i, c in enumerate(top_cands)
            ]
        }

        system_prompt = (
            "You are an expert identity resolution analyst for a defensive cybersecurity digital footprint tool. "
            "Evaluate whether each candidate profile belongs to the searched person described in the query.\n"
            "Return valid JSON array of objects with keys:\n"
            "[\n"
            "  {\n"
            "    \"index\": int,\n"
            "    \"same_person_probability\": float (0.0 to 1.0),\n"
            "    \"supporting\": [string],\n"
            "    \"contradicting\": [string],\n"
            "    \"missing\": [string]\n"
            "  }\n"
            "]"
        )

        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": json.dumps(prompt_payload)}
            ]
        )

        resp_text = response.content[0].text.strip()
        # Parse JSON output
        evaluations = json.loads(resp_text)
        eval_dict = {item["index"]: item for item in evaluations if "index" in item}

        for i, cand in enumerate(top_cands):
            if i in eval_dict:
                llm_eval = eval_dict[i]
                llm_prob = float(llm_eval.get("same_person_probability", 0.5))
                ml_conf = cand["confidence_score"] / 100.0

                # Blend: 60% Model + 40% LLM
                blended_prob = (0.60 * ml_conf) + (0.40 * llm_prob)
                new_conf = int(round(blended_prob * 100))
                cand["confidence_score"] = max(5, min(99, new_conf))

                # Update band
                if cand["confidence_score"] >= 80:
                    cand["band"] = "strong"
                elif cand["confidence_score"] >= 50:
                    cand["band"] = "plausible"
                else:
                    cand["band"] = "weak"

                # Append LLM observations to evidence
                if llm_eval.get("supporting"):
                    cand["evidence"]["supporting"].extend(llm_eval["supporting"])
                if llm_eval.get("contradicting"):
                    cand["evidence"]["contradicting"].extend(llm_eval["contradicting"])
                if llm_eval.get("missing"):
                    cand["evidence"]["missing"].extend(llm_eval["missing"])

        return candidates, True

    except Exception as e:
        print(f"LLM Judge warning (degraded silently): {e}")
        return candidates, False
