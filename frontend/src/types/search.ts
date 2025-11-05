export interface ChunkResult {
  chunk_text: string;
  section_title?: string;
  section_type?: string;
  chunk_index?: number;
  score?: number;
}

export interface GraphMetadata {
  citation_count: number;
  is_seminal: boolean;
  cited_by_results: number;
  is_foundational: boolean;
}

export interface PaperResult {
  arxiv_id: string;
  title: string;
  published_date?: string;
  primary_category?: string;
  categories: string[];
  chunks: ChunkResult[];
  graph_metadata: GraphMetadata;
  max_score: number;
}

export interface GraphInsights {
  total_papers: number;
  internal_citations: number;
  foundational_papers_added: number;
  central_papers: string[];
}

export interface EnhancedSearchResponse {
  results: PaperResult[];
  graph_insights: GraphInsights;
  query: string;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  include_foundations?: boolean;
  min_foundation_citations?: number;
}
