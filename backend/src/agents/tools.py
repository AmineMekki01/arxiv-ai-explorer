from agents import function_tool
from typing import Optional, List, Dict, Any
from src.services.retrieval.retriever import get_retriever

retriever = get_retriever()

@function_tool
def search_papers(
    query: str,
    limit: int = 10,
    exclude_sections: Optional[List[str]] = None,
    include_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    This tool performs a vector search over papers and chunks.
    Args:
        query: The search query.
        limit: The number of results to return.
        exclude_sections: List of section titles to ignore.
        include_sections: List of section titles to only consider.
    Returns:
        A dictionary containing the search results.
    """
    print(f"Tool Called with Search papers: {query}")
    results = retriever.vector_search(query, limit=limit, exclude_sections=exclude_sections, include_sections=include_sections)

    return results
