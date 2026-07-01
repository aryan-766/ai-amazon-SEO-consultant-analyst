from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class UploadSessionBase(BaseModel):
    filename: str

class UploadSessionResponse(UploadSessionBase):
    id: str
    uploaded_at: datetime
    status: str
    summary_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class KeywordBase(BaseModel):
    keyword: str
    search_volume: int
    cpr: int
    position_bias_ctr: float

class KeywordResponse(KeywordBase):
    id: int
    session_id: str
    word_count: int
    char_count: int
    contains_number: bool
    contains_unit: bool
    contains_brand: bool
    contains_tech: bool
    brand_name: Optional[str] = None
    brand_type: str
    product_type: str
    tech_type: Optional[str] = None
    intent: str
    buyer_stage: str
    traffic_potential: float
    ctr_potential: float
    ranking_potential: float
    commercial_potential: float
    competitor_ranks: Optional[Dict[str, Optional[int]]] = None
    competitor_coverage: int
    ranking_gap: bool
    topic_cluster: Optional[str] = None
    keyword_cluster_id: Optional[int] = None
    opportunity_score: float
    revenue_score: float
    competition_score: float
    traffic_score: float
    trend_score: float
    gap_score: float
    content_score: float
    priority_score: float
    business_score: float
    seo_score: float
    final_ai_score: float

    class Config:
        from_attributes = True

class KeywordListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    keywords: List[KeywordResponse]

class AnalyzeRequest(BaseModel):
    session_id: str
    user_brand: str
    competitors: List[str]

class ListingBase(BaseModel):
    title: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    description: Optional[str] = None
    search_terms: Optional[str] = None

class ListingResponse(ListingBase):
    id: int
    session_id: str
    aplus_content_ideas: Optional[List[Dict[str, str]]] = None
    faq: Optional[List[Dict[str, str]]] = None
    seo_score: int
    updated_at: datetime

    class Config:
        from_attributes = True

class ListingGenerateRequest(BaseModel):
    session_id: str
    target_keywords: List[str]

class ListingAnalyzeRequest(BaseModel):
    session_id: str
    title: str
    bullet_points: List[str]
    description: str
    search_terms: str

class ListingAnalyzeResponse(BaseModel):
    score: int
    matches: Dict[str, bool]  # keyword -> matched boolean
    used_keywords: List[str]
    unused_keywords: List[str]
    suggestions: List[str]

class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    history: List[ChatMessageResponse]

# Dashboard schemas
class KPICards(BaseModel):
    total_keywords: int
    total_categories: int
    total_competitors: int
    easy_wins: int
    high_opportunity_keywords: int
    total_search_volume: int

class DistributionItem(BaseModel):
    name: str
    value: int

class CompetitorShareItem(BaseModel):
    name: str
    top_10_count: int
    top_30_count: int
    avg_rank: float

class DashboardResponse(BaseModel):
    kpis: KPICards
    intent_distribution: List[DistributionItem]
    buyer_journey: List[DistributionItem]
    category_distribution: List[DistributionItem]
    competitor_comparison: List[CompetitorShareItem]

class ExportRequest(BaseModel):
    session_id: str
    format: str = Field(default="xlsx", description="Either 'xlsx' or 'pdf'")
