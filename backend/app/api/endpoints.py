from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import uuid
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.db import get_db
from backend.app.models.models import UploadSession, Keyword, Listing, ChatMessage
from backend.app.schemas import schemas
from backend.app.services.excel import parse_and_validate_file
from backend.app.services.cleaning import clean_and_normalize_data
from backend.app.services.features import run_feature_engineering
from backend.app.services.scoring import run_scoring_engine
from backend.app.services.competitor import analyze_competitors, find_gaps_and_wins
from backend.app.services.copilot import query_copilot_chat
from backend.app.services.listing import analyze_listing_keywords, generate_optimized_listing_llm
from backend.app.services.reports import build_styled_excel, build_pdf_report

router = APIRouter()

@router.post("/upload", response_model=schemas.UploadSessionResponse)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.xlsx', '.xls', '.csv']:
        raise HTTPException(status_code=400, detail="Invalid file format. Only Excel (.xlsx, .xls) and CSV (.csv) are supported.")
    
    # Generate unique filename to avoid collision
    session_id = str(uuid.uuid4())
    save_filename = f"{session_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, save_filename)
    
    # Save file to upload directory
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    
    # Parse and validate columns
    try:
        parsed = parse_and_validate_file(file_path)
    except Exception as e:
        # Cleanup file if validation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Data validation failed: {str(e)}")
    
    summary = parsed["summary"]
    preview = parsed["preview"]
    
    # Create session in database
    session = UploadSession(
        id=session_id,
        filename=file.filename,
        status="CLEANED",
        summary_metadata=json.dumps({
            "file_path": file_path,
            "total_rows": summary["total_rows"],
            "columns_detected": summary["columns_detected"],
            "keyword_column": summary["keyword_column"],
            "search_volume_column": summary["search_volume_column"],
            "competing_products_column": summary["competing_products_column"],
            "competitors": summary["competitors_found"],
            "competitor_columns_map": summary["competitor_columns_map"],
            "preview": preview[:5] # Keep small preview in session logs
        })
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Parse summary metadata for response
    session.summary_metadata = json.loads(session.summary_metadata)
    return session

@router.post("/analyze")
def analyze_dataset(
    request: schemas.AnalyzeRequest,
    db: Session = Depends(get_db)
):
    session = db.query(UploadSession).filter(UploadSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    # Load settings from session metadata
    meta = json.loads(session.summary_metadata)
    file_path = meta["file_path"]
    keyword_col = meta["keyword_column"]
    sv_col = meta["search_volume_column"]
    cpr_col = meta["competing_products_column"]
    competitor_map = meta["competitor_columns_map"]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Saved dataset file was not found on server disk.")
    
    try:
        # 1. Re-read DataFrame
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        # 2. Data Cleaning
        df_cleaned, clean_report = clean_and_normalize_data(
            df, keyword_col, sv_col, cpr_col, competitor_map
        )
        
        # 3. Feature Engineering
        df_featured = run_feature_engineering(
            df_cleaned, keyword_col, request.user_brand, request.competitors
        )
        
        # 4. Scoring Engine
        df_scored = run_scoring_engine(
            df_featured, cpr_col, sv_col, competitor_map
        )
        
        # 5. Competitor aggregate analysis
        comp_analysis = analyze_competitors(df_scored, competitor_map, request.user_brand)
        
        # 6. Easy wins and gaps count
        easy_wins, gaps = find_gaps_and_wins(df_scored, competitor_map)

        # Clear existing keywords for this session (if re-analyzing)
        db.query(Keyword).filter(Keyword.session_id == request.session_id).delete()

        # 7. Write to database
        keywords_to_insert = []
        for _, row in df_scored.iterrows():
            # Build competitor ranks dictionary
            ranks_dict = {}
            for comp, col in competitor_map.items():
                ranks_dict[comp] = int(row[col])

            # Determine if ranking gap exists (e.g. user does not rank/ranks > 50, but at least one competitor ranks <= 20)
            user_rank = 101 # default
            # Check if user brand ranks
            for comp, col in competitor_map.items():
                if comp.lower() == request.user_brand.lower():
                    user_rank = int(row[col])
            
            comp_top_ranks = [r for c, r in ranks_dict.items() if c.lower() != request.user_brand.lower() and r <= 20]
            ranking_gap = (user_rank > 50) and (len(comp_top_ranks) > 0)

            kw_record = Keyword(
                session_id=request.session_id,
                keyword=str(row[keyword_col]),
                search_volume=int(row[sv_col]),
                cpr=int(row[cpr_col]),
                position_bias_ctr=float(row["ctr_potential"]),
                word_count=int(row["word_count"]),
                char_count=int(row["char_count"]),
                contains_number=bool(row["contains_number"]),
                contains_unit=bool(row["contains_unit"]),
                contains_brand=bool(row["contains_brand"]),
                contains_tech=bool(row["contains_tech"]),
                brand_name=row["brand_name"],
                brand_type=str(row["brand_type"]),
                product_type=str(row["product_type"]),
                tech_type=row["tech_type"],
                intent=str(row["intent"]),
                buyer_stage=str(row["buyer_stage"]),
                traffic_potential=float(row["traffic_potential"]),
                ctr_potential=float(row["ctr_potential"]),
                ranking_potential=float(100.0 - row["competition_score"]),
                commercial_potential=float(row["commercial_potential"]),
                competitor_ranks=json.dumps(ranks_dict),
                competitor_coverage=int(row["competitor_coverage"]),
                ranking_gap=bool(ranking_gap),
                topic_cluster=row["topic_cluster"],
                keyword_cluster_id=int(row["keyword_cluster_id"]) if pd.notna(row["keyword_cluster_id"]) else None,
                opportunity_score=float(row["opportunity_score"]),
                revenue_score=float(row["revenue_score"]),
                competition_score=float(row["competition_score"]),
                traffic_score=float(row["traffic_score"]),
                trend_score=float(row["trend_score"]),
                gap_score=float(row["gap_score"]),
                content_score=float(row["content_score"]),
                priority_score=float(row["priority_score"]),
                business_score=float((row["revenue_score"] + row["priority_score"]) / 2),
                seo_score=float(row["seo_score"]),
                final_ai_score=float(row["final_ai_score"])
            )
            keywords_to_insert.append(kw_record)

        # Batch insert
        db.bulk_save_objects(keywords_to_insert)
        
        # Update session metadata
        meta.update({
            "user_brand": request.user_brand,
            "competitors_list": request.competitors,
            "cleaning_report": clean_report,
            "competitor_analysis": comp_analysis,
            "easy_wins_count": len(easy_wins),
            "gaps_count": len(gaps),
            "categories": list(df_scored["product_type"].unique())
        })
        
        session.status = "ANALYZED"
        session.summary_metadata = json.dumps(meta)
        db.commit()
        
    except Exception as e:
        session.status = "ERROR"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return {"status": "SUCCESS", "message": f"Session {request.session_id} analyzed successfully. Total keywords saved: {len(df_scored)}."}

@router.get("/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard_data(
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    session = db.query(UploadSession).filter(UploadSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    if session.status != "ANALYZED":
        raise HTTPException(status_code=400, detail="Dataset has not been analyzed yet. Please run analysis first.")
    
    meta = json.loads(session.summary_metadata)
    
    # Query database for summaries
    keywords = db.query(Keyword).filter(Keyword.session_id == session_id).all()
    if not keywords:
        return schemas.DashboardResponse(
            kpis=schemas.KPICards(total_keywords=0, total_categories=0, total_competitors=0, easy_wins=0, high_opportunity_keywords=0, total_search_volume=0),
            intent_distribution=[], buyer_journey=[], category_distribution=[], competitor_comparison=[]
        )
        
    total_keywords = len(keywords)
    total_search_volume = sum(k.search_volume for k in keywords)
    categories = list(set(k.product_type for k in keywords))
    
    # Count metrics
    high_opp_count = sum(1 for k in keywords if k.opportunity_score >= 70)
    easy_wins_count = meta.get("easy_wins_count", 0)
    
    # Intent Distribution
    intent_counts = {}
    buyer_counts = {}
    cat_counts = {}
    
    for k in keywords:
        intent_counts[k.intent] = intent_counts.get(k.intent, 0) + 1
        buyer_counts[k.buyer_stage] = buyer_counts.get(k.buyer_stage, 0) + 1
        cat_counts[k.product_type] = cat_counts.get(k.product_type, 0) + 1
        
    intent_dist = [schemas.DistributionItem(name=k, value=v) for k, v in intent_counts.items()]
    buyer_dist = [schemas.DistributionItem(name=k, value=v) for k, v in buyer_counts.items()]
    cat_dist = [schemas.DistributionItem(name=k, value=v) for k, v in cat_counts.items()]
    
    # Competitor Comparison
    comp_analysis = meta.get("competitor_analysis", {}).get("summaries", {})
    comp_comparison = []
    for comp, data in comp_analysis.items():
        comp_comparison.append(schemas.CompetitorShareItem(
            name=comp,
            top_10_count=data["top_10_count"],
            top_30_count=data["top_30_count"],
            avg_rank=data["avg_rank"]
        ))
        
    return schemas.DashboardResponse(
        kpis=schemas.KPICards(
            total_keywords=total_keywords,
            total_categories=len(categories),
            total_competitors=len(comp_comparison),
            easy_wins=easy_wins_count,
            high_opportunity_keywords=high_opp_count,
            total_search_volume=total_search_volume
        ),
        intent_distribution=intent_dist,
        buyer_journey=buyer_dist,
        category_distribution=cat_dist,
        competitor_comparison=comp_comparison
    )

@router.get("/keywords", response_model=schemas.KeywordListResponse)
def get_keywords(
    session_id: str = Query(...),
    search: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cluster: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("opportunity_score"),
    sort_desc: bool = Query(True),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    query = db.query(Keyword).filter(Keyword.session_id == session_id)
    
    if search:
        query = query.filter(Keyword.keyword.ilike(f"%{search}%"))
    if intent:
        query = query.filter(Keyword.intent == intent)
    if category:
        query = query.filter(Keyword.product_type == category)
    if cluster:
        query = query.filter(Keyword.topic_cluster == cluster)
        
    # Sorting
    if sort_by and hasattr(Keyword, sort_by):
        col = getattr(Keyword, sort_by)
        if sort_desc:
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        query = query.order_by(Keyword.opportunity_score.desc())
        
    total = query.count()
    keywords = query.offset(offset).limit(limit).all()
    
    # Parse json columns for response
    for kw in keywords:
        if kw.competitor_ranks:
            kw.competitor_ranks = json.loads(kw.competitor_ranks)
            
    return schemas.KeywordListResponse(
        total=total,
        limit=limit,
        offset=offset,
        keywords=keywords
    )

@router.get("/competitors")
def get_competitor_names(
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    session = db.query(UploadSession).filter(UploadSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    meta = json.loads(session.summary_metadata or "{}")
    competitors = meta.get("competitors_list", meta.get("competitors", []))
    user_brand = meta.get("user_brand", "")
    comp_analysis = meta.get("competitor_analysis", {})
    
    return {
        "user_brand": user_brand,
        "competitors": competitors,
        "analysis": comp_analysis
    }

@router.get("/categories")
def get_category_names(
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    session = db.query(UploadSession).filter(UploadSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    meta = json.loads(session.summary_metadata or "{}")
    categories = meta.get("categories", ["Accessory"])
    return {"categories": categories}

@router.get("/reports")
def get_reports(
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    # Provide metadata for reports section
    return {
        "reports": [
            {"id": "exec_summary", "name": "Executive Summary", "description": "High-level summary of opportunities, traffic potentials, and key categories."},
            {"id": "competitor", "name": "Competitor Gaps & SOV", "description": "Deep-dive overlap analysis, competitor strengths, and weakness profiling."},
            {"id": "seo_listing", "name": "Listing Optimization Audit", "description": "Audit report outlining listing quality scores, missing high opportunity keywords and indexing gaps."}
        ]
    }

@router.post("/chat", response_model=schemas.ChatResponse)
async def chat_copilot(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db)
):
    # Save user message
    user_msg = ChatMessage(session_id=request.session_id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    
    # Retrieve semantic details and query Ollama (RAG)
    reply = await query_copilot_chat(db, request.session_id, request.message)
    
    # Save assistant message
    asst_msg = ChatMessage(session_id=request.session_id, role="assistant", content=reply)
    db.add(asst_msg)
    db.commit()
    
    history = db.query(ChatMessage).filter(ChatMessage.session_id == request.session_id).order_by(ChatMessage.timestamp.asc()).all()
    return schemas.ChatResponse(response=reply, history=history)

@router.post("/listing/generate", response_model=schemas.ListingResponse)
async def generate_listing(
    request: schemas.ListingGenerateRequest,
    db: Session = Depends(get_db)
):
    # Determine general product type from session keywords
    primary_kw = db.query(Keyword).filter(Keyword.session_id == request.session_id).order_by(Keyword.opportunity_score.desc()).first()
    product_type = primary_kw.product_type if primary_kw else "Accessory"
    
    # Generate content using LLM (Ollama or Fallback)
    generated = await generate_optimized_listing_llm(request.target_keywords, product_type=product_type)
    
    listing = Listing(
        session_id=request.session_id,
        title=generated["title"],
        bullet_points=json.dumps(generated["bullet_points"]),
        description=generated["description"],
        search_terms=generated["search_terms"],
        # Save structural extensions if generated
        aplus_content_ideas=json.dumps(generated.get("aplus_content_ideas", [])),
        faq=json.dumps(generated.get("faq", [])),
        seo_score=0 # will be scored via analyze call
    )
    db.add(listing)
    db.commit()
    
    # Perform SEO scoring on generated data
    analysis = analyze_listing_keywords(
        listing.title,
        generated["bullet_points"],
        listing.description,
        listing.search_terms,
        request.target_keywords
    )
    listing.seo_score = analysis["score"]
    db.commit()
    db.refresh(listing)
    
    listing.bullet_points = json.loads(listing.bullet_points)
    listing.aplus_content_ideas = json.loads(listing.aplus_content_ideas or "[]")
    listing.faq = json.loads(listing.faq or "[]")
    return listing

@router.post("/listing/analyze", response_model=schemas.ListingAnalyzeResponse)
def analyze_listing(
    request: schemas.ListingAnalyzeRequest,
    db: Session = Depends(get_db)
):
    # Retrieve the top 30 opportunity keywords for this session to run analysis
    kws_objs = db.query(Keyword).filter(Keyword.session_id == request.session_id).order_by(Keyword.opportunity_score.desc()).limit(30).all()
    target_keywords = [k.keyword for k in kws_objs]
    
    analysis = analyze_listing_keywords(
        request.title,
        request.bullet_points,
        request.description,
        request.search_terms,
        target_keywords
    )
    
    return schemas.ListingAnalyzeResponse(
        score=analysis["score"],
        matches=analysis["matches"],
        used_keywords=analysis["used_keywords"],
        unused_keywords=analysis["unused_keywords"],
        suggestions=analysis["suggestions"]
    )

@router.post("/export")
def export_data(
    request: schemas.ExportRequest,
    db: Session = Depends(get_db)
):
    session = db.query(UploadSession).filter(UploadSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    if session.status != "ANALYZED":
        raise HTTPException(status_code=400, detail="Data must be analyzed before exporting reports.")

    file_ext = request.format.lower()
    if file_ext not in ["xlsx", "pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Only 'xlsx' and 'pdf' are supported.")

    export_filename = f"report_{request.session_id}.{file_ext}"
    export_path = os.path.join(settings.UPLOAD_DIR, export_filename)

    try:
        if file_ext == "xlsx":
            build_styled_excel(db, request.session_id, export_path)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            display_name = f"Amazon_SEO_Keywords_{session.filename}"
            if not display_name.endswith(".xlsx"):
                display_name += ".xlsx"
        else:
            build_pdf_report(db, request.session_id, export_path)
            media_type = "application/pdf"
            display_name = f"Amazon_SEO_Executive_Summary_{session.filename.split('.')[0]}.pdf"

        # Return file response
        return FileResponse(
            path=export_path,
            filename=display_name,
            media_type=media_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
