from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import Counter
import numpy as np

from sqlalchemy import or_, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.models.paper_interaction import PaperView, PaperLike, PaperSave
from src.models.user import UserPreferences
from src.services.knowledge_graph import Neo4jClient
from src.core import logger


class PaperRecommender:
    """Generate personalized paper recommendations."""
    
    INTERACTION_WEIGHTS = {
        "saved": 5.0,
        "liked": 3.0,
        "viewed": 0.5
    }
    
    PREFERENCE_WEIGHT = 10.0
    
    DECAY_HALFLIFE_DAYS = 30
    
    def __init__(self, db: Session, neo4j_client: Optional[Neo4jClient] = None):
        self.db = db
        self.neo4j_client = neo4j_client
    
    def get_recommendations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        strategies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id: User identifier
            limit: Number of recommendations to return
            strategies: Which strategies to use (default: all)
        
        Returns:
            List of recommended papers with scores
        """
        if strategies is None:
            strategies = ["content", "graph"] if self.neo4j_client else ["content"]
        
        user_prefs = self._get_user_preferences(user_id)
        
        interactions = self._get_user_interactions(user_id)
        
        if not interactions or not any(interactions.values()):
            return self._cold_start_recommendations(limit, offset, user_prefs)
        
        recommendations = {}
        
        if "content" in strategies:
            content_recs = self._content_based_recommendations(user_id, interactions, user_prefs)
            self._merge_recommendations(recommendations, content_recs, weight=1.0)
        
        if "graph" in strategies and self.neo4j_client:
            graph_recs = self._graph_based_recommendations(user_id, interactions)
            self._merge_recommendations(recommendations, graph_recs, weight=0.8)
        
        saved_arxiv_ids = {
            i.arxiv_id for i in interactions["saved"]
        }
        recommendations = {
            arxiv_id: score 
            for arxiv_id, score in recommendations.items() 
            if arxiv_id not in saved_arxiv_ids
        }

        if not recommendations:
            print("Fallback recommendations")
            interacted_ids = [i.arxiv_id for lst in interactions.values() for i in lst]
            papers_interacted = self.db.query(Paper).filter(Paper.arxiv_id.in_(interacted_ids)).all()
            cat_counter = Counter()
            for p in papers_interacted:
                if p.categories:
                    cat_counter.update(p.categories)
            top_categories = [c for c, _ in cat_counter.most_common(5)]

            if top_categories:
                from sqlalchemy import desc
                candidates = self.db.query(Paper).order_by(desc(Paper.published_date)).limit(1000).all()

                fallback_scores: Dict[str, float] = {}
                top_cat_set = set(top_categories)
                for p in candidates:
                    if p.arxiv_id in saved_arxiv_ids:
                        continue
                    if not p.categories:
                        continue
                    overlap = len(set(p.categories) & top_cat_set)
                    if overlap > 0:
                        score = float(overlap)
                        if p.published_date:
                            now = datetime.now(timezone.utc)
                            pub_date = p.published_date if p.published_date.tzinfo else p.published_date.replace(tzinfo=timezone.utc)
                            days_old = (now - pub_date).days
                            if days_old < 30:
                                score *= 1.3
                            elif days_old < 90:
                                score *= 1.1
                        fallback_scores[p.arxiv_id] = max(fallback_scores.get(p.arxiv_id, 0.0), score)

                if fallback_scores:
                    recommendations = fallback_scores

        sorted_recs = sorted(
            recommendations.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        sorted_recs = sorted_recs[offset: offset + limit]
        
        arxiv_ids = [arxiv_id for arxiv_id, _ in sorted_recs]
        papers = self.db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
        
        paper_map = {p.arxiv_id: p for p in papers}
        
        results = []
        for arxiv_id, score in sorted_recs:
            if arxiv_id in paper_map:
                paper = paper_map[arxiv_id]
                results.append({
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "authors": paper.authors,
                    "published_date": paper.published_date.isoformat() if paper.published_date else None,
                    "categories": paper.categories,
                    "citation_count": paper.citation_count,
                    "recommendation_score": round(score, 3),
                    "thumbnail_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                })
        
        return results
    
    def _get_user_interactions(
        self, 
        user_id: str,
        days: int = 90
    ) -> Dict[str, List[PaperView | PaperLike | PaperSave]]:
        """Get recent user interactions."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        papers_liked = self.db.query(PaperLike).filter(
            PaperLike.user_id == user_id,
            PaperLike.created_at >= since
        ).all()
        
        papers_viewed = self.db.query(PaperView).filter(
            PaperView.user_id == user_id,
            PaperView.created_at >= since
        ).all()

        papers_saved = self.db.query(PaperSave).filter(
            PaperSave.user_id == user_id,
            PaperSave.created_at >= since
        ).all()
        
        return {
            "liked": papers_liked,
            "viewed": papers_viewed,
            "saved": papers_saved
        }
    
    def _get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user's explicit preferences."""
        try:
            prefs = self.db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            return prefs
        except Exception as e:
            logger.error(f"Error fetching user preferences: {e}")
            return None
    
    def _content_based_recommendations(
        self,
        user_id: str,
        interactions: Dict[str, List[PaperView | PaperLike | PaperSave]],
        user_prefs: Optional[UserPreferences] = None
    ) -> Dict[str, float]:
        """Recommend papers similar to what user has interacted with."""
        recommendations = {}
        
        category_weights = Counter()
        author_weights = Counter()
        
        if user_prefs and user_prefs.preferred_categories:
            for category in user_prefs.preferred_categories:
                category_weights[category] += self.PREFERENCE_WEIGHT
        
        now = datetime.now(timezone.utc)
        
        for interaction_type, interaction_list in interactions.items():
            base_weight = self.INTERACTION_WEIGHTS.get(interaction_type, 1.0)
            
            for interaction in interaction_list:
                interaction_time = interaction.created_at
                if interaction_time.tzinfo is None:
                    interaction_time = interaction_time.replace(tzinfo=timezone.utc)
                days_ago = (now - interaction_time).days
                decay_factor = 0.5 ** (days_ago / self.DECAY_HALFLIFE_DAYS)
                
                final_weight = base_weight * decay_factor
                
                paper = self.db.query(Paper).filter(
                    Paper.arxiv_id == interaction.arxiv_id
                ).first()
                
                if paper:
                    if paper.categories:
                        for cat in paper.categories:
                            category_weights[cat] += final_weight
                    if paper.authors:
                        for author in paper.authors[:3]:
                            author_weights[author] += final_weight
            
        top_categories = dict(category_weights.most_common(10))
        top_authors = dict(author_weights.most_common(15))
        
        if not top_categories and not top_authors:
            return recommendations
        
        from sqlalchemy import desc
        candidate_papers = self.db.query(Paper).order_by(desc(Paper.published_date)).limit(1000).all()
        
        interacted_ids = set()
        for interaction_list in interactions.values():
            for interaction in interaction_list:
                interacted_ids.add(interaction.arxiv_id)
        
        for paper in candidate_papers:
            if paper.arxiv_id in interacted_ids:
                continue
                
            score = 0.0
            
            if paper.categories:
                for cat in paper.categories:
                    if cat in top_categories:
                        score += top_categories[cat] * 2.0
            
            if paper.authors:
                for author in paper.authors[:5]:
                    if author in top_authors:
                        score += top_authors[author] * 1.5
            
            if paper.published_date:
                pub_date = paper.published_date
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                days_old = (now - pub_date).days
                if days_old < 30:
                    score *= 1.5
                elif days_old < 90:
                    score *= 1.2
            
            if paper.citation_count and paper.citation_count > 0:
                score *= (1.0 + np.log1p(paper.citation_count) * 0.1)
            
            if score > 0:
                recommendations[paper.arxiv_id] = score
        
        return recommendations
    
    def _merge_recommendations(
        self,
        target: Dict[str, float],
        source: Dict[str, float],
        weight: float = 1.0
    ):
        """Merge recommendation scores with weighting."""
        for arxiv_id, score in source.items():
            target[arxiv_id] = target.get(arxiv_id, 0.0) + (score * weight)
    
    def _graph_based_recommendations(
        self,
        user_id: str,
        interactions: Dict[str, List[PaperView | PaperLike | PaperSave]]
    ) -> Dict[str, float]:
        """Recommend papers using Neo4j graph relationships."""
        if not self.neo4j_client:
            return {}
        
        recommendations = {}
        now = datetime.now(timezone.utc)
        
        weighted_papers = []
        for interaction_type, interaction_list in interactions.items():
            base_weight = self.INTERACTION_WEIGHTS.get(interaction_type, 1.0)
            
            for interaction in interaction_list:
                interaction_time = interaction.created_at
                if interaction_time.tzinfo is None:
                    interaction_time = interaction_time.replace(tzinfo=timezone.utc)
                days_ago = (now - interaction_time).days
                decay_factor = 0.5 ** (days_ago / self.DECAY_HALFLIFE_DAYS)
                
                final_weight = base_weight * decay_factor
                weighted_papers.append((interaction.arxiv_id, final_weight))
        
        weighted_papers.sort(key=lambda x: x[1], reverse=True)
        top_papers = weighted_papers[:10]
        
        try:
            for arxiv_id, weight in top_papers:
                cited_query = """
                MATCH (p:Paper {arxiv_id: $arxiv_id})-[:CITES]->(cited:Paper)
                RETURN cited.arxiv_id as arxiv_id, cited.citation_count as citation_count
                LIMIT 20
                """
                
                with self.neo4j_client.driver.session() as session:
                    cited_results = session.run(cited_query, arxiv_id=arxiv_id)
                    for record in cited_results:
                        rec_id = record["arxiv_id"]
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 2.0 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[rec_id] = recommendations.get(rec_id, 0.0) + score
                
                citing_query = """
                MATCH (citing:Paper)-[:CITES]->(p:Paper {arxiv_id: $arxiv_id})
                RETURN citing.arxiv_id as arxiv_id, citing.citation_count as citation_count
                LIMIT 15
                """
                
                with self.neo4j_client.driver.session() as session:
                    citing_results = session.run(citing_query, arxiv_id=arxiv_id)
                    for record in citing_results:
                        rec_id = record["arxiv_id"]
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 1.5 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[rec_id] = recommendations.get(rec_id, 0.0) + score
                
                coauthor_query = """
                MATCH (p:Paper {arxiv_id: $arxiv_id})-[:AUTHORED_BY]->(a:Author)
                MATCH (a)-[:AUTHORED_BY]-(related:Paper)
                WHERE related.arxiv_id <> $arxiv_id
                RETURN related.arxiv_id as arxiv_id, related.citation_count as citation_count
                LIMIT 10
                """
                
                with self.neo4j_client.driver.session() as session:
                    coauthor_results = session.run(coauthor_query, arxiv_id=arxiv_id)
                    for record in coauthor_results:
                        rec_id = record["arxiv_id"]
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 1.8 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[rec_id] = recommendations.get(rec_id, 0.0) + score
        
        except Exception as e:
            logger.error(f"Error in graph-based recommendations: {e}")
        
        return recommendations
    
    def _cold_start_recommendations(
        self,
        limit: int = 20,
        offset: int = 0,
        user_prefs: Optional[UserPreferences] = None
    ) -> List[Dict[str, Any]]:
        """Return trending/popular papers for new users, biased by preferences."""
        from sqlalchemy import desc
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        
        query = self.db.query(Paper).filter(
            Paper.published_date >= recent_cutoff
        )
        
        if user_prefs and user_prefs.preferred_categories:
            pref_filters = [cast(Paper.categories, JSONB).contains([cat]) for cat in user_prefs.preferred_categories]
            if pref_filters:
                query = query.filter(or_(*pref_filters))
        
        papers = query.order_by(
            desc(Paper.citation_count),
            desc(Paper.published_date)
        ).limit(100).all()
        
        if len(papers) < limit:
            classic_papers = self.db.query(Paper).filter(
                Paper.citation_count > 10
            ).order_by(
                desc(Paper.citation_count)
            ).limit(100).all()
            papers.extend([p for p in classic_papers if p not in papers])
        
        results: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        
        for paper in papers:
            recency_score = 0.0
            if paper.published_date:
                pub_date = paper.published_date
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                days_old = (now - pub_date).days
                recency_score = max(0.0, 1.0 - (days_old / 365.0))
            
            popularity_score = np.log1p(paper.citation_count or 0)
            
            preference_boost = 1.0
            if user_prefs and user_prefs.preferred_categories and paper.categories:
                matching_prefs = len(set(paper.categories) & set(user_prefs.preferred_categories))
                preference_boost = 1.0 + (matching_prefs * 0.5)
            
            trending_score = (recency_score * 2.0 + popularity_score) * preference_boost
            
            results.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "citation_count": paper.citation_count,
                "recommendation_score": round(trending_score, 3),
                "thumbnail_url": f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf",
            })
        
        results.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return results[offset:offset + limit]
