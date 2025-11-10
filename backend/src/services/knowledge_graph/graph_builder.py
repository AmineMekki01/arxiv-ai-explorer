from typing import Dict, Any
from datetime import datetime, timezone
from loguru import logger

from .neo4j_client import Neo4jClient
from src.models.paper import Paper
from src.utils.arxiv_utils import normalize_arxiv_id


class KnowledgeGraphBuilder:
    """
    Intelligent graph builder that creates a multi-layered knowledge graph with:
    - Hierarchical categories (MainCategory → SubCategory)
    - Research areas (from metadata, not key_concepts)
    - Temporal nodes (Year)
    - Quality tiers
    - Enhanced relationships with context
    """
    
    def __init__(self, client: Neo4jClient):
        self.client = client
        
    def create_paper_node(self, paper: Paper) -> Dict[str, Any]:
        """
        Create enhanced paper node with metrics and flags.
        Uses normalized arXiv ID (without version suffix) for consistency.
        """
        canonical_id = normalize_arxiv_id(paper.arxiv_id)
        
        if canonical_id != paper.arxiv_id:
            logger.info(f"Normalizing arXiv ID: {paper.arxiv_id} -> {canonical_id}")
        
        if paper.published_date:
            age_days = (datetime.now(timezone.utc) - paper.published_date).days
            age_years = age_days / 365.25
        else:
            age_days = 0
            age_years = 0.1
            logger.warning(f"Paper {canonical_id} has no published_date; defaulting age metrics to zero")
        citation_velocity = (paper.citation_count or 0) / max(age_years, 0.1)
        
        query = """
        MERGE (p:Paper {arxiv_id: $arxiv_id})
        SET p.s2_paper_id = $s2_paper_id,
            p.original_arxiv_id = $original_arxiv_id,
            p.doi = $doi,
            p.title = $title,
            p.abstract = $abstract,
            p.published_date = datetime($published_date),
            p.published_year = $published_year,
            p.updated_date = datetime($updated_date),
            p.version = $version,
            p.primary_category = $primary_category,
            p.word_count = $word_count,
            p.reading_time = $reading_time,
            p.citation_count = $citation_count,
            p.reference_count = $reference_count,
            p.influential_citation_count = $influential_citation_count,
            p.quality_score = $quality_score,
            p.citation_velocity = $citation_velocity,
            p.age_days = $age_days,
            p.is_external = false,
            p.is_highly_cited = $is_highly_cited,
            p.is_recent = $is_recent,
            p.is_influential = $is_influential,
            p.updated_at = datetime()
        RETURN p
        """
        
        parameters = {
            "arxiv_id": canonical_id,
            "original_arxiv_id": paper.arxiv_id,
            "s2_paper_id": paper.s2_paper_id,
            "doi": paper.doi,
            "title": paper.title,
            "abstract": paper.abstract or "",
            "published_date": paper.published_date.isoformat() if paper.published_date else None,
            "published_year": paper.published_date.year if paper.published_date else None,
            "updated_date": paper.updated_date.isoformat() if paper.updated_date else None,
            "version": paper.version or 1,
            "primary_category": paper.primary_category,
            "word_count": paper.word_count,
            "reading_time": paper.reading_time,
            "citation_count": paper.citation_count or 0,
            "reference_count": paper.reference_count or 0,
            "influential_citation_count": paper.influential_citation_count or 0,
            "quality_score": paper.quality_score,
            "citation_velocity": citation_velocity,
            "age_days": age_days,
            "is_highly_cited": (paper.citation_count or 0) > 100,
            "is_recent": age_days < 365,
            "is_influential": (paper.influential_citation_count or 0) > 10,
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created/updated paper node: {canonical_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create paper node {canonical_id}: {e}")
            raise
    
    def create_category_hierarchy(self, paper: Paper) -> Dict[str, Any]:
        """
        Create hierarchical category structure: MainCategory → SubCategory
        Example: cs → cs.AI, cs.LG
        """
        categories = []
        
        for category in (paper.categories or []):
            if "." in category:
                main_code, sub_code = category.split(".", 1)
                categories.append({
                    "main_code": main_code,
                    "sub_code": category,
                    "is_primary": category == paper.primary_category
                })
            else:
                categories.append({
                    "main_code": category,
                    "sub_code": category,
                    "is_primary": category == paper.primary_category
                })
        
        if not categories:
            return {"nodes_created": 0, "relationships_created": 0}
        
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        UNWIND $categories AS cat
        
        // Create MainCategory
        MERGE (mc:MainCategory {code: cat.main_code})
        ON CREATE SET 
            mc.paper_count = 0,
            mc.created_at = datetime()
        ON MATCH SET
            mc.paper_count = mc.paper_count + 1
        
        // Create SubCategory
        MERGE (sc:SubCategory {code: cat.sub_code})
        ON CREATE SET 
            sc.main_code = cat.main_code,
            sc.paper_count = 0,
            sc.total_citations = 0,
            sc.created_at = datetime()
        ON MATCH SET
            sc.paper_count = sc.paper_count + 1,
            sc.total_citations = sc.total_citations + $citation_count
        
        // Link SubCategory to MainCategory
        MERGE (sc)-[:CHILD_OF]->(mc)
        
        // Link Paper to categories
        MERGE (p)-[r1:BELONGS_TO_MAIN]->(mc)
        MERGE (p)-[r2:BELONGS_TO_SUB {is_primary: cat.is_primary}]->(sc)
        """
        
        canonical_id = normalize_arxiv_id(paper.arxiv_id)
        parameters = {
            "arxiv_id": canonical_id,
            "categories": categories,
            "citation_count": paper.citation_count or 0
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created category hierarchy for {paper.arxiv_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create category hierarchy for {paper.arxiv_id}: {e}")
            raise
        
    def create_author_nodes(self, paper: Paper) -> Dict[str, Any]:
        """
        Create author nodes with position information and affiliations.
        """
        if not paper.authors:
            return {"nodes_created": 0, "relationships_created": 0}
        
        authors_data = []
        total_authors = len(paper.authors)
        
        for idx, author_name in enumerate(paper.authors):
            affiliation = None
            if paper.affiliations and idx < len(paper.affiliations):
                affiliation = paper.affiliations[idx]
            
            author_id = f"author_{hash(author_name.lower().strip()) % 1000000000}"
            authors_data.append({
                "id": author_id,
                "name": author_name.strip(),
                "normalized_name": author_name.lower().strip(),
                "position": idx,
                "is_first_author": idx == 0,
                "is_last_author": idx == total_authors - 1,
                "affiliation_at_time": affiliation,
                "total_authors": total_authors
            })
        
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        UNWIND $authors AS author
        
        MERGE (a:Author {author_id: author.id})
        ON CREATE SET 
            a.name = author.name,
            a.normalized_name = author.normalized_name,
            a.paper_count = 0,
            a.total_citations = 0,
            a.first_paper_date = datetime($published_date),
            a.created_at = datetime()
        ON MATCH SET
            a.paper_count = a.paper_count + 1,
            a.total_citations = a.total_citations + $citation_count,
            a.last_paper_date = datetime($published_date)
        
        MERGE (p)-[r:AUTHORED_BY]->(a)
        ON CREATE SET 
            r.position = author.position,
            r.is_first_author = author.is_first_author,
            r.is_last_author = author.is_last_author,
            r.affiliation_at_time = author.affiliation_at_time,
            r.created_at = datetime()
        """
        
        canonical_id = normalize_arxiv_id(paper.arxiv_id)
        parameters = {
            "arxiv_id": canonical_id,
            "authors": authors_data,
            "citation_count": paper.citation_count or 0,
            "published_date": paper.published_date.isoformat() if paper.published_date else None
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created {len(authors_data)} author nodes for {paper.arxiv_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create authors for {paper.arxiv_id}: {e}")
            raise
    
    def create_institution_nodes(self, paper: Paper) -> Dict[str, Any]:
        """
        Create institution nodes from affiliations.
        """
        if not paper.affiliations:
            return {"nodes_created": 0, "relationships_created": 0}
        
        unique_affiliations = list(set(paper.affiliations))
        
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        UNWIND $affiliations AS affiliation
        
        MERGE (i:Institution {name: affiliation})
        ON CREATE SET 
            i.normalized_name = toLower(affiliation),
            i.paper_count = 0,
            i.total_citations = 0,
            i.created_at = datetime()
        ON MATCH SET
            i.paper_count = i.paper_count + 1,
            i.total_citations = i.total_citations + $citation_count
        
        MERGE (p)-[r:AFFILIATED_WITH]->(i)
        ON CREATE SET r.created_at = datetime()
        """
        
        canonical_id = normalize_arxiv_id(paper.arxiv_id)
        parameters = {
            "arxiv_id": canonical_id,
            "affiliations": unique_affiliations,
            "citation_count": paper.citation_count or 0
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created {len(unique_affiliations)} institution nodes for {paper.arxiv_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create institutions for {paper.arxiv_id}: {e}")
            raise
        
    def create_year_node(self, paper: Paper) -> Dict[str, Any]:
        """
        Create Year node for temporal queries.
        """
        if not paper.published_date:
            return {"nodes_created": 0, "relationships_created": 0}
        
        year = paper.published_date.year
        
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        
        MERGE (y:Year {year: $year})
        ON CREATE SET 
            y.paper_count = 0,
            y.total_citations = 0,
            y.created_at = datetime()
        ON MATCH SET
            y.paper_count = y.paper_count + 1,
            y.total_citations = y.total_citations + $citation_count
        
        MERGE (p)-[r:PUBLISHED_IN]->(y)
        ON CREATE SET r.created_at = datetime()
        """
        
        canonical_id = normalize_arxiv_id(paper.arxiv_id)
        parameters = {
            "arxiv_id": canonical_id,
            "year": year,
            "citation_count": paper.citation_count or 0
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created year node {year} for {paper.arxiv_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create year node for {paper.arxiv_id}: {e}")
            raise
        
    def create_citation_relationships(self, paper: Paper) -> Dict[str, Any]:
        """
        Create smart citation relationships with context inference.
        All arXiv IDs are normalized to canonical form (without version suffix).
        """
        if not paper.references:
            return {"relationships_created": 0}
        
        citing_id = normalize_arxiv_id(paper.arxiv_id)
        
        citations = []
        for ref in paper.references:
            arxiv_id = ref.get("arxiv_id")
            s2_id = ref.get("s2_paper_id")
            doi = ref.get("doi")
            norm_arxiv = normalize_arxiv_id(arxiv_id) if arxiv_id else None
            # Skip if we have none of the identifiers
            if not (norm_arxiv or s2_id or doi):
                continue
            citations.append({
                "arxiv_id": norm_arxiv,
                "original_arxiv_id": arxiv_id,
                "s2_paper_id": s2_id,
                "doi": doi,
                "title": ref.get("title", ""),
                "year": ref.get("year"),
                "is_influential": ref.get("is_influential", False)
            })
        
        if not citations:
            return {"relationships_created": 0}
        
        query = """
        MATCH (citing:Paper {arxiv_id: $citing_id})
        UNWIND $citations AS citation
        WITH citing, citation
        WHERE citation.arxiv_id IS NOT NULL OR citation.s2_paper_id IS NOT NULL OR citation.doi IS NOT NULL

        OPTIONAL MATCH (n1:Paper {arxiv_id: citation.arxiv_id})
        OPTIONAL MATCH (n2:Paper {s2_paper_id: citation.s2_paper_id})
        OPTIONAL MATCH (n3:Paper {doi: citation.doi})
        WITH citing, citation, coalesce(n1, n2, n3) AS citedExisting

        FOREACH (_ IN CASE WHEN citedExisting IS NULL AND citation.arxiv_id IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {arxiv_id: citation.arxiv_id})
        )
        FOREACH (_ IN CASE WHEN citedExisting IS NULL AND citation.arxiv_id IS NULL AND citation.s2_paper_id IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {s2_paper_id: citation.s2_paper_id})
        )
        FOREACH (_ IN CASE WHEN citedExisting IS NULL AND citation.arxiv_id IS NULL AND citation.s2_paper_id IS NULL AND citation.doi IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {doi: citation.doi})
        )

        WITH citing, citation
        OPTIONAL MATCH (m1:Paper {arxiv_id: citation.arxiv_id})
        OPTIONAL MATCH (m2:Paper {s2_paper_id: citation.s2_paper_id})
        OPTIONAL MATCH (m3:Paper {doi: citation.doi})
        WITH citing, citation, coalesce(m1, m2, m3) AS cited
        WITH citing, citation, cited
        WHERE cited IS NOT NULL
        
        SET cited.title = coalesce(citation.title, cited.title),
            cited.original_arxiv_id = coalesce(citation.original_arxiv_id, cited.original_arxiv_id),
            cited.s2_paper_id = coalesce(citation.s2_paper_id, cited.s2_paper_id),
            cited.doi = coalesce(citation.doi, cited.doi),
            cited.is_external = true,
            cited.published_year = coalesce(citation.year, cited.published_year),
            cited.updated_at = datetime(),
            cited.created_at = coalesce(cited.created_at, datetime())
        
        MERGE (citing)-[r:CITES]->(cited)
        ON CREATE SET 
            r.is_influential = citation.is_influential,
            r.created_at = datetime()
        ON MATCH SET
            r.is_influential = citation.is_influential
        
        WITH citing, cited, citation
        WHERE citation.is_influential = true
        MERGE (citing)-[b:BUILDS_ON]->(cited)
        ON CREATE SET b.created_at = datetime()
        """
        
        parameters = {
            "citing_id": citing_id,
            "citations": citations
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created {len(citations)} citation relationships for {citing_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create citations for {citing_id}: {e}")
            raise
    
    def create_reverse_citations(self, paper: Paper) -> Dict[str, Any]:
        """
        Create incoming citation relationships from cited_by field.
        All arXiv IDs are normalized to canonical form (without version suffix).
        """
        if not paper.cited_by:
            return {"relationships_created": 0}
        
        cited_id = normalize_arxiv_id(paper.arxiv_id)
        
        citing_papers = []
        for citing in paper.cited_by:
            arxiv_id = citing.get("arxiv_id")
            s2_id = citing.get("s2_paper_id")
            doi = citing.get("doi")
            norm_arxiv = normalize_arxiv_id(arxiv_id) if arxiv_id else None
            if not (norm_arxiv or s2_id or doi):
                continue
            citing_papers.append({
                "arxiv_id": norm_arxiv,
                "original_arxiv_id": arxiv_id,
                "s2_paper_id": s2_id,
                "doi": doi,
                "title": citing.get("title", ""),
                "year": citing.get("year")
            })
        
        if not citing_papers:
            return {"relationships_created": 0}
        
        query = """
        MATCH (cited:Paper {arxiv_id: $cited_id})
        UNWIND $citing_papers AS citing_paper
        WITH cited, citing_paper
        WHERE citing_paper.arxiv_id IS NOT NULL OR citing_paper.s2_paper_id IS NOT NULL OR citing_paper.doi IS NOT NULL

        OPTIONAL MATCH (n1:Paper {arxiv_id: citing_paper.arxiv_id})
        OPTIONAL MATCH (n2:Paper {s2_paper_id: citing_paper.s2_paper_id})
        OPTIONAL MATCH (n3:Paper {doi: citing_paper.doi})
        WITH cited, citing_paper, coalesce(n1, n2, n3) AS citingExisting

        FOREACH (_ IN CASE WHEN citingExisting IS NULL AND citing_paper.arxiv_id IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {arxiv_id: citing_paper.arxiv_id})
        )
        FOREACH (_ IN CASE WHEN citingExisting IS NULL AND citing_paper.arxiv_id IS NULL AND citing_paper.s2_paper_id IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {s2_paper_id: citing_paper.s2_paper_id})
        )
        FOREACH (_ IN CASE WHEN citingExisting IS NULL AND citing_paper.arxiv_id IS NULL AND citing_paper.s2_paper_id IS NULL AND citing_paper.doi IS NOT NULL THEN [1] ELSE [] END |
          MERGE (:Paper {doi: citing_paper.doi})
        )

        WITH cited, citing_paper
        OPTIONAL MATCH (m1:Paper {arxiv_id: citing_paper.arxiv_id})
        OPTIONAL MATCH (m2:Paper {s2_paper_id: citing_paper.s2_paper_id})
        OPTIONAL MATCH (m3:Paper {doi: citing_paper.doi})
        WITH cited, citing_paper, coalesce(m1, m2, m3) AS citing
        WITH cited, citing_paper, citing
        WHERE citing IS NOT NULL
        
        SET citing.title = coalesce(citing_paper.title, citing.title),
            citing.original_arxiv_id = coalesce(citing_paper.original_arxiv_id, citing.original_arxiv_id),
            citing.s2_paper_id = coalesce(citing_paper.s2_paper_id, citing.s2_paper_id),
            citing.doi = coalesce(citing_paper.doi, citing.doi),
            citing.is_external = true,
            citing.published_year = coalesce(citing_paper.year, citing.published_year),
            citing.updated_at = datetime(),
            citing.created_at = coalesce(citing.created_at, datetime())
        
        MERGE (citing)-[r:CITES]->(cited)
        ON CREATE SET r.created_at = datetime()
        """
        
        parameters = {
            "cited_id": cited_id,
            "citing_papers": citing_papers
        }
        
        try:
            result = self.client.execute_write(query, parameters)
            logger.info(f"Created {len(citing_papers)} reverse citations for {cited_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create reverse citations for {cited_id}: {e}")
            raise
        
    def build_full_graph(self, paper: Paper) -> Dict[str, Any]:
        """
        Build complete smart graph structure for a paper.
        """
        logger.info(f"Building smart knowledge graph for: {paper.arxiv_id}")
        
        summary = {
            "arxiv_id": paper.arxiv_id,
            "nodes_created": 0,
            "relationships_created": 0,
            "operations": []
        }
        
        try:
            result = self.create_paper_node(paper)
            summary["nodes_created"] += result.get("nodes_created", 0)
            summary["operations"].append("paper_node")
            
            result = self.create_category_hierarchy(paper)
            summary["nodes_created"] += result.get("nodes_created", 0)
            summary["relationships_created"] += result.get("relationships_created", 0)
            summary["operations"].append("category_hierarchy")
            
            result = self.create_author_nodes(paper)
            summary["nodes_created"] += result.get("nodes_created", 0)
            summary["relationships_created"] += result.get("relationships_created", 0)
            summary["operations"].append("authors")
            
            result = self.create_institution_nodes(paper)
            summary["nodes_created"] += result.get("nodes_created", 0)
            summary["relationships_created"] += result.get("relationships_created", 0)
            summary["operations"].append("institutions")
            
            result = self.create_year_node(paper)
            summary["nodes_created"] += result.get("nodes_created", 0)
            summary["relationships_created"] += result.get("relationships_created", 0)
            summary["operations"].append("year")
            
            if paper.references:
                result = self.create_citation_relationships(paper)
                summary["relationships_created"] += result.get("relationships_created", 0)
                summary["operations"].append("citations")
            
            if paper.cited_by:
                result = self.create_reverse_citations(paper)
                summary["relationships_created"] += result.get("relationships_created", 0)
                summary["operations"].append("reverse_citations")
            
            logger.info(f"✅ Smart graph built for {paper.arxiv_id}: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to build smart graph for {paper.arxiv_id}: {e}")
            raise
