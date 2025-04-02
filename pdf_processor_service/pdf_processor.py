import os
import uuid
import fitz  # PyMuPDF
import subprocess
from tqdm import tqdm

class PDFProcessingService:
    """
    Service for processing PDF documents with different extraction methods
    based on document type (scanned vs. digital text).
    
    This service handles:
    - PDF type detection
    - Text extraction (OCR for scanned, direct extraction for digital)
    - Annotation extraction
    - File management
    """
    
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
            print(f"🔍 Processing PDF: {pdf_path}")
            
            # Detect document type
            if self._is_scanned_pdf(pdf_path):
                document_type = "scanned"
                text_file_path = self._process_scanned_pdf(
                    pdf_path, output_file, job_dir, languages
                )
            else:
                # Check if it has annotations
                has_annotations = self._has_annotations(pdf_path)
                document_type = "digital_with_annotations" if has_annotations else "digital"
                
                text_file_path = self._process_digital_pdf(
                    pdf_path, output_file, has_annotations
                )
            
            print(f"✅ Document processed successfully. Text saved to: {text_file_path}")
            print(f'Document type is {document_type}')
            
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
    
    def _is_scanned_pdf(self, pdf_path, max_pages=5, min_chars_per_page=50):
        """
        Detect if a PDF contains scanned images rather than digital text.
        
        Args:
            pdf_path (str): Path to the PDF file
            max_pages (int): Maximum number of pages to check
            min_chars_per_page (int): Minimum characters per page to consider as text
        
        Returns:
            bool: True if the PDF appears to be scanned, False otherwise
        """
        print("Detecting if PDF is scanned...")
        doc = fitz.open(pdf_path)
        pages_checked = 0
        empty_pages = 0
        
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pages_checked += 1
            if len(page.get_text().strip()) < min_chars_per_page:
                empty_pages += 1
        
        # If most checked pages have minimal text, likely a scanned document
        scanned_percentage = empty_pages / pages_checked
        print(f"Scanned pages detected: {empty_pages}/{pages_checked} ({scanned_percentage:.0%})")
        return scanned_percentage > 0.7
    
    def _has_annotations(self, pdf_path):
        """
        Check if a PDF has annotations.
        
        Args:
            pdf_path (str): Path to the PDF file
        
        Returns:
            bool: True if the PDF has annotations, False otherwise
        """
        print("Checking for annotations...")
        doc = fitz.open(pdf_path)
        for page in doc:
            if page.annots():
                return True
        return False
    
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
        print(f"📄 PDF appears to be scanned. Running OCR with languages: {', '.join(languages)}...")
        
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
            print("✅ PDF is clean digital text. Extracting...")
        
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