import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

def analyze_competitors(
    df: pd.DataFrame,
    competitor_cols_map: Dict[str, str],
    user_brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes competitor summaries: average rank, keyword coverage, share of voice.
    Identifies strong/weak competitors and keyword overlap.
    """
    summary = {}
    if df.empty or not competitor_cols_map:
        return {"competitors_list": [], "summaries": {}, "matrix": {}}

    competitors = list(competitor_cols_map.keys())
    total_keywords = len(df)
    
    # Initialize competitor metrics
    comp_summaries = {}
    for comp, col in competitor_cols_map.items():
        # Clean ranks (excluding 101 which means unranked)
        ranks = df[col]
        ranked_kws = df[df[col] <= 100]
        top_10 = df[df[col] <= 10]
        top_30 = df[df[col] <= 30]

        avg_rank = float(ranked_kws[col].mean()) if not ranked_kws.empty else 101.0
        coverage = float(len(ranked_kws) / total_keywords * 100) if total_keywords > 0 else 0.0
        
        # Share of Voice (weighted index: higher rank = higher SOV)
        # Formula: Sum of (Search Volume of keyword * Position Weight)
        # Position Weight = 1 / log2(Position + 1)
        weights = 1.0 / np.log2(ranked_kws[col] + 1)
        sov = float((ranked_kws["search_volume"] * weights).sum())

        comp_summaries[comp] = {
            "name": comp,
            "avg_rank": round(avg_rank, 1),
            "coverage_pct": round(coverage, 1),
            "top_10_count": len(top_10),
            "top_30_count": len(top_30),
            "sov": round(sov, 1),
            "status": "Strong" if avg_rank < 30 and coverage > 50 else ("Weak" if avg_rank > 60 or coverage < 20 else "Moderate")
        }

    # Identify market leader
    leader = None
    max_sov = -1
    for comp, metrics in comp_summaries.items():
        if metrics["sov"] > max_sov:
            max_sov = metrics["sov"]
            leader = comp

    # Overlap Matrix: percentage of keywords shared in top 30
    overlap_matrix = {}
    for c1, col1 in competitor_cols_map.items():
        overlap_matrix[c1] = {}
        c1_top_30 = set(df[df[col1] <= 30].index)
        for c2, col2 in competitor_cols_map.items():
            if c1 == c2:
                overlap_matrix[c1][c2] = 100.0
                continue
            c2_top_30 = set(df[df[col2] <= 30].index)
            intersection = c1_top_30.intersection(c2_top_30)
            union = c1_top_30.union(c2_top_30)
            overlap_pct = (len(intersection) / len(union) * 100) if union else 0.0
            overlap_matrix[c1][c2] = round(overlap_pct, 1)

    return {
        "competitors_list": competitors,
        "market_leader": leader,
        "summaries": comp_summaries,
        "overlap_matrix": overlap_matrix
    }

def find_gaps_and_wins(
    df: pd.DataFrame,
    competitor_cols_map: Dict[str, str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filters keywords to find:
    1. Easy Wins: High Search Volume, Low Competition (Competition Score < 50), and Opportunity > 60.
    2. Untapped/Gap Keywords: Competitors ranking in top 20, but the overall average rank is low or user is not indexable.
    """
    # Easy wins:
    # high opportunity, low competition, search volume > 300
    easy_wins_mask = (df["opportunity_score"] >= 60) & (df["competition_score"] <= 55) & (df["search_volume"] >= 300)
    easy_wins = df[easy_wins_mask]

    # Gaps:
    # 2+ competitors rank in the top 20, but gap score is high (indicating opportunity to steal traffic)
    competitor_cols = list(competitor_cols_map.values())
    if competitor_cols:
        comp_in_top_20 = (df[competitor_cols] <= 20).sum(axis=1)
        # Gap is high if competitor coverage is high, but priority score is also high
        gaps_mask = (comp_in_top_20 >= 2) & (df["opportunity_score"] >= 50)
        keyword_gaps = df[gaps_mask]
    else:
        keyword_gaps = pd.DataFrame()

    return easy_wins, keyword_gaps
