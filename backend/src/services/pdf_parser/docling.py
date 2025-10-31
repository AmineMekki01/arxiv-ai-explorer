import torch
import logging
from pathlib import Path
from typing import Optional

import pypdfium2 as pdfium
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.document import DoclingDocument
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions

logger = logging.getLogger(__name__)


class DoclingParser:
    """Docling PDF parser for scientific document processing."""

    def __init__(self, max_pages: int, max_file_size_mb: int, do_ocr: bool = False, do_table_structure: bool = True):
        """Initialize DocumentConverter with optimized pipeline options.

        :param max_pages: Maximum number of pages to process
        :param max_file_size_mb: Maximum file size in MB
        :param do_ocr: Enable OCR for scanned PDFs (default: False, very slow)
        :param do_table_structure: Extract table structures (default: True)
        """
        self._init_pipeline_options(do_ocr=do_ocr, do_table_structure=do_table_structure)
        self._converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=self.pipeline_options)})
        self._warmed_up = False
        self.max_pages = max_pages
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _init_pipeline_options(self, do_ocr: bool, do_table_structure: bool):
        if torch.cuda.is_available():
            self.pipeline_options = PdfPipelineOptions(
                do_table_structure=do_table_structure,
                do_ocr=do_ocr,
                accelerator_options=AcceleratorOptions(device=AcceleratorDevice.GPU)
            )
        elif torch.backends.mps.is_available():
            self.pipeline_options = PdfPipelineOptions(
                do_table_structure=do_table_structure,
                do_ocr=do_ocr,
                accelerator_options=AcceleratorOptions(device=AcceleratorDevice.MPS)
            )
        else:
            self.pipeline_options = PdfPipelineOptions(
                do_table_structure=do_table_structure,
                do_ocr=do_ocr,
                accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU)
            )

    def _warm_up_models(self):
        """Pre-warm the models with a small dummy document to avoid cold start."""
        if not self._warmed_up:
            self._warmed_up = True

    def _validate_pdf(self, pdf_path: Path) -> bool:
        """Comprehensive PDF validation including size and page limits.

        :param pdf_path: Path to PDF file
        :returns: True if PDF appears valid and within limits, False otherwise
        """
        try:
            if pdf_path.stat().st_size == 0:
                logger.error(f"PDF file is empty: {pdf_path}")
                raise ValueError(f"PDF file is empty: {pdf_path}")

            file_size = pdf_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                logger.warning(
                    f"PDF file size ({file_size / 1024 / 1024:.1f}MB) exceeds limit ({self.max_file_size_bytes / 1024 / 1024:.1f}MB), skipping processing"
                )
                raise ValueError(
                    f"PDF file too large: {file_size / 1024 / 1024:.1f}MB > {self.max_file_size_bytes / 1024 / 1024:.1f}MB"
                )

            with open(pdf_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    logger.error(f"File does not have PDF header: {pdf_path}")
                    raise ValueError(f"File does not have PDF header: {pdf_path}")

            pdf_doc = pdfium.PdfDocument(str(pdf_path))
            actual_pages = len(pdf_doc)
            pdf_doc.close()

            if actual_pages > self.max_pages:
                logger.warning(
                    f"PDF has {actual_pages} pages, exceeding limit of {self.max_pages} pages. Skipping processing to avoid performance issues."
                )
                raise ValueError(f"PDF has too many pages: {actual_pages} > {self.max_pages}")

            return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            raise ValueError(f"Error validating PDF {pdf_path}: {e}")

    async def parse_pdf(self, pdf_path: Path) -> Optional[DoclingDocument]:
        """Parse PDF using Docling parser and return raw DoclingDocument.
        Limited to 20 pages to avoid memory issues with large papers.

        :param pdf_path: Path to PDF file
        :returns: DoclingDocument object or None if parsing failed
        """
        try:
            self._validate_pdf(pdf_path)
            self._warm_up_models()

            result = self._converter.convert(str(pdf_path), max_num_pages=self.max_pages, max_file_size=self.max_file_size_bytes)
            doc = result.document
            
            logger.info(f"Parsed {pdf_path.name}")
            return doc

        except ValueError as e:
            error_msg = str(e).lower()
            if "too large" in error_msg or "too many pages" in error_msg:
                logger.info(f"Skipping PDF processing due to size/page limits: {e}")
                return None
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to parse PDF with Docling: {e}")
            logger.error(f"PDF path: {pdf_path}")
            logger.error(f"PDF size: {pdf_path.stat().st_size} bytes")
            logger.error(f"Error type: {type(e).__name__}")

            error_msg = str(e).lower()

            if "not valid" in error_msg:
                logger.error("PDF appears to be corrupted or not a valid PDF file")
                raise ValueError(f"PDF appears to be corrupted or invalid: {pdf_path}")
            elif "timeout" in error_msg:
                logger.error("PDF processing timed out - file may be too complex")
                raise ValueError(f"PDF processing timed out: {pdf_path}")
            elif "memory" in error_msg or "ram" in error_msg:
                logger.error("Out of memory - PDF may be too large or complex")
                raise ValueError(f"Out of memory processing PDF: {pdf_path}")
            elif "max_num_pages" in error_msg or "page" in error_msg:
                logger.error(f"PDF processing issue likely related to page limits (current limit: {self.max_pages} pages)")
                raise ValueError(
                    f"PDF processing failed, possibly due to page limit ({self.max_pages} pages). Error: {e}"
                )
            else:
                raise ValueError(f"Failed to parse PDF with Docling: {e}")