import json
from openai import OpenAI
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_ROUTER

class MultiAgentRouter:
    @staticmethod
    def route_query(prompt: str) -> tuple[str, str, dict]:
        """
        Định tuyến tác nhân động (Dynamic Router) bằng LLM.
        Phân tích câu hỏi người dùng để quyết định chọn nguồn tri thức phù hợp.
        
        Trả về:
            - route (str): Nguồn tri thức được định tuyến ('WEB_SEARCH' hoặc 'LOCAL_KNOWLEDGE').
            - reason (str): Lý do định tuyến cụ thể.
            - usage (dict): Thông tin tiêu thụ token của cuộc gọi LLM định tuyến này.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            return "LOCAL_KNOWLEDGE", "Không cấu hình API Key - Mặc định chọn LOCAL_KNOWLEDGE", empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            # Ghi nhận bước định tuyến này vào Langfuse
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="dynamic-agent-routing",
                model=TraceConfig.DEFAULT_MODEL,
                input=prompt
            ) as generation:
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT_ROUTER
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
                route = data.get("route", "LOCAL_KNOWLEDGE")
                reason = data.get("reason", "")
                return route, reason, usage_data
                
        except Exception as e:
            print(f"Lỗi khi định tuyến tác nhân: {str(e)}")
            return "LOCAL_KNOWLEDGE", f"Lỗi hệ thống: {str(e)}", empty_usage
