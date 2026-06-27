import chromadb
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """ChromaDB client for vector storage and semantic search"""
    
    def __init__(self, path: str = "./chroma_data"):
        self.path = path
        self.client = None
        self.collection = None
        self.init_connection()
    
    def init_connection(self):
        """Initialize ChromaDB connection"""
        try:
            self.client = chromadb.PersistentClient(path=self.path)
            self.collection = self.client.get_or_create_collection(
                name="org-memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("✓ ChromaDB connected successfully")
        except Exception as e:
            logger.error(f"❌ ChromaDB connection failed: {str(e)}")
            self.client = None
            self.collection = None
    
    def add_document(self, doc_id: str, text: str, source: str = "unknown", url: str = "") -> bool:
        """Add document to ChromaDB with vector embedding"""
        try:
            if not self.collection:
                logger.error("ChromaDB not initialized")
                return False
            
            self.collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[{
                    "source": source,
                    "url": url,
                    "text_length": len(text)
                }]
            )
            logger.info(f"✓ Document added: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add document: {str(e)}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a specific document"""
        try:
            if not self.collection:
                return None
            
            result = self.collection.get(ids=[doc_id])
            if result and result['documents']:
                return {
                    "id": doc_id,
                    "text": result['documents'][0],
                    "metadata": result['metadatas'][0] if result['metadatas'] else {}
                }
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get document: {str(e)}")
            return None
    
    def get_all_documents(self, limit: int = 100) -> List[Dict]:
        """Get all documents"""
        try:
            if not self.collection:
                return []
            
            result = self.collection.get(limit=limit)
            
            documents = []
            if result['documents']:
                for i, doc in enumerate(result['documents']):
                    documents.append({
                        "id": result['ids'][i],
                        "text": doc,
                        "metadata": result['metadatas'][i] if result['metadatas'] else {}
                    })
            
            return documents
        except Exception as e:
            logger.error(f"❌ Failed to get documents: {str(e)}")
            return []
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search documents using semantic similarity"""
        try:
            if not self.collection:
                return []
            
            result = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not result or not result['documents'] or not result['documents'][0]:
                logger.info(f"No documents found for query: {query}")
                return []
            
            results = []
            for i, doc in enumerate(result['documents'][0]):
                results.append({
                    "id": result['ids'][0][i],
                    "text": doc,
                    "distance": result['distances'][0][i] if result['distances'] else 0,
                    "relevance": 1 - (result['distances'][0][i] if result['distances'] else 0),
                    "metadata": result['metadatas'][0][i] if result['metadatas'] else {}
                })
            
            return results
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return []
    
    def health_check(self) -> bool:
        """Check connection health"""
        try:
            if self.collection:
                self.collection.count()
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return False

_chromadb_client = None

def init_chromadb(path: str = "./chroma_data") -> ChromaDBClient:
    """Initialize ChromaDB client"""
    global _chromadb_client
    try:
        _chromadb_client = ChromaDBClient(path)
        logger.info("✓ ChromaDB client initialized")
        return _chromadb_client
    except Exception as e:
        logger.error(f"❌ Failed to initialize ChromaDB: {str(e)}")
        _chromadb_client = None
        return None

def get_chromadb_client() -> ChromaDBClient:
    """Get ChromaDB client instance"""
    return _chromadb_client