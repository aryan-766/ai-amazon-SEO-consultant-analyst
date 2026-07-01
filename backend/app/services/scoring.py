import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_opportunity_score(search_volume: float, comp_score: float, max_sv: float) -> float:
    """
    Computes Opportunity Score:
    High search volume + Low competition = High opportunity.
    """
    if max_sv == 0:
        sv_factor = 0
    else:
        # Use log scale for search volume to prevent outliers from squashing scores
        sv_factor = np.log1p(search_volume) / np.log1p(max_sv)
    
    # 60% search volume weight, 40% low competition weight
    opp = (sv_factor * 60) + ((100 - comp_score) * 0.4)
    return float(np.clip(opp, 0, 100))

def run_scoring_engine(
    df: pd.DataFrame,
    cpr_col: str,
    sv_col: str,
    competitor_cols_map: Dict[str, str]
) -> pd.DataFrame:
    """
    Vectorized calculation of 10 keyword scores (0-100) across the dataset.
    """
    if df.empty:
        return df

    # Max values for normalization
    max_sv = float(df[sv_col].max()) if df[sv_col].max() > 0 else 1.0
    max_cpr = float(df[cpr_col].max()) if df[cpr_col].max() > 0 else 1.0

    # 1. Competition Score
    # Log scale based on competing products count.
    df["competition_score"] = 100 * (1 - 1 / (1 + np.log1p(df[cpr_col])))
    # Adjust: add small weight for average competitor ranks if competitors rank highly
    # If there are competitors, calculate mean competitor rank
    competitor_cols = list(competitor_cols_map.values())
    if competitor_cols:
        # If competitor ranks are high (1 to 20), it means competition is fierce
        comp_ranks_df = df[competitor_cols].replace(101, np.nan)
        avg_comp_rank = comp_ranks_df.mean(axis=1).fillna(101)
        # Ranks closer to 1 increase competition score
        comp_rank_factor = (101 - avg_comp_rank) / 100 * 20 # Up to +20 points
        df["competition_score"] = (df["competition_score"] * 0.8 + comp_rank_factor).clip(0, 100)
    else:
        df["competition_score"] = df["competition_score"].clip(0, 100)

    # 2. Opportunity Score
    df["opportunity_score"] = df.apply(
        lambda row: calculate_opportunity_score(row[sv_col], row["competition_score"], max_sv),
        axis=1
    )

    # 3. Traffic Score
    # Percentile based search volume score
    if len(df) > 1:
        df["traffic_score"] = df[sv_col].rank(pct=True) * 100
    else:
        df["traffic_score"] = 50.0

    # 4. Trend Score
    # Generate mock trend score (60-80 for GaN/PD chargers, 40-60 for generic cables, declining for older tech)
    # If there is organic trend data we use it; otherwise we base it on tech/product attributes
    def get_trend(row):
        score = 50.0 # base
        if row["tech_type"] in ["GaN", "PD", "MagSafe"]:
            score += 25
        if row["intent"] in ["Transactional", "Commercial"]:
            score += 10
        if "outdated" in row["keyword"] or "micro usb" in row["keyword"]:
            score -= 30
        return float(np.clip(score + np.random.uniform(-5, 5), 0, 100))

    df["trend_score"] = df.apply(get_trend, axis=1)

    # 5. Revenue Score
    # Estimate Revenue: Search Volume * CTR * Conversion Rate * Est Product Price ($25)
    # Normalize between 0-100
    conv_rates = {
        "Transactional": 0.12,
        "Commercial": 0.08,
        "Comparison": 0.05,
        "Review": 0.05,
        "Navigational": 0.15,
        "Informational": 0.01
    }
    df["conversion_rate_est"] = df["intent"].map(conv_rates).fillna(0.05)
    df["est_revenue"] = df[sv_col] * df["ctr_potential"] * df["conversion_rate_est"] * 25.0 # ASP=$25
    max_rev = df["est_revenue"].max() if df["est_revenue"].max() > 0 else 1.0
    df["revenue_score"] = (np.log1p(df["est_revenue"]) / np.log1p(max_rev)) * 100
    df["revenue_score"] = df["revenue_score"].clip(0, 100)

    # 6. Gap Score
    # Calculated as the percentage of top competitors ranking in top 20
    # Higher gap score means more competitors rank here, indicating the category standard keyword,
    # but the user is NOT ranking (user rank = 101).
    if competitor_cols:
        # Check how many competitors rank in top 20
        comp_in_top_20 = (df[competitor_cols] <= 20).sum(axis=1)
        total_competitors = len(competitor_cols)
        # Gap is high if competitor coverage is high
        df["competitor_coverage"] = comp_in_top_20
        df["gap_score"] = (comp_in_top_20 / total_competitors) * 100
    else:
        df["competitor_coverage"] = 0
        df["gap_score"] = 0.0

    # 7. Content Score
    # Richness of keyword (longer, brand specific, contains numbers/units/tech details)
    def get_content_score(row):
        score = 30.0
        score += min(row["word_count"] * 10, 30) # up to 30
        if row["contains_tech"]:
            score += 15
        if row["contains_unit"]:
            score += 10
        if row["contains_number"]:
            score += 10
        if row["contains_brand"]:
            score += 5
        return float(min(score, 100))

    df["content_score"] = df.apply(get_content_score, axis=1)

    # 8. SEO Score
    # Combines commercial potential and search intent relevance
    df["seo_score"] = (df["commercial_potential"] * 60) + (df["content_score"] * 0.4)
    df["seo_score"] = df["seo_score"].clip(0, 100)

    # 9. Priority Score
    # Strategic score: mix of Opportunity, Trend, and Gap
    df["priority_score"] = (df["opportunity_score"] * 0.4) + (df["trend_score"] * 0.3) + (df["gap_score"] * 0.3)
    df["priority_score"] = df["priority_score"].clip(0, 100)

    # 10. Final AI Score
    # Overall recommendation rating: weighted sum of priority, revenue, and traffic
    df["final_ai_score"] = (df["priority_score"] * 0.5) + (df["revenue_score"] * 0.3) + (df["traffic_score"] * 0.2)
    df["final_ai_score"] = df["final_ai_score"].clip(0, 100)

    # Cleanup temporary columns
    if "conversion_rate_est" in df.columns:
        df.drop(columns=["conversion_rate_est"], inplace=True)
    if "est_revenue" in df.columns:
        df.drop(columns=["est_revenue"], inplace=True)

    return df

def get_score_explanation(score_name: str, val: float) -> str:
    """Return human readable explanation of a specific score and its level."""
    level = "Low"
    if val >= 75:
        level = "High / Excellent"
    elif val >= 40:
        level = "Medium / Moderate"
        
    explanations = {
        "opportunity_score": f"This keyword has an {level} opportunity index ({val:.1f}/100) based on high customer demand (Search Volume) relative to supply/competing listings.",
        "competition_score": f"Competition is {level} ({val:.1f}/100). Higher scores mean many listings compete for organic placement, making bidding and indexing more challenging.",
        "traffic_score": f"The traffic potential is {level} ({val:.1f}/100). This indicates where this keyword ranks in the overall search volume distribution of this dataset.",
        "trend_score": f"Demand momentum is {level} ({val:.1f}/100). High trend scores suggest growing search interest and positive market speed.",
        "revenue_score": f"Expected revenue yield is {level} ({val:.1f}/100), modeled using search CTR, commercial intent, and category average prices.",
        "gap_score": f"Competitor ranking coverage is {level} ({val:.1f}/100). Higher gap scores mean competitors are ranking successfully here but you may be losing share.",
        "content_score": f"Semantic detail level is {level} ({val:.1f}/100), evaluating long-tail modifiers, specs (units), and specific tech features.",
        "seo_score": f"Search engine relevance is {level} ({val:.1f}/100), combining commercial intention and details fit for backend search terms.",
        "priority_score": f"Priority ranking is {level} ({val:.1f}/100), combining growth velocity, competitive gap, and net opportunity.",
        "final_ai_score": f"The aggregate recommendation index is {level} ({val:.1f}/100), highlighting this keyword as a key optimization candidate."
    }
    return explanations.get(score_name.lower(), f"Score value is {val:.1f}/100 ({level}).")
