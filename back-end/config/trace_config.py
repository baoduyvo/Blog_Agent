import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()

class TraceConfig:
    # 1. Cấu hình thư mục và đường dẫn file log cục bộ
    BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ROOT_DIR = os.path.dirname(BACKEND_DIR)
    LOCAL_LOG_PATH = os.path.join(ROOT_DIR, "data", "trace_logs.json")
    FORBIDDEN_KEYWORDS_PATH = os.path.join(ROOT_DIR, "data", "forbidden_keywords.json")


    # 2. Cấu hình các thông số kết nối Langfuse
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

    # 3. Cấu hình OpenAI Agent
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEFAULT_MODEL = "gpt-4o-mini"

    # Instance Singleton cho Langfuse
    _langfuse_client = None

    @classmethod
    def get_langfuse_client(cls) -> Langfuse:
        """Trả về instance Langfuse dùng chung (Singleton)"""
        if cls._langfuse_client is None:
            cls._langfuse_client = Langfuse(
                public_key=cls.LANGFUSE_PUBLIC_KEY,
                secret_key=cls.LANGFUSE_SECRET_KEY,
                host=cls.LANGFUSE_HOST
            )
        return cls._langfuse_client
