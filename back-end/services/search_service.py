from typing import List

class SearchService:
    @staticmethod
    def get_welcome_message(name: str = "Khách") -> str:
        return f"Chào mừng {name} đến với hệ thống API!"

    @staticmethod
    def search_courses(query: str = "", limit: int = 10) -> List[dict]:
        mock_data = [
            {"id": 1, "title": "Học lập trình Python cơ bản", "category": "Python"},
            {"id": 2, "title": "Xây dựng web app với FastAPI", "category": "FastAPI"},
            {"id": 3, "title": "Next.js và kiến trúc Frontend hiện đại", "category": "NextJS"},
            {"id": 4, "title": "Cách thiết kế RESTful API hiệu quả", "category": "API"},
        ]
        
        if not query:
            return mock_data[:limit]
            
        return [
            item for item in mock_data
            if query.lower() in item["title"].lower() or query.lower() in item["category"].lower()
        ][:limit]
