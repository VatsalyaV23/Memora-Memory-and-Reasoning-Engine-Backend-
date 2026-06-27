from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import hashlib
import time
from typing import List, Optional
from datetime import datetime

# Import clients
from app.config import config
from app.chromadb_client import init_chromadb, get_chromadb_client
from app.gemini_client import init_gemini, get_gemini_client
from app.rag_engine import init_rag_engine, get_rag_engine
from app.decision_extractor import init_decision_extractor, get_decision_extractor

# Optional imports
try:
    from app.postgres_client import init_postgres, get_postgres_client
    POSTGRES_AVAILABLE = True
except Exception as e:
    POSTGRES_AVAILABLE = False
    print(f"⚠️  PostgreSQL not available: {str(e)}")

try:
    from app.neo4j_client import init_neo4j, get_neo4j_client
    NEO4J_AVAILABLE = True
except Exception as e:
    NEO4J_AVAILABLE = False
    print(f"⚠️  Neo4j not available: {str(e)}")

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Org Memory Engine",
    description="Capture & reason about organizational decisions with AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        config.EXTENSION_ORIGIN,
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# PYDANTIC MODELS
# ============================================

class HealthResponse(BaseModel):
    status: str
    message: str
    chromadb: str = "unknown"
    gemini: str = "unknown"
    postgres: str = "unknown"
    neo4j: str = "unknown"

class CaptureRequest(BaseModel):
    text: str
    source: str = "unknown"
    url: str = ""

class CaptureResponse(BaseModel):
    id: str
    message: str

class ExtractDecisionsRequest(BaseModel):
    text: str
    source: str = "unknown"
    url: str = ""

class Decision(BaseModel):
    decision_id: str
    title: str
    status: str
    description: str
    confidence: float = 0.8

class ExtractDecisionsResponse(BaseModel):
    decisions: List[Decision]
    count: int

class AskRequest(BaseModel):
    question: str

class Citation(BaseModel):
    source: str
    text_preview: str
    relevance: float

class AskResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    has_evidence: bool

# ============================================
# INITIALIZATION
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    logger.info("🚀 Starting Org Memory Engine v1.0...")
    
    # Initialize ChromaDB
    try:
        logger.info("Initializing ChromaDB...")
        init_chromadb(config.CHROMA_DB_PATH)
        logger.info("✓ ChromaDB initialized")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB initialization warning: {str(e)}")
    
    # Initialize Gemini API
    try:
        logger.info("Initializing Gemini API...")
        init_gemini(config.GEMINI_API_KEY)
        logger.info("✓ Gemini initialized")
    except Exception as e:
        logger.warning(f"⚠️  Gemini initialization warning: {str(e)}")
    
    # Initialize RAG Engine
    try:
        logger.info("Initializing RAG Engine...")
        init_rag_engine()
        logger.info("✓ RAG Engine initialized")
    except Exception as e:
        logger.warning(f"⚠️  RAG Engine initialization warning: {str(e)}")
    
    # Initialize Decision Extractor
    try:
        logger.info("Initializing Decision Extractor...")
        init_decision_extractor()
        logger.info("✓ Decision Extractor initialized")
    except Exception as e:
        logger.warning(f"⚠️  Decision Extractor initialization warning: {str(e)}")
    
    # Optional: Initialize PostgreSQL
    if POSTGRES_AVAILABLE and config.USE_DATABASE:
        try:
            logger.info("Initializing PostgreSQL...")
            init_postgres(config.DATABASE_URL)
            logger.info("✓ PostgreSQL initialized")
        except Exception as e:
            logger.warning(f"⚠️  PostgreSQL initialization warning: {str(e)}")
    
    # Optional: Initialize Neo4j
    if NEO4J_AVAILABLE and config.USE_NEO4J:
        try:
            logger.info("Initializing Neo4j...")
            init_neo4j()
            logger.info("✓ Neo4j initialized")
        except Exception as e:
            logger.warning(f"⚠️  Neo4j initialization warning: {str(e)}")
    
    logger.info("✅ Org Memory Engine ready!")

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    chroma = get_chromadb_client()
    gemini = get_gemini_client()
    
    chromadb_status = "ok" if chroma and chroma.health_check() else "warning"
    gemini_status = "ok" if gemini and gemini.available else "warning"
    
    postgres_status = "unknown"
    neo4j_status = "unknown"
    
    if POSTGRES_AVAILABLE:
        try:
            db = get_postgres_client()
            postgres_status = "ok" if db and db.health_check() else "warning"
        except:
            postgres_status = "unavailable"
    
    if NEO4J_AVAILABLE:
        try:
            graph = get_neo4j_client()
            neo4j_status = "ok" if graph and graph.health_check() else "warning"
        except:
            neo4j_status = "unavailable"
    
    return {
        "status": "ok",
        "message": "Org Memory Engine is running",
        "chromadb": chromadb_status,
        "gemini": gemini_status,
        "postgres": postgres_status,
        "neo4j": neo4j_status
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check endpoint"""
    chroma = get_chromadb_client()
    gemini = get_gemini_client()
    
    chromadb_status = "ok" if chroma and chroma.health_check() else "warning"
    gemini_status = "ok" if gemini and gemini.available else "warning"
    
    postgres_status = "unknown"
    neo4j_status = "unknown"
    
    if POSTGRES_AVAILABLE:
        try:
            db = get_postgres_client()
            postgres_status = "ok" if db and db.health_check() else "warning"
        except:
            postgres_status = "unavailable"
    
    if NEO4J_AVAILABLE:
        try:
            graph = get_neo4j_client()
            neo4j_status = "ok" if graph and graph.health_check() else "warning"
        except:
            neo4j_status = "unavailable"
    
    return {
        "status": "ok",
        "message": "All systems operational",
        "chromadb": chromadb_status,
        "gemini": gemini_status,
        "postgres": postgres_status,
        "neo4j": neo4j_status
    }

# ============================================
# CAPTURE ENDPOINTS
# ============================================

@app.post("/capture", response_model=CaptureResponse)
async def capture(request: CaptureRequest):
    """Capture text and store in ChromaDB"""
    try:
        if not request.text or len(request.text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text must be at least 10 characters")
        
        chroma = get_chromadb_client()
        if not chroma or not chroma.collection:
            raise HTTPException(status_code=500, detail="Storage not available")
        
        # Generate unique ID
        doc_id = hashlib.md5(f"{request.text[:20]}_{time.time()}".encode()).hexdigest()[:12]
        
        # Store in ChromaDB
        success = chroma.add_document(
            doc_id=doc_id,
            text=request.text,
            source=request.source,
            url=request.url
        )
        
        if success:
            logger.info(f"✓ Captured {len(request.text)} characters")
            return {
                "id": doc_id,
                "message": f"✅ Captured {len(request.text)} characters"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store document")
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Capture failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Capture failed: {str(e)}")

@app.get("/list")
async def list_documents(limit: int = 10):
    """List captured documents"""
    try:
        chroma = get_chromadb_client()
        if not chroma:
            return {"documents": [], "count": 0}
        
        docs = chroma.get_all_documents(limit=limit)
        return {
            "documents": docs,
            "count": len(docs)
        }
    except Exception as e:
        logger.error(f"❌ List failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(query: str, limit: int = 5):
    """Search documents using semantic search"""
    try:
        chroma = get_chromadb_client()
        if not chroma:
            return {"query": query, "results": [], "count": 0}
        
        results = chroma.search(query=query, n_results=limit)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"❌ Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DECISION EXTRACTION
# ============================================

@app.post("/extract-decisions", response_model=ExtractDecisionsResponse)
async def extract_decisions(request: ExtractDecisionsRequest):
    """Extract decisions from text using AI"""
    try:
        if not request.text:
            return {"decisions": [], "count": 0}
        
        extractor = get_decision_extractor()
        if not extractor:
            return {"decisions": [], "count": 0}
            
        decisions = extractor.extract_decisions(request.text)
        
        if not decisions:
            return {"decisions": [], "count": 0}
        
        # Also store in ChromaDB
        try:
            chroma = get_chromadb_client()
            if chroma and chroma.collection:
                doc_id = hashlib.md5(f"{request.text[:20]}_{time.time()}".encode()).hexdigest()[:12]
                chroma.add_document(
                    doc_id=doc_id,
                    text=request.text,
                    source=request.source,
                    url=request.url
                )
        except Exception as e:
            logger.warning(f"⚠️  Could not store in ChromaDB: {str(e)}")
        
        logger.info(f"✓ Extracted {len(decisions)} decisions")
        
        return {
            "decisions": [
                Decision(
                    decision_id=d.decision_id,
                    title=d.title,
                    status=d.status,
                    description=d.description,
                    confidence=d.confidence
                )
                for d in decisions
            ],
            "count": len(decisions)
        }
    
    except Exception as e:
        logger.error(f"❌ Extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# QUESTION ANSWERING (RAG)
# ============================================

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Answer questions using RAG"""
    try:
        if not request.question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        rag = get_rag_engine()
        if not rag:
            raise HTTPException(status_code=500, detail="RAG engine not available")
            
        answer, citations = rag.answer_question(request.question)
        
        logger.info(f"✓ Answered question: {request.question[:50]}...")
        
        return {
            "answer": answer,
            "citations": [
                Citation(
                    source=c.get("source", "unknown"),
                    text_preview=c.get("text_preview", "")[:200],
                    relevance=c.get("relevance", 0.0)
                )
                for c in citations
            ],
            "has_evidence": len(citations) > 0
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Question answering failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.error(f"HTTPException: {exc.detail}")
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status": "error"
    }

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting on {config.BACKEND_HOST}:{config.BACKEND_PORT}")
    uvicorn.run(
        "app.main:app",
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        reload=(config.ENVIRONMENT == "development")
    )