import re
import json
from config.trace_config import TraceConfig
from agent.guardrail.llm_moderator import LLMModerator
from agent.guardrail.llm_classifier import LLMClassifier
from agent.guardrail.static_checks import StaticChecks

class InputGuardrail:
    @staticmethod
    def is_empty_or_null(prompt: str) -> bool:
        # Kiểm tra nếu prompt là None, rỗng hoặc chỉ chứa khoảng trắng
        if prompt is None:
            return True
        return len(prompt.strip()) == 0

    @staticmethod
    def has_special_characters(prompt: str) -> bool:
        # Phát hiện ký tự đặc biệt nguy hiểm (ví dụ: < > ; | $ \ { } [ ])
        pattern = r"[<>;|$\\{}[\]]"
        if re.search(pattern, prompt):
            return True
        return False

    @classmethod
    def is_safe(cls, prompt: str) -> tuple[bool, str, list, dict]:
        """
        Kiểm tra tính an toàn và hợp lệ của câu hỏi/chủ đề từ người dùng.
        Trả về:
            - bool: True nếu an toàn và đúng chủ đề, ngược lại False.
            - str: Lý do bị từ chối/chặn chi tiết.
            - list: Danh sách trace chi tiết từng bước kiểm tra.
            - dict: Bản đồ tổng hợp số lượng token tiêu thụ lũy tiến.
        """
        # Khởi tạo bộ tích lũy số lượng token tiêu thụ và danh sách trace bước
        accumulated_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        steps_trace = []

        # 1. Kiểm tra null hoặc rỗng
        step_1 = "Lớp 1.1 - Kiểm tra null hoặc rỗng"
        if cls.is_empty_or_null(prompt):
            reason = "Nội dung tin nhắn trống hoặc chỉ chứa khoảng trắng."
            steps_trace.append({"step": step_1, "status": "failed", "reason": reason})
            return False, reason, steps_trace, accumulated_usage
        steps_trace.append({"step": step_1, "status": "passed"})
            
        # 2. Kiểm tra ký tự đặc biệt nguy hiểm
        step_2 = "Lớp 1.1 - Kiểm tra ký tự đặc biệt nguy hiểm"
        if cls.has_special_characters(prompt):
            reason = "Nội dung tin nhắn chứa ký tự đặc biệt nguy hiểm hoặc không được phép."
            steps_trace.append({"step": step_2, "status": "failed", "reason": reason})
            return False, reason, steps_trace, accumulated_usage
        steps_trace.append({"step": step_2, "status": "passed"})

        # 3. Đọc và so khớp từ khóa nhạy cảm từ file JSON dùng chung
        step_3 = "Lớp 1.1 - So khớp từ khóa nhạy cảm"
        with open(TraceConfig.FORBIDDEN_KEYWORDS_PATH, "r", encoding="utf-8") as f:
            forbidden_keywords = json.load(f)
        
        keyword_match = None
        for word in forbidden_keywords:
            if word in prompt.lower():
                keyword_match = word
                break
                
        if keyword_match:
            reason = f"Nội dung tin nhắn chứa từ khóa bị cấm: '{keyword_match}'."
            steps_trace.append({"step": step_3, "status": "failed", "reason": reason})
            return False, reason, steps_trace, accumulated_usage
        steps_trace.append({"step": step_3, "status": "passed"})
                
        # 4. Gọi LLM để lọc các câu hỏi bậy bạ/nhạy cảm không nằm trong từ điển từ khóa (Lớp 1.2)
        step_4 = "Lớp 1.2 - Kiểm duyệt bằng LLM"
        flagged, mod_usage = LLMModerator.is_flagged(prompt)
        
        # Tích lũy token
        for k in accumulated_usage:
            accumulated_usage[k] += mod_usage.get(k, 0)

        if flagged:
            reason = "Nội dung tin nhắn bị hệ thống kiểm duyệt tự động gắn cờ là không an toàn."
            steps_trace.append({"step": step_4, "status": "failed", "reason": reason, "usage": mod_usage})
            return False, reason, steps_trace, accumulated_usage
        steps_trace.append({"step": step_4, "status": "passed", "usage": mod_usage})
            
        # 5. Phân loại chủ đề nâng cao bằng mô hình ngôn ngữ lớn (Lớp 1.3 - LLM Classification Check)
        step_5 = "Lớp 1.3 - Phân loại chủ đề bằng LLM"
        is_safe_and_relevant, reason, class_usage = LLMClassifier.classify_prompt(prompt)
        
        # Tích lũy token
        for k in accumulated_usage:
            accumulated_usage[k] += class_usage.get(k, 0)

        if not is_safe_and_relevant:
            steps_trace.append({"step": step_5, "status": "failed", "reason": reason, "usage": class_usage})
            return False, reason, steps_trace, accumulated_usage
        steps_trace.append({"step": step_5, "status": "passed", "usage": class_usage})
            
        return True, "Hợp lệ", steps_trace, accumulated_usage

    @classmethod
    def verify_combined_plan(cls, combined_text: str) -> tuple[bool, str, list, dict]:
        """
        Kiểm tra tập trung chuỗi gộp (gồm tất cả search_queries và instructions)
        sau khi CriticAgent lập kế hoạch.
        Trả về:
            - bool: True nếu chuỗi gộp an toàn và đúng quy chuẩn, ngược lại False.
            - str: Lý do bị từ chối/chặn chi tiết.
            - list: Danh sách các bước kiểm duyệt đã chạy qua.
            - dict: Dung lượng token tiêu thụ.
        """
        return cls.is_safe(combined_text)

