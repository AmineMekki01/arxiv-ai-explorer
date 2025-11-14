from typing import List, Dict, Any, Optional, Tuple
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
from src.services.retrieval.retriever import get_retriever
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
    
    @staticmethod
    def _base_arxiv_id(arxiv_id: Optional[str]) -> Optional[str]:
        """Normalize arxiv_id by stripping version suffix like 'v3'."""
        if not arxiv_id:
            return None
        if 'v' in arxiv_id:
            parts = arxiv_id.split('v')
            if len(parts) >= 2 and parts[-1].isdigit():
                return 'v'.join(parts[:-1])
        return arxiv_id
    
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
            strategies = ["semantic", "content", "graph"] if self.neo4j_client else ["semantic", "content"]
        
        user_prefs = self._get_user_preferences(user_id)
        
        interactions = self._get_user_interactions(user_id)
        
        if not interactions or not any(interactions.values()):
            if strategies and "trending" in strategies:
                return self._cold_start_recommendations(limit, offset, user_prefs)
            return self._cold_start_recommendations(limit, offset, user_prefs)
        
        recommendations: Dict[str, float] = {}
        reasons_map: Dict[str, List[str]] = {}
        
        if strategies and "trending" in strategies:
            return self._cold_start_recommendations(limit, offset, user_prefs)

        if "semantic" in strategies:
            sem_scores, sem_reasons = self._semantic_recommendations(user_id, interactions)
            self._merge_recommendations(recommendations, sem_scores, weight=1.0)
            for k, vals in sem_reasons.items():
                reasons_map.setdefault(k, []).extend(vals)

        if "content" in strategies:
            content_scores, content_reasons = self._content_based_recommendations(user_id, interactions, user_prefs)
            self._merge_recommendations(recommendations, content_scores, weight=1.0)
            for k, vals in content_reasons.items():
                reasons_map.setdefault(k, []).extend(vals)
        
        if "graph" in strategies and self.neo4j_client:
            print(f"interactions {interactions}")
            graph_scores, graph_reasons = self._graph_based_recommendations(user_id, interactions)
            self._merge_recommendations(recommendations, graph_scores, weight=0.8)
            for k, vals in graph_reasons.items():
                reasons_map.setdefault(k, []).extend(vals)
            print(f"graph scores {graph_scores}")
            print(f"graph reasons {graph_reasons}")
        
        recent_interacted_ids = {
            i.arxiv_id for lst in interactions.values() for i in lst
        }
        recommendations = {
            arxiv_id: score
            for arxiv_id, score in recommendations.items()
            if arxiv_id not in recent_interacted_ids
        }
        for rid in list(reasons_map.keys()):
            if rid not in recommendations:
                reasons_map.pop(rid, None)

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

        arxiv_ids_all = list(recommendations.keys())
        if not arxiv_ids_all:
            return []

        papers_all = self.db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids_all)).all()
        paper_map_all = {p.arxiv_id: p for p in papers_all}

        candidates_list: List[Tuple[str, float]] = [
            (aid, recommendations[aid]) for aid in arxiv_ids_all if aid in paper_map_all
        ]
        candidates_list.sort(key=lambda x: x[1], reverse=True)

        mmr_k = min(limit + offset, len(candidates_list))
        selected_ids = self._mmr_select(
            candidates=candidates_list,
            paper_map=paper_map_all,
            k=mmr_k,
            lambda_=0.3,
        )
        selected_ids = selected_ids[offset: offset + limit]
        
        results = []
        for arxiv_id in selected_ids:
            paper = paper_map_all.get(arxiv_id)
            if not paper:
                continue
            score = recommendations.get(arxiv_id, 0.0)
            results.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "citation_count": paper.citation_count,
                "recommendation_score": round(score, 3),
                "thumbnail_url": f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf",
                "reasons": reasons_map.get(paper.arxiv_id, [])[:2],
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
    ) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        """Recommend papers similar to what user has interacted with."""
        recommendations: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}
        
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
            return recommendations, reasons

        recent_interacted_ids = {i.arxiv_id for lst in interactions.values() for i in lst}

        candidates = (
            self.db.query(Paper)
            .order_by(Paper.published_date.desc())
            .limit(2000)
            .all()
        )

        for p in candidates:
            if not p:
                continue
            if p.arxiv_id in recent_interacted_ids:
                continue
            p_categories = p.categories or []
            p_authors = (p.authors or [])[:5]

            cat_score = sum(top_categories.get(c, 0.0) for c in p_categories)
            auth_score = sum(top_authors.get(a, 0.0) for a in p_authors)
            base_relevance = cat_score + 1.2 * auth_score
            if base_relevance <= 0:
                continue

            recency_multiplier = 1.0
            if p.published_date:
                pub_date = p.published_date if p.published_date.tzinfo else p.published_date.replace(tzinfo=timezone.utc)
                days_old = max(0, (now - pub_date).days)
                recency_multiplier = 0.5 ** (days_old / 180.0)

            citation_boost = 1.0 + (np.log1p(p.citation_count or 0) * 0.05)

            score = float(base_relevance) * recency_multiplier * citation_boost
            if score <= 0:
                continue

            item_reasons: List[str] = []
            if p_categories:
                matched_cats = [c for c in p_categories if c in top_categories]
                if matched_cats:
                    item_reasons.append(f"Matches your interest in {', '.join(matched_cats[:2])}")
            if p_authors:
                matched_auth = [a for a in p_authors if a in top_authors]
                if matched_auth:
                    item_reasons.append(f"More from {matched_auth[0]}")

            prev = recommendations.get(p.arxiv_id, 0.0)
            recommendations[p.arxiv_id] = max(prev, score)
            if item_reasons:
                reasons.setdefault(p.arxiv_id, []).extend(item_reasons[:2])

        return recommendations, reasons

    def _map_graph_id_to_db(self, rec_id: str) -> Optional[str]:
        """Map a Neo4j arxiv_id to an existing Paper.arxiv_id in the DB.
        Tries exact match first; otherwise uses base id to find the latest version.
        Returns the chosen arxiv_id or None if not found.
        """
        paper = self.db.query(Paper).filter(Paper.arxiv_id == rec_id).first()
        if paper:
            return paper.arxiv_id
        base = self._base_arxiv_id(rec_id)
        if not base:
            return None
        candidates = (
            self.db.query(Paper)
            .filter(Paper.arxiv_id.like(f"{base}%"))
            .order_by(Paper.published_date.desc())
            .all()
        )
        if candidates:
            return candidates[0].arxiv_id
        return None
    
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
    ) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        """Recommend papers using Neo4j graph relationships."""
        if not self.neo4j_client:
            return {}, {}
        
        recommendations: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}
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
                base_id = self._base_arxiv_id(arxiv_id) or arxiv_id
                cited_query = """
                MATCH (p:Paper {arxiv_id: $arxiv_id})-[:CITES]->(cited:Paper)
                RETURN cited.arxiv_id as arxiv_id, cited.citation_count as citation_count
                LIMIT 20
                """
                
                with self.neo4j_client.driver.session() as session:
                    cited_results = session.run(cited_query, arxiv_id=base_id)
                    for record in cited_results:
                        rec_id = record["arxiv_id"]
                        if not rec_id:
                            continue
                        mapped_id = self._map_graph_id_to_db(rec_id)
                        if not mapped_id:
                            continue
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 2.0 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[mapped_id] = recommendations.get(mapped_id, 0.0) + score
                        reasons.setdefault(mapped_id, []).append("Cited by your interacted paper")
                
                citing_query = """
                MATCH (citing:Paper)-[:CITES]->(p:Paper {arxiv_id: $arxiv_id})
                RETURN citing.arxiv_id as arxiv_id, citing.citation_count as citation_count
                LIMIT 15
                """
                
                with self.neo4j_client.driver.session() as session:
                    citing_results = session.run(citing_query, arxiv_id=base_id)
                    for record in citing_results:
                        rec_id = record["arxiv_id"]
                        if not rec_id:
                            continue
                        mapped_id = self._map_graph_id_to_db(rec_id)
                        if not mapped_id:
                            continue
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 1.5 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[mapped_id] = recommendations.get(mapped_id, 0.0) + score
                        reasons.setdefault(mapped_id, []).append("Cites your interacted paper")
                
                coauthor_query = """
                MATCH (p:Paper {arxiv_id: $arxiv_id})-[:AUTHORED_BY]->(a:Author)
                MATCH (a)-[:AUTHORED_BY]-(related:Paper)
                WHERE related.arxiv_id <> $arxiv_id
                RETURN related.arxiv_id as arxiv_id, related.citation_count as citation_count
                LIMIT 10
                """
                
                with self.neo4j_client.driver.session() as session:
                    coauthor_results = session.run(coauthor_query, arxiv_id=base_id)
                    for record in coauthor_results:
                        rec_id = record["arxiv_id"]
                        if not rec_id:
                            continue
                        mapped_id = self._map_graph_id_to_db(rec_id)
                        if not mapped_id:
                            continue
                        citation_count = record.get("citation_count", 0) or 0
                        score = weight * 1.8 * (1.0 + np.log1p(citation_count) * 0.1)
                        recommendations[mapped_id] = recommendations.get(mapped_id, 0.0) + score
                        reasons.setdefault(mapped_id, []).append("Shared authorship with your papers")
        
        except Exception as e:
            logger.error(f"Error in graph-based recommendations: {e}")
        
        return recommendations, reasons

    def _semantic_recommendations(
        self,
        user_id: str,
        interactions: Dict[str, List[PaperView | PaperLike | PaperSave]],
        seeds_limit: int = 5,
        per_seed: int = 30,
    ) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        """Generate semantic candidates from Qdrant seeded by recent liked/saved (then viewed)."""
        seed_ids: List[str] = []
        for key in ["saved", "liked", "viewed"]:
            for inter in interactions.get(key, []):
                if inter.arxiv_id not in seed_ids:
                    seed_ids.append(inter.arxiv_id)
        seed_ids = seed_ids[:seeds_limit]
        if not seed_ids:
            return {}, {}

        recs: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}

        seed_papers = self.db.query(Paper).filter(Paper.arxiv_id.in_(seed_ids)).all()
        seed_map = {p.arxiv_id: p for p in seed_papers}

        retriever = get_retriever()
        for sid in seed_ids:
            sp = seed_map.get(sid)
            if not sp:
                continue
            title = sp.title or ""
            abstract = sp.abstract or ""
            query_text = (title + "\n\n" + abstract)[:4000]
            try:
                results = retriever.vector_search(query=query_text, limit=per_seed)
            except Exception as e:
                logger.error(f"Semantic search error for seed {sid}: {e}")
                continue

            for r in results:
                aid = r.get("arxiv_id")
                if not aid or aid == sid:
                    continue
                score = float(r.get("score") or 0.0)
                if score <= 0:
                    continue
                prev = recs.get(aid, 0.0)
                recs[aid] = max(prev, score)
                reasons.setdefault(aid, []).append(f"Semantic similar to '{(title[:60] + '...') if len(title) > 60 else title}'")

        return recs, reasons

    def _mmr_select(
        self,
        candidates: List[Tuple[str, float]],
        paper_map: Dict[str, Paper],
        k: int,
        lambda_: float = 0.3,
    ) -> List[str]:
        """Select diverse items with Maximal Marginal Relevance using metadata similarity fallback.

        candidates: list of (arxiv_id, relevance)
        returns: ordered list of selected arxiv_ids
        """
        selected: List[str] = []
        remaining = candidates.copy()

        def meta_similarity(a: Paper, b: Paper) -> float:
            sim = 0.0
            a_cats = set(a.categories or [])
            b_cats = set(b.categories or [])
            if a_cats or b_cats:
                inter = len(a_cats & b_cats)
                union = len(a_cats | b_cats) or 1
                sim += 0.5 * (inter / union)
            a_auth = set((a.authors or [])[:5])
            b_auth = set((b.authors or [])[:5])
            if a_auth and b_auth:
                inter_a = len(a_auth & b_auth)
                sim += 0.5 * min(1.0, inter_a / 2.0)
            return max(0.0, min(1.0, sim))

        while remaining and len(selected) < k:
            best_id = None
            best_score = -1e9
            for aid, rel in remaining:
                if not selected:
                    redundancy = 0.0
                else:
                    p_a = paper_map.get(aid)
                    max_sim = 0.0
                    if p_a:
                        for sid in selected:
                            p_s = paper_map.get(sid)
                            if p_s:
                                sim = meta_similarity(p_a, p_s)
                                if sim > max_sim:
                                    max_sim = sim
                    redundancy = max_sim
                mmr = lambda_ * rel - (1.0 - lambda_) * redundancy
                if mmr > best_score:
                    best_score = mmr
                    best_id = aid
            if best_id is None:
                break
            selected.append(best_id)
            remaining = [(aid, rel) for (aid, rel) in remaining if aid != best_id]
        return selected
    
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
