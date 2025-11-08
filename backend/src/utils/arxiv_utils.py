import re


def normalize_arxiv_id(arxiv_id: str) -> str:
    """
    Normalize arXiv ID to canonical form (without version suffix).
    
    Examples:
        2511.00617v1 -> 2511.00617
        2511.00617 -> 2511.00617
        arxiv:2511.00617v2 -> 2511.00617
        
    Args:
        arxiv_id: Raw arXiv ID (may include version or prefix)
        
    Returns:
        Canonical arXiv ID without version suffix
    """
    if not arxiv_id:
        return arxiv_id
    
    arxiv_id = arxiv_id.lower().replace('arxiv:', '').replace('https://arxiv.org/abs/', '').strip()
    
    arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
    
    return arxiv_id


def extract_version(arxiv_id: str) -> int:
    """
    Extract version number from arXiv ID.
    
    Args:
        arxiv_id: arXiv ID (may include version)
        
    Returns:
        Version number (default 1 if not specified)
    """
    if not arxiv_id:
        return 1
    
    match = re.search(r'v(\d+)$', arxiv_id)
    if match:
        return int(match.group(1))
    return 1


def is_valid_arxiv_id(arxiv_id: str) -> bool:
    """
    Check if string is a valid arXiv ID format.
    
    Supports both old (e.g., hep-th/9901001) and new (e.g., 2511.00617) formats.
    
    Args:
        arxiv_id: String to validate
        
    Returns:
        True if valid arXiv ID format
    """
    if not arxiv_id:
        return False
    
    clean_id = normalize_arxiv_id(arxiv_id)
    
    new_format = re.match(r'^\d{4}\.\d{4,5}$', clean_id)
    
    old_format = re.match(r'^[a-z\-]+/\d{7}$', clean_id)
    
    return bool(new_format or old_format)
