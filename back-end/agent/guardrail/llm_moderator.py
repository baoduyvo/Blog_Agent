import json
from openai import OpenAI
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_MODERATION

class LLMModerator:
    @staticmethod
    def is_flagged(prompt: str) -> tuple[bool, dict]:
        """
        Gọi LLM để kiểm duyệt tin nhắn đầu vào (nhận diện nội dung bậy bạ, tục tĩu,
        hoặc cố tình tấn công prompt injection).
        Trả về:
            - flagged (bool): True nếu bị gắn cờ, ngược lại False.
            - usage (dict): Thông tin tiêu thụ token của cuộc gọi LLM này.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            return False, empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            # Ghi nhận bước gọi LLM kiểm duyệt vào Langfuse
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="guardrail-llm-moderation",
                model=TraceConfig.DEFAULT_MODEL,
                input=prompt
            ) as generation:
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT_MODERATION
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
                return data.get("flagged", False), usage_data
                
        except Exception as e:
            print(f"Lỗi khi kiểm duyệt bằng LLM: {str(e)}")
            return False, empty_usage
