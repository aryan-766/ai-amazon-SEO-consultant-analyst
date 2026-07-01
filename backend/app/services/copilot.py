import os
import json
import httpx
import re
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import Keyword, ChatMessage
from backend.app.services.features import get_embedding_model, ML_LIBS_AVAILABLE

# Simple in-memory cache for session keyword embeddings
# maps session_id -> { "keywords": List[str], "embeddings": np.ndarray }
_embeddings_cache: Dict[str, Dict[str, Any]] = {}

def get_cosine_similarity(query_emb: np.ndarray, doc_embs: np.ndarray) -> np.ndarray:
    """Compute cosine similarities between a query embedding and a matrix of document embeddings."""
    # query_emb: shape (D,)
    # doc_embs: shape (N, D)
    dot_product = np.dot(doc_embs, query_emb)
    query_norm = np.linalg.norm(query_emb)
    doc_norms = np.linalg.norm(doc_embs, axis=1)
    
    # Avoid division by zero
    doc_norms[doc_norms == 0] = 1e-9
    if query_norm == 0:
        query_norm = 1e-9
        
    return dot_product / (query_norm * doc_norms)

def build_context_from_keywords(keywords: List[Keyword]) -> str:
    """Format keywords as a clean markdown table for the LLM prompt context."""
    if not keywords:
        return "No relevant keywords found in the dataset matching your query."
        
    context = "| Keyword | Search Volume | Opportunity Score | Competition Score | Intent | Product Type | Competitor Ranks |\n"
    context += "|---|---|---|---|---|---|---|\n"
    
    for k in keywords[:15]:  # limit to top 15 retrieved to avoid prompt bloat
        ranks_dict = json.loads(k.competitor_ranks or "{}")
        ranks_str = ", ".join([f"{comp}: {rank if rank <= 100 else 'Unranked'}" for comp, rank in ranks_dict.items()])
        context += f"| {k.keyword} | {k.search_volume} | {k.opportunity_score:.1f} | {k.competition_score:.1f} | {k.intent} | {k.product_type} | {ranks_str} |\n"
        
    return context

def retrieve_relevant_keywords(
    db: Session,
    session_id: str,
    query: str,
    top_n: int = 15
) -> List[Keyword]:
    """Retrieve keywords relevant to the query using semantic search or text fallback."""
    all_kws = db.query(Keyword).filter(Keyword.session_id == session_id).all()
    if not all_kws:
        return []

    model = get_embedding_model()
    
    if ML_LIBS_AVAILABLE and model is not None:
        try:
            # Check cache
            cache_entry = _embeddings_cache.get(session_id)
            if not cache_entry or len(cache_entry["keywords"]) != len(all_kws):
                # Generate embeddings for all keywords in this session
                kw_texts = [k.keyword for k in all_kws]
                embeddings = model.encode(kw_texts, show_progress_bar=False)
                cache_entry = {
                    "keywords": kw_texts,
                    "embeddings": embeddings
                }
                _embeddings_cache[session_id] = cache_entry
            
            # Embed query
            query_emb = model.encode([query], show_progress_bar=False)[0]
            
            # Compute similarities
            similarities = get_cosine_similarity(query_emb, cache_entry["embeddings"])
            
            # Get top indices
            top_indices = np.argsort(similarities)[::-1][:top_n]
            return [all_kws[idx] for idx in top_indices]
            
        except Exception as e:
            print(f"Semantic retrieval failed: {e}. Falling back to text matching.")
            
    # Text-based fallback filter
    query_words = set(query.lower().split())
    matched_kws = []
    
    for k in all_kws:
        kw_text = k.keyword.lower()
        score = 0
        for word in query_words:
            if word in kw_text:
                score += 1
            if k.product_type.lower() in word:
                score += 2
        if score > 0:
            matched_kws.append((k, score))
            
    if matched_kws:
        # Sort by match score descending, then by search volume descending
        matched_kws.sort(key=lambda x: (x[1], x[0].search_volume), reverse=True)
        return [item[0] for item in matched_kws[:top_n]]
        
    # If no keyword matches, return top keywords by search volume
    return sorted(all_kws, key=lambda x: x.search_volume, reverse=True)[:top_n]

async def query_copilot_chat(
    db: Session,
    session_id: str,
    user_query: str
) -> str:
    """
    RAG-based chat with Ollama.
    1. Retrieve relevant keywords.
    2. Format prompt with context.
    3. Call Ollama.
    """
    # 1. Retrieve keywords
    relevant_kws = retrieve_relevant_keywords(db, session_id, user_query)
    context_table = build_context_from_keywords(relevant_kws)
    
    # 2. Get previous messages for history (limit last 5 messages)
    history_msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.desc()).limit(6).all()
    history_msgs.reverse()
    
    history_str = ""
    for msg in history_msgs:
        if msg.role == "user" and msg.content != user_query:
            history_str += f"User: {msg.content}\n"
        elif msg.role == "assistant":
            history_str += f"Assistant: {msg.content}\n"
            
    system_prompt = (
        "You are the Amazon SEO Copilot, a brilliant data analyst and e-commerce growth strategist.\n"
        "Your task is to answer the user's question using ONLY the provided keyword dataset context.\n"
        "Rules:\n"
        "1. Prioritize accuracy. Do NOT make up figures or facts. Only mention ASINs, search volumes, or scores present in the context.\n"
        "2. If you don't find the answer in the provided context, state that you lack specific metrics for that query in this upload.\n"
        "3. Provide formatted markdown tables and bullet points where helpful to organize analysis.\n"
        "4. Be professional, concise, and business-focused."
    )
    
    prompt = (
        f"{system_prompt}\n\n"
        f"--- START DATA CONTEXT ---\n"
        f"{context_table}\n"
        f"--- END DATA CONTEXT ---\n\n"
        f"Conversation History:\n"
        f"{history_str}"
        f"User: {user_query}\n"
        f"Assistant:"
    )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3
                    }
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
    except Exception as e:
        print(f"Ollama connection error: {e}. Generating database fallback response.")
        
    # Smart Fallback Response (if Ollama is down/not configured)
    # Give a detailed data summary based on the retrieved relevant keywords
    summary = f"**[Local Fallback Mode - Ollama Offline]**\n\nHere are the retrieved relevant keywords matching your query:\n\n"
    summary += context_table
    summary += "\n\n*To view full AI reasoning, please start Ollama locally (`ollama run qwen2.5:7b`).*"
    return summary
