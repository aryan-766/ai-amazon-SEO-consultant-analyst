import pandas as pd
import numpy as np
import re
import os
import json
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile

def clean_column_name(col: str) -> str:
    """Normalize column headers to lowercase and strip special characters."""
    return re.sub(r'[^a-z0-9_]', '', str(col).lower().strip().replace(' ', '_'))

def detect_columns(df: pd.DataFrame) -> Tuple[str, str, str, List[str]]:
    """
    Detect core columns and competitor rank columns.
    Returns:
        keyword_col: Column name containing keywords
        sv_col: Column name containing search volume
        cpr_col: Column name for competing products / CPR
        competitor_cols: List of column names representing competitor ranks
    """
    keyword_col = None
    sv_col = None
    cpr_col = None
    competitor_cols = []

    # Cleaned versions of headers for checking
    cleaned_headers = {col: clean_column_name(col) for col in df.columns}

    # 1. Detect Keyword column
    for col, clean in cleaned_headers.items():
        if clean in ['keyword', 'search_phrase', 'phrase', 'keywords', 'search_term', 'query']:
            keyword_col = col
            break
    if not keyword_col:
        # Fallback to first string column or anything containing "keyword" or "phrase"
        for col in df.columns:
            if 'keyword' in str(col).lower() or 'phrase' in str(col).lower():
                keyword_col = col
                break
        if not keyword_col:
            # Last resort: first column
            keyword_col = df.columns[0]

    # 2. Detect Search Volume column
    for col, clean in cleaned_headers.items():
        if clean in ['search_volume', 'volume', 'monthly_search_volume', 'est_monthly_search_volume', 'sv']:
            sv_col = col
            break
    if not sv_col:
        for col in df.columns:
            if 'volume' in str(col).lower() or 'search' in str(col).lower() and 'volume' in str(col).lower():
                sv_col = col
                break

    # 3. Detect Competing Products / CPR
    for col, clean in cleaned_headers.items():
        if clean in ['competing_products', 'competing_product_count', 'cpr', 'cpr_8day_search_volume', 'cerebro_product_rank']:
            cpr_col = col
            break
    if not cpr_col:
        for col in df.columns:
            if 'competing' in str(col).lower() or 'cpr' in str(col).lower():
                cpr_col = col
                break

    # 4. Detect Competitor Rank columns (Helium 10 style: B0XXXXXXXX - Position (Rank) or similar)
    for col in df.columns:
        col_lower = str(col).lower()
        # Look for ASIN-like pattern or "position (rank)" or "rank" for specific products
        # But exclude the main product rank column (e.g. "organic rank", "position")
        is_competitor = False
        
        # Check if it has an ASIN format: B0 followed by 8 alphanumeric chars
        asin_match = re.search(r'\b(b0[a-z0-9]{8})\b', col_lower)
        
        # Or if it contains "position (rank)" and has a brand/ASIN prefix
        if 'position' in col_lower and 'rank' in col_lower:
            # Make sure it's not the main overall rank column
            if not any(x in col_lower for x in ['search rank', 'main rank', 'organic rank', 'your rank']):
                is_competitor = True
        elif asin_match:
            is_competitor = True
            
        if is_competitor and col != keyword_col and col != sv_col and col != cpr_col:
            competitor_cols.append(col)

    return keyword_col, sv_col, cpr_col, competitor_cols

def parse_and_validate_file(file_path: str) -> Dict[str, Any]:
    """
    Loads Excel or CSV file, identifies layout, normalizes it, and returns data + summary.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read file: {str(e)}")

    if df.empty:
        raise ValueError("The uploaded file is empty.")

    keyword_col, sv_col, cpr_col, competitor_cols = detect_columns(df)

    if not keyword_col:
        raise ValueError("Could not find a valid Keyword column in the file.")

    # Standardize basic columns
    df_clean = df.copy()
    
    # Keyword: convert to string, strip
    df_clean[keyword_col] = df_clean[keyword_col].astype(str).str.strip()
    
    # Search Volume: convert to numeric, handle NaNs
    if sv_col:
        df_clean[sv_col] = pd.to_numeric(df_clean[sv_col], errors='coerce').fillna(0).astype(int)
    else:
        # If no search volume found, set default 0
        sv_col = 'Search Volume'
        df_clean[sv_col] = 0

    # CPR/Competing products: convert to numeric
    if cpr_col:
        df_clean[cpr_col] = pd.to_numeric(df_clean[cpr_col], errors='coerce').fillna(0).astype(int)
    else:
        cpr_col = 'Competing Products'
        df_clean[cpr_col] = 0

    # Extract competitor information
    competitor_names = []
    for col in competitor_cols:
        # Extract ASIN or Brand name from column title
        asin_match = re.search(r'\b(b0[a-z0-9]{8})\b', col, re.IGNORECASE)
        if asin_match:
            brand_id = asin_match.group(1).upper()
        else:
            # Clean column name to get brand/identifying token
            brand_id = col.replace("Position (Rank)", "").replace("-", "").strip()
            if not brand_id:
                brand_id = col
        competitor_names.append(brand_id)

    # Preview first 15 rows (convert NaNs to None for JSON compatibility)
    preview_df = df_clean.head(15).replace({np.nan: None})
    preview_data = preview_df.to_dict(orient='records')

    summary = {
        "total_rows": len(df_clean),
        "columns_detected": list(df.columns),
        "keyword_column": keyword_col,
        "search_volume_column": sv_col,
        "competing_products_column": cpr_col,
        "competitors_found": competitor_names,
        "competitor_columns_map": {competitor_names[i]: competitor_cols[i] for i in range(len(competitor_cols))}
    }

    return {
        "dataframe": df_clean,
        "summary": summary,
        "preview": preview_data
    }
