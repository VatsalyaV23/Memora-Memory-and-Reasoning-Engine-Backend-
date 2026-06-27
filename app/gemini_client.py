import google.generativeai as genai
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

# Mock data for demo when API fails
MOCK_ANSWERS = {
    "default": "This is a demo response. To get real answers, please provide a valid GEMINI_API_KEY.",
    "database": "We decided to use PostgreSQL for relational data and ChromaDB for vector search.",
    "framework": "The tech stack includes FastAPI, ChromaDB, PostgreSQL, and Google Gemini.",
    "decision": "Based on the organizational memory, the key decision was to adopt modern AI-powered decision tracking.",
}

class GeminiClient:
    """Gemini LLM client for decision extraction and reasoning"""
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.available = False
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.available = True
                logger.info("✓ Gemini client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Gemini initialization failed: {str(e)}")
                self.available = False
        else:
            logger.warning("⚠️ No Gemini API key provided - using mock responses")
    
    def extract_decisions(self, text: str) -> List[Dict]:
        """Extract decisions from text using LLM"""
        try:
            if not self.available:
                # Return mock data
                return [
                    {
                        "title": "Use ChromaDB for Vector Storage",
                        "status": "decided",
                        "description": "Extracted from captured text - using mock AI response"
                    },
                    {
                        "title": "Implement RAG Pipeline",
                        "status": "approved",
                        "description": "For enhanced question answering"
                    }
                ]
            
            prompt = f"""
            Analyze the following text and extract all decisions mentioned.
            For each decision, provide:
            1. Title (brief decision name)
            2. Status (approved, rejected, decided, pending)
            3. Description (reasoning or details)
            
            Format as JSON array:
            [
                {{
                    "title": "decision title",
                    "status": "approved/rejected/decided/pending",
                    "description": "reasoning"
                }}
            ]
            
            Text to analyze:
            {text}
            
            Return ONLY valid JSON, no other text.
            """
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.warning("Empty response from Gemini")
                return []
            
            # Parse JSON response
            try:
                text_response = response.text.strip()
                if text_response.startswith('```json'):
                    text_response = text_response[7:-3]
                elif text_response.startswith('```'):
                    text_response = text_response[3:-3]
                
                decisions = json.loads(text_response)
                
                if not isinstance(decisions, list):
                    decisions = [decisions]
                
                logger.info(f"✓ Extracted {len(decisions)} decisions")
                return decisions
            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {str(e)}")
                return []
        
        except Exception as e:
            logger.error(f"❌ Decision extraction failed: {str(e)}")
            return []
    
    def generate_answer(self, question: str, context: str) -> str:
        """Generate an answer based on context"""
        try:
            if not self.available:
                # Check for keywords in question for smart mock responses
                question_lower = question.lower()
                for keyword, answer in MOCK_ANSWERS.items():
                    if keyword in question_lower:
                        return answer
                return MOCK_ANSWERS["default"]
            
            prompt = f"""
            Based on the following context, answer the question concisely.
            If the answer is not in the context, say "I don't have enough information to answer this question."
            
            Context:
            {context}
            
            Question:
            {question}
            
            Answer:
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                logger.info(f"✓ Generated answer for: {question[:50]}...")
                return response.text.strip()
            else:
                return "Unable to generate answer"
        
        except Exception as e:
            logger.error(f"❌ Answer generation failed: {str(e)}")
            return MOCK_ANSWERS["default"]
    
    def detect_relationships(self, decisions: List[str]) -> List[Dict]:
        """Detect relationships between decisions"""
        try:
            if not self.available:
                # Return mock relationships
                return [
                    {
                        "from": 0,
                        "to": 1,
                        "relationship_type": "DEPENDS_ON",
                        "reason": "Vector storage decision enables RAG pipeline"
                    }
                ]
            
            decisions_text = "\n".join([f"{i+1}. {d}" for i, d in enumerate(decisions)])
            
            prompt = f"""
            Analyze the following decisions and identify any relationships between them.
            Return as JSON array with from, to, and relationship_type fields.
            
            Decisions:
            {decisions_text}
            
            Return JSON array:
            [
                {{
                    "from": "decision 1 index",
                    "to": "decision 2 index", 
                    "relationship_type": "DEPENDS_ON/BLOCKS/RELATED_TO",
                    "reason": "explanation"
                }}
            ]
            
            Return ONLY valid JSON.
            """
            
            response = self.model.generate_content(prompt)
            
            try:
                text_response = response.text.strip()
                if text_response.startswith('```json'):
                    text_response = text_response[7:-3]
                elif text_response.startswith('```'):
                    text_response = text_response[3:-3]
                
                relationships = json.loads(text_response)
                return relationships if isinstance(relationships, list) else []
            
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            logger.error(f"❌ Relationship detection failed: {str(e)}")
            return []

_gemini_client = None

def init_gemini(api_key: str = "") -> GeminiClient:
    """Initialize Gemini client"""
    global _gemini_client
    try:
        _gemini_client = GeminiClient(api_key)
        logger.info("✓ Gemini client initialized")
        return _gemini_client
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini: {str(e)}")
        _gemini_client = GeminiClient()  # Create with mock mode
        return _gemini_client

def get_gemini_client() -> GeminiClient:
    """Get Gemini client instance"""
    if _gemini_client is None:
        return GeminiClient()  # Return mock client
    return _gemini_client