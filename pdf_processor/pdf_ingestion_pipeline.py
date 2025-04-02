import os
import subprocess
import argparse
import sys
from tqdm import tqdm
import fitz  # PyMuPDF

# ============================
# DEPENDENCY INSTALLATION INFO
# ============================
# Required pip packages:
# - PyMuPDF: pip install PyMuPDF
# - tqdm: pip install tqdm
#
# System dependencies:
# - Tesseract OCR:
#   - macOS: brew install tesseract
#   - Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   - Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki

def check_dependencies():
    """Check if all required dependencies are installed"""
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

# === Utility Functions ===

def is_scanned(pdf_path, max_pages=5, min_chars_per_page=50):
    """Better detection of scanned PDFs by looking at text density"""
    doc = fitz.open(pdf_path)
    pages_checked = 0
    empty_pages = 0
    
    print("Detecting if PDF is scanned...")
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

def has_annotations(pdf_path):
    """Check if PDF has annotations"""
    print("Checking for annotations...")
    doc = fitz.open(pdf_path)
    for page in doc:
        if page.annots():
            return True
    return False

def ocr_with_tesseract(input_pdf, output_folder, languages=["eng"]):
    """OCR with PDF to image conversion first"""
    print(f"Converting PDF to images and running OCR with languages: {', '.join(languages)}...")
    
    # Create output folders
    os.makedirs(output_folder, exist_ok=True)
    images_folder = os.path.join(output_folder, "images")
    os.makedirs(images_folder, exist_ok=True)
    
    # Convert PDF to images using PyMuPDF
    doc = fitz.open(input_pdf)
    image_files = []
    
    # Extract each page as an image
    for page_num, page in enumerate(tqdm(doc, desc="Converting pages to images")):
        pix = page.get_pixmap(dpi=300)  # Higher DPI for better OCR quality
        image_path = os.path.join(images_folder, f"page_{page_num+1}.png")
        pix.save(image_path)
        image_files.append(image_path)
    
    # Now process each image with Tesseract
    text_results = []
    for i, image_path in enumerate(tqdm(image_files, desc="OCR Processing")):
        # Create a temporary text file path
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        text_file = os.path.join(output_folder, f"{base_name}.txt")
        
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
    output_text_file = os.path.join(output_folder, "ocr_result.txt")
    with open(output_text_file, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    return output_text_file

def extract_structured_text(pdf_path):
    """Extract text with structure preservation and progress display"""
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

def extract_annotations(pdf_path):
    """Extract annotations as separate structured data with progress indicator"""
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
                "highlighted_text": get_text_for_annotation(page, annot)
            }
            annotations.append(annot_data)
    
    return annotations

def get_text_for_annotation(page, annot):
    """Get the text covered by an annotation"""
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

def save_text_to_file(text, out_path):
    """Save extracted text to a file"""
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

# === Main Ingestion Logic ===

def prepare_pdf_for_llm(input_pdf, output_text_file, tmp_folder="tmp/", languages=["eng"]):
    """Main function to process PDF and make it LLM-ready"""
    os.makedirs(tmp_folder, exist_ok=True)
    print(f"🔍 Analyzing: {input_pdf}")
    
    try:
        # Main processing workflow with progress tracking
        steps = ["Analyzing PDF", "Processing content", "Saving output"]
        with tqdm(total=len(steps), desc="Overall progress", position=0) as pbar:
            pbar.set_description(f"Step 1: {steps[0]}")
            
            if is_scanned(input_pdf):
                print("📄 PDF appears to be scanned. Running OCR...")
                # Create a subfolder for OCR outputs
                ocr_folder = os.path.join(tmp_folder, "ocr_output")
                pbar.update(1)
                
                pbar.set_description(f"Step 2: {steps[1]}")
                # This function now handles both conversion to images and OCR
                ocr_text_file = ocr_with_tesseract(input_pdf, ocr_folder, languages)
                
                # Read the OCR result directly - no need to extract text again
                with open(ocr_text_file, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                if has_annotations(input_pdf):
                    print("📝 PDF has annotations. Extracting and processing...")
                    pbar.update(1)
                    
                    pbar.set_description(f"Step 2: {steps[1]}")
                    # Extract main text
                    text = extract_structured_text(input_pdf)
                    
                    # Also extract annotations as structured data
                    annotations = extract_annotations(input_pdf)
                    
                    # Append annotations in a structured format
                    if annotations:
                        text += "\n\n=== ANNOTATIONS ===\n\n"
                        for i, annot in enumerate(annotations):
                            text += f"Annotation {i+1} (Page {annot['page']}, {annot['type']}):\n"
                            text += f"Text: {annot['highlighted_text']}\n"
                            if annot['content']:
                                text += f"Comment: {annot['content']}\n"
                            text += "\n"
                else:
                    print("✅ PDF is clean digital text. Extracting...")
                    pbar.update(1)
                    
                    pbar.set_description(f"Step 2: {steps[1]}")
                    text = extract_structured_text(input_pdf)
            
            pbar.set_description(f"Step 3: {steps[2]}")
            # Save the final text
            save_text_to_file(text, output_text_file)
            pbar.update(1)
            
        print(f"📤 Text saved to: {output_text_file}")
        return output_text_file
    
    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        raise

# === Command-line interface ===

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PDF files for LLM input")
    parser.add_argument("input_pdf", help="Path to the input PDF file")
    parser.add_argument("--output", "-o", default="text_for_llm.txt", 
                        help="Path for the output text file")
    parser.add_argument("--tmp", default="tmp/", 
                        help="Temporary folder for intermediate files")
    parser.add_argument("--lang", default="eng", 
                        help="Languages for OCR, comma-separated (e.g., eng,fra,deu)")
    
    args = parser.parse_args()
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Convert comma-separated languages to list
    languages = args.lang.split(",")
    
    try:
        prepare_pdf_for_llm(args.input_pdf, args.output, args.tmp, languages)
        print("✨ Processing completed successfully!")
    except Exception as e:
        print(f"Failed to process PDF: {str(e)}")
        sys.exit(1)