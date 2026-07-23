import os
import json
import re
from rank_bm25 import BM25Okapi
from config.trace_config import TraceConfig

class BM25Search:
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tách từ đơn giản và dọn dẹp ký tự cho thuật toán BM25"""
        if not text:
            return []
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = [w for w in cleaned.split() if len(w) > 1]
        return tokens

    @classmethod
    def search_local_books(cls, query: str, top_k: int = 4) -> list[dict]:
        """
        Thực hiện tìm kiếm từ khóa thô (thuật toán BM25) trong kho tài liệu cục bộ
        (local_knowledge.json / sách nội bộ) dựa trên chủ đề của người dùng.
        
        Trả về:
            - list[dict]: Danh sách tối đa top_k (mặc định 4) tài liệu ứng viên (docs)
              có độ trùng khớp từ khóa cao nhất kèm điểm số BM25 score.
        """
        knowledge_path = os.path.join(TraceConfig.ROOT_DIR, "data", "local_knowledge.json")
        if not os.path.exists(knowledge_path):
            print(f"Không tìm thấy kho tài liệu cục bộ tại: {knowledge_path}")
            return []

        try:
            with open(knowledge_path, "r", encoding="utf-8") as f:
                documents = json.load(f)
        except Exception as e:
            print(f"Lỗi khi đọc kho tài liệu local_knowledge.json: {str(e)}")
            return []

        if not documents:
            return []

        # 1. Tách từ cho toàn bộ các tài liệu trong kho sách
        corpus_tokens = []
        doc_list = []

        for doc in documents:
            # Tạo chuỗi văn bản hợp nhất (Book + Topic + Content + Tags)
            book = doc.get("book", "")
            topic = doc.get("topic", "")
            content = doc.get("content", "")
            tags = " ".join(doc.get("tags", []))
            
            full_text = f"{book} {topic} {content} {tags}"
            tokens = cls._tokenize(full_text)
            
            if tokens:
                corpus_tokens.append(tokens)
                doc_list.append(doc)

        if not corpus_tokens:
            return []

        # 2. Khởi tạo mô hình BM25Okapi với toàn bộ corpus
        bm25 = BM25Okapi(corpus_tokens)

        # 3. Tách từ cho câu hỏi/chủ đề của người dùng
        query_tokens = cls._tokenize(query)
        if not query_tokens:
            return doc_list[:top_k]

        # 4. Tính toán điểm số BM25 (BM25 Scores) cho từng tài liệu
        doc_scores = bm25.get_scores(query_tokens)

        # 5. Sắp xếp và lấy ra top_k tài liệu có điểm trùng khớp từ khóa cao nhất
        scored_docs = list(zip(doc_list, doc_scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        top_docs = []
        for doc, score in scored_docs[:top_k]:
            doc_copy = dict(doc)
            doc_copy["bm25_score"] = float(score)
            top_docs.append(doc_copy)

        return top_docs

    @classmethod
    def get_simplified_docs(cls, docs: list[dict]) -> list[dict]:
        """
        Nén dữ liệu ngữ cảnh (Context Compression):
        Tạo danh sách rút gọn simplified_docs chứa:
            - index (chỉ mục 1, 2, 3, 4...)
            - title (tiêu đề bài viết/sách + chủ đề)
            - snippet (cắt ngắn đúng 150 ký tự đầu tiên của nội dung bài viết)
        """
        simplified_docs = []
        for idx, doc in enumerate(docs, start=1):
            book = doc.get("book", "")
            topic = doc.get("topic", "")
            title = f"{book} - {topic}" if book and topic else (topic or doc.get("title", ""))
            
            content = doc.get("content", "")
            snippet = content[:150] if len(content) > 150 else content
            
            simplified_docs.append({
                "index": idx,
                "title": title,
                "snippet": snippet
            })
            
        return simplified_docs

