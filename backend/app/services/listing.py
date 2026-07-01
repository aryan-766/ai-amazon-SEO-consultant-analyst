import re
import json
import httpx
from typing import List, Dict, Any, Tuple
from backend.app.core.config import settings

def analyze_listing_keywords(
    title: str,
    bullets: List[str],
    description: str,
    search_terms: str,
    target_keywords: List[str]
) -> Dict[str, Any]:
    """
    Analyzes which target keywords are included in the listing,
    calculates an SEO listing score (0-100) and returns recommendations.
    """
    title_clean = title.lower()
    bullets_clean = " ".join(bullets).lower()
    description_clean = description.lower()
    search_terms_clean = search_terms.lower()
    
    matches = {}
    used_keywords = []
    unused_keywords = []
    
    # Matching logic: case-insensitive word matching
    for kw in target_keywords:
        kw_lower = kw.lower()
        # Escaping regex characters just in case
        pattern = re.compile(r'\b' + re.escape(kw_lower) + r'\b')
        
        in_title = bool(pattern.search(title_clean))
        in_bullets = bool(pattern.search(bullets_clean))
        in_desc = bool(pattern.search(description_clean))
        in_terms = bool(pattern.search(search_terms_clean))
        
        is_matched = in_title or in_bullets or in_desc or in_terms
        matches[kw] = {
            "matched": is_matched,
            "in_title": in_title,
            "in_bullets": in_bullets,
            "in_description": in_desc,
            "in_search_terms": in_terms
        }
        
        if is_matched:
            used_keywords.append(kw)
        else:
            unused_keywords.append(kw)

    # Score calculation algorithm
    # Weights: Title matches (40%), Bullets matches (35%), Description (15%), Search Terms (10%)
    if not target_keywords:
        score = 100
    else:
        title_score = sum(1 for kw in target_keywords if matches[kw]["in_title"]) / len(target_keywords) * 100
        bullets_score = sum(1 for kw in target_keywords if matches[kw]["in_bullets"]) / len(target_keywords) * 100
        desc_score = sum(1 for kw in target_keywords if matches[kw]["in_description"]) / len(target_keywords) * 100
        terms_score = sum(1 for kw in target_keywords if matches[kw]["in_search_terms"]) / len(target_keywords) * 100
        
        score = int((title_score * 0.40) + (bullets_score * 0.35) + (desc_score * 0.15) + (terms_score * 0.10))

    # Dynamic suggestions
    suggestions = []
    if title_score < 40:
        suggestions.append("Critical: Include more high-opportunity keywords in your Title for maximum index indexing weight.")
    if bullets_score < 50:
        suggestions.append("Improvement: Spread key search volume phrases across all 5 Bullet Points, using capitalization for headers.")
    if desc_score < 30:
        suggestions.append("Recommendation: Integrate long-tail informational keywords in your Product Description to capture comparison search queries.")
    if terms_score < 30:
        suggestions.append("Tip: Populate Backend Search Terms with unused keywords to index without cluttering the customer-facing copy.")
        
    if score >= 85:
        suggestions.append("Listing is highly optimized! Ready to publish on Amazon.")
    elif score >= 60:
        suggestions.append("Listing has solid optimization, but adding 2-3 more target keywords will improve ranking breadth.")
        
    return {
        "score": score,
        "matches": {k: v["matched"] for k, v in matches.items()},
        "matches_detail": matches,
        "used_keywords": used_keywords,
        "unused_keywords": unused_keywords,
        "suggestions": suggestions
    }

async def generate_optimized_listing_llm(
    target_keywords: List[str],
    product_type: str = "Accessory"
) -> Dict[str, Any]:
    """
    Calls local Ollama instance running Qwen2.5 7B to write highly optimized listing copy.
    Falls back to high quality rule-based templates if Ollama is unreachable.
    """
    keyword_list_str = ", ".join(target_keywords[:10])
    
    prompt = (
        f"You are an expert Amazon Listing Copywriter and SEO Specialist.\n"
        f"Generate a highly optimized, compelling Amazon Product Listing in JSON format for a product of category '{product_type}'.\n"
        f"You MUST weave in these exact target keywords: {keyword_list_str}.\n"
        f"Write listing elements conforming to Amazon character rules:\n"
        f"- Title (under 200 characters): Use capitalization, separate features with dashes or pipes.\n"
        f"- Bullet Points (5 bullets, each under 250 characters): Start each bullet with a bold capitalized feature summary.\n"
        f"- Description (under 2000 characters): Detailed HTML-formatted story focusing on benefit, specs, and package list.\n"
        f"- Backend Search Terms (under 249 bytes, space-separated, no punctuation).\n"
        f"- A+ Content Ideas (list of 3 section ideas with titles and image descriptions).\n"
        f"- FAQ (3 questions and answers based on user concerns).\n\n"
        f"Response MUST be a valid JSON matching this schema:\n"
        f"{{\n"
        f"  \"title\": \"string\",\n"
        f"  \"bullet_points\": [\"bullet 1\", \"bullet 2\", \"bullet 3\", \"bullet 4\", \"bullet 5\"],\n"
        f"  \"description\": \"string\",\n"
        f"  \"search_terms\": \"string\",\n"
        f"  \"aplus_content_ideas\": [{{\"section\": \"string\", \"concept\": \"string\"}}],\n"
        f"  \"faq\": [{{\"question\": \"string\", \"answer\": \"string\"}}]\n"
        f"}}\n"
        f"Do not write any markdown wrappers (like ```json) or chat intros. Output raw JSON only."
    )
    
    try:
        # Request local Ollama api
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4
                    }
                }
            )
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                # Clean up any potential markdown formatting the model added
                if text.startswith("```"):
                    text = re.sub(r'^```(json)?\n|```$', '', text, flags=re.MULTILINE).strip()
                
                parsed_json = json.loads(text)
                return parsed_json
    except Exception as e:
        print(f"Ollama generation failed or timed out: {e}. Utilizing fallback template generator.")
        
    # Return high-quality rule-based fallback templates
    primary_kw = target_keywords[0].title() if target_keywords else "Premium Device"
    other_kws = target_keywords[1:5] if len(target_keywords) > 1 else ["durable", "high performance"]
    kws_str = ", ".join(other_kws)
    
    fallback = {
        "title": f"Professional {primary_kw} - Optimized for High Performance & Speed - Compatible with {kws_str.title()}",
        "bullet_points": [
            f"MAXIMUM PERFORMANCE: Specially designed to match {primary_kw} standards, providing rapid and consistent operation.",
            f"UNIVERSAL CONNECTIVITY: Optimizes device speeds across multiple platforms, incorporating key {kws_str} compatibility features.",
            "PREMIUM DURABILITY: Constructed using military-grade reinforced shielding to withstand daily wear and tear.",
            "ADVANCED SMART CHIPSET: Monitors thermal limits dynamically to safeguard your valuable hardware assets.",
            "SLIM COMPACT DESIGN: Elegant and lightweight form factor makes it perfect for business travel and daily commutes."
        ],
        "description": f"<h3>Next-Generation {primary_kw} Solution</h3><p>Take control of your workflow with our advanced {primary_kw} accessory. Crafted to address core customer demands, this item includes integrated {kws_str} elements that maximize speed and durability.</p><p>Package includes: 1x {primary_kw}, User manual, and 12-month worry-free warranty support.</p>",
        "search_terms": " ".join(target_keywords[:8]).lower(),
        "aplus_content_ideas": [
            {"section": "Header Banner", "concept": "Hero graphic of the product highlighting the compact design and premium materials."},
            {"section": "Feature Grid", "concept": "3-column diagram layout depicting high performance specs, compatibility list, and safety certifications."},
            {"section": "Lifestyle Use", "concept": "Image carousel showcasing use on a clean office desk and during active travel."}
        ],
        "faq": [
            {"question": "Is this product compatible with fast charging?", "answer": f"Yes, it supports quick speed standards matching {primary_kw} and other {kws_str} profiles."},
            {"question": "What is the warranty period?", "answer": "The item comes with a 1-year replacement warranty coverage for peace of mind."},
            {"question": "Where are the backend search terms used?", "answer": "They are indexed in the Amazon catalog to ensure searchability without cluttering client-facing listing pages."}
        ]
    }
    return fallback
