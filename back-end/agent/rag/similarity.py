import math
import json
import os
from config.trace_config import TraceConfig
from agent.rag.vector_embedding import VectorEmbedder
from agent.rag.db import EmbeddingDatabase

class SimilaritySearch:
    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """
        Tính toán độ tương đồng Cosine (Cosine Similarity) giữa hai vector.
        Độ tương đồng nằm trong khoảng [-1.0, 1.0], càng gần 1.0 càng tương đồng lớn.
        """
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    @classmethod
    def find_most_similar_log(cls, query_embedding: list[float]) -> tuple[dict, float, int]:
        """
        Tìm kiếm câu hỏi có độ tương đồng ngữ nghĩa cao nhất trong tệp trace_logs.json.
        """
        logs_path = TraceConfig.LOCAL_LOG_PATH
        if not os.path.exists(logs_path):
            return None, 0.0, 0

        try:
            with open(logs_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            return None, 0.0, 0

        best_match = None
        best_score = -1.0
        extra_tokens = 0

        for log in logs:
            if not log.get("input"):
                continue

            # Lấy vector nhúng từ SQLite database hoặc file log
            key = log["input"]
            past_embedding = log.get("embedding") or EmbeddingDatabase.get_embedding(key)
            if not past_embedding:
                past_embedding, tokens = VectorEmbedder.get_embedding(key)
                extra_tokens += tokens
                EmbeddingDatabase.save_embedding(key, past_embedding)
            
            if past_embedding:
                score = cls.cosine_similarity(query_embedding, past_embedding)
                if score > best_score:
                    best_score = score
                    best_match = log

        return best_match, best_score, extra_tokens

    @classmethod
    def find_most_similar_blog(cls, query_embedding: list[float]) -> tuple[dict, float]:
        """
        Tìm kiếm bài viết blog có độ tương đồng ngữ nghĩa cao nhất trong blog_posts.json.
        Tự động lấy vector nhúng tương ứng từ CSDL SQLite embeddings.db.
        """
        blog_path = os.path.join(TraceConfig.ROOT_DIR, "data", "blog_posts.json")
        if not os.path.exists(blog_path):
            return None, 0.0

        try:
            with open(blog_path, "r", encoding="utf-8") as f:
                blogs = json.load(f)
        except Exception:
            return None, 0.0

        best_match = None
        best_score = -1.0

        for blog in blogs:
            key = blog["title"]
            past_embedding = blog.get("embedding") or EmbeddingDatabase.get_embedding(key)
            if not past_embedding:
                past_embedding, tokens = VectorEmbedder.get_embedding(key)
                EmbeddingDatabase.save_embedding(key, past_embedding)
            
            if past_embedding:
                score = cls.cosine_similarity(query_embedding, past_embedding)
                if score > best_score:
                    best_score = score
                    best_match = blog

        return best_match, best_score

    @classmethod
    def find_most_similar_knowledge(cls, query_embedding: list[float]) -> tuple[dict, float]:
        """
        Tìm kiếm bài học tri thức có độ tương đồng ngữ nghĩa cao nhất trong local_knowledge.json.
        Tự động lấy vector nhúng tương ứng từ CSDL SQLite embeddings.db.
        """
        knowledge_path = os.path.join(TraceConfig.ROOT_DIR, "data", "local_knowledge.json")
        if not os.path.exists(knowledge_path):
            return None, 0.0

        try:
            with open(knowledge_path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            return None, 0.0

        best_match = None
        best_score = -1.0
    
        for item in items:
            key = f"{item['book']} - {item['topic']} - {item['content']}"
            past_embedding = item.get("embedding") or EmbeddingDatabase.get_embedding(key)
            if not past_embedding:
                past_embedding, tokens = VectorEmbedder.get_embedding(key)
                EmbeddingDatabase.save_embedding(key, past_embedding)
            
            if past_embedding:
                score = cls.cosine_similarity(query_embedding, past_embedding)
                if score > best_score:
                    best_score = score
                    best_match = item

        return best_match, best_score
