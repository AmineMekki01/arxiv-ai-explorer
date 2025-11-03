"""Utilities for working with DoclingDocument objects."""
from typing import Dict, Any, List
import logging

from docling.datamodel.document import DoclingDocument

logger = logging.getLogger(__name__)


def serialize_docling_document(doc: DoclingDocument) -> Dict[str, Any]:
    """
    Serialize a DoclingDocument to a dictionary for storage.
    
    Args:
        doc: DoclingDocument object to serialize
        
    Returns:
        Dictionary representation of the document
    """
    try:
        return doc.model_dump()
    except Exception as e:
        logger.error(f"Failed to serialize DoclingDocument: {e}")
        raise


def deserialize_docling_document(doc_dict: Dict[str, Any]) -> DoclingDocument:
    """
    Deserialize a dictionary to a DoclingDocument object.
    
    Args:
        doc_dict: Dictionary representation of the document
        
    Returns:
        DoclingDocument object
    """
    try:
        return DoclingDocument.model_validate(doc_dict)
    except Exception as e:
        logger.error(f"Failed to deserialize DoclingDocument: {e}")
        raise


def extract_full_text(doc: DoclingDocument) -> str:
    """
    Extract full text from a DoclingDocument.
    
    Args:
        doc: DoclingDocument object
        
    Returns:
        Full text content
    """
    try:
        if hasattr(doc, 'texts') and doc.texts:
            return "\n".join([t.text for t in doc.texts if hasattr(t, 'text') and t.text])
        return ""
    except Exception as e:
        logger.error(f"Failed to extract text from DoclingDocument: {e}")
        return ""


def extract_sections_from_docling(doc: DoclingDocument) -> List[Dict[str, str]]:
    """
    Extract section structure from DoclingDocument for metadata extraction.
    
    Args:
        doc: DoclingDocument object
        
    Returns:
        List of section dictionaries with 'title' and 'content' keys
    """
    sections = []
    current_section = {"title": "Content", "content": ""}
    
    try:
        for element in doc.texts:
            if hasattr(element, "label") and element.label in ["title", "section_header"]:
                if current_section["content"].strip():
                    sections.append({
                        "title": current_section["title"],
                        "content": current_section["content"].strip()
                    })
                current_section = {
                    "title": element.text.strip() if hasattr(element, "text") else "Untitled",
                    "content": ""
                }
            else:
                if hasattr(element, "text") and element.text:
                    current_section["content"] += element.text + "\n"
        
        if current_section["content"].strip():
            sections.append({
                "title": current_section["title"],
                "content": current_section["content"].strip()
            })
        
        return sections
    except Exception as e:
        logger.error(f"Failed to extract sections from DoclingDocument: {e}")
        return []


def get_document_metadata(doc: DoclingDocument) -> Dict[str, Any]:
    """
    Extract metadata from a DoclingDocument.
    
    Args:
        doc: DoclingDocument object
        
    Returns:
        Dictionary with document metadata
    """
    metadata = {}
    
    try:
        if hasattr(doc, 'name') and doc.name:
            metadata['document_name'] = doc.name
        
        if hasattr(doc, 'origin') and doc.origin:
            metadata['mime_type'] = getattr(doc.origin, 'mimetype', None)
            metadata['filename'] = getattr(doc.origin, 'filename', None)
        
        metadata['text_count'] = len(doc.texts) if hasattr(doc, 'texts') else 0
        metadata['table_count'] = len(doc.tables) if hasattr(doc, 'tables') else 0
        metadata['picture_count'] = len(doc.pictures) if hasattr(doc, 'pictures') else 0
        
    except Exception as e:
        logger.error(f"Failed to extract metadata from DoclingDocument: {e}")
    
    return metadata
