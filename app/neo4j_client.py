from neo4j import GraphDatabase
from app.config import config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Neo4jClient:
    """Neo4j client for managing decision graphs"""
    
    def __init__(self):
        """Initialize Neo4j connection"""
        try:
            self.driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            logger.info("✓ Neo4j connected successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {str(e)}")
            self.driver = None
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def health_check(self) -> bool:
        """Check if Neo4j is connected"""
        try:
            if not self.driver:
                return False
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"❌ Neo4j health check failed: {str(e)}")
            return False
    
    def create_constraints(self):
        """Create database constraints for unique IDs"""
        if not self.driver:
            logger.warning("Neo4j driver not initialized, skipping constraints")
            return
        
        with self.driver.session() as session:
            try:
                # Create unique constraint on Decision.id
                session.run(
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE"
                )
                logger.info("✓ Decision ID constraint created")
                
                # Create unique constraint on Person.name
                session.run(
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE"
                )
                logger.info("✓ Person name constraint created")
                
            except Exception as e:
                logger.warning(f"Constraint creation issue: {str(e)}")
    
    def create_decision_node(
        self,
        decision_id: str,
        title: str,
        status: str,
        description: str = "",
        source_doc_id: str = "",
        source: str = "unknown",
        url: str = ""
    ) -> bool:
        """
        Create a Decision node in Neo4j.
        
        Args:
            decision_id: Unique ID for decision
            title: Decision title
            status: "decided", "approved", "rejected", "final", "selected"
            description: Full decision description
            source_doc_id: ChromaDB document ID
            source: Source (slack, gmail, etc.)
            url: URL reference
            
        Returns:
            True if successful
        """
        if not self.driver:
            logger.error("Neo4j driver not initialized")
            return False
        
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    CREATE (d:Decision {
                        id: $id,
                        title: $title,
                        status: $status,
                        description: $description,
                        source_doc_id: $source_doc_id,
                        source: $source,
                        url: $url,
                        created_at: datetime(),
                        updated_at: datetime()
                    })
                    """,
                    id=decision_id,
                    title=title,
                    status=status,
                    description=description,
                    source_doc_id=source_doc_id,
                    source=source,
                    url=url
                )
                logger.info(f"✓ Decision node created: {decision_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create decision node: {str(e)}")
            return False
    
    def create_person_node(self, name: str, role: str = "team_member") -> bool:
        """
        Create a Person node in Neo4j.
        
        Args:
            name: Person's name
            role: Role (e.g., "tech_lead", "manager", "team_member")
            
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (p:Person {name: $name})
                    SET p.role = $role, p.updated_at = datetime()
                    """,
                    name=name,
                    role=role
                )
                logger.info(f"✓ Person node created/merged: {name}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create person node: {str(e)}")
            return False
    
    def create_relationship(
        self,
        from_decision_id: str,
        to_decision_id: str,
        relationship_type: str,
        reason: str = ""
    ) -> bool:
        """
        Create a relationship between two decisions.
        
        Args:
            from_decision_id: Starting decision ID
            to_decision_id: Ending decision ID
            relationship_type: "DEPENDS_ON", "BLOCKS", "RELATED_TO", "SUPERSEDES"
            reason: Why this relationship exists
            
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            allowed_types = {"DEPENDS_ON", "BLOCKS", "RELATED_TO", "SUPERSEDES"}
            if relationship_type not in allowed_types:
                logger.warning(f"Invalid relationship type '{relationship_type}', defaulting to RELATED_TO")
                relationship_type = "RELATED_TO"

            with self.driver.session() as session:
                session.run(
                    f"""
                    MATCH (d1:Decision {{id: $from_id}})
                    MATCH (d2:Decision {{id: $to_id}})
                    CREATE (d1)-[r:{relationship_type} {{reason: $reason, created_at: datetime()}}]->(d2)
                    """,
                    from_id=from_decision_id,
                    to_id=to_decision_id,
                    reason=reason
                )
                logger.info(f"✓ Relationship created: {from_decision_id} -{relationship_type}-> {to_decision_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create relationship: {str(e)}")
            return False
    
    def get_decision(self, decision_id: str) -> dict:
        """
        Get a decision node by ID.
        
        Args:
            decision_id: Decision ID
            
        Returns:
            Decision data as dictionary
        """
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (d:Decision {id: $id}) RETURN d",
                    id=decision_id
                )
                record = result.single()
                if record:
                    return dict(record['d'])
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get decision: {str(e)}")
            return {}
    
    def get_decision_dependencies(self, decision_id: str) -> list:
        """
        Get all decisions that this decision depends on.
        
        Args:
            decision_id: Decision ID
            
        Returns:
            List of dependent decisions
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Decision {id: $id})-[r:DEPENDS_ON]->(dep:Decision)
                    RETURN dep, r
                    """,
                    id=decision_id
                )
                dependencies = []
                for record in result:
                    dependencies.append({
                        "decision": dict(record['dep']),
                        "reason": record['r'].get('reason', '')
                    })
                return dependencies
        except Exception as e:
            logger.error(f"❌ Failed to get dependencies: {str(e)}")
            return []
    
    def get_decision_impacted(self, decision_id: str) -> list:
        """
        Get all decisions impacted by this decision.
        
        Args:
            decision_id: Decision ID
            
        Returns:
            List of impacted decisions
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Decision {id: $id})<-[r:DEPENDS_ON]-(imp:Decision)
                    RETURN imp, r
                    """,
                    id=decision_id
                )
                impacted = []
                for record in result:
                    impacted.append({
                        "decision": dict(record['imp']),
                        "reason": record['r'].get('reason', '')
                    })
                return impacted
        except Exception as e:
            logger.error(f"❌ Failed to get impacted decisions: {str(e)}")
            return []
    
    def get_all_decisions(self, limit: int = 50) -> list:
        """
        Get all decisions in the graph.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of decisions
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (d:Decision) RETURN d ORDER BY d.created_at DESC LIMIT $limit",
                    limit=limit
                )
                decisions = []
                for record in result:
                    decisions.append(dict(record['d']))
                return decisions
        except Exception as e:
            logger.error(f"❌ Failed to get decisions: {str(e)}")
            return []
    
    def export_graph_json(self) -> dict:
        """
        Export entire graph as JSON for visualization.
        
        Returns:
            Dictionary with nodes and relationships
        """
        if not self.driver:
            return {"nodes": [], "relationships": []}
        
        try:
            with self.driver.session() as session:
                # Get all nodes
                nodes_result = session.run("MATCH (n:Decision) RETURN n")
                nodes = []
                for record in nodes_result:
                    node = dict(record['n'])
                    nodes.append({
                        "id": node.get('id'),
                        "label": node.get('title', node.get('id')),
                        "status": node.get('status', 'unknown'),
                        "properties": node
                    })
                
                # Get all relationships
                rels_result = session.run(
                    "MATCH (a:Decision)-[r]->(b:Decision) RETURN a.id as from, b.id as to, type(r) as type, r"
                )
                relationships = []
                for record in rels_result:
                    relationships.append({
                        "from": record['from'],
                        "to": record['to'],
                        "type": record['type'],
                        "reason": record['r'].get('reason', '')
                    })
                
                return {
                    "nodes": nodes,
                    "relationships": relationships,
                    "node_count": len(nodes),
                    "relationship_count": len(relationships)
                }
        except Exception as e:
            logger.error(f"❌ Failed to export graph: {str(e)}")
            return {"nodes": [], "relationships": [], "error": str(e)}

# Global client instance
neo4j_client = None

def init_neo4j():
    """Initialize Neo4j client"""
    global neo4j_client
    neo4j_client = Neo4jClient()
    if neo4j_client.driver:
        neo4j_client.create_constraints()
    return neo4j_client

def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client instance"""
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = init_neo4j()
    return neo4j_client