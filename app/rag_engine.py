import logging
from typing import Tuple, List, Dict
from app.chromadb_client import get_chromadb_client
from app.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

class RAGEngine:
    """RAG (Retrieval-Augmented Generation) Engine"""
    
    def __init__(self):
        self.chroma = get_chromadb_client()
        self.gemini = get_gemini_client()
    
    def answer_question(self, question: str, top_k: int = 5) -> Tuple[str, List[Dict]]:
        """
        Answer a question using RAG pipeline:
        1. Retrieve relevant documents from ChromaDB
        2. Augment prompt with retrieved documents
        3. Generate answer using Gemini
        """
        try:
            # Step 1: Retrieve
            if not self.chroma:
                logger.error("ChromaDB not available")
                return "Database not available", []
            
            retrieved_docs = self.chroma.search(question, n_results=top_k)
            
            if not retrieved_docs:
                logger.info(f"No documents found for question: {question}")
                return "No relevant information found in the knowledge base", []
            
            # Step 2: Augment
            context = "\n".join([
                f"[{i+1}] {doc['text']}"
                for i, doc in enumerate(retrieved_docs)
            ])
            
            # Step 3: Generate
            if not self.gemini:
                logger.error("Gemini not available")
                return "LLM not available", []
            
            answer = self.gemini.generate_answer(question, context)
            
            # Format citations
            citations = [
                {
                    "source": doc['metadata'].get('source', 'unknown'),
                    "text_preview": doc['text'][:200],
                    "relevance": doc.get('relevance', 0.0)
                }
                for doc in retrieved_docs
            ]
            
            logger.info(f"✓ RAG answer generated for: {question[:50]}...")
            
            return answer, citations
        
        except Exception as e:
            logger.error(f"❌ RAG pipeline failed: {str(e)}")
            return f"Error answering question: {str(e)}", []

_rag_engine = None

def init_rag_engine():
    """Initialize RAG Engine"""
    global _rag_engine
    try:
        _rag_engine = RAGEngine()
        logger.info("✓ RAG Engine initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG Engine: {str(e)}")
        _rag_engine = None

def get_rag_engine() -> RAGEngine:
    """Get RAG Engine instance"""
    if _rag_engine is None:
        logger.error("❌ RAG Engine not initialized")
    return _rag_engine