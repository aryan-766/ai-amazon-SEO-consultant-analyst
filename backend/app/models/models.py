import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

class UploadSession(Base):
    __tablename__ = "upload_sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="PENDING")  # PENDING, CLEANED, ANALYZED, ERROR
    summary_metadata = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    keywords = relationship("Keyword", back_populates="session", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False)
    
    keyword = Column(String(255), nullable=False, index=True)
    search_volume = Column(Integer, default=0)
    cpr = Column(Integer, default=0)  # Cerebro Product Rank / competing products count
    position_bias_ctr = Column(Float, default=0.0)
    
    # NLP & engineered features
    word_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    contains_number = Column(Boolean, default=False)
    contains_unit = Column(Boolean, default=False)
    contains_brand = Column(Boolean, default=False)
    contains_tech = Column(Boolean, default=False)
    brand_name = Column(String(100), nullable=True)
    brand_type = Column(String(50), default="Generic")  # Generic, Branded, Competitor Branded
    product_type = Column(String(100), default="Accessory")
    tech_type = Column(String(100), nullable=True)
    intent = Column(String(50), default="Informational")  # Transactional, Commercial, etc.
    buyer_stage = Column(String(50), default="Awareness")  # Awareness, Interest, etc.
    
    # Traffic metrics
    traffic_potential = Column(Float, default=0.0)
    ctr_potential = Column(Float, default=0.0)
    ranking_potential = Column(Float, default=0.0)
    commercial_potential = Column(Float, default=0.0)
    
    # Competitor metrics
    competitor_ranks = Column(Text, nullable=True)  # JSON string representing competitor -> rank dict
    competitor_coverage = Column(Integer, default=0)
    ranking_gap = Column(Boolean, default=False)
    
    # Semantic clustering
    topic_cluster = Column(String(255), nullable=True)
    keyword_cluster_id = Column(Integer, nullable=True)
    
    # Normalized scores (0-100)
    opportunity_score = Column(Float, default=0.0)
    revenue_score = Column(Float, default=0.0)
    competition_score = Column(Float, default=0.0)
    traffic_score = Column(Float, default=0.0)
    trend_score = Column(Float, default=0.0)
    gap_score = Column(Float, default=0.0)
    content_score = Column(Float, default=0.0)
    priority_score = Column(Float, default=0.0)
    business_score = Column(Float, default=0.0)
    seo_score = Column(Float, default=0.0)
    final_ai_score = Column(Float, default=0.0)
    
    # Relationship
    session = relationship("UploadSession", back_populates="keywords")


class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(500), nullable=True)
    bullet_points = Column(Text, nullable=True)  # JSON list of strings
    description = Column(Text, nullable=True)
    search_terms = Column(Text, nullable=True)
    aplus_content_ideas = Column(Text, nullable=True)  # JSON structure
    faq = Column(Text, nullable=True)  # JSON structure
    seo_score = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    session = relationship("UploadSession", back_populates="listings")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("UploadSession", back_populates="chat_messages")
