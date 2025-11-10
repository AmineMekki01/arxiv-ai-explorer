"""Neo4j client for knowledge graph operations."""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, Session
from loguru import logger

from src.config import get_settings


class Neo4jClient:
    """Client for Neo4j database operations."""
    
    def __init__(self):
        """Initialize Neo4j client with connection settings."""
        settings = get_settings()
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.database = settings.neo4j_database
        self.driver: Optional[Driver] = None
        
    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            if self.password: # not going to use auth for now, having some issue. once i decide to deploy will change to it
                auth = (self.user, self.password)
                logger.info(f"Connecting to Neo4j at {self.uri} with authentication")
            else:
                auth = None
                logger.info(f"Connecting to Neo4j at {self.uri} without authentication")
                
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=auth,
                max_connection_lifetime=3600,
                max_connection_pool_size=50
            )
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self) -> None:
        """Close Neo4j database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
            
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
            
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a write transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Summary statistics
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                summary = result.consume()
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                }
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
            
    def create_constraints(self) -> None:
        """Create database constraints for data integrity."""
        constraints = [
            "CREATE CONSTRAINT paper_arxiv_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.arxiv_id IS UNIQUE",
            "CREATE CONSTRAINT paper_s2_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.s2_paper_id IS UNIQUE",
            "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.author_id IS UNIQUE",
            "CREATE CONSTRAINT main_category_code IF NOT EXISTS FOR (mc:MainCategory) REQUIRE mc.code IS UNIQUE",
            "CREATE CONSTRAINT sub_category_code IF NOT EXISTS FOR (sc:SubCategory) REQUIRE sc.code IS UNIQUE",
            "CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT year_value IF NOT EXISTS FOR (y:Year) REQUIRE y.year IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                self.execute_write(constraint)
                logger.info(f"Created constraint: {constraint.split('FOR')[0]}")
            except Exception as e:
                logger.warning(f"Constraint creation failed (may already exist): {e}")
                
    def create_indexes(self) -> None:
        """Create database indexes for query performance."""
        indexes = [
            "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
            "CREATE INDEX paper_date IF NOT EXISTS FOR (p:Paper) ON (p.published_date)",
            "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.published_year)",
            "CREATE INDEX paper_category IF NOT EXISTS FOR (p:Paper) ON (p.primary_category)",
            "CREATE INDEX paper_s2_id IF NOT EXISTS FOR (p:Paper) ON (p.s2_paper_id)",
            "CREATE INDEX paper_doi IF NOT EXISTS FOR (p:Paper) ON (p.doi)",
            "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
            "CREATE INDEX author_normalized IF NOT EXISTS FOR (a:Author) ON (a.normalized_name)",
            "CREATE INDEX main_category_code IF NOT EXISTS FOR (mc:MainCategory) ON (mc.code)",
            "CREATE INDEX sub_category_code IF NOT EXISTS FOR (sc:SubCategory) ON (sc.code)",
            "CREATE INDEX institution_name IF NOT EXISTS FOR (i:Institution) ON (i.name)",
        ]
        
        for index in indexes:
            try:
                self.execute_write(index)
                logger.info(f"Created index: {index.split('FOR')[0]}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
                
    def initialize_schema(self) -> None:
        """Initialize database schema with constraints and indexes."""
        logger.info("Initializing Neo4j schema...")
        self.create_constraints()
        self.create_indexes()
        logger.info("Schema initialization complete")
        
    def clear_database(self) -> None:
        """Clear all nodes and relationships from the database. USE WITH CAUTION!"""
        logger.warning("Clearing Neo4j database...")
        self.execute_write("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats_query = """
        MATCH (n)
        WITH labels(n) AS label, count(*) AS count
        RETURN label[0] AS node_type, count
        UNION ALL
        MATCH ()-[r]->()
        RETURN type(r) AS node_type, count(r) AS count
        """
        results = self.execute_query(stats_query)
        
        stats = {
            "nodes": {},
            "relationships": {},
        }
        
        for record in results:
            node_type = record.get("node_type")
            count = record.get("count", 0)
            
            if node_type and node_type.isupper():
                stats["relationships"][node_type] = count
            else:
                stats["nodes"][node_type or "Unknown"] = count
                
        return stats
