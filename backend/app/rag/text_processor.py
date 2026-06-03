import fitz  
from typing import List, Dict, Any
import re
import io
from PIL import Image
import pytesseract
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
        """Extracts plain text with explicit page numbers and handles automatic OCR fallbacks."""
        pages_data = []
       
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
          
            if not text.strip():
                print(f"👁️ [OCR FALLBACK ACTIVATED] Scanned page layer detected on Page {page_num + 1}. Running Tesseract...")
                try:
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    text = pytesseract.image_to_string(image)
                except Exception as ocr_error:
                    print(f"⚠️ OCR extraction failed on page {page_num + 1}: {str(ocr_error)}")
                    text = ""

            if text:
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
                if len(split.strip()) > 10:  
                    chunks.append({
                        "text": split,
                        "page_number": page_num
                    })
        return chunks