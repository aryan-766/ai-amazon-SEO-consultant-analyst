from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.core.config import settings
from backend.app.core.db import engine, Base
from backend.app.api.endpoints import router as api_router

# Initialize Database tables
Base.metadata.create_all(bind=engine)

def seed_demo_data():
    from backend.app.core.db import SessionLocal
    from backend.app.models.models import UploadSession, Keyword
    import json
    
    db = SessionLocal()
    try:
        # Check if demo session exists
        demo_session = db.query(UploadSession).filter(UploadSession.id == "demo").first()
        if demo_session:
            return
            
        # Create demo session
        session = UploadSession(
            id="demo",
            filename="Demo_Amazon_Keywords_Chargers.xlsx",
            status="ANALYZED",
            summary_metadata=json.dumps({
                "file_path": "",
                "total_rows": 16,
                "columns_detected": ["Keyword", "Search Volume", "Competing Products"],
                "keyword_column": "Keyword",
                "search_volume_column": "Search Volume",
                "competing_products_column": "Competing Products",
                "user_brand": "Ambrane",
                "competitors_list": ["Anker", "Boat", "Belkin", "Mivi"],
                "easy_wins_count": 6,
                "gaps_count": 4,
                "categories": ["Power Bank", "Charger", "Cable", "Earbuds"],
                "competitor_analysis": {
                    "market_leader": "Anker",
                    "summaries": {
                        "Anker": {"name": "Anker", "avg_rank": 14.5, "coverage_pct": 85.0, "top_10_count": 12, "top_30_count": 15, "sov": 18500.0, "status": "Strong"},
                        "Boat": {"name": "Boat", "avg_rank": 32.1, "coverage_pct": 55.0, "top_10_count": 6, "top_30_count": 10, "sov": 9200.0, "status": "Moderate"},
                        "Belkin": {"name": "Belkin", "avg_rank": 45.3, "coverage_pct": 40.0, "top_10_count": 3, "top_30_count": 7, "sov": 5400.0, "status": "Moderate"},
                        "Mivi": {"name": "Mivi", "avg_rank": 62.4, "coverage_pct": 25.0, "top_10_count": 1, "top_30_count": 4, "sov": 2100.0, "status": "Weak"},
                        "Ambrane": {"name": "Ambrane", "avg_rank": 28.5, "coverage_pct": 60.0, "top_10_count": 8, "top_30_count": 12, "sov": 11500.0, "status": "Strong"}
                    }
                }
            })
        )
        db.add(session)
        db.commit()
        
        raw_kws = [
            ("power bank 20000mah", 25000, 120, "Power Bank", "Generic", "Transactional", "Purchase", 85.0, 92.0, 35.0, 78.0, 45.0, 80.0, 85.0, 85.0),
            ("anker power bank 20000mah", 35000, 90, "Power Bank", "Competitor Branded", "Navigational", "Comparison", 75.0, 88.0, 55.0, 85.0, 70.0, 60.0, 75.0, 78.0),
            ("best portable charger", 18000, 310, "Power Bank", "Generic", "Commercial", "Interest", 82.0, 80.0, 65.0, 65.0, 30.0, 85.0, 78.0, 80.0),
            ("ambrane power bank 10000mah", 12000, 45, "Power Bank", "Branded", "Navigational", "Comparison", 90.0, 78.0, 25.0, 72.0, 15.0, 65.0, 88.0, 85.0),
            ("fast charger for iphone", 42000, 520, "Charger", "Generic", "Transactional", "Purchase", 70.0, 95.0, 85.0, 82.0, 60.0, 75.0, 70.0, 75.0),
            ("usb c wall charger block", 28000, 380, "Charger", "Generic", "Transactional", "Purchase", 76.0, 89.0, 75.0, 75.0, 45.0, 78.0, 75.0, 78.0),
            ("best 65w gan charger", 9500, 40, "Charger", "Generic", "Commercial", "Interest", 88.0, 72.0, 30.0, 90.0, 80.0, 90.0, 92.0, 90.0),
            ("anker 65w wall charger", 15000, 75, "Charger", "Competitor Branded", "Navigational", "Comparison", 80.0, 81.0, 45.0, 88.0, 65.0, 80.0, 82.0, 80.0),
            ("belkin wireless charging pad", 8000, 110, "Charger", "Competitor Branded", "Navigational", "Comparison", 65.0, 64.0, 50.0, 60.0, 55.0, 70.0, 65.0, 64.0),
            ("magsafe charger block for iphone", 14000, 160, "Charger", "Generic", "Transactional", "Purchase", 78.0, 75.0, 55.0, 80.0, 50.0, 82.0, 78.0, 78.0),
            ("fast charging usb c cable", 32000, 480, "Cable", "Generic", "Transactional", "Purchase", 72.0, 90.0, 80.0, 70.0, 55.0, 70.0, 72.0, 75.0),
            ("iphone charger cable 6ft", 26000, 290, "Cable", "Generic", "Transactional", "Purchase", 75.0, 86.0, 68.0, 65.0, 40.0, 75.0, 76.0, 78.0),
            ("heavy duty type c cable", 7500, 35, "Cable", "Generic", "Commercial", "Interest", 85.0, 60.0, 28.0, 75.0, 75.0, 88.0, 86.0, 84.0),
            ("boat wireless earbuds bluetooth", 38000, 240, "Earbuds", "Competitor Branded", "Navigational", "Comparison", 78.0, 92.0, 60.0, 80.0, 65.0, 70.0, 78.0, 80.0),
            ("best noise cancelling tws under 3000", 16000, 85, "Earbuds", "Generic", "Commercial", "Interest", 89.0, 82.0, 35.0, 85.0, 80.0, 92.0, 94.0, 92.0),
            ("noise cancellation earbuds fast charge", 6200, 28, "Earbuds", "Generic", "Commercial", "Interest", 84.0, 58.0, 22.0, 78.0, 75.0, 85.0, 88.0, 85.0)
        ]
        
        kws_objects = []
        for kw, sv, cpr, category, brand_type, intent, stage, opp, rev, comp, trend, gap, content, seo, final in raw_kws:
            comp_ranks = {
                "Anker": 2 if "anker" in kw else (14 if category == "Charger" else 101),
                "Boat": 3 if "boat" in kw else (22 if category == "Earbuds" else 101),
                "Belkin": 10 if "belkin" in kw else (35 if category == "Charger" else 101),
                "Mivi": 8 if category == "Earbuds" else 101,
                "Ambrane": 5 if "ambrane" in kw else (18 if category == "Power Bank" else 101)
            }
            
            kws_objects.append(Keyword(
                session_id="demo",
                keyword=kw,
                search_volume=sv,
                cpr=cpr,
                position_bias_ctr=0.08 if intent == "Transactional" else 0.05,
                word_count=len(kw.split()),
                char_count=len(kw),
                contains_number=any(char.isdigit() for char in kw),
                contains_unit="mah" in kw or "w" in kw or "ft" in kw,
                contains_brand="anker" in kw or "boat" in kw or "belkin" in kw or "ambrane" in kw,
                contains_tech="gan" in kw or "magsafe" in kw or "pd" in kw,
                brand_name="Anker" if "anker" in kw else ("Boat" if "boat" in kw else ("Belkin" if "belkin" in kw else ("Ambrane" if "ambrane" in kw else None))),
                brand_type=brand_type,
                product_type=category,
                tech_type="GaN" if "gan" in kw else ("MagSafe" if "magsafe" in kw else ("PD" if "pd" in kw or "65w" in kw else None)),
                intent=intent,
                buyer_stage=stage,
                traffic_potential=float(sv * 0.05),
                ctr_potential=0.05,
                ranking_potential=float(100.0 - comp),
                commercial_potential=0.9 if intent == "Transactional" else 0.7,
                competitor_ranks=json.dumps(comp_ranks),
                competitor_coverage=sum(1 for r in comp_ranks.values() if r <= 20),
                ranking_gap=comp_ranks["Ambrane"] > 30 and any(r <= 20 for c, r in comp_ranks.items() if c != "Ambrane"),
                topic_cluster=f"{category} Charging" if category in ["Charger", "Power Bank", "Cable"] else "TWS Devices",
                keyword_cluster_id=1 if category == "Power Bank" else (2 if category == "Charger" else 3),
                opportunity_score=opp,
                revenue_score=rev,
                competition_score=comp,
                trend_score=trend,
                gap_score=gap,
                content_score=content,
                priority_score=float((opp + trend + gap) / 3),
                business_score=float((rev + opp) / 2),
                seo_score=seo,
                final_ai_score=final
            ))
        db.bulk_save_objects(kws_objects)
        db.commit()
    except Exception as e:
        print(f"Error seeding demo data: {e}")
    finally:
        db.close()

seed_demo_data()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adapt to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to Amazon SEO Copilot API"}

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
