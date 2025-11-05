import sys
from typing import List, Dict, Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

sys.path.insert(0, "/opt/airflow")

from src.database import get_sync_session
from src.models.paper import Paper
from src.services.knowledge_graph import Neo4jClient, KnowledgeGraphBuilder
from src.core import logger


class InitializeKGSchemaOperator(BaseOperator):
    """
    Initialize Neo4j schema with constraints and indexes.
    Run this once before building the knowledge graph.
    """
    
    template_fields = ()
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Initialize Neo4j schema."""
        self.log.info("🔧 Initializing Neo4j schema...")
        
        try:
            with Neo4jClient() as client:
                client.initialize_schema()
                stats = client.get_stats()
                
                self.log.info("Schema initialized successfully")
                self.log.info(f"Current graph stats: {stats}")
                
                return {
                    "status": "success",
                    "stats": stats
                }
                
        except Exception as e:
            self.log.error(f"Failed to initialize schema: {e}")
            raise


class BuildKnowledgeGraphOperator(BaseOperator):
    """
    Build knowledge graph from papers.
    Creates nodes for papers, authors, concepts, institutions
    and relationships including citations.
    """
    
    template_fields = ("input_task_id",)
    
    def __init__(
        self,
        input_task_id: str = None,
        max_papers: int = None,
        only_missing: bool = False,
        **kwargs
    ):
        """
        Initialize operator.
        
        Args:
            input_task_id: Task ID that provides paper data (optional)
            max_papers: Maximum papers to process
            only_missing: Only process papers not yet in graph
        """
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.max_papers = max_papers
        self.only_missing = only_missing
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Build knowledge graph for papers."""
        self.log.info("Starting knowledge graph building...")
        
        if self.input_task_id:
            papers = context["ti"].xcom_pull(task_ids=self.input_task_id)
            if not papers:
                self.log.info("No papers from XCom")
                return {"processed": 0, "success": 0, "failed": 0}
        else:
            papers = self._load_papers_from_db()
        
        papers = self._normalize_papers(papers)

        if not papers:
            self.log.info("No papers to process")
            return {"processed": 0, "success": 0, "failed": 0}
        
        self.log.info(f"Processing {len(papers)} papers for knowledge graph")
        
        results = self._build_graphs(papers)
        
        self.log.info(
            "Knowledge graph building complete: "
            f"{results['success']} succeeded, {results['failed']} failed"
        )
        
        return results
    
    def _normalize_papers(self, papers) -> List[Paper]:
        """Normalize XCom payloads to ORM Paper objects.
        Expected shape (from upstream):
          { 'persisted': int, 'skipped': int, 'papers': [ { 'arxiv_id': str }, ... ] }
        Falls back to handling lists of strings/dicts/ORM Paper.
        """
        if not papers:
            return []

        if isinstance(papers, dict) and 'papers' in papers and isinstance(papers['papers'], (list, tuple)):
            raw_items = papers['papers']
            arxiv_ids = [self._normalize_arxiv_id(item.get('arxiv_id')) for item in raw_items if isinstance(item, dict) and item.get('arxiv_id')]
        else:
            try:
                seq = list(papers) if not isinstance(papers, (list, tuple)) else papers
            except Exception:
                return []

            if not seq:
                return []

            if isinstance(seq[0], Paper):
                return list(seq)

            arxiv_ids: List[str] = []
            if isinstance(seq[0], str):
                arxiv_ids = [self._normalize_arxiv_id(p) for p in seq if isinstance(p, str) and p]
            elif isinstance(seq[0], dict):
                arxiv_ids = [self._normalize_arxiv_id(p.get('arxiv_id')) for p in seq if isinstance(p, dict) and p.get('arxiv_id')]
            else:
                try:
                    arxiv_ids = [self._normalize_arxiv_id(getattr(p, 'arxiv_id')) for p in seq if getattr(p, 'arxiv_id', None)]
                    if arxiv_ids and isinstance(seq[0], Paper):
                        return list(seq)
                except Exception:
                    pass

        if not arxiv_ids:
            self.log.warning("Unsupported papers payload type for normalization; skipping.")
            return []

        def _strip_version(s: str) -> str:
            if 'v' in s:
                parts = s.rsplit('v', 1)
                if parts[1].isdigit():
                    return parts[0]
            return s

        query_ids = list({*(arxiv_ids), *(_strip_version(a) for a in arxiv_ids if a)})
        with get_sync_session() as session:
            db_papers = session.query(Paper).filter(Paper.arxiv_id.in_(query_ids)).all()
        by_id = {p.arxiv_id: p for p in db_papers}

        normalized: List[Paper] = []
        missing: List[str] = []
        for a in arxiv_ids:
            if a in by_id:
                normalized.append(by_id[a])
            else:
                av = _strip_version(a)
                if av in by_id:
                    normalized.append(by_id[av])
                else:
                    missing.append(a)
        if missing:
            self.log.warning(f"Some arxiv_ids not found in DB and will be skipped: {missing}")
        return normalized

    @staticmethod
    def _normalize_arxiv_id(raw: str | None) -> str | None:
        if not raw:
            return None
        s = str(raw).strip()
        if s.lower().startswith('arxiv:'):
            s = s.split(':', 1)[1]
        return s

    def _load_papers_from_db(self) -> List[Paper]:
        with get_sync_session() as session:
            query = session.query(Paper).filter(Paper.s2_paper_id.isnot(None))
            candidates = query.all()

        if not self.only_missing:
            return candidates if not self.max_papers else candidates[:self.max_papers]

        arxiv_ids = [p.arxiv_id for p in candidates]
        with Neo4jClient() as client:
            existing = self._get_existing_ids_in_graph(client, arxiv_ids)

        missing = [p for p in candidates if p.arxiv_id not in existing]
        return missing if not self.max_papers else missing[:self.max_papers]

    def _get_existing_ids_in_graph(self, client, arxiv_ids: list[str]) -> set[str]:
        if not arxiv_ids:
            return set()
        existing = set()
        BATCH = 500
        query = """
        UNWIND $ids AS id
        MATCH (p:Paper {arxiv_id: id})
        RETURN p.arxiv_id AS arxiv_id
        """
        for i in range(0, len(arxiv_ids), BATCH):
            batch = arxiv_ids[i:i+BATCH]
            rows = client.execute_query(query, {"ids": batch}) or []
            existing.update(r["arxiv_id"] for r in rows)
        return existing

    def _build_graphs(self, papers: List[Paper]) -> Dict[str, Any]:
        """Build knowledge graph for papers."""
        success_count = 0
        failed_count = 0
        total_nodes = 0
        total_relationships = 0
        
        try:
            with Neo4jClient() as client:
                builder = KnowledgeGraphBuilder(client)
                
                for idx, paper in enumerate(papers, 1):
                    try:
                        arxiv_id = getattr(paper, 'arxiv_id', None) or str(paper)
                        self.log.info(f"[{idx}/{len(papers)}] Building graph for {arxiv_id}")
                        
                        result = builder.build_full_graph(paper)
                        
                        total_nodes += result.get("nodes_created", 0)
                        total_relationships += result.get("relationships_created", 0)
                        success_count += 1
                        
                        self.log.info(
                            f"{arxiv_id}: "
                            f"+{result.get('nodes_created', 0)} nodes, "
                            f"+{result.get('relationships_created', 0)} relationships"
                        )
                        
                    except Exception as e:
                        failed_count += 1
                        self.log.error(f"Failed to build graph for {getattr(paper, 'arxiv_id', None) or str(paper)}: {e}")
                
                stats = client.get_stats()
                self.log.info(f"Final graph stats: {stats}")
                
        except Exception as e:
            self.log.error(f"Knowledge graph building failed: {e}")
            raise
        
        return {
            "processed": len(papers),
            "success": success_count,
            "failed": failed_count,
            "nodes_created": total_nodes,
            "relationships_created": total_relationships,
        }


class UpdateCitationNetworkOperator(BaseOperator):
    """
    Update citation relationships in the knowledge graph.
    Used when citation data is refreshed from Semantic Scholar.
    """
    
    template_fields = ("input_task_id",)
    
    def __init__(
        self,
        input_task_id: str = None,
        **kwargs
    ):
        """
        Initialize operator.
        
        Args:
            input_task_id: Task ID that provides updated citation data
        """
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Update citation relationships."""
        self.log.info("Updating citation network...")
        
        if self.input_task_id:
            papers = context["ti"].xcom_pull(task_ids=self.input_task_id)
            if not papers:
                self.log.info("No papers from XCom")
                return {"processed": 0, "updated": 0}
        else:
            papers = self._load_recently_updated_papers()
        
        if not papers:
            self.log.info("No papers to update")
            return {"processed": 0, "updated": 0}
        
        self.log.info(f"Updating citations for {len(papers)} papers")
        
        results = self._update_citations(papers)
        
        self.log.info(f"Citation network updated: {results['updated']} papers")
        
        return results
    
    def _load_recently_updated_papers(self) -> List[Paper]:
        """Load papers with recently updated citations."""
        from datetime import datetime, timedelta, timezone
        
        with get_sync_session() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            
            return session.query(Paper).filter(
                Paper.last_citation_update >= cutoff,
                Paper.s2_paper_id.isnot(None)
            ).all()
    
    def _update_citations(self, papers: List[Paper]) -> Dict[str, Any]:
        """Update citation relationships for papers."""
        updated_count = 0
        
        try:
            with Neo4jClient() as client:
                builder = KnowledgeGraphBuilder(client)
                
                for idx, paper in enumerate(papers, 1):
                    try:
                        self.log.info(f"[{idx}/{len(papers)}] Updating citations for {paper.arxiv_id}")
                        
                        delete_query = """
                        MATCH (p:Paper {arxiv_id: $arxiv_id})-[r:CITES]->()
                        DELETE r
                        """
                        client.execute_write(delete_query, {"arxiv_id": paper.arxiv_id})
                        
                        if paper.references:
                            builder.create_citation_relationships(paper)
                        
                        if paper.cited_by:
                            builder.create_reverse_citations(paper)
                        
                        updated_count += 1
                        self.log.info(f"Updated citations for {paper.arxiv_id}")
                        
                    except Exception as e:
                        self.log.error(f"Failed to update citations for {paper.arxiv_id}: {e}")
                
        except Exception as e:
            self.log.error(f"Citation network update failed: {e}")
            raise
        
        return {
            "processed": len(papers),
            "updated": updated_count,
        }


class GetGraphStatsOperator(BaseOperator):
    """Get statistics about the knowledge graph."""
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Get graph statistics."""
        self.log.info("Getting graph statistics...")
        
        try:
            with Neo4jClient() as client:
                stats = client.get_stats()
                
                self.log.info(f"Graph Stats:")
                self.log.info(f"Nodes: {stats.get('nodes', {})}")
                self.log.info(f"Relationships: {stats.get('relationships', {})}")
                
                return stats
                
        except Exception as e:
            self.log.error(f"Failed to get stats: {e}")
            raise
