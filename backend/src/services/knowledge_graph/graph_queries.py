from typing import List, Dict, Any, Optional
from loguru import logger
from src.utils.arxiv_utils import normalize_arxiv_id

from .neo4j_client import Neo4jClient


class GraphQueryService:
    """Service for querying the knowledge graph."""
    
    def __init__(self, client: Neo4jClient):
        """
        Initialize query service.
        
        Args:
            client: Neo4j client instance
        """
        self.client = client
        
    def find_similar_papers(
        self,
        arxiv_id: str,
        limit: int = 10,
        method: str = "concept"
    ) -> List[Dict[str, Any]]:
        """
        Find papers similar to the given paper based on shared concepts.
        
        Args:
            arxiv_id: Source paper ID
            limit: Maximum number of results
            method: Similarity method (concept, author, citation, combined)
            
        Returns:
            List of similar papers with similarity scores
        """
        if method == "concept":
            query = """
            MATCH (p1:Paper {arxiv_id: $arxiv_id})-[:BELONGS_TO_SUB]->(sc:SubCategory)<-[:BELONGS_TO_SUB]-(p2:Paper)
            WHERE p1 <> p2
            WITH p2, count(sc) as shared_concepts, collect(sc.code) as concepts
            RETURN p2.arxiv_id as arxiv_id,
                   p2.title as title,
                   toString(p2.published_date) as published_date,
                   shared_concepts,
                   concepts
            ORDER BY shared_concepts DESC
            LIMIT $limit
            """
        elif method == "author":
            query = """
            MATCH (p1:Paper {arxiv_id: $arxiv_id})-[:AUTHORED_BY]->(a:Author)<-[:AUTHORED_BY]-(p2:Paper)
            WHERE p1 <> p2
            WITH p2, count(a) as shared_authors, collect(a.name) as authors
            RETURN p2.arxiv_id as arxiv_id,
                   p2.title as title,
                   toString(p2.published_date) as published_date,
                   shared_authors,
                   authors
            ORDER BY shared_authors DESC
            LIMIT $limit
            """
        elif method == "citation":
            query = """
            MATCH (p1:Paper {arxiv_id: $arxiv_id})-[:CITES]->(cited:Paper)<-[:CITES]-(p2:Paper)
            WHERE p1 <> p2
            WITH p2, count(cited) as shared_citations, collect(cited.arxiv_id) as cited_papers
            RETURN p2.arxiv_id as arxiv_id,
                   p2.title as title,
                   toString(p2.published_date) as published_date,
                   shared_citations,
                   cited_papers
            ORDER BY shared_citations DESC
            LIMIT $limit
            """
        else:
            query = """
            MATCH (p1:Paper {arxiv_id: $arxiv_id})
            OPTIONAL MATCH (p1)-[:BELONGS_TO_SUB]->(sc:SubCategory)<-[:BELONGS_TO_SUB]-(p2:Paper)
            OPTIONAL MATCH (p1)-[:AUTHORED_BY]->(a:Author)<-[:AUTHORED_BY]-(p2)
            WHERE p1 <> p2
            WITH p2, 
                 count(DISTINCT sc) as concept_overlap,
                 count(DISTINCT a) as author_overlap
            WHERE concept_overlap > 0 OR author_overlap > 0
            WITH p2,
                 (concept_overlap * 2 + author_overlap * 3) as similarity_score
            RETURN p2.arxiv_id as arxiv_id,
                   p2.title as title,
                   toString(p2.published_date) as published_date,
                   similarity_score
            ORDER BY similarity_score DESC
            LIMIT $limit
            """
            
        canonical = normalize_arxiv_id(arxiv_id)
        parameters = {
            "arxiv_id": canonical,
            "limit": limit
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} similar papers for {arxiv_id} using {method} method")
            return results
        except Exception as e:
            logger.error(f"Failed to find similar papers: {e}")
            return []
            
    def find_citation_network(
        self,
        arxiv_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get citation network around a paper.
        
        Args:
            arxiv_id: Source paper ID
            depth: Network depth (1-3)
            
        Returns:
            Citation network with nodes and edges
        """
        if depth == 1:
            query = """
            MATCH (p:Paper {arxiv_id: $arxiv_id})
            OPTIONAL MATCH (p)-[c:CITES]->(cited:Paper)
            OPTIONAL MATCH (citing:Paper)-[ci:CITES]->(p)
            RETURN collect(DISTINCT {
                       arxiv_id: cited.arxiv_id,
                       s2_paper_id: cited.s2_paper_id,
                       doi: cited.doi,
                       title: cited.title,
                       citation_count: cited.citation_count,
                       is_seminal: cited.is_highly_cited
                   }) as cited_papers,
                   collect(DISTINCT {
                       arxiv_id: citing.arxiv_id,
                       s2_paper_id: citing.s2_paper_id,
                       doi: citing.doi,
                       title: citing.title,
                       citation_count: citing.citation_count,
                       is_seminal: citing.is_highly_cited
                   }) as citing_papers
            """
        elif depth == 2:
            query = """
            MATCH (p:Paper {arxiv_id: $arxiv_id})
            OPTIONAL MATCH path = (p)-[:CITES*1..2]->(cited:Paper)
            OPTIONAL MATCH path2 = (citing:Paper)-[:CITES*1..2]->(p)
            WITH collect(DISTINCT {
                       arxiv_id: cited.arxiv_id,
                       s2_paper_id: cited.s2_paper_id,
                       doi: cited.doi,
                       title: cited.title,
                       citation_count: cited.citation_count,
                       is_seminal: cited.is_highly_cited
                   }) as cited_papers,
                 collect(DISTINCT {
                       arxiv_id: citing.arxiv_id,
                       s2_paper_id: citing.s2_paper_id,
                       doi: citing.doi,
                       title: citing.title,
                       citation_count: citing.citation_count,
                       is_seminal: citing.is_highly_cited
                   }) as citing_papers
            RETURN cited_papers, citing_papers
            """
        else:  # depth == 3
            query = """
            MATCH (p:Paper {arxiv_id: $arxiv_id})
            OPTIONAL MATCH path = (p)-[:CITES*1..3]->(cited:Paper)
            OPTIONAL MATCH path2 = (citing:Paper)-[:CITES*1..3]->(p)
            WITH collect(DISTINCT {
                       arxiv_id: cited.arxiv_id,
                       s2_paper_id: cited.s2_paper_id,
                       doi: cited.doi,
                       title: cited.title,
                       citation_count: cited.citation_count,
                       is_seminal: cited.is_highly_cited
                   }) as cited_papers,
                 collect(DISTINCT {
                       arxiv_id: citing.arxiv_id,
                       s2_paper_id: citing.s2_paper_id,
                       doi: citing.doi,
                       title: citing.title,
                       citation_count: citing.citation_count,
                       is_seminal: citing.is_highly_cited
                   }) as citing_papers
            RETURN cited_papers, citing_papers
            """
            
        canonical = normalize_arxiv_id(arxiv_id)
        parameters = {"arxiv_id": canonical}
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Retrieved citation network for {arxiv_id} at depth {depth}")
            if results and len(results) > 0:
                result = results[0]
                cited = [p for p in result.get("cited_papers", []) if p]
                citing = [p for p in result.get("citing_papers", []) if p]
                logger.info(f"Found {len(cited)} cited papers and {len(citing)} citing papers")
                return {"cited_papers": cited, "citing_papers": citing}
            return {"cited_papers": [], "citing_papers": []}
        except Exception as e:
            logger.error(f"Failed to get citation network for {arxiv_id}: {e}")
            return {"cited_papers": [], "citing_papers": []}
            
    def find_research_path(
        self,
        from_arxiv_id: str,
        to_arxiv_id: str,
        max_hops: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find shortest path between two papers through citations.
        
        Args:
            from_arxiv_id: Starting paper ID
            to_arxiv_id: Ending paper ID
            max_hops: Maximum path length
            
        Returns:
            List of papers in the path
        """
        query = """
        MATCH path = shortestPath(
            (p1:Paper {arxiv_id: $from_id})-[:CITES*1..%d]->(p2:Paper {arxiv_id: $to_id})
        )
        RETURN [node in nodes(path) | {
            arxiv_id: node.arxiv_id,
            title: node.title,
            published_date: node.published_date
        }] as path
        """ % max_hops
        
        from_canonical = normalize_arxiv_id(from_arxiv_id)
        to_canonical = normalize_arxiv_id(to_arxiv_id)
        parameters = {
            "from_id": from_canonical,
            "to_id": to_canonical
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            if results and results[0].get("path"):
                logger.info(f"Found research path from {from_arxiv_id} to {to_arxiv_id}")
                return results[0]["path"]
            logger.info(f"No path found between {from_arxiv_id} and {to_arxiv_id}")
            return []
        except Exception as e:
            logger.error(f"Failed to find research path: {e}")
            return []
            
    def find_influential_papers(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find most influential papers by citation count.
        
        Args:
            category: Filter by category (optional)
            limit: Maximum number of results
            
        Returns:
            List of influential papers
        """
        if category:
            query = """
            MATCH (p:Paper {primary_category: $category})
            OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
            WITH p, count(citing) as citation_count
            RETURN p.arxiv_id as arxiv_id,
                   p.title as title,
                   toString(p.published_date) as published_date,
                   p.primary_category as category,
                   citation_count
            ORDER BY citation_count DESC
            LIMIT $limit
            """
            parameters = {"category": category, "limit": limit}
        else:
            query = """
            MATCH (p:Paper)
            OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
            WITH p, count(citing) as citation_count
            RETURN p.arxiv_id as arxiv_id,
                   p.title as title,
                   toString(p.published_date) as published_date,
                   p.primary_category as category,
                   citation_count
            ORDER BY citation_count DESC
            LIMIT $limit
            """
            parameters = {"limit": limit}
            
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} influential papers")
            return results
        except Exception as e:
            logger.error(f"Failed to find influential papers: {e}")
            return []
            
    def find_trending_concepts(
        self,
        time_window_days: int = 180,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find trending research concepts.
        
        Args:
            time_window_days: Time window for trend analysis
            limit: Maximum number of results
            
        Returns:
            List of trending concepts
        """
        query = """
        MATCH (p:Paper)-[:BELONGS_TO_SUB]->(sc:SubCategory)
        WHERE p.published_date >= datetime() - duration({days: $days})
        WITH sc, count(p) as paper_count, collect(p.arxiv_id)[0..5] as sample_papers
        RETURN sc.code as concept,
               paper_count,
               sample_papers
        ORDER BY paper_count DESC
        LIMIT $limit
        """
        
        parameters = {
            "days": time_window_days,
            "limit": limit
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} trending concepts")
            return results
        except Exception as e:
            logger.error(f"Failed to find trending concepts: {e}")
            return []
            
    def find_author_collaborations(
        self,
        author_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find collaboration network for an author.
        
        Args:
            author_name: Author name
            limit: Maximum number of results
            
        Returns:
            List of collaborators and shared papers
        """
        query = """
        MATCH (a1:Author {normalized_name: toLower($author_name)})<-[:AUTHORED_BY]-(p:Paper)-[:AUTHORED_BY]->(a2:Author)
        WHERE a1 <> a2
        WITH a2, count(p) as collaboration_count, collect(p.arxiv_id) as shared_papers
        RETURN a2.name as collaborator,
               collaboration_count,
               shared_papers
        ORDER BY collaboration_count DESC
        LIMIT $limit
        """
        
        parameters = {
            "author_name": author_name.strip(),
            "limit": limit
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} collaborators for {author_name}")
            return results
        except Exception as e:
            logger.error(f"Failed to find collaborations: {e}")
            return []
            
    def find_research_gaps(
        self,
        concept1: str,
        concept2: str
    ) -> List[Dict[str, Any]]:
        """
        Find potential research gaps between two concepts.
        
        Args:
            concept1: First concept name
            concept2: Second concept name
            
        Returns:
            Papers that bridge the concepts
        """
        query = """
        MATCH (sc1:SubCategory {code: $concept1})<-[:BELONGS_TO_SUB]-(p:Paper)-[:BELONGS_TO_SUB]->(sc2:SubCategory {code: $concept2})
        RETURN p.arxiv_id as arxiv_id,
               p.title as title,
               toString(p.published_date) as published_date,
               p.abstract as abstract
        ORDER BY p.published_date DESC
        LIMIT 10
        """
        
        parameters = {
            "concept1": concept1,
            "concept2": concept2
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} papers bridging {concept1} and {concept2}")
            return results
        except Exception as e:
            logger.error(f"Failed to find research gaps: {e}")
            return []
            
    def get_paper_context(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Get comprehensive context for a paper.
        
        Args:
            arxiv_id: Paper ID
            
        Returns:
            Paper context including all relationships
        """
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
        OPTIONAL MATCH (p)-[:AFFILIATED_WITH]->(i:Institution)
        OPTIONAL MATCH (p)-[:BELONGS_TO_SUB]->(sc:SubCategory)
        OPTIONAL MATCH (p)-[:PUBLISHED_IN]->(y:Year)
        OPTIONAL MATCH (p)-[:CITES]->(cited:Paper)
        OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
        RETURN p.arxiv_id as arxiv_id,
               p.title as title,
               p.abstract as abstract,
               toString(p.published_date) as published_date,
               collect(DISTINCT a.name) as authors,
               collect(DISTINCT sc.code) as categories,
               collect(DISTINCT i.name) as institutions,
               y.year as year,
               collect(DISTINCT cited.arxiv_id) as citations,
               collect(DISTINCT citing.arxiv_id) as cited_by
        """
        
        canonical = normalize_arxiv_id(arxiv_id)
        parameters = {"arxiv_id": canonical}
        
        try:
            results = self.client.execute_query(query, parameters)
            if results:
                logger.info(f"Retrieved context for paper {arxiv_id}")
                return results[0]
            logger.warning(f"No context found for paper {arxiv_id}")
            return {}
        except Exception as e:
            logger.error(f"Failed to get paper context: {e}")
            return {}
    
    def get_internal_citations(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Find citation relationships within a set of papers.
        
        Args:
            paper_ids: List of arXiv IDs
            
        Returns:
            List of citation edges between papers in the set
        """
        if not paper_ids:
            return []
        
        query = """
        MATCH (p1:Paper)-[:CITES]->(p2:Paper)
        WHERE p1.arxiv_id IN $paper_ids 
          AND p2.arxiv_id IN $paper_ids
        RETURN p1.arxiv_id as source,
               p2.arxiv_id as target,
               p2.title as target_title
        """
        
        try:
            results = self.client.execute_query(query, {"paper_ids": paper_ids})
            logger.info(f"Found {len(results)} internal citations among {len(paper_ids)} papers")
            return results
        except Exception as e:
            logger.error(f"Failed to get internal citations: {e}")
            return []
    
    def find_missing_foundations(
        self,
        paper_ids: List[str],
        min_citations: int = 3,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find foundational papers cited by many papers in the set but not in the set themselves.
        
        Args:
            paper_ids: List of arXiv IDs in current result set
            min_citations: Minimum number of citations from result set
            limit: Maximum foundations to return
            
        Returns:
            List of foundational papers with citation counts
        """
        if not paper_ids:
            return []
        
        query = """
        MATCH (result:Paper)-[:CITES]->(cited:Paper)
        WHERE result.arxiv_id IN $paper_ids 
          AND NOT cited.arxiv_id IN $paper_ids
        WITH cited, count(result) as citation_count
        WHERE citation_count >= $min_citations
        RETURN cited.arxiv_id as arxiv_id,
               cited.title as title,
               toString(cited.published_date) as published_date,
               cited.citation_count as total_citations,
               citation_count as cited_by_results
        ORDER BY citation_count DESC, cited.citation_count DESC
        LIMIT $limit
        """
        
        parameters = {
            "paper_ids": paper_ids,
            "min_citations": min_citations,
            "limit": limit
        }
        
        try:
            results = self.client.execute_query(query, parameters)
            logger.info(f"Found {len(results)} missing foundations for {len(paper_ids)} papers")
            return results
        except Exception as e:
            logger.error(f"Failed to find missing foundations: {e}")
            return []
    
    def get_papers_metadata(self, paper_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get graph metadata for a batch of papers.
        
        Args:
            paper_ids: List of arXiv IDs
            
        Returns:
            Dictionary mapping arxiv_id to metadata
        """
        if not paper_ids:
            return {}
        
        query = """
        MATCH (p:Paper)
        WHERE p.arxiv_id IN $paper_ids
        OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
        RETURN p.arxiv_id as arxiv_id,
               p.citation_count as citation_count,
               p.influential_citation_count as influential_citation_count,
               count(DISTINCT citing) as cited_by_count,
               p.published_date as published_date
        """
        
        try:
            results = self.client.execute_query(query, {"paper_ids": paper_ids})
            metadata_dict = {}
            for row in results:
                arxiv_id = row["arxiv_id"]
                metadata_dict[arxiv_id] = {
                    "citation_count": row.get("citation_count", 0),
                    "influential_citation_count": row.get("influential_citation_count", 0),
                    "cited_by_count": row.get("cited_by_count", 0),
                    "is_seminal": row.get("citation_count", 0) > 100,
                    "published_date": str(row.get("published_date", ""))
                }
            logger.info(f"Retrieved metadata for {len(metadata_dict)} papers")
            return metadata_dict
        except Exception as e:
            logger.error(f"Failed to get papers metadata: {e}")
            return {}
