import os
import uuid
import fitz  # PyMuPDF
import subprocess
import re
from tqdm import tqdm

class PDFProcessingService:
    """
    Service for processing PDF documents with different extraction methods
    based on document type (scanned, digital text, or searchable scan).
    
    This service handles:
    - PDF type detection, including searchable scans
    - Text extraction (OCR for scanned, direct extraction for others)
    - Annotation extraction
    - File management
    """
    
    # Define document types
    DOCTYPE_SCANNED = "scanned"                           # Image only, no text layer
    DOCTYPE_DIGITAL = "digital"                           # Native digital text
    DOCTYPE_DIGITAL_ANNOTATED = "digital_with_annotations"  # Digital with annotations
    DOCTYPE_SEARCHABLE_SCAN = "searchable_scan"           # Visually scanned with text layer
    
    def __init__(self, base_temp_dir="pdf_processing_tmp"):
        """
        Initialize the PDF processing service.
        
        Args:
            base_temp_dir (str): Base directory for temporary processing files
        """
        self.base_temp_dir = base_temp_dir
        os.makedirs(base_temp_dir, exist_ok=True)
    
    def process_document(self, pdf_path, output_file=None, languages=["eng"]):
        """
        Process a PDF document and extract its text content.
        
        Args:
            pdf_path (str): Path to the input PDF file
            output_file (str, optional): Path where extracted text should be saved
                                         If None, a path will be generated
            languages (list): List of language codes for OCR
        
        Returns:
            dict: Processing result with keys:
                - success (bool): Whether processing succeeded
                - job_id (str): Unique ID for this processing job
                - text_file_path (str): Path to the extracted text file
                - document_type (str): Type of document detected
                - error (str, optional): Error message if processing failed
        """
        # Create unique job ID and directories
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(self.base_temp_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # If no output file specified, create one in the job directory
        if output_file is None:
            output_file = os.path.join(job_dir, "extracted_text.txt")
        
        try:
            # Verify file exists with enhanced error reporting
            pdf_path = self._verify_file_exists(pdf_path)
            print(f"🔍 Processing PDF: {pdf_path}")
            
            # Detect document type with enhanced logic
            document_type, has_annotations = self._detect_document_type(pdf_path)
            
            # Process based on document type
            if document_type == self.DOCTYPE_SCANNED:
                # Pure scanned document, must use OCR
                print(f"📄 Document is purely scanned. Running OCR...")
                text_file_path = self._process_scanned_pdf(
                    pdf_path, output_file, job_dir, languages
                )
            else:
                # Digital text, digital with annotations, or searchable scan
                if document_type == self.DOCTYPE_SEARCHABLE_SCAN:
                    print(f"📑 Document is a searchable scan (images with text layer). Extracting text...")
                else:
                    print(f"📝 Document is digital{' with annotations' if has_annotations else ''}. Extracting text...")
                
                text_file_path = self._process_digital_pdf(
                    pdf_path, output_file, has_annotations
                )
            
            print(f"✨ Document processed successfully as {document_type}")
            
            return {
                "success": True,
                "job_id": job_id,
                "text_file_path": text_file_path,
                "document_type": document_type
            }
            
        except Exception as e:
            print(f"❌ Error processing PDF: {str(e)}")
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
                "document_type": "unknown"
            }
    
    def _verify_file_exists(self, pdf_path):
        """
        Verify file exists with enhanced error reporting.
        
        Args:
            pdf_path (str): Path to verify
            
        Returns:
            str: Verified path (may be modified if using filename only)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(pdf_path):
            # Enhanced debugging information
            print(f"WARNING: File does not exist at path: {pdf_path}")
            print(f"Current working directory: {os.getcwd()}")
            
            # Try to find the file by checking if just the filename exists in the current directory
            filename = os.path.basename(pdf_path)
            if os.path.exists(filename):
                print(f"File found with just the filename: {filename}")
                return filename
            
            # List files in the directory to help debugging
            try:
                parent_dir = os.path.dirname(pdf_path)
                if parent_dir and os.path.exists(parent_dir):
                    print(f"Files in {parent_dir}:")
                    for f in os.listdir(parent_dir):
                        print(f"  - {f}")
            except Exception as e:
                print(f"Error listing directory: {e}")
                
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        return pdf_path
    
    def _detect_document_type(self, pdf_path, sample_pages=5):
        """
        Enhanced document type detection that recognizes searchable scans.
        
        Args:
            pdf_path (str): Path to the PDF file
            sample_pages (int): Number of pages to sample for detection
        
        Returns:
            tuple: (document_type, has_annotations)
        """
        print("🔍 Detecting document type...")
        doc = fitz.open(pdf_path)
        
        # Initialize counters
        pages_with_text = 0
        pages_with_images = 0
        empty_pages = 0
        
        # Check for annotations
        has_annotations = False
        for page in doc:
            if page.annots():
                has_annotations = True
                break
                
        # Sample pages for analysis
        max_pages = min(sample_pages, len(doc))
        for i in range(max_pages):
            page = doc[i]
            
            # Check for text
            text = page.get_text().strip()
            if text:
                pages_with_text += 1
                if len(text) < 50:  # Less than 50 chars might be just page numbers/headers
                    empty_pages += 1
            else:
                empty_pages += 1
            
            # Check for images
            image_list = page.get_images(full=True)
            if image_list and self._images_cover_most_of_page(page, image_list):
                pages_with_images += 1
        
        # Analyze results to determine document type
        is_visual_scan = (pages_with_images / max_pages) > 0.5
        has_text_layer = (pages_with_text / max_pages) > 0.5
        is_mostly_empty = (empty_pages / max_pages) > 0.7
        
        # Decision logic for document type
        if is_mostly_empty and is_visual_scan:
            print("📄 Document appears to be a pure scanned document (images only)")
            document_type = self.DOCTYPE_SCANNED
        elif is_visual_scan and has_text_layer:
            print("📋 Document appears to be a searchable scan (has images with text layer)")
            document_type = self.DOCTYPE_SEARCHABLE_SCAN
        else:
            if has_annotations:
                print("📝 Document is digital with annotations")
                document_type = self.DOCTYPE_DIGITAL_ANNOTATED
            else:
                print("📄 Document is pure digital text")
                document_type = self.DOCTYPE_DIGITAL
        
        return document_type, has_annotations
    
    def _images_cover_most_of_page(self, page, image_list):
        """
        Determine if images cover most of a page.
        
        Args:
            page: PyMuPDF page object
            image_list: List of images returned by page.get_images()
            
        Returns:
            bool: Whether images cover the majority of the page
        """
        if not image_list:
            return False
            
        page_area = page.rect.width * page.rect.height
        
        # Calculate total image area (simplistic approach)
        image_area = 0
        for img in image_list:
            # Get the xref of the image
            xref = img[0]
            
            # We need to find instances of this image on the page
            # (an image might appear multiple times or be scaled)
            for irect in page.get_image_rects(xref):
                # Add up the area of each image instance
                width = irect.width
                height = irect.height
                image_area += width * height
        
        # Consider the page image-dominated if images cover more than 30% of the page
        # This is a heuristic - adjust based on your document types
        coverage_ratio = image_area / page_area
        return coverage_ratio > 0.3
    
    def _process_scanned_pdf(self, pdf_path, output_file, job_dir, languages=["eng"]):
        """
        Process a scanned PDF using OCR.
        
        Args:
            pdf_path (str): Path to the PDF file
            output_file (str): Path where extracted text should be saved
            job_dir (str): Directory for temporary files
            languages (list): List of language codes for OCR
            
        Returns:
            str: Path to the extracted text file
        """
        print(f"📄 Converting PDF to images and running OCR with languages: {', '.join(languages)}...")
        
        # Create directory for extracted images
        images_dir = os.path.join(job_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Convert PDF to images
        doc = fitz.open(pdf_path)
        image_files = []
        
        # Extract each page as an image
        for page_num, page in enumerate(tqdm(doc, desc="Converting pages to images")):
            pix = page.get_pixmap(dpi=300)  # Higher DPI for better OCR quality
            image_path = os.path.join(images_dir, f"page_{page_num+1}.png")
            pix.save(image_path)
            image_files.append(image_path)
        
        # Process each image with Tesseract
        text_results = []
        for i, image_path in enumerate(tqdm(image_files, desc="OCR Processing")):
            # Create a temporary text file path
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            text_file = os.path.join(job_dir, f"{base_name}.txt")
            
            # Run Tesseract on the image
            lang_param = "+".join(languages)
            try:
                subprocess.run(
                    ["tesseract", image_path, os.path.splitext(text_file)[0], 
                     "-l", lang_param, "txt"],
                    check=True, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Read the extracted text
                with open(text_file, "r", encoding="utf-8") as f:
                    page_text = f.read()
                
                # Add page marker and text
                text_results.append(f"\n\n=== Page {i+1} ===\n\n{page_text}")
                
            except subprocess.CalledProcessError as e:
                print(f"Error processing image {image_path}: {e}")
                # Continue with next image instead of failing completely
                text_results.append(f"\n\n=== Page {i+1} (OCR FAILED) ===\n\n")
        
        # Combine all text results
        full_text = "\n".join(text_results)
        
        # Write combined text to output file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        return output_file
    
    def _process_digital_pdf(self, pdf_path, output_file, has_annotations=False):
        """
        Process a digital PDF by extracting its text content.
        
        Args:
            pdf_path (str): Path to the PDF file
            output_file (str): Path where extracted text should be saved
            has_annotations (bool): Whether the PDF has annotations
            
        Returns:
            str: Path to the extracted text file
        """
        if has_annotations:
            print("📝 PDF has annotations. Extracting and processing...")
        else:
            print("✅ Extracting text from PDF...")
        
        # Extract main text with structure preservation
        text = self._extract_structured_text(pdf_path)
        
        # If there are annotations, extract and append them
        if has_annotations:
            annotations = self._extract_annotations(pdf_path)
            
            if annotations:
                text += "\n\n=== ANNOTATIONS ===\n\n"
                for i, annot in enumerate(annotations):
                    text += f"Annotation {i+1} (Page {annot['page']}, {annot['type']}):\n"
                    text += f"Text: {annot['highlighted_text']}\n"
                    if annot['content']:
                        text += f"Comment: {annot['content']}\n"
                    text += "\n"
        
        # Save the text to the output file
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        return output_file
    
    def _extract_structured_text(self, pdf_path):
        """
        Extract text from a PDF with structure preservation.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text with structure markers
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        text_blocks = []
        
        # Process with progress bar
        for page_num in tqdm(range(total_pages), desc="Extracting text", unit="page"):
            page = doc[page_num]
            
            # Add page marker
            text_blocks.append(f"\n\n=== Page {page_num+1} ===\n\n")
            
            # Extract blocks which somewhat preserve paragraphs
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5:  # Ensure the block has text
                    text_blocks.append(block[4])  # The 5th element contains the text
        
        return "\n".join(text_blocks)
    
    def _extract_annotations(self, pdf_path):
        """
        Extract annotations from a PDF document.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            list: List of annotation dictionaries
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        annotations = []
        
        # Use tqdm for progress
        for page_num in tqdm(range(total_pages), desc="Extracting annotations", unit="page"):
            page = doc[page_num]
            for annot in page.annots():
                annot_data = {
                    "page": page_num + 1,
                    "type": annot.type[1],
                    "content": annot.info.get("content", ""),
                    "rect": list(annot.rect),
                    "highlighted_text": self._get_text_for_annotation(page, annot)
                }
                annotations.append(annot_data)
        
        return annotations
    
    def _get_text_for_annotation(self, page, annot):
        """
        Get the text covered by an annotation (for highlights).
        
        Args:
            page: PDF page object
            annot: Annotation object
            
        Returns:
            str: Text covered by the annotation
        """
        if annot.type[1] == "Highlight":
            quads = annot.vertices
            if quads:
                # Convert quadrilaterals to rectangles
                rect = fitz.Rect(quads[0][0], quads[0][1], quads[2][0], quads[2][1])
                words = page.get_text("words")
                text = ""
                for word in words:
                    if len(word) >= 4:  # Make sure word has coordinates
                        word_rect = fitz.Rect(word[:4])
                        if rect.intersects(word_rect):
                            text += word[4] + " "
                return text.strip()
        return ""
    
    def check_dependencies(self):
        """
        Check if all required dependencies are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise
        """
        try:
            import fitz
            import tqdm
        except ImportError as e:
            print(f"Missing Python dependency: {e}")
            print("Please install required packages:")
            print("pip install PyMuPDF tqdm")
            return False
        
        # Check for Tesseract
        try:
            result = subprocess.run(["tesseract", "--version"], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True)
            if result.returncode != 0:
                raise Exception()
        except:
            print("Tesseract OCR not found or not working properly.")
            print("Please install Tesseract:")
            print("  - macOS: brew install tesseract")
            print("  - Ubuntu/Debian: sudo apt-get install tesseract-ocr")
            print("  - Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        
        return True
    
    def cleanup_job(self, job_id):
        """
        Clean up temporary files for a specific job.
        
        Args:
            job_id (str): ID of the job to clean up
            
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        job_dir = os.path.join(self.base_temp_dir, job_id)
        if os.path.exists(job_dir):
            try:
                import shutil
                shutil.rmtree(job_dir)
                return True
            except Exception as e:
                print(f"Error cleaning up job directory: {e}")
                return False
        return False
    
    def get_pdf_info(self, pdf_path):
        """
        Get basic information about a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            dict: PDF information
        """
        try:
            doc = fitz.open(pdf_path)
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "is_encrypted": doc.is_encrypted,
                "permissions": doc.permissions
            }
            return info
        except Exception as e:
            print(f"Error getting PDF info: {e}")
            return {"error": str(e)}