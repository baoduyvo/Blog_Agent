from openai import OpenAI
from config.trace_config import TraceConfig

class VectorEmbedder:
    @staticmethod
    def get_embedding(text: str) -> tuple[list[float], int]:
        """
        Gửi yêu cầu đến API Embedding của OpenAI (text-embedding-3-small)
        để chuyển văn bản thành vector 1536 chiều đại diện cho tọa độ ngữ nghĩa.
        
        Trả về:
            - query_embedding (list[float]): Vector nhúng 1536 chiều.
            - embed_tokens (int): Số token đã tiêu thụ cho bước này.
        """
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            # Trả về vector rỗng làm fallback nếu không cấu hình API Key
            return [0.0] * 1536, 0

        try:
            client = OpenAI(api_key=api_key)
            
            # Ghi nhận bước tạo embedding này vào Langfuse dưới dạng Span
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="span",
                name="openai-embedding",
                metadata={"model": "text-embedding-3-small"},
                input={"text": text}
            ) as span:
                
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                
                embedding = response.data[0].embedding
                embed_tokens = response.usage.total_tokens
                
                # Cập nhật kết quả trace log
                span.update(
                    output={"dimension": len(embedding)},
                    usage={"total_tokens": embed_tokens}
                )
                
                return embedding, embed_tokens
                
        except Exception as e:
            print(f"Lỗi khi gọi OpenAI Embeddings API: {str(e)}")
            return [0.0] * 1536, 0
