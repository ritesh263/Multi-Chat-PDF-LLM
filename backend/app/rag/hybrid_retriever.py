from typing import List, Dict, Any
import re

class HybridRanker:
    @staticmethod
    def extract_keywords(text: str) -> set:
        """Tokenizes text into a clean set of lowercased alphanumeric keywords."""
        return set(re.findall(r'\b\w{3,}\b', text.lower()))

    @classmethod
    def score_lexical_relevance(cls, query: str, chunk_text: str) -> float:
        """
        Calculates a lightweight Jaccard-style keyword overlap score 
        to serve as a localized lexical ranker fallback.
        """
        query_words = cls.extract_keywords(query)
        chunk_words = cls.extract_keywords(chunk_text)
        
        if not query_words:
            return 0.0
            
        intersection = query_words.intersection(chunk_words)
        return len(intersection) / len(query_words)

    @classmethod
    def merge_results(cls, query: str, vector_results: List[Dict[str, Any]], alpha: float = 0.7) -> List[Dict[str, Any]]:
        """
        Merges and re-ranks vector search outputs by blending dense semantic 
        scores with sparse keyword overlap scores.
        
        Parameters:
          - alpha: Weight given to semantic vector search (0.7 = 70% vector, 30% keyword)
        """
        re_ranked = []
        
        for item in vector_results:
            vector_score = item["metadata"].get("score", 0.0)
            lexical_score = cls.score_lexical_relevance(query, item["text"])
            
            hybrid_score = (alpha * vector_score) + ((1 - alpha) * lexical_score)
            
            item["metadata"]["hybrid_composite_score"] = float(hybrid_score)
            re_ranked.append(item)
            
        re_ranked.sort(key=lambda x: x["metadata"]["hybrid_composite_score"], reverse=True)
        return re_ranked