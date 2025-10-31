import logging
from pathlib import Path
from typing import Optional

from docling.datamodel.document import DoclingDocument
from .docling import DoclingParser

logger = logging.getLogger(__name__)


class PDFParserService:
    """Main PDF parsing service using Docling only."""

    def __init__(self, max_pages: int, max_file_size_mb: int, do_ocr: bool = False, do_table_structure: bool = True):
        """Initialize PDF parser service with configurable limits."""
        self.docling_parser = DoclingParser(
            max_pages=max_pages, max_file_size_mb=max_file_size_mb, do_ocr=do_ocr, do_table_structure=do_table_structure
        )

    async def parse_pdf(self, pdf_path: Path) -> Optional[DoclingDocument]:
        """Parse PDF using Docling parser and return raw DoclingDocument.

        :param pdf_path: Path to PDF file
        :returns: DoclingDocument object or None if parsing failed
        """
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            result = await self.docling_parser.parse_pdf(pdf_path)
            if result:
                logger.info(f"Parsed {pdf_path.name}")
                return result
            else:
                logger.error(f"Docling parsing returned no result for {pdf_path.name}")
                raise ValueError(f"Docling parsing returned no result for {pdf_path.name}")

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Docling parsing error for {pdf_path.name}: {e}")
            raise ValueError(f"Docling parsing error for {pdf_path.name}: {e}")