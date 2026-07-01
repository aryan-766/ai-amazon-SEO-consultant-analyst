import pandas as pd
import numpy as np
import re
from typing import Dict, Any, Tuple

def clean_keyword_text(text: str) -> str:
    """Normalize keyword text: trim whitespace, lowercase, remove redundant spaces."""
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove simple emojis or special characters if any, but keep alphanumeric + spaces
    text = re.sub(r'[^\w\s\-]', '', text)
    return text

def clean_and_normalize_data(
    df: pd.DataFrame,
    keyword_col: str,
    sv_col: str,
    cpr_col: str,
    competitor_cols_map: Dict[str, str]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans the dataframe:
    1. Removes empty keyword rows.
    2. Trims and normalizes keyword text.
    3. Handles null/nan values in search volume and CPR.
    4. Handles competitor ranks (converts to numeric, sets empty/unranked to 101).
    5. Deduplicates by keyword, keeping the one with higher search volume.
    6. Returns cleaned DataFrame and cleaning summary report.
    """
    initial_rows = len(df)
    
    # Copy to avoid modifying original
    df_clean = df.copy()

    # 1. Handle missing keywords
    df_clean = df_clean.dropna(subset=[keyword_col])
    df_clean = df_clean[df_clean[keyword_col].astype(str).str.strip() != ""]
    after_null_kw_removal = len(df_clean)
    null_keywords_removed = initial_rows - after_null_kw_removal

    # 2. Normalize keywords
    df_clean[keyword_col] = df_clean[keyword_col].apply(clean_keyword_text)

    # 3. Handle null/nan in Search Volume and CPR
    df_clean[sv_col] = pd.to_numeric(df_clean[sv_col], errors='coerce').fillna(0).astype(int)
    # Clamp search volume to >= 0
    df_clean[sv_col] = df_clean[sv_col].clip(lower=0)

    df_clean[cpr_col] = pd.to_numeric(df_clean[cpr_col], errors='coerce').fillna(0).astype(int)
    df_clean[cpr_col] = df_clean[cpr_col].clip(lower=0)

    # 4. Handle competitor ranks
    # Competitor ranks are stored as numbers; unranked or missing ranks are mapped to 101 (out of range/unranked)
    for competitor, col in competitor_cols_map.items():
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(101).astype(int)
        # Check that ranks are between 1 and 101
        df_clean[col] = df_clean[col].apply(lambda x: x if 1 <= x <= 101 else 101)

    # 5. Deduplicate keywords
    # Sort by search volume descending, then drop duplicate keywords keeping the first (highest search volume)
    df_clean = df_clean.sort_values(by=sv_col, ascending=False)
    df_clean = df_clean.drop_duplicates(subset=[keyword_col], keep='first')
    after_dedup = len(df_clean)
    duplicates_removed = after_null_kw_removal - after_dedup

    cleaning_report = {
        "initial_rows": initial_rows,
        "null_keywords_removed": null_keywords_removed,
        "duplicates_removed": duplicates_removed,
        "final_rows": after_dedup,
        "search_volume_filled_nan": int(df[sv_col].isna().sum()),
        "cpr_filled_nan": int(df[cpr_col].isna().sum())
    }

    return df_clean, cleaning_report
