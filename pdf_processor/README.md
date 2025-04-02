




┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│                 │     │                    │     │                  │
│  Input PDF      │────▶│  Is Scanned PDF?   │────▶│  PDFPlumber      │
│  (Insurance     │     │  Detection         │  No │  (Text-based     │
│   Policy)       │     │                    │     │   processing)    │
│                 │     │                    │     │                  │
└─────────────────┘     └────────┬───────────┘     └──────────┬───────┘
                                 │ Yes                        │
                                 ▼                            │
                        ┌────────────────────┐                │
                        │                    │                │
                        │  Tesseract OCR     │                │
                        │  (Scanned PDF      │                │
                        │   processing)      │                │
                        │                    │                │
                        └──────────┬─────────┘                │
                                   │                          │
                                   ▼                          ▼
                        ┌────────────────────┐     ┌──────────────────┐
                        │                    │     │                  │
                        │  Table             │◀────│  Table           │
                        │  Detection         │     │  Extraction      │
                        │  (from OCR)        │     │  (PDFPlumber)    │
                        │                    │     │                  │
                        └──────────┬─────────┘     └──────────┬───────┘
                                   │                          │
                                   └──────────────┬───────────┘
                                                  │
                                                  ▼
                                   ┌────────────────────────────┐
                                   │                            │
                                   │  Format Content            │
                                   │  (Text or Markdown)        │
                                   │                            │
                                   └─────────────┬──────────────┘
                                                 │
                                                 ▼
                                   ┌────────────────────────────┐
                                   │                            │
                                   │  Output                    │
                                   │  (Text/Markdown)           │
                                   │                            │
                                   └────────────────────────────┘


#Detailed Processing Logic
##PDF Type Detection
The system will automatically detect whether a PDF is primarily text-based or scanned:

1. Open the PDF with PDFPlumber
2. Sample the first few pages (up to 5)
3. For each page, extract text and count characters
4. If the average character count per page is below the threshold (default: 5), consider it a scanned document
5. If force_ocr=True, skip this detection and process everything with OCR