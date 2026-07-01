import pandas as pd
import numpy as np
import re
import os
import json
from typing import List, Dict, Any, Tuple, Optional

# Attempt to import machine learning and embedding libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    ML_LIBS_AVAILABLE = True
except ImportError:
    ML_LIBS_AVAILABLE = False
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

# Pre-defined lexicons for categories and technology
PRODUCT_LEXICON = {
    "Power Bank": [r"power\s*bank", r"portable\s*charger", r"external\s*battery", r"battery\s*pack", r"powerbank"],
    "Cable": [r"cable", r"cord", r"wire", r"charger\s*cable", r"charging\s*cable", r"usb\s*cable"],
    "Charger": [r"charger", r"wall\s*charger", r"charging\s*block", r"charging\s*brick", r"multi\s*port\s*charger"],
    "Adapter": [r"adapter", r"convertor", r"car\s*adapter", r"headphone\s*adapter"],
    "Earbuds": [r"earbuds", r"earphone", r"headphone", r"tws", r"airpods"],
    "Neckband": [r"neckband", r"collar\s*earphone"],
    "Watch": [r"watch", r"smartwatch", r"fitness\s*band", r"fitness\s*tracker"],
}

TECH_LEXICON = {
    "GaN": [r"\bgan\b", r"gallium\s*nitride"],
    "PD": [r"\bpd\b", r"power\s*delivery", r"pd\s*3\.0"],
    "QC": [r"\bqc\b", r"quick\s*charge", r"qc\s*3\.0", r"qc\s*4\.0"],
    "USB C": [r"usb\s*c", r"type\s*c", r"usbc"],
    "Lightning": [r"lightning", r"apple\s*cable", r"iphone\s*cable"],
    "Wireless": [r"wireless", r"inductive", r"qi\s*charging", r"qi"],
    "Fast Charging": [r"fast\s*charg", r"quick\s*charg", r"speedy\s*charg", r"ultra\s*fast"],
    "MagSafe": [r"magsafe", r"magnetic\s*charg", r"mag\s*safe"],
}

INTENT_LEXICON = {
    "Transactional": [r"\bbuy\b", r"\bprice\b", r"\bshop\b", r"\border\b", r"\bsale\b", r"\bcheap\b", r"\bonline\b", r"\bpack\b", r"\bset\b", r"\bunder\b", r"\bdeals\b"],
    "Commercial": [r"\bbest\b", r"\btop\b", r"\bpremium\b", r"\bpro\b", r"\bquality\b", r"\bfastest\b", r"\bheavy\s*duty\b", r"\bhigh\s*speed\b"],
    "Informational": [r"\bhow\b", r"\bwhat\b", r"\bguide\b", r"\btutorial\b", r"\binstructions\b", r"\bcompatibility\b", r"\bwhy\b", r"\bhelp\b", r"\bexplain\b"],
    "Comparison": [r"\bvs\b", r"\bcompare\b", r"\bdifference\b", r"\bor\b", r"\bversus\b", r"\bcomparison\b"],
    "Review": [r"\breview\b", r"\breviews\b", r"\brating\b", r"\bratings\b", r"\btest\b", r"\brecommendation\b", r"\bworth\b"],
}

BUYING_MODIFIERS = [r"buy", r"price", r"cheap", r"sale", r"discount", r"coupon", r"online"]
COMPARISON_MODIFIERS = [r"vs", r"compare", r"comparison", r"versus", r"or", r"difference", r"against"]
REVIEW_MODIFIERS = [r"review", r"reviews", r"rating", r"ratings", r"good", r"bad", r"test", r"feedback"]
PRICE_MODIFIERS = [r"price", r"cost", r"dollar", r"usd", r"under", r"cheap", r"expensive", r"value"]
QUESTION_MODIFIERS = [r"how", r"what", r"why", r"where", r"when", r"who", r"can", r"is", r"does"]

# Cache for embedding model
_embedding_model = None

def get_embedding_model():
    """Retrieve or load sentence transformer model locally."""
    global _embedding_model
    if _embedding_model is None and ML_LIBS_AVAILABLE:
        try:
            # We use bge-small-en-v1.5 as requested
            _embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        except Exception as e:
            print(f"Error loading SentenceTransformer: {e}. Falling back to TF-IDF.")
            _embedding_model = None
    return _embedding_model

def detect_regex_list(text: str, regex_list: List[str]) -> bool:
    """Helper to check if any regex in a list matches the text."""
    for pattern in regex_list:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def extract_features_for_row(
    keyword: str,
    user_brand: str,
    competitors: List[str]
) -> Dict[str, Any]:
    """Extract all text features, types, intent, and buying stages for a single keyword."""
    kw_lower = keyword.lower()
    
    # 1. Basic length stats
    word_count = len(kw_lower.split())
    char_count = len(kw_lower)
    
    # 2. Key boolean checks
    contains_number = bool(re.search(r'\d', kw_lower))
    
    # Unit detection (e.g. 20w, 10000mah, 6ft, 3a)
    contains_unit = detect_regex_list(kw_lower, [
        r'\b\d+w\b', r'\b\d+\s*mah\b', r'\b\d+\s*ft\b', r'\b\d+\s*v\b', 
        r'\b\d+\s*m\b', r'\b\d+\s*cm\b', r'\b\d+\s*in\b', r'\b\d+\s*amp\b', 
        r'\b\d+\s*a\b', r'\busb\b', r'\btype\b'
    ])
    
    # Brand checks
    brand_found = None
    brand_type = "Generic"
    
    # Check for user brand
    if user_brand.lower() in kw_lower:
        brand_found = user_brand
        brand_type = "Branded"
    else:
        # Check for competitors
        for comp in competitors:
            if comp.lower() in kw_lower:
                brand_found = comp
                brand_type = "Competitor Branded"
                break
                
    contains_brand = brand_found is not None
    
    # Tech check
    contains_tech = False
    tech_type = "Other"
    for tech, patterns in TECH_LEXICON.items():
        if detect_regex_list(kw_lower, patterns):
            contains_tech = True
            tech_type = tech
            break
            
    # Product check
    product_type = "Accessory"
    for prod, patterns in PRODUCT_LEXICON.items():
        if detect_regex_list(kw_lower, patterns):
            product_type = prod
            break
            
    # Intent Detection
    intent = "Informational"  # default
    for int_type, patterns in INTENT_LEXICON.items():
        if detect_regex_list(kw_lower, patterns):
            intent = int_type
            break
            
    # If a brand is found and no commercial/transactional modifier is found, it's Navigational
    if contains_brand and intent == "Informational":
        intent = "Navigational"
        
    # Buyer Stage
    buyer_stage = "Awareness"
    if intent == "Informational":
        buyer_stage = "Awareness"
    elif intent == "Commercial":
        buyer_stage = "Interest"
    elif intent == "Comparison" or intent == "Review":
        buyer_stage = "Comparison"
    elif intent == "Transactional":
        buyer_stage = "Purchase"
    elif contains_brand:
        buyer_stage = "Comparison" # Default for navigational brand queries

    # Special check for retention terms (e.g. warranty, replacement)
    if detect_regex_list(kw_lower, [r"replacement", r"warranty", r"fix", r"repair", r"spare", r"broken"]):
        buyer_stage = "Retention"

    return {
        "word_count": word_count,
        "char_count": char_count,
        "contains_number": contains_number,
        "contains_unit": contains_unit,
        "contains_brand": contains_brand,
        "contains_tech": contains_tech,
        "brand_name": brand_found,
        "brand_type": brand_type,
        "product_type": product_type,
        "tech_type": tech_type if contains_tech else None,
        "intent": intent,
        "buyer_stage": buyer_stage
    }

def cluster_keywords(
    keywords: List[str],
    n_clusters: int = 15
) -> Tuple[List[int], List[str]]:
    """
    Cluster a list of keywords semantically.
    Returns:
        cluster_ids: list of integer cluster ids
        cluster_names: list of names mapped to cluster ids
    """
    if not keywords:
        return [], []
        
    n_samples = len(keywords)
    n_clusters = min(n_clusters, n_samples)
    if n_clusters < 1:
        n_clusters = 1

    model = get_embedding_model()
    
    if ML_LIBS_AVAILABLE and model is not None:
        try:
            # Generate embeddings
            embeddings = model.encode(keywords, show_progress_bar=False)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_ids = kmeans.fit_predict(embeddings).tolist()
        except Exception as e:
            print(f"Semantic clustering failed, falling back to TF-IDF. Error: {e}")
            # Fallback to TFIDF
            vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
            X = vectorizer.fit_transform(keywords)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_ids = kmeans.fit_predict(X).tolist()
    else:
        # Fallback to TF-IDF vectorizer + KMeans
        try:
            vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
            X = vectorizer.fit_transform(keywords)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_ids = kmeans.fit_predict(X).tolist()
        except Exception:
            # Absolute fallback: uniform division if anything goes wrong
            cluster_ids = [i % n_clusters for i in range(len(keywords))]

    # Generate cluster names based on the most frequent keyword / representative term in the cluster
    cluster_keywords_map = {i: [] for i in range(n_clusters)}
    for idx, cid in enumerate(cluster_ids):
        cluster_keywords_map[cid].append(keywords[idx])

    cluster_names = {}
    for cid, kws in cluster_keywords_map.items():
        if not kws:
            cluster_names[cid] = f"Cluster {cid}"
            continue
        # Find the shortest keyword to represent the cluster or the most search-volume-heavy (heuristically)
        # Here we just select the shortest word count keyword (which represents the core topic)
        shortest_kw = min(kws, key=lambda x: len(x.split()))
        cluster_names[cid] = shortest_kw.title()

    cluster_name_list = [cluster_names[cid] for cid in cluster_ids]
    return cluster_ids, cluster_name_list

def run_feature_engineering(
    df: pd.DataFrame,
    keyword_col: str,
    user_brand: str,
    competitors: List[str]
) -> pd.DataFrame:
    """
    Applies feature engineering across the entire dataframe.
    """
    # 1. Row-wise NLP features
    nlp_features = []
    for kw in df[keyword_col]:
        nlp_features.append(extract_features_for_row(kw, user_brand, competitors))
    
    df_features = pd.DataFrame(nlp_features)
    
    # Combine original df with engineered features
    for col in df_features.columns:
        df[col] = df_features[col].values

    # 2. Cluster keywords semantically
    keywords_list = df[keyword_col].tolist()
    # Dynamic target clusters: ~1 cluster per 15 keywords, bounded between 5 and 30
    target_clusters = max(5, min(30, len(keywords_list) // 15))
    cluster_ids, cluster_names = cluster_keywords(keywords_list, n_clusters=target_clusters)
    
    df["keyword_cluster_id"] = cluster_ids
    df["topic_cluster"] = cluster_names

    # 3. Traffic potentials (CTR approximations based on standard SERP CTR)
    # CTR is higher if listing optimizer score or opportunity is high; initially, CTR is estimated
    # between 1% and 10% based on whether it is Commercial/Transactional (high CTR potential)
    intent_ctr_map = {
        "Transactional": 0.08,
        "Commercial": 0.06,
        "Navigational": 0.12,
        "Comparison": 0.04,
        "Review": 0.04,
        "Informational": 0.02
    }
    df["ctr_potential"] = df["intent"].map(intent_ctr_map).fillna(0.03)
    df["traffic_potential"] = (df["search_volume"] * df["ctr_potential"]).astype(float)
    
    # 4. Commercial potential: scalar between 0 and 1
    intent_comm_map = {
        "Transactional": 1.0,
        "Commercial": 0.8,
        "Comparison": 0.6,
        "Review": 0.5,
        "Navigational": 0.4,
        "Informational": 0.2
    }
    df["commercial_potential"] = df["intent"].map(intent_comm_map).fillna(0.3)

    return df
