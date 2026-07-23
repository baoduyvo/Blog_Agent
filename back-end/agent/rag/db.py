import sqlite3
import json
import os
from config.trace_config import TraceConfig

class EmbeddingDatabase:
    DB_PATH = os.path.join(TraceConfig.ROOT_DIR, "data", "embeddings.db")

    @classmethod
    def get_connection(cls):
        # Đảm bảo thư mục data tồn tại
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)
        return sqlite3.connect(cls.DB_PATH)

    @classmethod
    def init_db(cls):
        """Khởi tạo cấu trúc bảng SQLite nếu chưa tồn tại"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT UNIQUE,
                embedding TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def save_embedding(cls, prompt: str, embedding: list[float]):
        """Lưu trữ vector nhúng của câu hỏi vào SQLite"""
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO query_embeddings (prompt, embedding) VALUES (?, ?)",
                (prompt, json.dumps(embedding))
            )
            conn.commit()
        except Exception as e:
            print(f"Lỗi khi lưu embedding vào SQLite: {str(e)}")
        finally:
            conn.close()

    @classmethod
    def get_embedding(cls, prompt: str) -> list[float]:
        """Truy vấn lấy vector nhúng từ SQLite cho một câu hỏi"""
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT embedding FROM query_embeddings WHERE prompt = ?", (prompt,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None

    @classmethod
    def get_all_embeddings(cls) -> list[tuple[str, list[float]]]:
        """Lấy tất cả các câu hỏi và vector nhúng đã lưu trong SQLite"""
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT prompt, embedding FROM query_embeddings")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            try:
                result.append((row[0], json.loads(row[1])))
            except Exception:
                continue
        return result
