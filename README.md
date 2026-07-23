# Blog_Agent

Hệ thống AI Multi-Agent tích hợp RAG, Guardrail kiểm duyệt bảo mật 3 lớp, Cào dữ liệu Web theo thời gian thực (DuckDuckGo Search & BeautifulSoup4), Lập chỉ mục cục bộ, Thuật toán BM25 và Thẩm định ngữ nghĩa chéo (Cross-semantic AgentEvaluator).

## Cấu trúc Dự án
- `back-end/`: Máy chủ FastAPI (Python) cung cấp API điều hướng Multi-Agent Router, RAG Vector Search & Agent Evaluator.
- `front-end/`: Giao diện người dùng Next.js (React / CSS Modules) theo phong cách Glassmorphism hiện đại.
- `data/`: Lưu trữ bài viết chỉ mục (`blog_posts.json`), kho tri thức sách (`local_knowledge.json`) và nhật ký hệ thống (`trace_logs.json`).

## Hướng dẫn Khởi chạy
```bash
./start.sh
```
