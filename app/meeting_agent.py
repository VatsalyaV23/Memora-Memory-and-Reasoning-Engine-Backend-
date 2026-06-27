import logging
import uuid
import threading
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.gemini_client import get_gemini_client
from app.postgres_client import get_postgres_client

logger = logging.getLogger(__name__)

class MeetingSession(BaseModel):
    """Meeting session model"""
    meeting_id: str
    title: str
    participants: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    recording_enabled: bool = True
    agent_active: bool = False
    transcript: str = ""
    decisions_extracted: List[dict] = []
    audio_file: Optional[str] = None

class MeetingAgentManager:
    """Manages AI agent participation in meetings"""
    
    def __init__(self):
        self.active_meetings = {}
        self.gemini = get_gemini_client()
        self.db = get_postgres_client()
        self.recording_threads = {}
    
    def start_meeting(self, title: str, participants: List[str], 
                     enable_recording: bool = True) -> MeetingSession:
        """Start a new meeting session"""
        try:
            meeting_id = str(uuid.uuid4())[:12]
            meeting = MeetingSession(
                meeting_id=meeting_id,
                title=title,
                participants=participants,
                start_time=datetime.now(),
                recording_enabled=enable_recording,
                agent_active=False
            )
            
            self.active_meetings[meeting_id] = meeting
            logger.info(f"✓ Meeting started: {meeting_id} - {title}")
            
            return meeting
        except Exception as e:
            logger.error(f"❌ Failed to start meeting: {str(e)}")
            raise
    
    def deploy_agent(self, meeting_id: str) -> dict:
        """Deploy AI agent to join and monitor meeting"""
        try:
            if meeting_id not in self.active_meetings:
                raise ValueError(f"Meeting {meeting_id} not found")
            
            meeting = self.active_meetings[meeting_id]
            meeting.agent_active = True
            
            logger.info(f"🤖 Agent deployed to meeting {meeting_id}")
            
            if meeting.recording_enabled:
                # Start transcription processing in background thread
                thread = threading.Thread(
                    target=self._process_meeting,
                    args=(meeting_id,),
                    daemon=True
                )
                thread.start()
                self.recording_threads[meeting_id] = thread
            
            return {"status": "deployed", "meeting_id": meeting_id}
        
        except Exception as e:
            logger.error(f"❌ Failed to deploy agent: {str(e)}")
            raise
    
    def _process_meeting(self, meeting_id: str):
        """Process meeting transcription"""
        try:
            meeting = self.active_meetings.get(meeting_id)
            if not meeting:
                return
            
            logger.info(f"🎙️ Processing meeting {meeting_id}")
            
            # Simulate transcription (in real scenario, would process audio)
            mock_transcript = f"""
            Meeting: {meeting.title}
            Participants: {', '.join(meeting.participants)}
            
            Discussion points:
            - Architecture decisions
            - Technology stack selection
            - Scaling strategy
            
            Key decisions made:
            1. Use microservices architecture
            2. Implement caching layer
            3. Scale horizontally
            """
            
            meeting.transcript = mock_transcript
            self._extract_decisions_from_transcript(meeting_id, mock_transcript)
            
            logger.info(f"🎙️ Processing complete for {meeting_id}")
        
        except Exception as e:
            logger.error(f"❌ Meeting processing failed: {str(e)}")
            meeting = self.active_meetings.get(meeting_id)
            if meeting:
                meeting.agent_active = False
    
    def _extract_decisions_from_transcript(self, meeting_id: str, text: str):
        """Extract decisions from transcribed text"""
        try:
            if not self.gemini or not self.gemini.available:
                logger.info("Gemini not available for decision extraction")
                return
            
            meeting = self.active_meetings.get(meeting_id)
            if not meeting:
                return
            
            # Ask Gemini to identify decisions
            prompt = f"""
            Analyze this meeting transcript and identify any decisions made or actions decided.
            Be concise. If a decision is found, respond with:
            DECISION_FOUND: true
            TITLE: [decision title]
            DETAILS: [brief details]
            
            If no decision, respond: DECISION_FOUND: false
            
            Text: "{text}"
            """
            
            try:
                response = self.gemini.model.generate_content(prompt)
                response_text = response.text.strip()
                
                if "DECISION_FOUND: true" in response_text:
                    logger.info(f"✓ Decision detected in meeting {meeting_id}")
                    meeting.decisions_extracted.append({
                        "timestamp": datetime.now().isoformat(),
                        "text": text[:200],
                        "extracted": response_text
                    })
            except Exception as api_error:
                logger.warning(f"Gemini API error: {str(api_error)}")
        
        except Exception as e:
            logger.error(f"❌ Decision extraction failed: {str(e)}")
    
    def end_meeting(self, meeting_id: str) -> dict:
        """End meeting and process results"""
        try:
            if meeting_id not in self.active_meetings:
                raise ValueError(f"Meeting {meeting_id} not found")
            
            meeting = self.active_meetings[meeting_id]
            meeting.agent_active = False
            meeting.end_time = datetime.now()
            
            # Wait for recording thread to finish
            if meeting_id in self.recording_threads:
                self.recording_threads[meeting_id].join(timeout=5)
                del self.recording_threads[meeting_id]
            
            # Generate summary
            summary = self._generate_summary(meeting_id)
            
            # Store in database if available
            if self.db:
                self._store_meeting(meeting, summary)
            
            logger.info(f"✓ Meeting ended: {meeting_id}")
            
            # Prepare result
            result = {
                "meeting_id": meeting_id,
                "duration": str(meeting.end_time - meeting.start_time),
                "transcript": meeting.transcript,
                "decisions": meeting.decisions_extracted,
                "summary": summary
            }
            
            # Remove from active meetings after storing
            del self.active_meetings[meeting_id]
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to end meeting: {str(e)}")
            raise
    
    def _generate_summary(self, meeting_id: str) -> str:
        """Generate AI summary of meeting"""
        try:
            if not self.gemini or not self.gemini.available:
                return "Summary not available"
            
            meeting = self.active_meetings.get(meeting_id)
            if not meeting:
                return "Meeting not found"
            
            prompt = f"""
            Summarize this meeting in 2-3 sentences. Focus on key decisions and action items.
            
            Title: {meeting.title}
            Participants: {', '.join(meeting.participants)}
            
            Transcript:
            {meeting.transcript}
            """
            
            try:
                response = self.gemini.model.generate_content(prompt)
                return response.text.strip()
            except Exception as api_error:
                logger.warning(f"Gemini summary generation failed: {str(api_error)}")
                return "Summary generation failed"
        
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            return "Summary generation failed"
    
    def _store_meeting(self, meeting: MeetingSession, summary: str):
        """Store meeting data in database"""
        try:
            if not self.db or not self.db.conn:
                return
            
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO meetings (
                        id, title, participants, transcript, summary, 
                        decisions_count, started_at, ended_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    meeting.meeting_id,
                    meeting.title,
                    ','.join(meeting.participants),
                    meeting.transcript,
                    summary,
                    len(meeting.decisions_extracted),
                    meeting.start_time,
                    meeting.end_time
                ))
                self.db.conn.commit()
            
            logger.info(f"✓ Meeting stored: {meeting.meeting_id}")
        
        except Exception as e:
            logger.error(f"❌ Failed to store meeting: {str(e)}")
            if self.db and self.db.conn:
                self.db.conn.rollback()
    
    def get_meeting(self, meeting_id: str) -> Optional[MeetingSession]:
        """Get active meeting session"""
        return self.active_meetings.get(meeting_id)
    
    def get_all_active_meetings(self) -> List[MeetingSession]:
        """Get all active meetings"""
        return list(self.active_meetings.values())

# Global instance
_meeting_agent = None

def init_meeting_agent():
    """Initialize meeting agent"""
    global _meeting_agent
    try:
        _meeting_agent = MeetingAgentManager()
        logger.info("✓ Meeting Agent initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Meeting Agent: {str(e)}")
        _meeting_agent = None

def get_meeting_agent() -> Optional[MeetingAgentManager]:
    """Get meeting agent instance"""
    return _meeting_agent