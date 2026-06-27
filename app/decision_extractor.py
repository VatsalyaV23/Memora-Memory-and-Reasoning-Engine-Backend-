import logging
import json
from typing import List, Dict
from app.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

class Decision:
    """Decision data class"""
    def __init__(self, decision_id: str, title: str, status: str, description: str = "", confidence: float = 0.8):
        self.decision_id = decision_id
        self.title = title
        self.status = status
        self.description = description
        self.confidence = confidence

class DecisionExtractor:
    """Extract decisions from text using LLM"""
    
    def __init__(self):
        self.gemini = get_gemini_client()
    
    def extract_decisions(self, text: str) -> List[Decision]:
        """Extract decisions from text"""
        try:
            if not self.gemini:
                logger.error("Gemini not available")
                return []
            
            # Get raw decisions from Gemini
            raw_decisions = self.gemini.extract_decisions(text)
            
            if not raw_decisions:
                logger.info("No decisions extracted")
                return []
            
            # Convert to Decision objects
            decisions = []
            for i, dec in enumerate(raw_decisions):
                try:
                    decision_id = f"dec_{hash(dec.get('title', f'decision_{i}')) % 100000:05d}"
                    
                    decision = Decision(
                        decision_id=decision_id,
                        title=dec.get('title', 'Unknown Decision'),
                        status=dec.get('status', 'decided').lower(),
                        description=dec.get('description', ''),
                        confidence=dec.get('confidence', 0.8)
                    )
                    decisions.append(decision)
                
                except Exception as e:
                    logger.warning(f"Failed to parse decision {i}: {str(e)}")
                    continue
            
            logger.info(f"✓ Extracted {len(decisions)} decisions from text")
            return decisions
        
        except Exception as e:
            logger.error(f"❌ Decision extraction failed: {str(e)}")
            return []

_decision_extractor = None

def init_decision_extractor():
    """Initialize Decision Extractor"""
    global _decision_extractor
    try:
        _decision_extractor = DecisionExtractor()
        logger.info("✓ Decision Extractor initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Decision Extractor: {str(e)}")
        _decision_extractor = None

def get_decision_extractor() -> DecisionExtractor:
    """Get Decision Extractor instance"""
    if _decision_extractor is None:
        logger.error("❌ Decision Extractor not initialized")
    return _decision_extractor