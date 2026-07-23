import json
from openai import OpenAI
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_CRITIC

class CriticAgent:
    @classmethod
    def _generate_mock_plan(cls, query: str) -> dict:
        """
        Chế độ Mô phỏng (Mock Mode):
        Tự động sinh kế hoạch tìm kiếm mẫu dựa trên từ khóa câu hỏi khi không có API Key.
        """
        q_lower = query.lower()
        
        if "giao tiếp" in q_lower or "ứng xử" in q_lower:
            return {
                "search_queries": [
                    "Kỹ năng giao tiếp ứng xử hiệu quả",
                    "Bài học giao tiếp từ sách Đắc Nhân Tâm",
                    "Phương pháp lắng nghe chân thành trong giao tiếp"
                ],
                "key_objectives": [
                    "Nghiên cứu nguyên tắc giao tiếp Đắc Nhân Tâm",
                    "Tổng hợp các phương pháp lắng nghe và thấu hiểu người đối diện"
                ],
                "instructions": "Tìm kiếm thông tin về sách Đắc Nhân Tâm và các kỹ năng giao tiếp ứng xử thực tế."
            }
        elif "khắc kỷ" in q_lower or "stoic" in q_lower:
            return {
                "search_queries": [
                    "Chủ nghĩa Khắc kỷ Stoicism ứng dụng",
                    "Ranh giới kiểm soát Dichotomy of Control",
                    "Rèn luyện tâm lý kiên cường trước biến cố"
                ],
                "key_objectives": [
                    "Phân tích triết lý Khắc kỷ Stoic",
                    "Tìm hiểu ranh giới những việc có thể và không thể kiểm soát"
                ],
                "instructions": "Thu thập tài liệu triết học Khắc kỷ Stoicism và ứng dụng trong cuộc sống hàng ngày."
            }
        elif "tập trung" in q_lower or "deep work" in q_lower or "pomodoro" in q_lower:
            return {
                "search_queries": [
                    "Phương pháp tập trung sâu Deep Work",
                    "Kỹ thuật quản lý thời gian Pomodoro",
                    "Bí quyết làm việc từ xa không bị sao nhãng"
                ],
                "key_objectives": [
                    "Nghiên cứu phương pháp Deep Work của Cal Newport",
                    "Ứng dụng kỹ thuật Pomodoro 25 phút"
                ],
                "instructions": "Cào dữ liệu và tổng hợp các bước rèn luyện sự tập trung làm việc hiệu quả."
            }
        else:
            return {
                "search_queries": [
                    f"{query} mới nhất",
                    f"tin tức thông tin về {query}",
                    f"hướng dẫn tổng quan {query}"
                ],
                "key_objectives": [
                    f"Nghiên cứu và tổng hợp đầy đủ thông tin về {query}",
                    f"Phân tích các khía cạnh chính của {query}"
                ],
                "instructions": f"Thực hiện tìm kiếm trên Google/DuckDuckGo để tổng hợp dữ liệu chi tiết cho: {query}"
            }

    @classmethod
    def generate_research_plan(cls, query: str) -> tuple[dict, dict]:
        """
        Tác nhân Phản biện & Lập kế hoạch nghiên cứu (Critic Agent):
        Gửi yêu cầu đến OpenAI API (gpt-4o-mini) ở chế độ JSON Object.
        Nếu không có API Key, tự động kích hoạt Chế độ Mô phỏng (_generate_mock_plan).
        
        Trả về:
            - plan (dict): Cấu trúc JSON kế hoạch nghiên cứu.
            - usage (dict): Thông tin tiêu thụ token của bước lập kế hoạch này.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        
        # Nếu không có API Key, kích hoạt Chế độ Mô phỏng (Mock Mode)
        if not api_key:
            return cls._generate_mock_plan(query), empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="critic-agent-research-plan",
                model=TraceConfig.DEFAULT_MODEL,
                input={"query": query}
            ) as generation:
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_CRITIC},
                        {"role": "user", "content": f"Hãy lập kế hoạch nghiên cứu tìm kiếm web cho câu hỏi: '{query}'"}
                    ],
                    response_format={"type": "json_object"}
                )
                
                result_text = response.choices[0].message.content
                usage_data = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
                generation.update(
                    output=result_text,
                    usage=usage_data
                )
                
                plan_data = json.loads(result_text)
                return plan_data, usage_data
                
        except Exception as e:
            print(f"Lỗi khi CriticAgent gọi LLM: {str(e)} -> Chuyển sang Chế độ Mô phỏng (Mock Mode)")
            return cls._generate_mock_plan(query), empty_usage

    @staticmethod
    def get_combined_plan_text(plan: dict) -> str:
        """
        Gộp tất cả các chuỗi trong search_queries và văn bản của instructions
        lại thành một chuỗi duy nhất để phục vụ kiểm duyệt tập trung.
        """
        queries_list = plan.get("search_queries", [])
        queries_text = " ".join(queries_list) if isinstance(queries_list, list) else str(queries_list)
        instructions_text = plan.get("instructions", "")
        
        combined_text = f"{queries_text} {instructions_text}".strip()
        return combined_text

    @classmethod
    def evaluate_and_refine(cls, query: str, raw_response: str) -> tuple[str, bool, str, dict]:
        """Thẩm định và hoàn thiện kết quả thô nếu cần thiết"""
        plan, usage = cls.generate_research_plan(query)
        return plan.get("instructions", raw_response), True, "Đã lập kế hoạch", usage

