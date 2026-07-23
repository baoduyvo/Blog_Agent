import re
from typing import Dict, Any

class StaticChecks:
    @staticmethod
    def clean_text(text: str) -> str:
        """Làm sạch văn bản đầu vào (loại bỏ khoảng trắng thừa)"""
        if not text:
            return ""
        return " ".join(text.strip().split())

    @staticmethod
    def validate_length(text: str, max_length: int = 1000) -> bool:
        """Kiểm tra độ dài văn bản không vượt quá giới hạn"""
        if not text:
            return False
        return len(text) <= max_length

    @staticmethod
    def contains_email(text: str) -> bool:
        """Kiểm tra xem văn bản có chứa địa chỉ Email không"""
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return bool(re.search(email_pattern, text))

    @staticmethod
    def contains_phone(text: str) -> bool:
        """Kiểm tra xem văn bản có chứa số điện thoại không (định dạng Việt Nam)"""
        phone_pattern = r"(0[3|5|7|8|9])+([0-9]{8})\b"
        return bool(re.search(phone_pattern, text))

    @classmethod
    def validate_all(cls, text: str) -> Dict[str, Any]:
        """Thực hiện toàn bộ các bước kiểm tra hợp lệ tĩnh"""
        cleaned = cls.clean_text(text)
        
        is_length_valid = cls.validate_length(cleaned)
        has_email = cls.contains_email(cleaned)
        has_phone = cls.contains_phone(cleaned)
        
        is_valid = is_length_valid and not (has_email or has_phone)
        
        errors = []
        if not is_length_valid:
            errors.append("Tin nhắn quá dài (giới hạn 1000 ký tự).")
        if has_email:
            errors.append("Không được phép gửi địa chỉ Email vì lý do bảo mật.")
        if has_phone:
            errors.append("Không được phép gửi số điện thoại vì lý do bảo mật.")
            
        return {
            "is_valid": is_valid,
            "cleaned_text": cleaned,
            "errors": errors
        }

# Alias for backwards compatibility if needed
InputValidator = StaticChecks
