from openai import OpenAI
from config.trace_config import TraceConfig

class SearchAgent:
    def __init__(self):
        self.api_key = TraceConfig.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        # Cấu hình Langfuse dùng chung từ config
        self.langfuse = TraceConfig.get_langfuse_client()

    def answer_query(self, query: str) -> tuple:
        if not self.client:
            return f"Mock Agent Response: Đang tìm kiếm '{query}' nhưng chưa cấu hình OpenAI API Key.", None
        
        # Bắt đầu ghi nhận LLM Generation dưới trace hiện tại (kế thừa từ context active)
        with self.langfuse.start_as_current_observation(
            as_type="generation",
            name="openai-completion",
            model=TraceConfig.DEFAULT_MODEL,
            model_parameters={"temperature": 0.7},
            input=[
                {"role": "system", "content": "Bạn là một trợ lý tư vấn tìm kiếm khóa học và lập trình."},
                {"role": "user", "content": f"Hãy gợi ý hoặc trả lời về: {query}"}
            ]
        ) as generation:
            try:
                answer = "Tôi Xin Cảm Ơn Quý Khách !!!!!!!!!!!!!"
                usage_data = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
                
                # Cập nhật kết quả vào generation (tự động hoàn thành khi thoát block with)
                generation.update(
                    output=answer,
                    usage=usage_data
                )
                return answer, usage_data

            except Exception as e:
                error_msg = f"Lỗi từ OpenAI: {str(e)}"
                generation.update(
                    level="ERROR",
                    status_message=error_msg
                )
                return error_msg, None
