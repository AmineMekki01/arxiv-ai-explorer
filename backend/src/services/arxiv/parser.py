from __future__ import annotations

import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

import PyPDF2
import fitz

from src.core import logger

class PDFParser:
    """Parser for extracting structured content from arXiv PDFs."""
    
    def __init__(
        self,
        timeout: int = 60,
        max_file_size: int = 50 * 1024 * 1024,
    ) -> None:
        self.timeout = timeout
        self.max_file_size = max_file_size
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """Download PDF content from URL."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(pdf_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to download PDF: HTTP {response.status}")
                        return None
                    
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        logger.warning(f"PDF too large: {content_length} bytes")
                        return None
                    
                    content = await response.read()
                    if len(content) > self.max_file_size:
                        logger.warning(f"PDF too large: {len(content)} bytes")
                        return None
                    
                    return content
                    
        except Exception as e:
            logger.error(f"Failed to download PDF from {pdf_url}: {e}")
            return None
    
    def _extract_text_pypdf2(self, pdf_content: bytes) -> str:
        """Extract text using PyPDF2 (fallback method)."""
        if PyPDF2 is None:
            return ""
        
        try:
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file.flush()
                
                with open(tmp_file.name, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    
                    for page in reader.pages:
                        try:
                            text_parts.append(page.extract_text())
                        except Exception as e:
                            logger.warning(f"Failed to extract text from page: {e}")
                            continue
                    
                    return "\n".join(text_parts)
                    
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""
    
    def _extract_text_pymupdf(self, pdf_content: bytes) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract text, figures, and tables using PyMuPDF."""
        if fitz is None:
            return self._extract_text_pypdf2(pdf_content), [], []
        
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            text_parts = []
            figures = []
            tables = []
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    
                    page_text = page.get_text()
                    text_parts.append(page_text)
                    
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            
                            figures.append({
                                'page': page_num + 1,
                                'index': img_index,
                                'width': base_image.get('width', 0),
                                'height': base_image.get('height', 0),
                                'ext': base_image.get('ext', 'png'),
                                'size': len(base_image.get('image', b'')),
                            })
                        except Exception as e:
                            logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                    
                    page_text_lines = page_text.split('\n')
                    potential_tables = self._detect_tables(page_text_lines, page_num + 1)
                    tables.extend(potential_tables)
                    
                except Exception as e:
                    logger.warning(f"Failed to process page {page_num}: {e}")
                    continue
            
            doc.close()
            full_text = "\n".join(text_parts)
            
            return full_text, figures, tables
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return self._extract_text_pypdf2(pdf_content), [], []
    
    def _detect_tables(self, lines: List[str], page_num: int) -> List[Dict[str, Any]]:
        """Simple table detection based on text patterns."""
        tables = []
        current_table = []
        in_table = False
        
        for i, line in enumerate(lines):
            if re.search(r'\s{3,}|\t', line.strip()) and len(line.strip()) > 10:
                if not in_table:
                    in_table = True
                    current_table = [line.strip()]
                else:
                    current_table.append(line.strip())
            else:
                if in_table and len(current_table) >= 2:
                    tables.append({
                        'page': page_num,
                        'rows': len(current_table),
                        'content': '\n'.join(current_table),
                        'start_line': i - len(current_table),
                        'end_line': i - 1,
                    })
                in_table = False
                current_table = []
        
        if in_table and len(current_table) >= 2:
            tables.append({
                'page': page_num,
                'rows': len(current_table),
                'content': '\n'.join(current_table),
                'start_line': len(lines) - len(current_table),
                'end_line': len(lines) - 1,
            })
        
        return tables
    
    def _parse_sections(self, text: str) -> List[Dict[str, Any]]:
        """Parse text into sections based on common academic paper structure."""
        sections = []
        
        section_patterns = [
            (r'(?i)^abstract\s*$', 'abstract'),
            (r'(?i)^introduction\s*$', 'introduction'),
            (r'(?i)^related\s+work\s*$', 'related_work'),
            (r'(?i)^background\s*$', 'background'),
            (r'(?i)^method(?:s|ology)?\s*$', 'methods'),
            (r'(?i)^approach\s*$', 'methods'),
            (r'(?i)^experiment(?:s|al)?\s*(?:results?)?\s*$', 'experiments'),
            (r'(?i)^results?\s*$', 'results'),
            (r'(?i)^evaluation\s*$', 'evaluation'),
            (r'(?i)^discussion\s*$', 'discussion'),
            (r'(?i)^conclusion(?:s)?\s*$', 'conclusion'),
            (r'(?i)^future\s+work\s*$', 'future_work'),
            (r'(?i)^acknowledgment(?:s)?\s*$', 'acknowledgments'),
            (r'(?i)^references?\s*$', 'references'),
            (r'(?i)^appendix\s*', 'appendix'),
        ]
        
        lines = text.split('\n')
        current_section = {'title': 'content', 'type': 'content', 'content': [], 'start_line': 0}
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            section_found = False
            for pattern, section_type in section_patterns:
                if re.match(pattern, line_stripped):
                    if current_section['content']:
                        current_section['content'] = '\n'.join(current_section['content'])
                        current_section['end_line'] = i - 1
                        sections.append(current_section)
                    
                    current_section = {
                        'title': line_stripped,
                        'type': section_type,
                        'content': [],
                        'start_line': i,
                    }
                    section_found = True
                    break
            
            if not section_found:
                current_section['content'].append(line)
        
        if current_section['content']:
            current_section['content'] = '\n'.join(current_section['content'])
            current_section['end_line'] = len(lines) - 1
            sections.append(current_section)
        
        return sections
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            if re.match(r'^\d+$', line):
                continue
            
            if len(line) < 3:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def parse_pdf(self, pdf_url: str) -> Dict[str, Any]:
        """
        Parse a PDF from URL and extract structured content.
        
        Args:
            pdf_url: URL to the PDF file
        
        Returns:
            Dictionary containing extracted content:
            - text: Full text content
            - sections: List of parsed sections
            - figures: List of detected figures
            - tables: List of detected tables
            - metadata: Parsing metadata
        """
        logger.info(f"Starting PDF parsing for: {pdf_url}")
        
        pdf_content = await self._download_pdf(pdf_url)
        if not pdf_content:
            return {
                'text': '',
                'sections': [],
                'figures': [],
                'tables': [],
                'metadata': {'error': 'Failed to download PDF'},
            }
        
        try:
            text, figures, tables = self._extract_text_pymupdf(pdf_content)
            
            if not text:
                logger.warning("No text extracted from PDF")
                return {
                    'text': '',
                    'sections': [],
                    'figures': [],
                    'tables': [],
                    'metadata': {'error': 'No text extracted'},
                }
            
            cleaned_text = self._clean_text(text)
            
            sections = self._parse_sections(cleaned_text)
            
            logger.info(f"Successfully parsed PDF: {len(cleaned_text)} chars, {len(sections)} sections, {len(figures)} figures, {len(tables)} tables")
            
            return {
                'text': cleaned_text,
                'sections': sections,
                'figures': figures,
                'tables': tables,
                'metadata': {
                    'pdf_size': len(pdf_content),
                    'text_length': len(cleaned_text),
                    'num_sections': len(sections),
                    'num_figures': len(figures),
                    'num_tables': len(tables),
                },
            }
            
        except Exception as e:
            logger.error(f"Failed to parse PDF content: {e}")
            return {
                'text': '',
                'sections': [],
                'figures': [],
                'tables': [],
                'metadata': {'error': str(e)},
            }