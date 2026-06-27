import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration from environment variables with safe fallbacks"""
    
    # Backend settings
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Database settings (Optional)
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    USE_DATABASE = bool(DATABASE_URL)
    
    # ChromaDB settings
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_data")
    
    # Neo4j settings (Optional)
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    USE_NEO4J = os.getenv("USE_NEO4J", "false").lower() == "true"
    
    # Extension settings
    EXTENSION_ORIGIN = os.getenv("EXTENSION_ORIGIN", "chrome-extension://*")
    
    # Defaults for testing/demo
    ENABLE_MOCK_DATA = os.getenv("ENABLE_MOCK_DATA", "true").lower() == "true"

config = Config()

# Validation (non-blocking for demo)
if not config.GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set - AI features will be limited")