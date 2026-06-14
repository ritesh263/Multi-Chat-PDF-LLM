import fitz  
import docx
import io
import nltk
from typing import List, Dict, Any

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

class DocumentProcessor:
    @staticmethod
    def extract_text_with_metadata(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        ext = filename.lower().split('.')[-1]
        pages_data = []

        try:
            if ext == 'pdf':
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page_num in range(len(doc)):
                    page_text = doc[page_num].get_text()
                    if page_text.strip():
                        pages_data.append({"text": page_text, "page_number": page_num + 1})
            elif ext in ['txt', 'md']:
                text = file_bytes.decode('utf-8', errors='ignore')
                pages_data.append({"text": text, "page_number": 1})
            elif ext == 'docx':
                doc = docx.Document(io.BytesIO(file_bytes))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                pages_data.append({"text": text, "page_number": 1})
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
            return pages_data
        except Exception as e:
            raise Exception(f"Failed to parse document: {str(e)}")

    @staticmethod
    def chunk_text(pages_data: List[Dict[str, Any]], chunk_size: int = 800, overlap: int = 200) -> List[Dict[str, Any]]:
        """Semantic chunking: respects sentence boundaries instead of cutting words in half."""
        chunks = []
        for page in pages_data:
            text = page["text"]
            page_num = page["page_number"]
            
            sentences = nltk.sent_tokenize(text)
            
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence.split())
                
                if current_length + sentence_length > chunk_size and current_chunk:
                    chunks.append({"text": " ".join(current_chunk), "page_number": page_num})
                    
                    overlap_chunk = []
                    overlap_length = 0
                    for s in reversed(current_chunk):
                        if overlap_length + len(s.split()) <= overlap:
                            overlap_chunk.insert(0, s)
                            overlap_length += len(s.split())
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_length = overlap_length
                    
                current_chunk.append(sentence)
                current_length += sentence_length
                
            if current_chunk:
                chunks.append({"text": " ".join(current_chunk), "page_number": page_num})
                
        return chunks