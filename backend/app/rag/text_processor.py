import fitz  # 🟢 Upgraded from pypdf to PyMuPDF for native image rendering
from typing import List, Dict, Any
import re
import io
from PIL import Image
import pytesseract
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 🟢 Windows Path Pointer Config: 
# If Tesseract isn't globally registered in your Windows Environment Path variables, 
# uncomment the line below and point it to your local installation directory:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
        """Extracts plain text with explicit page numbers and handles automatic OCR fallbacks."""
        pages_data = []
        
        # Open document using PyMuPDF engine
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # 🟢 OCR FALLBACK TRACE: If page yields no digital character matrix, process visually
            if not text.strip():
                print(f"👁️ [OCR FALLBACK ACTIVATED] Scanned page layer detected on Page {page_num + 1}. Running Tesseract...")
                try:
                    # 1. Rasterize PDF vector into a high-res image stream in memory (300 DPI)
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    
                    # 2. Re-hydrate bytes stream into a standard PIL Image instance
                    image = Image.open(io.BytesIO(img_data))
                    
                    # 3. Read image canvas text characters visually
                    text = pytesseract.image_to_string(image)
                except Exception as ocr_error:
                    print(f"⚠️ OCR extraction failed on page {page_num + 1}: {str(ocr_error)}")
                    text = ""

            if text:
                # Execute your exact character sanitization routines
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    pages_data.append({
                        "page_number": page_num + 1,
                        "text": text
                    })
                    
        doc.close()
        return pages_data

    @staticmethod
    def split_documents(pages_data: List[Dict[str, Any]], chunk_size: int = 600, chunk_overlap: int = 120) -> List[Dict[str, Any]]:
        """Splits text sequences while tracking page lineages safely."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = []
        for page in pages_data:
            page_text = page["text"]
            page_num = page["page_number"]
            
            splits = splitter.split_text(page_text)
            for split in splits:
                if len(split.strip()) > 10:  # Prune meaningless artifacts
                    chunks.append({
                        "text": split,
                        "page_number": page_num
                    })
        return chunks