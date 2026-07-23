import json
from openai import OpenAI
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_CLASSIFICATION

class LLMClassifier:
    @staticmethod
    def classify_prompt(prompt: str) -> tuple[bool, str, dict]:
        """
        Phân loại ngữ cảnh nâng cao của chủ đề/câu hỏi người dùng gửi lên.
        Trả về:
            - is_safe_and_relevant (bool): True nếu an toàn và đúng chủ đề blog/phản tư, ngược lại False.
            - reason (str): Giải thích chi tiết lý do bị chặn bằng tiếng Việt nếu không hợp lệ.
            - usage (dict): Thông tin tiêu thụ token của cuộc gọi LLM phân loại này.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            return True, "", empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            # Ghi nhận bước gọi LLM phân loại vào Langfuse
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="guardrail-llm-classification",
                model=TraceConfig.DEFAULT_MODEL,
                input=prompt
            ) as generation:
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT_CLASSIFICATION
                        },
                        {"role": "user", "content": prompt}
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
                
                data = json.loads(result_text)
                is_safe = data.get("is_safe_and_relevant", True)
                reason = data.get("reason", "Hợp lệ")
                return is_safe, reason, usage_data
                
        except Exception as e:
            print(f"Lỗi khi phân loại bằng LLM: {str(e)}")
            return True, "", empty_usage
