from agent.agents import SearchAgent
from agent.guardrail import InputGuardrail
from services.local_trace_logger import LocalTraceLogger
from config.trace_config import TraceConfig
from agent.rag import VectorEmbedder, EmbeddingDatabase

# Sử dụng Langfuse client dùng chung
langfuse = TraceConfig.get_langfuse_client()


class ChatService:
    @staticmethod
    def chat_with_ai(message: str, request_meta: dict = None) -> str:
        # 1. Tạo một span để đo lường và log quá trình kiểm tra Guardrail bằng context manager
        with langfuse.start_as_current_observation(
            as_type="span",
            name="input-guardrail-check",
            input={"message": message}
        ) as guardrail_span:
            is_safe, reason, steps_trace, guardrail_usage = InputGuardrail.is_safe(message)
            guardrail_span.update(output={
                "is_safe": is_safe, 
                "reason": reason, 
                "steps": steps_trace,
                "usage": guardrail_usage
            })
        
        if not is_safe:
            msg = reason or "Nội dung tin nhắn chứa từ khóa không an toàn hoặc bị cấm."
            
            # Ghi log cục bộ khi không an toàn (kèm theo toàn bộ vết trace từng bước và token)
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=False,
                steps=steps_trace,
                ai_response=msg,
                request_meta=request_meta,
                usage=guardrail_usage
            )
            return msg
        
        # 1.4. Tạo Vector nhúng cho câu hỏi (Embedding)
        query_embedding, embed_tokens = VectorEmbedder.get_embedding(message)
        
        # Lưu trữ vector nhúng vào SQLite database thay vì lưu vào trace log
        EmbeddingDatabase.save_embedding(message, query_embedding)
        
        # Thêm bước tạo Embedding vào trace
        embedding_usage = {
            "prompt_tokens": embed_tokens,
            "completion_tokens": 0,
            "total_tokens": embed_tokens
        }
        steps_trace.append({
            "step": "Lớp 1.4 - Tạo Vector nhúng (Embedding)",
            "status": "passed",
            "usage": embedding_usage
        })
        
        # Cộng dồn token của bước embedding vào guardrail_usage
        for k in guardrail_usage:
            guardrail_usage[k] += embedding_usage.get(k, 0)

        # 1.5. So khớp tương đồng ngữ nghĩa trong CSDL Blog và Local Knowledge mẫu (Cosine Similarity)
        from agent.rag.similarity import SimilaritySearch
        from agent.multi import MultiAgentRouter
        
        best_blog, blog_score = SimilaritySearch.find_most_similar_blog(query_embedding)
        best_knowledge, knowledge_score = SimilaritySearch.find_most_similar_knowledge(query_embedding)
        
        # Chọn kết quả có độ tương đồng cao nhất giữa Blog và Knowledge
        if knowledge_score > blog_score:
            best_match = best_knowledge
            best_title = f"{best_knowledge['book']}: {best_knowledge['topic']}" if best_knowledge else "N/A"
            similarity_score = knowledge_score
            is_from_knowledge = True
        else:
            best_match = best_blog
            best_title = best_blog['title'] if best_blog else "N/A"
            similarity_score = blog_score
            is_from_knowledge = False
        
        # Thêm bước so khớp tương đồng ngữ nghĩa vào trace
        steps_trace.append({
            "step": "Lớp 1.5 - Tìm kiếm tương đồng ngữ nghĩa (Cosine Similarity)",
            "status": "passed",
            "reason": f"Khớp nhất: '{best_title}' (Score: {similarity_score:.4f})" if best_match else "Không có dữ liệu tri thức để so sánh",
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        })
        
        # Kiểm tra điều kiện Cache Hit (>= 92%)
        if best_match and similarity_score >= 0.92:
            if is_from_knowledge:
                answer = (
                    f"### {best_match['book']} - {best_match['topic']}\n"
                    f"{best_match['content']}\n\n"
                    f"**Thẻ từ khóa:** {', '.join(best_match.get('tags', []))}"
                )
            else:
                answer = (
                    f"### {best_match['title']}\n"
                    f"{best_match['content']}\n\n"
                    f"**Nguồn tham khảo:**\n"
                    + "\n".join(f"- {ref}" for ref in best_match.get("references", []))
                )
            
            # Ghi log cục bộ thành công với kết quả từ Cache (Lớp 2 lúc này là Cache)
            steps_trace.append({
                "step": "Lớp 2 - Trả dữ liệu trực tiếp từ Semantic Cache",
                "status": "passed",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            })
            
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=True,
                steps=steps_trace,
                ai_response=answer,
                request_meta=request_meta,
                usage=guardrail_usage
            )
            return answer

        # 1.6. Định tuyến tác nhân động (Dynamic Router) khi Cache Miss (< 92%)
        route, route_reason, router_usage = MultiAgentRouter.route_query(message)
        
        # Tích lũy token định tuyến
        for k in guardrail_usage:
            guardrail_usage[k] += router_usage.get(k, 0)

        steps_trace.append({
            "step": f"Lớp 1.6 - Định tuyến tác nhân ({route})",
            "status": "passed",
            "reason": route_reason,
            "usage": router_usage
        })

        # 2. Xử lý theo từng nhánh định tuyến của Router (Tạm thời comment nhánh LOCAL_KNOWLEDGE theo yêu cầu)
        # if route == "LOCAL_KNOWLEDGE" and best_knowledge:
        #     context_text = f"Sách: {best_knowledge.get('book')}\nChủ đề: {best_knowledge.get('topic')}\nNội dung: {best_knowledge.get('content')}"
        #     answer, synth_usage = ChatService._synthesize_local_answer(message, context_text)
        #     
        #     for k in guardrail_usage:
        #         guardrail_usage[k] += synth_usage.get(k, 0)
        #         
        #     steps_trace.append({
        #         "step": "Lớp 2 - Tổng hợp phản hồi từ Tri thức nội bộ (Local Knowledge)",
        #         "status": "passed",
        #         "usage": synth_usage
        #     })
        #     
        #     LocalTraceLogger.log_trace(
        #         message=message,
        #         is_safe=True,
        #         steps=steps_trace,
        #         ai_response=answer,
        #         request_meta=request_meta,
        #         usage=guardrail_usage
        #     )
        #     return answer

        # Thực thi quy trình Multi-Agent Research đầy đủ
        if True: # route == "WEB_SEARCH" hoặc tiếp tục chạy luồng nghiên cứu đầy đủ
            # 2.1. Gọi Critic Agent lập kế hoạch nghiên cứu tìm kiếm Web dạng JSON
            from agent.multi import CriticAgent
            critic_plan, critic_usage = CriticAgent.generate_research_plan(message)
            
            # Tích lũy token của Critic Agent
            for k in guardrail_usage:
                guardrail_usage[k] += critic_usage.get(k, 0)
                
            steps_trace.append({
                "step": "Lớp 2.1 - Lập kế hoạch nghiên cứu (Critic Agent)",
                "status": "passed",
                "reason": f"Từ khóa: {', '.join(critic_plan.get('search_queries', []))}",
                "usage": critic_usage,
                "plan": critic_plan
            })
            
            # 2.1b. Gộp tất cả các chuỗi trong search_queries và văn bản instructions thành một chuỗi duy nhất để kiểm duyệt tập trung qua InputGuardrail
            combined_plan_text = CriticAgent.get_combined_plan_text(critic_plan)
            plan_safe, plan_reason, plan_trace, plan_guard_usage = InputGuardrail.verify_combined_plan(combined_plan_text)
            
            # Tích lũy token từ bước kiểm duyệt kế hoạch
            for k in guardrail_usage:
                guardrail_usage[k] += plan_guard_usage.get(k, 0)
                
            if not plan_safe:
                reason_msg = f"Kế hoạch tìm kiếm bị chặn do không an toàn: {plan_reason}"
                steps_trace.append({
                    "step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)",
                    "status": "failed",
                    "reason": reason_msg,
                    "usage": plan_guard_usage
                })
                
                LocalTraceLogger.log_trace(
                    message=message,
                    is_safe=False,
                    steps=steps_trace,
                    ai_response=reason_msg,
                    request_meta=request_meta,
                    usage=guardrail_usage
                )
                return reason_msg

            steps_trace.append({
                "step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)",
                "status": "passed",
                "reason": "Kế hoạch tìm kiếm và chỉ dẫn hoàn toàn an toàn",
                "usage": plan_guard_usage
            })
            
            # 2.2. Gọi ResearcherAgent thực hiện nghiên cứu / cào dữ liệu theo kế hoạch từ Critic Agent
            from agent.multi import ResearcherAgent
            research_result, researcher_usage = ResearcherAgent.execute_research(message, critic_plan)
            
            # Tích lũy token của Researcher Agent
            for k in guardrail_usage:
                guardrail_usage[k] += researcher_usage.get(k, 0)
                
            steps_trace.append({
                "step": "Lớp 2.2 - Thực thi nghiên cứu & cào dữ liệu (ResearcherAgent)",
                "status": "passed",
                "usage": researcher_usage
            })

            # 3.1. Tìm kiếm từ khóa thô (BM25Search) trong kho sách nội bộ (local_knowledge.json)
            from agent.rag import BM25Search
            from agent.evaluation import AgentEvaluator
            
            raw_bm25_docs = BM25Search.search_local_books(message, top_k=4)
            simplified_docs = BM25Search.get_simplified_docs(raw_bm25_docs)
            
            steps_trace.append({
                "step": "Lớp 3.1 - Tìm kiếm từ khóa thô (BM25Search)",
                "status": "passed",
                "reason": f"Đã trích xuất {len(raw_bm25_docs)} tài liệu ứng viên từ kho sách nội bộ",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            })
            
            # 3.2. So sánh ngữ nghĩa chéo & Trích xuất 2 tài liệu gốc phù hợp nhất bằng AgentEvaluator
            selected_bm25_docs, eval_meta = AgentEvaluator.select_best_two_documents(
                query=message,
                original_docs=raw_bm25_docs,
                simplified_docs=simplified_docs
            )
            
            eval_usage = eval_meta.get("usage", {})
            for k in guardrail_usage:
                guardrail_usage[k] += eval_usage.get(k, 0)
                
            steps_trace.append({
                "step": "Lớp 3.2 - Thẩm định & So sánh ngữ nghĩa chéo (AgentEvaluator)",
                "status": "passed",
                "reason": eval_meta.get("reason", "Đã chọn 2 tài liệu phù hợp nhất"),
                "usage": eval_usage
            })

            # Định dạng phản hồi kết hợp kế hoạch nghiên cứu, kết quả từ ResearcherAgent và tài liệu trích dẫn từ kho sách
            queries_str = "\n".join(f"- `{q}`" for q in critic_plan.get("search_queries", []))
            objectives_str = "\n".join(f"- {obj}" for obj in critic_plan.get("key_objectives", []))
            
            ref_books_str = ""
            if selected_bm25_docs:
                ref_books_str = "\n\n---\n### Tri thức Gối đầu giường từ Sách (BM25 & Cross-semantic Evaluation):\n"
                for b_doc in selected_bm25_docs:
                    ref_books_str += f"- **{b_doc.get('book')}**: {b_doc.get('topic')}\n  *{b_doc.get('content')}*\n"

            formatted_answer = (
                f"### Kế hoạch Nghiên cứu (Critic Agent)\n"
                f"**Từ khóa tìm kiếm thông minh:**\n{queries_str}\n\n"
                f"**Mục tiêu nghiên cứu:**\n{objectives_str}\n\n"
                f"**Hướng dẫn tác nhân (Research Agent):**\n{critic_plan.get('instructions', '')}\n\n"
                f"---\n"
                f"### Kết quả Nghiên Cứu (Researcher Agent):\n{research_result}"
                f"{ref_books_str}"
            )


            
            # Tổng hợp số lượng token tiêu thụ lũy tiến từ tất cả các bước
            total_usage = guardrail_usage
            
            # Ghi log cục bộ khi thành công
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=True,
                steps=steps_trace,
                ai_response=formatted_answer,
                request_meta=request_meta,
                usage=total_usage
            )
            
            return formatted_answer



        # Fallback nếu không khớp nhánh nào
        return "Không thể xác định luồng định tuyến cho câu hỏi."

    @classmethod
    def chat_with_ai_stream(cls, message: str, request_meta: dict = None):
        """
        Streaming Server-Sent Events (SSE) theo thời gian thực cho từng bước thực thi (Real-time Step Streaming):
        Mỗi khi hệ thống hoàn thành một bước (từ Lớp 1.1 đến Lớp 3.2), trả về ngay dữ liệu JSON cho Frontend hiển thị.
        """
        import json
        
        # 1. Kiểm duyệt bảo mật (Input Guardrail)
        is_safe, reason, steps_trace, guardrail_usage = InputGuardrail.is_safe(message)
        
        # Stream tất cả các bước kiểm duyệt con từ Lớp 1.1 đến 1.3 cho Frontend
        for st in steps_trace:
            yield json.dumps({"type": "step", "step": st["step"], "status": st["status"], "reason": st.get("reason", "Thành công")})
        
        if not is_safe:
            msg = reason or "Nội dung tin nhắn chứa từ khóa không an toàn hoặc bị cấm."
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=False,
                steps=steps_trace,
                ai_response=msg,
                request_meta=request_meta,
                usage=guardrail_usage
            )
            yield json.dumps({"type": "final_result", "message": msg, "steps": steps_trace})
            return

        # 1.4. Mã hóa Vector nhúng
        yield json.dumps({"type": "step", "step": "Lớp 1.4 - Tạo Vector nhúng (Embedding)", "status": "running", "reason": "Đang tạo Vector nhúng 1536 chiều và lưu trữ CSDL SQLite..."})
        query_embedding, embed_tokens = VectorEmbedder.get_embedding(message)
        EmbeddingDatabase.save_embedding(message, query_embedding)
        
        embedding_usage = {"prompt_tokens": embed_tokens, "completion_tokens": 0, "total_tokens": embed_tokens}
        steps_trace.append({"step": "Lớp 1.4 - Tạo Vector nhúng (Embedding)", "status": "passed", "usage": embedding_usage})
        for k in guardrail_usage:
            guardrail_usage[k] += embedding_usage.get(k, 0)
            
        yield json.dumps({"type": "step", "step": "Lớp 1.4 - Tạo Vector nhúng (Embedding)", "status": "passed", "reason": "Đã tạo Vector nhúng 1536 chiều và lưu SQLite embeddings.db"})

        # 1.5. Cosine Similarity Semantic Cache
        yield json.dumps({"type": "step", "step": "Lớp 1.5 - Tìm kiếm tương đồng ngữ nghĩa (Cosine Similarity)", "status": "running", "reason": "Đang tính Cosine Similarity so khớp với blog_posts.json..."})
        from agent.rag import SimilaritySearch
        best_match, blog_score = SimilaritySearch.find_most_similar_blog(query_embedding)
        best_knowledge, knowledge_score = SimilaritySearch.find_most_similar_knowledge(query_embedding)
        
        if knowledge_score >= blog_score:
            best_title = best_knowledge['topic'] if best_knowledge else "Không có"
            similarity_score = knowledge_score
            is_from_knowledge = True
        else:
            best_title = best_match['title'] if (best_match and 'title' in best_match) else "Không có"
            similarity_score = blog_score
            is_from_knowledge = False
            
        step_1_5_reason = f"Khớp nhất: '{best_title}' (Score: {similarity_score:.4f})" if best_match else "Không có dữ liệu tri thức để so sánh"
        steps_trace.append({
            "step": "Lớp 1.5 - Tìm kiếm tương đồng ngữ nghĩa (Cosine Similarity)",
            "status": "passed",
            "reason": step_1_5_reason,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        })
        
        if best_match and similarity_score >= 0.92:
            if is_from_knowledge:
                answer = f"### {best_match['book']} - {best_match['topic']}\n{best_match['content']}\n\n**Thẻ từ khóa:** {', '.join(best_match.get('tags', []))}"
            else:
                answer = f"### {best_match['title']}\n{best_match['content']}\n\n**Nguồn tham khảo:**\n" + "\n".join(f"- {ref}" for ref in best_match.get("references", []))
                
            steps_trace.append({"step": "Lớp 2 - Trả dữ liệu trực tiếp từ Semantic Cache", "status": "passed", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=True,
                steps=steps_trace,
                ai_response=answer,
                request_meta=request_meta,
                usage=guardrail_usage
            )
            yield json.dumps({"type": "step", "step": "Lớp 1.5 - Tìm kiếm tương đồng ngữ nghĩa (Cosine Similarity)", "status": "passed", "reason": f"🚀 Cache Hit ({similarity_score*100:.1f}%) -> Trả kết quả cực nhanh < 5ms"})
            yield json.dumps({"type": "final_result", "message": answer, "steps": steps_trace})
            return
            
        yield json.dumps({"type": "step", "step": "Lớp 1.5 - Tìm kiếm tương đồng ngữ nghĩa (Cosine Similarity)", "status": "passed", "reason": step_1_5_reason})

        # 1.6. Dynamic Agent Router
        yield json.dumps({"type": "step", "step": "Lớp 1.6 - Định tuyến tác nhân (Dynamic Router)", "status": "running", "reason": "Đang phân loại nguồn tri thức cần tìm kiếm..."})
        from agent.multi import MultiAgentRouter
        route, route_reason, router_usage = MultiAgentRouter.route_query(message)
        
        for k in guardrail_usage:
            guardrail_usage[k] += router_usage.get(k, 0)
            
        router_step_name = f"Lớp 1.6 - Định tuyến tác nhân ({route})"
        steps_trace.append({"step": router_step_name, "status": "passed", "reason": route_reason, "usage": router_usage})
        yield json.dumps({"type": "step", "step": router_step_name, "status": "passed", "reason": route_reason})

        # if route == "LOCAL_KNOWLEDGE" and best_knowledge:
        #     answer = f"### {best_knowledge['book']} - {best_knowledge['topic']}\n{best_knowledge['content']}\n\n**Thẻ từ khóa:** {', '.join(best_knowledge.get('tags', []))}"
        #     steps_trace.append({"step": "Lớp 2 - Trả dữ liệu từ Tri thức nội bộ (Local Knowledge)", "status": "passed", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
        #     LocalTraceLogger.log_trace(
        #         message=message,
        #         is_safe=True,
        #         steps=steps_trace,
        #         ai_response=answer,
        #         request_meta=request_meta,
        #         usage=guardrail_usage
        #     )
        #     yield json.dumps({"type": "final_result", "message": answer, "steps": steps_trace})
        #     return

        # Nhánh WEB_SEARCH
        # 2.1. CriticAgent
        yield json.dumps({"type": "step", "step": "Lớp 2.1 - Lập kế hoạch nghiên cứu (Critic Agent)", "status": "running", "reason": "Đang phân tích chủ đề và sinh mảng từ khóa tìm kiếm..."})
        from agent.multi import CriticAgent
        critic_plan, critic_usage = CriticAgent.generate_research_plan(message)
        
        for k in guardrail_usage:
            guardrail_usage[k] += critic_usage.get(k, 0)
            
        plan_reason_str = f"Từ khóa: {', '.join(critic_plan.get('search_queries', []))}"
        steps_trace.append({"step": "Lớp 2.1 - Lập kế hoạch nghiên cứu (Critic Agent)", "status": "passed", "reason": plan_reason_str, "usage": critic_usage, "plan": critic_plan})
        yield json.dumps({"type": "step", "step": "Lớp 2.1 - Lập kế hoạch nghiên cứu (Critic Agent)", "status": "passed", "reason": plan_reason_str})

        # 2.1b. Centralized Plan Guardrail
        yield json.dumps({"type": "step", "step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)", "status": "running", "reason": "Đang kiểm duyệt tập trung chuỗi từ khóa và chỉ dẫn..."})
        combined_plan_text = CriticAgent.get_combined_plan_text(critic_plan)
        plan_safe, plan_reason, plan_trace, plan_guard_usage = InputGuardrail.verify_combined_plan(combined_plan_text)
        
        for k in guardrail_usage:
            guardrail_usage[k] += plan_guard_usage.get(k, 0)
            
        if not plan_safe:
            reason_msg = f"Kế hoạch tìm kiếm bị chặn do không an toàn: {plan_reason}"
            steps_trace.append({"step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)", "status": "failed", "reason": reason_msg, "usage": plan_guard_usage})
            LocalTraceLogger.log_trace(
                message=message,
                is_safe=False,
                steps=steps_trace,
                ai_response=reason_msg,
                request_meta=request_meta,
                usage=guardrail_usage
            )
            yield json.dumps({"type": "step", "step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)", "status": "failed", "reason": reason_msg})
            yield json.dumps({"type": "final_result", "message": reason_msg, "steps": steps_trace})
            return
            
        steps_trace.append({"step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)", "status": "passed", "reason": "Kế hoạch tìm kiếm và chỉ dẫn hoàn toàn an toàn", "usage": plan_guard_usage})
        yield json.dumps({"type": "step", "step": "Lớp 2.1b - Kiểm duyệt tập trung kế hoạch (Centralized Plan Guardrail)", "status": "passed", "reason": "Kế hoạch tìm kiếm và chỉ dẫn hoàn toàn an toàn"})

        # 2.2. DuckDuckGo Search & Scrape Page
        yield json.dumps({"type": "step", "step": "Lớp 2.2 - Thực thi nghiên cứu & cào dữ liệu (ResearcherAgent)", "status": "running", "reason": "Đang cào bài viết từ DuckDuckGo, làm sạch HTML và lập chỉ mục cục bộ..."})
        from agent.multi import ResearcherAgent
        research_result, researcher_usage = ResearcherAgent.execute_research(message, critic_plan)
        
        for k in guardrail_usage:
            guardrail_usage[k] += researcher_usage.get(k, 0)
            
        steps_trace.append({"step": "Lớp 2.2 - Thực thi nghiên cứu & cào dữ liệu (ResearcherAgent)", "status": "passed", "usage": researcher_usage})
        yield json.dumps({"type": "step", "step": "Lớp 2.2 - Thực thi nghiên cứu & cào dữ liệu (ResearcherAgent)", "status": "passed", "reason": "Đã cào nội dung thành công và lập chỉ mục cục bộ"})

        # 3.1. BM25Search
        yield json.dumps({"type": "step", "step": "Lớp 3.1 - Tìm kiếm từ khóa thô (BM25Search)", "status": "running", "reason": "Đang thực hiện BM25Search trên kho sách local_knowledge.json..."})
        from agent.rag import BM25Search
        from agent.evaluation import AgentEvaluator
        
        raw_bm25_docs = BM25Search.search_local_books(message, top_k=4)
        simplified_docs = BM25Search.get_simplified_docs(raw_bm25_docs)
        
        bm25_reason_str = f"Đã trích xuất {len(raw_bm25_docs)} tài liệu ứng viên từ kho sách nội bộ"
        steps_trace.append({
            "step": "Lớp 3.1 - Tìm kiếm từ khóa thô (BM25Search)",
            "status": "passed",
            "reason": bm25_reason_str,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        })
        yield json.dumps({"type": "step", "step": "Lớp 3.1 - Tìm kiếm từ khóa thô (BM25Search)", "status": "passed", "reason": bm25_reason_str})

        # 3.2. AgentEvaluator Cross-semantic Evaluation
        yield json.dumps({"type": "step", "step": "Lớp 3.2 - Thẩm định & So sánh ngữ nghĩa chéo (AgentEvaluator)", "status": "running", "reason": "Đang yêu cầu LLM so sánh ngữ nghĩa chéo để lọc ra 2 tài liệu phù hợp nhất..."})
        selected_bm25_docs, eval_meta = AgentEvaluator.select_best_two_documents(
            query=message,
            original_docs=raw_bm25_docs,
            simplified_docs=simplified_docs
        )
        
        eval_usage = eval_meta.get("usage", {})
        for k in guardrail_usage:
            guardrail_usage[k] += eval_usage.get(k, 0)
            
        eval_reason_str = eval_meta.get("reason", "Đã chọn 2 tài liệu phù hợp nhất")
        steps_trace.append({
            "step": "Lớp 3.2 - Thẩm định & So sánh ngữ nghĩa chéo (AgentEvaluator)",
            "status": "passed",
            "reason": eval_reason_str,
            "usage": eval_usage
        })
        yield json.dumps({"type": "step", "step": "Lớp 3.2 - Thẩm định & So sánh ngữ nghĩa chéo (AgentEvaluator)", "status": "passed", "reason": eval_reason_str})

        # 3.3. Final Blog Integration
        queries_str = "\n".join(f"- `{q}`" for q in critic_plan.get("search_queries", []))
        objectives_str = "\n".join(f"- {obj}" for obj in critic_plan.get("key_objectives", []))
        
        ref_books_str = ""
        if selected_bm25_docs:
            ref_books_str = "\n\n---\n### Tri thức Gối đầu giường từ Sách (BM25 & Cross-semantic Evaluation):\n"
            for b_doc in selected_bm25_docs:
                ref_books_str += f"- **{b_doc.get('book')}**: {b_doc.get('topic')}\n  *{b_doc.get('content')}*\n"

        formatted_answer = (
            f"### Kế hoạch Nghiên cứu (Critic Agent)\n"
            f"**Từ khóa tìm kiếm thông minh:**\n{queries_str}\n\n"
            f"**Mục tiêu nghiên cứu:**\n{objectives_str}\n\n"
            f"**Hướng dẫn tác nhân (Research Agent):**\n{critic_plan.get('instructions', '')}\n\n"
            f"---\n"
            f"### Kết quả Nghiên Cứu (Researcher Agent):\n{research_result}"
            f"{ref_books_str}"
        )
        
        LocalTraceLogger.log_trace(
            message=message,
            is_safe=True,
            steps=steps_trace,
            ai_response=formatted_answer,
            request_meta=request_meta,
            usage=guardrail_usage
        )
        
        yield json.dumps({"type": "final_result", "message": formatted_answer, "steps": steps_trace})

    @staticmethod
    def _synthesize_local_answer(user_query: str, knowledge_context: str) -> tuple[str, dict]:
        """
        Dùng LLM tổng hợp phản hồi cá nhân hóa trực tiếp trả lời câu hỏi người dùng
        dựa trên tri thức gối đầu giường làm bối cảnh.
        """
        from openai import OpenAI
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        if not api_key:
            return knowledge_context, empty_usage

        try:
            client = OpenAI(api_key=api_key)
            prompt = (
                f"Câu hỏi của người dùng: '{user_query}'\n\n"
                f"Tri thức gối đầu giường làm căn cứ:\n{knowledge_context}\n\n"
                f"Hãy đóng vai chuyên gia tư vấn phát triển bản thân và phản tư cuộc sống. "
                f"Hãy trả lời trực tiếp, sâu sắc và truyền cảm hứng cho câu hỏi của người dùng trên, "
                f"kết hợp khéo léo tri thức gối đầu giường ở trên thành lời khuyên thực tế. "
                f"Trình bày dạng Markdown đẹp mắt, có cấu trúc các bước rõ ràng."
            )
            response = client.chat.completions.create(
                model=TraceConfig.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "Bạn là Trợ lý AI tư vấn phát triển bản thân và phản tư cuộc sống sâu sắc."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            return content, usage
        except Exception as e:
            print(f"Lỗi khi tổng hợp tri thức nội bộ: {str(e)}")
            return knowledge_context, empty_usage




