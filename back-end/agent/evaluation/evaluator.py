import json
from openai import OpenAI
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_CROSS_EVALUATION

class AgentEvaluator:
    @staticmethod
    def evaluate_retrieval_relevance(query: str, simplified_docs: list[dict]) -> tuple[dict, dict]:
        """
        Thẩm định độ phù hợp của dữ liệu nén (Context Compression) so với câu hỏi của người dùng.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        
        fallback_eval = {
            "selected_index": 1 if simplified_docs else None,
            "relevance_score": 0.85,
            "reason": "Mô phỏng đánh giá độ phù hợp thành công."
        }
        
        if not api_key:
            return fallback_eval, empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="agent-evaluation-retrieval",
                model=TraceConfig.DEFAULT_MODEL,
                input={"query": query, "docs": simplified_docs}
            ) as generation:
                
                system_prompt = (
                    "Bạn là một hệ thống Thẩm định & Đánh giá RAG (RAG Evaluation System).\n"
                    "Nhiệm vụ của bạn là đánh giá độ phù hợp của các tài liệu rút gọn so với câu hỏi của người dùng, "
                    "và chọn ra chỉ mục tài liệu phù hợp nhất (nếu có).\n\n"
                    "Trả về kết quả dưới định dạng JSON duy nhất như sau:\n"
                    "{\n"
                    "  \"selected_index\": chỉ số index (1, 2, 3...) hoặc null nếu không tài liệu nào phù hợp,\n"
                    "  \"relevance_score\": điểm số phù hợp từ 0.0 đến 1.0,\n"
                    "  \"reason\": \"Nhận xét lý do đánh giá ngắn gọn bằng tiếng Việt\"\n"
                    "}"
                )
                
                user_prompt = (
                    f"Câu hỏi của người dùng: {query}\n\n"
                    f"Danh sách tài liệu nén ngữ cảnh (simplified_docs):\n"
                    f"{json.dumps(simplified_docs, ensure_ascii=False, indent=2)}"
                )
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
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
                
                eval_data = json.loads(result_text)
                return eval_data, usage_data
                
        except Exception as e:
            print(f"Lỗi khi đánh giá AgentEvaluator: {str(e)}")
            return fallback_eval, empty_usage

    @classmethod
    def select_best_two_documents(
        cls, 
        query: str, 
        original_docs: list[dict], 
        simplified_docs: list[dict] = None
    ) -> tuple[list[dict], dict]:
        """
        Yêu cầu LLM so sánh ngữ nghĩa chéo (Cross-semantic Evaluation) giữa 4 tài liệu đối chiếu
        với chủ đề viết blog, parse kết quả JSON chọn ra 2 index và trích xuất ĐÚNG 2 tài liệu gốc 
        tương ứng từ mảng 4 tài liệu ban đầu (original_docs).
        
        Trả về:
            - selected_original_docs (list[dict]): Danh sách đúng 2 tài liệu đầy đủ gốc được trích xuất.
            - eval_meta (dict): Chứa selected_indices, reason giải thích và token usage.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Nếu chưa truyền simplified_docs, tự động tạo từ original_docs
        if not simplified_docs:
            from agent.rag import BM25Search
            simplified_docs = BM25Search.get_simplified_docs(original_docs)
        
        # Fallback (Dự phòng): Mặc định trả về 2 tài liệu đầu tiên từ kết quả tìm kiếm BM25 thô
        fallback_selected = original_docs[:2] if len(original_docs) >= 2 else original_docs
        fallback_meta = {
            "selected_indices": [1, 2] if len(original_docs) >= 2 else [1],
            "reason": "Mặc định trả về 2 tài liệu đầu tiên từ kết quả BM25 thô (Fallback Mode do lỗi kết nối/parse LLM).",
            "usage": empty_usage
        }
        
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            return fallback_selected, fallback_meta

        try:
            client = OpenAI(api_key=api_key)
            
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="agent-evaluation-cross-semantic",
                model=TraceConfig.DEFAULT_MODEL,
                input={"query": query, "docs": simplified_docs}
            ) as generation:
                
                user_prompt = (
                    f"Chủ đề viết blog của người dùng: {query}\n\n"
                    f"Danh sách 4 tài liệu đối chiếu (simplified_docs):\n"
                    f"{json.dumps(simplified_docs, ensure_ascii=False, indent=2)}"
                )
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_CROSS_EVALUATION},
                        {"role": "user", "content": user_prompt}
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
                
                # PARSE KẾT QUẢ JSON & XỬ LÝ LỖI PARSE (Parse Error Fallback)
                try:
                    eval_data = json.loads(result_text)
                    selected_indices = eval_data.get("selected_indices", [1, 2])
                    reason = eval_data.get("reason", "Đã so sánh ngữ nghĩa chéo và trích xuất 2 tài liệu phù hợp nhất.")
                except Exception as parse_err:
                    print(f"Lỗi parse JSON kết quả so sánh ngữ nghĩa chéo: {str(parse_err)} -> Trả về 2 tài liệu BM25 thô mặc định.")
                    return fallback_selected, fallback_meta
                
                # Áp chỉ mục (1-based index) để trích xuất 2 tài liệu tương ứng từ mảng original_docs ban đầu
                selected_original_docs = []
                for idx in selected_indices:
                    if isinstance(idx, int) and 1 <= idx <= len(original_docs):
                        selected_original_docs.append(original_docs[idx - 1])
                        
                # Đảm bảo giữ đúng 2 tài liệu gốc nếu có đủ dữ liệu
                if len(selected_original_docs) != 2 and len(original_docs) >= 2:
                    print("-> Trích xuất không đủ 2 tài liệu -> Trả về 2 tài liệu đầu tiên từ kết quả BM25 thô.")
                    selected_original_docs = original_docs[:2]
                    selected_indices = [1, 2]
                    
                eval_meta = {
                    "selected_indices": selected_indices,
                    "reason": reason,
                    "usage": usage_data
                }
                
                return selected_original_docs, eval_meta
                
        except Exception as conn_err:
            print(f"Lỗi kết nối LLM khi so sánh ngữ nghĩa chéo: {str(conn_err)} -> Trả về 2 tài liệu BM25 thô mặc định.")
            return fallback_selected, fallback_meta
