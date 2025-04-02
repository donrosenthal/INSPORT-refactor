
"""
https://claude.ai/chat/81bf679c-b4ca-42e6-afa3-5d63e2fdea28
Insurance PDF Processor

This script extracts text from insurance policy PDF documents using a hybrid approach:
- PDFPlumber for text-based PDFs
- Tesseract OCR for scanned PDFs

It includes functionality to:
1. Detect whether a PDF is text-based or scanned
2. Extract text from text-based PDFs using PDFPlumber
3. Extract text from scanned PDFs using Tesseract OCR
4. Process and format tables found in the PDFs
"""

import os
import re
import sys
import io
import logging
from typing import Dict, List, Union, Tuple, Optional, Any

# Required third-party libraries
try:
    import pdfplumber
    import pytesseract
    from pdf2image import convert_from_path
    import numpy as np
    from PIL import Image
except ImportError as e:
    print(f"Error: Missing required dependencies. {str(e)}")
    print("Please install required packages: pip install pdfplumber pytesseract pdf2image numpy pillow")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("insurance_pdf_processor")

# Type definitions for clarity
PDFContent = Dict[str, Any]  # Structured content from PDF
TableData = List[List[str]]  # Table as a list of rows, each row is a list of cells

def is_scanned_pdf(pdf_path: str, threshold: int = 5, sample_pages: int = 5) -> bool:
    """
    Determine if a PDF is primarily scanned (image-based) or text-based.
    
    Args:
        pdf_path: Path to the PDF file
        threshold: Minimum number of characters per page to consider text-based
        sample_pages: Number of pages to sample for detection
        
    Returns:
        bool: True if the PDF is primarily scanned, False if text-based
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the provided PDF is invalid
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Limit to sampling first few pages
            pages_to_check = min(len(pdf.pages), sample_pages)
            
            if pages_to_check == 0:
                logger.warning(f"PDF has no pages: {pdf_path}")
                return False
            
            total_chars = 0
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                total_chars += len(text)
                
                # Early detection - if any page has significant text, consider it text-based
                if len(text) > threshold * 100:  # Significant text on a single page
                    logger.info(f"PDF detected as text-based (significant text on page {i+1})")
                    return False
            
            avg_chars = total_chars / pages_to_check
            is_scanned = avg_chars < threshold
            
            logger.info(f"PDF detection result for {pdf_path}: {'Scanned' if is_scanned else 'Text-based'} " +
                       f"(avg {avg_chars:.1f} chars per page)")
            return is_scanned
            
    except Exception as e:
        logger.error(f"Error detecting PDF type: {str(e)}")
        raise ValueError(f"Invalid or corrupted PDF: {str(e)}")

def extract_text_with_pdfplumber(pdf_path: str, extract_tables: bool = True, 
                                max_pages: Optional[int] = None) -> PDFContent:
    """
    Extract text from a text-based PDF using PDFPlumber.
    
    Args:
        pdf_path: Path to the PDF file
        extract_tables: If True, extract and format tables separately
        max_pages: Maximum number of pages to process
        
    Returns:
        dict: Dictionary containing extracted text and tables
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the provided PDF is invalid
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Limit pages if specified
            page_count = len(pdf.pages)
            pages_to_process = page_count if max_pages is None else min(page_count, max_pages)
            
            logger.info(f"Processing {pages_to_process} pages from {pdf_path} with PDFPlumber")
            
            extracted_content = {
                "pages": [],
                "tables": []
            }
            
            for i in range(pages_to_process):
                page = pdf.pages[i]
                page_text = page.extract_text() or ""
                
                page_content = {
                    "number": i + 1,
                    "text": page_text,
                    "tables": []
                }
                
                # Extract tables if requested
                if extract_tables:
                    try:
                        tables = page.extract_tables()
                        
                        for table_idx, table in enumerate(tables):
                            if table and any(table):  # Ensure table has content
                                # Clean table data (handle None values and strip whitespace)
                                cleaned_table = [
                                    [str(cell).strip() if cell is not None else "" for cell in row]
                                    for row in table
                                ]
                                
                                table_data = {
                                    "page": i + 1,
                                    "index": table_idx,
                                    "data": cleaned_table
                                }
                                
                                page_content["tables"].append(table_data)
                                extracted_content["tables"].append(table_data)
                    except Exception as table_error:
                        logger.warning(f"Error extracting tables from page {i+1}: {str(table_error)}")
                
                extracted_content["pages"].append(page_content)
            
            return extracted_content
            
    except Exception as e:
        logger.error(f"Error extracting text with PDFPlumber: {str(e)}")
        raise ValueError(f"Failed to process PDF with PDFPlumber: {str(e)}")

def extract_text_with_tesseract(pdf_path: str, language: str = "eng", 
                               dpi: int = 300, max_pages: Optional[int] = None) -> PDFContent:
    """
    Extract text from a scanned PDF using Tesseract OCR.
    
    Args:
        pdf_path: Path to the PDF file
        language: OCR language setting for Tesseract
        dpi: DPI setting for image conversion
        max_pages: Maximum number of pages to process
        
    Returns:
        dict: Dictionary containing extracted text and any detected tables
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        RuntimeError: If OCR processing fails
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        # Convert PDF to images
        logger.info(f"Converting PDF to images at {dpi} DPI")
        images = convert_from_path(
            pdf_path, 
            dpi=dpi, 
            first_page=1,
            last_page=max_pages
        )
        
        logger.info(f"Processing {len(images)} pages from {pdf_path} with Tesseract OCR")
        
        extracted_content = {
            "pages": [],
            "tables": []
        }
        
        for i, image in enumerate(images):
            # Process with Tesseract OCR
            try:
                custom_config = f'--oem 3 --psm 6 -l {language}'
                ocr_text = pytesseract.image_to_string(image, config=custom_config)
                
                # Basic cleanup of OCR text
                ocr_text = ocr_text.replace('\n\n', '\n§\n')  # Mark paragraph breaks
                ocr_text = re.sub(r'\n+', '\n', ocr_text)     # Remove multiple newlines
                ocr_text = ocr_text.replace('\n§\n', '\n\n')  # Restore paragraph breaks
                
                page_content = {
                    "number": i + 1,
                    "text": ocr_text,
                    "tables": []
                }
                
                # Detect potential tables using heuristics
                potential_tables = detect_tables_in_ocr_text(ocr_text)
                for table_idx, table in enumerate(potential_tables):
                    if table and any(table):  # Ensure table has content
                        table_data = {
                            "page": i + 1,
                            "index": table_idx,
                            "data": table
                        }
                        page_content["tables"].append(table_data)
                        extracted_content["tables"].append(table_data)
                
                extracted_content["pages"].append(page_content)
                
            except Exception as ocr_error:
                logger.warning(f"Error processing page {i+1} with OCR: {str(ocr_error)}")
                # Add empty page to maintain page count
                extracted_content["pages"].append({
                    "number": i + 1,
                    "text": f"[OCR PROCESSING ERROR ON PAGE {i+1}]",
                    "tables": []
                })
        
        return extracted_content
        
    except Exception as e:
        logger.error(f"Error extracting text with Tesseract: {str(e)}")
        raise RuntimeError(f"Failed to process PDF with Tesseract: {str(e)}")

def detect_tables_in_ocr_text(text: str) -> List[TableData]:
    """
    Detect potential tables in OCR text using pattern matching.
    
    Args:
        text: OCR text to analyze
        
    Returns:
        list: Detected tables as nested lists
    """
    tables = []
    
    # Split text into lines
    lines = text.split('\n')
    
    # Look for potential table patterns
    current_table = []
    in_table = False
    
    for line in lines:
        # Heuristics for table detection:
        # 1. Lines with multiple whitespace separations (3+ spaces together)
        # 2. Lines with pipe or tab characters
        # 3. Lines with consistent spacing patterns
        
        # Check for pipe characters (common in tables)
        if '|' in line and len(line) > 5:
            if not in_table:
                in_table = True
                current_table = []
            
            # Split by pipe character
            cells = [cell.strip() for cell in line.split('|')]
            current_table.append(cells)
            continue
        
        # Check for tab characters
        if '\t' in line and len(line) > 5:
            if not in_table:
                in_table = True
                current_table = []
            
            # Split by tab character
            cells = [cell.strip() for cell in line.split('\t')]
            current_table.append(cells)
            continue
            
        # Check for multiple space separations (3+ spaces together)
        if re.search(r'\s{3,}', line) and len(line) > 10:
            # Potential table row with space-separated columns
            if not in_table:
                in_table = True
                current_table = []
            
            # Split by multiple spaces (3 or more)
            cells = [cell.strip() for cell in re.split(r'\s{3,}', line) if cell.strip()]
            if len(cells) >= 2:  # Require at least 2 cells to be a table row
                current_table.append(cells)
            continue
            
        # Currency/number patterns common in insurance tables
        if re.search(r'\$\s*\d+(?:[.,]\d+)+', line) and re.search(r'\s{2,}', line):
            if not in_table:
                in_table = True
                current_table = []
            
            # Split by multiple spaces (2 or more)
            cells = [cell.strip() for cell in re.split(r'\s{2,}', line) if cell.strip()]
            if len(cells) >= 2:  # Require at least 2 cells to be a table row
                current_table.append(cells)
            continue
        
        # If we reach here, line is not part of a table
        if in_table:
            # End current table if it has at least 2 rows
            if len(current_table) >= 2:
                # Normalize table (ensure all rows have same number of columns)
                max_cols = max(len(row) for row in current_table)
                normalized_table = []
                for row in current_table:
                    # Pad rows with empty cells if needed
                    normalized_row = row + [""] * (max_cols - len(row))
                    normalized_table.append(normalized_row)
                
                tables.append(normalized_table)
            
            in_table = False
            current_table = []
    
    # Handle case where file ends while still in a table
    if in_table and len(current_table) >= 2:
        # Normalize table (ensure all rows have same number of columns)
        max_cols = max(len(row) for row in current_table)
        normalized_table = []
        for row in current_table:
            # Pad rows with empty cells if needed
            normalized_row = row + [""] * (max_cols - len(row))
            normalized_table.append(normalized_row)
        
        tables.append(normalized_table)
    
    return tables

def format_extracted_content(extracted_content: PDFContent, output_format: str = "text") -> str:
    """
    Format extracted content as plain text.
    
    Args:
        extracted_content: Dictionary containing extracted text and tables
        output_format: Output format, either "text" or "markdown"
        
    Returns:
        str: Formatted text
    """
    result = []
    
    # Process each page
    for page in extracted_content["pages"]:
        # Add page marker in debug mode
        result.append(f"--- Page {page['number']} ---")
        
        # Add page text
        if page["text"]:
            result.append(page["text"])
        
        # Add tables for this page
        page_tables = [t for t in extracted_content["tables"] if t["page"] == page["number"]]
        for table in page_tables:
            result.append("\n[TABLE]")
            for row in table["data"]:
                result.append(" | ".join(row))
            result.append("[/TABLE]\n")
    
    return "\n\n".join(result)

def convert_insurance_pdf_to_text(
    pdf_path: str,
    output_format: str = "text",     # "text" or "markdown" (Phase 2)
    force_ocr: bool = False,         # Force OCR even for text-based PDFs
    extract_tables: bool = True,     # Attempt specialized table extraction
    detect_scanned: bool = True,     # Automatically detect if PDF is scanned
    scan_threshold: int = 5,         # Min text chars per page to consider as text-based
    max_pages: Optional[int] = None, # Limit processing to first N pages
    ocr_language: str = "eng",       # OCR language setting
    dpi: int = 300                   # DPI for image conversion (OCR quality)
) -> str:
    """
    Convert insurance policy PDF document to text format using a hybrid approach:
    - PDFPlumber for text-based PDFs
    - Tesseract OCR for scanned PDFs
    
    Args:
        pdf_path: Path to the PDF file
        output_format: Output format, either "text" or "markdown"
        force_ocr: If True, apply OCR to all pages regardless of content type
        extract_tables: If True, use specialized table extraction
        detect_scanned: If True, automatically detect if PDF is scanned
        scan_threshold: Minimum number of text characters per page to consider as text-based
        max_pages: Maximum number of pages to process
        ocr_language: OCR language setting for Tesseract
        dpi: DPI setting for image conversion
        
    Returns:
        str: Extracted text in the specified format
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the provided PDF is invalid
        RuntimeError: If processing fails due to Tesseract or PDFPlumber errors
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Determine if PDF is scanned or text-based
    is_scanned = force_ocr
    if not force_ocr and detect_scanned:
        try:
            is_scanned = is_scanned_pdf(pdf_path, threshold=scan_threshold)
        except Exception as e:
            logger.warning(f"Error during PDF type detection, falling back to OCR: {str(e)}")
            is_scanned = True
    
    # Extract content based on PDF type
    try:
        if is_scanned:
            logger.info(f"Processing as scanned PDF with Tesseract OCR")
            extracted_content = extract_text_with_tesseract(
                pdf_path, 
                language=ocr_language, 
                dpi=dpi, 
                max_pages=max_pages
            )
        else:
            logger.info(f"Processing as text-based PDF with PDFPlumber")
            extracted_content = extract_text_with_pdfplumber(
                pdf_path, 
                extract_tables=extract_tables, 
                max_pages=max_pages
            )
        
        # Format the extracted content
        return format_extracted_content(extracted_content, output_format)
        
    except Exception as e:
        logger.error(f"Error during PDF processing: {str(e)}")
        raise RuntimeError(f"Failed to process PDF: {str(e)}")

def main():
    """
    Main function when script is run standalone.
    Processes PDF file specified as command-line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python insurance_pdf_processor.py <pdf_file_path> [--ocr] [--max-pages N]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    force_ocr = "--ocr" in sys.argv
    
    # Check for max pages option
    max_pages = None
    if "--max-pages" in sys.argv:
        try:
            max_pages_index = sys.argv.index("--max-pages") + 1
            if max_pages_index < len(sys.argv):
                max_pages = int(sys.argv[max_pages_index])
        except (ValueError, IndexError):
            print("Invalid --max-pages value")
            sys.exit(1)
    
    try:
        extracted_text = convert_insurance_pdf_to_text(
            pdf_path,
            force_ocr=force_ocr,
            max_pages=max_pages
        )
        
        print(extracted_text)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()