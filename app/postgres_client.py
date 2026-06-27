import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class PostgresClient:
    """PostgreSQL client for decision storage"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.driver = True
        self.init_connection()
    
    def init_connection(self):
        """Initialize database connection and create tables"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.create_tables()
            logger.info("✓ PostgreSQL connected successfully")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {str(e)}")
            self.driver = False
            raise
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            with self.conn.cursor() as cur:
                # Decisions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS decisions (
                        id VARCHAR(50) PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        status VARCHAR(50),
                        description TEXT,
                        source VARCHAR(100),
                        source_doc_id VARCHAR(100),
                        url TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        confidence FLOAT DEFAULT 0.8
                    )
                """)
                
                # Decision relationships table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS decision_relationships (
                        id SERIAL PRIMARY KEY,
                        from_decision_id VARCHAR(50),
                        to_decision_id VARCHAR(50),
                        relationship_type VARCHAR(50),
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        FOREIGN KEY (from_decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
                        FOREIGN KEY (to_decision_id) REFERENCES decisions(id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for faster queries
                cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relationships_from ON decision_relationships(from_decision_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relationships_to ON decision_relationships(to_decision_id)")
                
                self.conn.commit()
                logger.info("✓ PostgreSQL tables and indexes created")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {str(e)}")
            self.conn.rollback()
            raise
    
    def create_decision_node(self, decision_id: str, title: str, status: str,
                            description: str = "", source_doc_id: str = "",
                            source: str = "unknown", url: str = "") -> bool:
        """Create a decision node"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO decisions (id, title, status, description, source, source_doc_id, url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                """, (decision_id, title, status, description, source, source_doc_id, url))
                self.conn.commit()
                logger.info(f"✓ Decision node created: {decision_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create decision node: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_decision(self, decision_id: str) -> Optional[Dict]:
        """Get a single decision by ID"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM decisions WHERE id = %s", (decision_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"❌ Failed to get decision: {str(e)}")
            return None
    
    def get_all_decisions(self, limit: int = 50) -> List[Dict]:
        """Get all decisions"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM decisions ORDER BY created_at DESC LIMIT %s", (limit,))
                results = cur.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"❌ Failed to get decisions: {str(e)}")
            return []
    
    def create_relationship(self, from_decision_id: str, to_decision_id: str,
                           relationship_type: str, reason: str = "") -> bool:
        """Create a relationship between two decisions"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO decision_relationships (from_decision_id, to_decision_id, relationship_type, reason)
                    VALUES (%s, %s, %s, %s)
                """, (from_decision_id, to_decision_id, relationship_type, reason))
                self.conn.commit()
                logger.info(f"✓ Relationship created: {from_decision_id} -{relationship_type}-> {to_decision_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create relationship: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_decision_dependencies(self, decision_id: str) -> List[Dict]:
        """Get decisions that this one depends on"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT d.id, d.title, d.status, d.description, dr.relationship_type, dr.reason
                    FROM decisions d
                    JOIN decision_relationships dr ON d.id = dr.to_decision_id
                    WHERE dr.from_decision_id = %s
                """, (decision_id,))
                results = cur.fetchall()
                
                formatted = []
                for row in results:
                    formatted.append({
                        "decision": dict(row),
                        "reason": row.get('reason', '')
                    })
                return formatted
        except Exception as e:
            logger.error(f"❌ Failed to get dependencies: {str(e)}")
            return []
    
    def get_decision_impacted(self, decision_id: str) -> List[Dict]:
        """Get decisions impacted by this one"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT d.id, d.title, d.status, d.description, dr.relationship_type, dr.reason
                    FROM decisions d
                    JOIN decision_relationships dr ON d.id = dr.from_decision_id
                    WHERE dr.to_decision_id = %s
                """, (decision_id,))
                results = cur.fetchall()
                
                formatted = []
                for row in results:
                    formatted.append({
                        "decision": dict(row),
                        "reason": row.get('reason', '')
                    })
                return formatted
        except Exception as e:
            logger.error(f"❌ Failed to get impacted decisions: {str(e)}")
            return []
    
    def search_decisions(self, query: str, limit: int = 10) -> List[Dict]:
        """Search decisions by title or description"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM decisions
                    WHERE title ILIKE %s OR description ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (f"%{query}%", f"%{query}%", limit))
                results = cur.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return []
    
    def export_graph_json(self) -> Dict:
        """Export entire graph as JSON"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM decisions")
                decisions = [dict(row) for row in cur.fetchall()]
                
                cur.execute("SELECT * FROM decision_relationships")
                relationships = [dict(row) for row in cur.fetchall()]
                
                return {
                    "nodes": decisions,
                    "relationships": relationships,
                    "node_count": len(decisions),
                    "relationship_count": len(relationships)
                }
        except Exception as e:
            logger.error(f"❌ Export failed: {str(e)}")
            return {"nodes": [], "relationships": [], "node_count": 0, "relationship_count": 0}
    
    def health_check(self) -> bool:
        """Check if connection is healthy"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return False

_postgres_client = None

def init_postgres(database_url: str):
    """Initialize PostgreSQL client"""
    global _postgres_client
    try:
        _postgres_client = PostgresClient(database_url)
        logger.info("✓ PostgreSQL client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL: {str(e)}")
        _postgres_client = None

def get_postgres_client() -> PostgresClient:
    """Get PostgreSQL client instance"""
    if _postgres_client is None:
        logger.error("❌ PostgreSQL client not initialized")
    return _postgres_client