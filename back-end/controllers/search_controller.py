from fastapi import APIRouter, Request
from typing import Dict, Any
from services.search_service import SearchService
from services.chat_service import ChatService
from dtos.search import SearchResponse
from dtos.chat import ChatRequest, ChatResponse
from config.trace_config import TraceConfig

router = APIRouter()

# Sử dụng Langfuse client dùng chung
langfuse = TraceConfig.get_langfuse_client()


@router.get("/")
def read_root() -> Dict[str, Any]:
    return {
        "status": "success",
        "message": "Chào mừng bạn đến với ứng dụng FastAPI!"
    }

@router.get("/api/welcome")
def welcome(name: str = "Khách") -> Dict[str, Any]:
    message = SearchService.get_welcome_message(name)
    return {
        "status": "success",
        "message": message
    }

@router.get("/api/search", response_model=SearchResponse)
def search(query: str = "", limit: int = 10) -> Dict[str, Any]:
    results = SearchService.search_courses(query, limit)
    return {
        "status": "success",
        "query": query,
        "results": results
    }

@router.post("/api/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest) -> Dict[str, Any]:
    # 1. Thu thập metadata của request
    meta = {
        "http_method": request.method,
        "url": str(request.url),
        "client_host": request.client.host if request.client else "unknown",
    }
    
    # 2. Bắt đầu trace ghi nhận cuộc gọi API bằng context manager của Langfuse v4
    with langfuse.start_as_current_observation(
        as_type="span",
        name="API-Endpoint-Chat",
        input={"message": body.message},
        metadata={
            **meta,
            "headers": dict(request.headers)
        }
    ) as trace:
        
        # 3. Gọi tầng Service xử lý (Context trace được tự động truyền xuống các hàm con)
        response_message = ChatService.chat_with_ai(body.message, request_meta=meta)
        
        # 4. Cập nhật output cho trace
        trace.update(output={"response": response_message})
        
        return {
            "status": "success",
            "message": response_message
        }

# @router.post("/api/chat/stream")
# def chat_stream(request: Request, body: ChatRequest):
#     from fastapi.responses import StreamingResponse
#     meta = {
#         "http_method": request.method,
#         "url": str(request.url),
#         "client_host": request.client.host if request.client else "unknown",
#     }
#     
#     def event_generator():
#         for chunk in ChatService.chat_with_ai_stream(body.message, request_meta=meta):
#             yield f"data: {chunk}\n\n"
#             
#     return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/api/admin/logs")
def get_admin_logs() -> Dict[str, Any]:
    import os
    import json
    
    logs_path = TraceConfig.LOCAL_LOG_PATH
    if not os.path.exists(logs_path):
        return {"status": "success", "logs": []}
        
    try:
        with open(logs_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                logs = json.loads(content)
                # Đảo ngược để hiển thị log mới nhất lên đầu
                logs.reverse()
                return {"status": "success", "logs": logs}
    except Exception as e:
        return {"status": "error", "message": f"Không thể đọc log: {str(e)}", "logs": []}
        
    return {"status": "success", "logs": []}





