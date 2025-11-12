import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchRequest(BaseModel):
    description: str
    sector: Optional[str] = None
    region: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Funding Finder API is running"}


@app.get("/test")
def test_database():
    response: Dict[str, Any] = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Basic keyword-based matcher as an initial version
# In production you could swap for embeddings/semantic search
KEYWORD_MAP = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning"],
    "health": ["health", "biotech", "med", "clinical", "healthcare"],
    "climate": ["climate", "environment", "energy", "sustainability", "carbon"],
    "education": ["education", "edtech", "school", "learning", "students"],
    "agriculture": ["agriculture", "agritech", "farming", "crop", "soil"],
    "transport": ["transport", "mobility", "ev", "autonomous", "logistics"],
    "cyber": ["cyber", "security", "infosec", "privacy"],
}


def extract_categories(text: str) -> List[str]:
    text_l = text.lower()
    cats = []
    for k, kws in KEYWORD_MAP.items():
        if any(kw in text_l for kw in kws):
            cats.append(k)
    return cats or ["general"]


def simple_score(query: str, opportunity: dict) -> float:
    # Bag-of-words overlap score (0-100)
    q_words = set(w for w in query.lower().split())
    desc = (opportunity.get("description") or "") + " " + " ".join(opportunity.get("categories", []))
    o_words = set(w for w in desc.lower().split())
    if not q_words:
        return 0.0
    overlap = len(q_words & o_words)
    return round(min(100.0, (overlap / max(5, len(q_words))) * 100.0), 2)


@app.post("/match")
async def match_opportunities(req: MatchRequest):
    if db is None:
        # Still allow demo behavior with static examples if DB not configured
        sample = [
            {
                "title": "AI for Social Good Grants",
                "agency": "Open Philanthropy",
                "description": "Funding for artificial intelligence projects that benefit society, including health and education.",
                "categories": ["ai", "education"],
                "eligibility": ["nonprofit", "researcher", "startup"],
                "region": "Global",
                "deadline": "Rolling",
                "amount": "$50k-$250k",
                "url": "https://example.org/ai-social-good"
            },
            {
                "title": "Climate Innovation Fund",
                "agency": "Green Future Foundation",
                "description": "Supports climate and energy innovations reducing carbon emissions.",
                "categories": ["climate", "energy"],
                "eligibility": ["startup", "small business"],
                "region": "US",
                "deadline": "2025-03-01",
                "amount": "$100k-$1M",
                "url": "https://example.org/climate-innovation"
            },
            {
                "title": "Digital Health Seed Grants",
                "agency": "HealthTech Council",
                "description": "Early-stage grants for digital health apps and clinical decision support.",
                "categories": ["health", "ai"],
                "eligibility": ["researcher", "startup"],
                "region": "EU",
                "deadline": "2025-05-01",
                "amount": "€50k-€200k",
                "url": "https://example.org/digital-health"
            }
        ]
    else:
        # Pull opportunities from DB if available
        sample = get_documents("fundingopportunity", {})

    # Filter by region or sector hint
    items = []
    cats = extract_categories(req.description + " " + (req.sector or ""))

    for opp in sample:
        if req.region and opp.get("region") and req.region.lower() not in opp.get("region").lower():
            # simple region filter; if region is provided but doesn't match, skip
            continue
        score = simple_score(req.description, opp)
        bonus = 0
        if any(c in (opp.get("categories") or []) for c in cats):
            bonus += 15
        if req.sector and req.sector.lower() in (" ".join(opp.get("categories", [])) + " " + opp.get("description", "")).lower():
            bonus += 10
        final = max(0, min(100, score + bonus))
        items.append({
            "title": opp.get("title"),
            "agency": opp.get("agency"),
            "url": opp.get("url"),
            "amount": opp.get("amount"),
            "deadline": opp.get("deadline"),
            "region": opp.get("region"),
            "categories": opp.get("categories", []),
            "eligibility": opp.get("eligibility", []),
            "match_score": final,
            "why": f"Matched on keywords {cats}; base score {score}, bonuses {bonus}",
        })

    # Sort by score desc and keep top 10
    items.sort(key=lambda x: x["match_score"], reverse=True)

    # Create a short report
    top3 = items[:3]
    summary_lines = [
        f"1) {x['title']} — {x['agency']} (Score {x['match_score']})" for x in top3
    ]
    report = {
        "query": req.description,
        "detected_categories": cats,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "highlights": summary_lines,
        "notes": "Scores are heuristic. Add more data to improve matches.",
    }

    return {"results": items[:10], "report": report}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
