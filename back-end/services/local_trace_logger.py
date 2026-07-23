import os
import json
from datetime import datetime
from config.trace_config import TraceConfig

DATA_FILE_PATH = TraceConfig.LOCAL_LOG_PATH


class LocalTraceLogger:
    @staticmethod
    def log_trace(message: str, is_safe: bool, steps: list = None, ai_response: str = None, request_meta: dict = None, usage: dict = None):
        # Đảm bảo thư mục chứa file tồn tại
        os.makedirs(os.path.dirname(DATA_FILE_PATH), exist_ok=True)
        
        # Tự động tìm failed_step
        failed_step = "Hoàn thành kiểm tra"
        if steps:
            for s in steps:
                if s.get("status") == "failed":
                    failed_step = s.get("step")
                    break

        # Định dạng một bản ghi trace log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_metadata": request_meta or {},
            "input": message,
            "guardrail": {
                "is_safe": is_safe,
                "failed_step": failed_step,
                "steps": steps or []
            },
            "ai_response": ai_response,
            "usage": usage or {}
        }
        
        # Đọc danh sách log hiện tại từ file JSON
        logs = []
        if os.path.exists(DATA_FILE_PATH):
            try:
                with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
            except Exception:
                logs = []
                
        # Thêm trace log mới
        logs.append(log_entry)
        
        # Ghi ngược lại file JSON
        try:
            with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Lỗi khi ghi trace log cục bộ: {str(e)}")
