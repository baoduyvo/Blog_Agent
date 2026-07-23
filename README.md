# 🚀 Blog_Agent - Hệ Thống AI Multi-Agent & Hybrid RAG

Hệ thống AI Multi-Agent thông minh tích hợp **RAG Hybrid (Vector Embedding + BM25Okapi)**, **Kiểm duyệt Bảo mật Guardrail 3 Lớp**, **Cào Dữ liệu Web Thời gian thực (DuckDuckGo Search & BeautifulSoup4)**, **Lập chỉ mục Cục bộ**, và **Thẩm định Ngữ nghĩa Chéo (Cross-semantic AgentEvaluator)**.

---

## 📐 Sơ Đồ Kiến Trúc & Quy Trình Hoạt Động (Architecture Flowchart)

![Blog Agent Architecture Flowchart](docs/architecture.png)

<details>
<summary><b>🔍 Xem mã nguồn sơ đồ Mermaid (Mermaid Source Code)</b></summary>

```mermaid
graph TD
    User([👤 Người dùng nhập tin nhắn]) --> CS[ChatService: Tiếp nhận tin nhắn]
    
    %% LỚP 1: GUARDRAIL BẢO MẬT & KIỂM DUYỆT
    subgraph Guardrail ["🛡️ LỚP 1: KIỂM DUYỆT BẢO MẬT (Input Guardrails)"]
        CS --> L1_1["Lớp 1.1: Static Checks <br/> (Null / Regex Ký tự / Từ khóa cấm)"]
        L1_1 -- Bị chặn --> Reject1[Từ chối ngay lập tức & Ghi log]
        
        L1_1 -- Hợp lệ --> L1_2["Lớp 1.2: LLM Moderation <br/> (gpt-4o-mini - Lọc bậy bạ / Injection)"]
        L1_2 -- Flagged --> Reject2[Từ chối & Ghi log]
        
        L1_2 -- An toàn --> L1_3["Lớp 1.3: LLM Topic Classification <br/> (gpt-4o-mini - Kiểm tra chủ đề)"]
        L1_3 -- Unsafe / Irrelevant --> Reject3[Trả lý do từ chối & Ghi log]
    end

    %% LỚP 1.4 & 1.5: RAG & SEMANTIC CACHE
    subgraph RAG_Cache ["⚡ LỚP 1.4 & 1.5: EMBEDDING & SEMANTIC CACHE"]
        L1_3 -- Safe --> L1_4["Lớp 1.4: Vector Embedding <br/> (text-embedding-3-small -> Vector 1536 chiều)"]
        L1_4 --> SaveDB[("💾 SQLite: embeddings.db <br/> (Lưu Vector nhúng)")]
        
        L1_4 --> L1_5["Lớp 1.5: Cosine Similarity Search <br/> (So khớp với blog_posts.json & local_knowledge.json)"]
        
        L1_5 -- "Cache Hit (≥ 92%)" --> HitReturn["🚀 Trả trực tiếp bài Blog / Tri thức cũ <br/> (Thời gian < 5ms - Tiết kiệm 100% Token)"]
    end

    %% LỚP 1.6 & MULTI-AGENT WEB SEARCH
    subgraph MultiAgent ["🧠 LỚP 1.6 & 2: MULTI-AGENT WEB SEARCH"]
        L1_5 -- "Cache Miss (< 92%)" --> L1_6["Lớp 1.6: Dynamic Agent Router <br/> (Mô hình phân loại nguồn tri thức)"]
        
        L1_6 -- "Route: LOCAL_KNOWLEDGE" --> LK["Tải Tri thức Kinh điển nội bộ <br/> (Nhà giả kim, Đắc nhân tâm, Khắc kỷ)"]
        
        L1_6 -- "Route: WEB_SEARCH" --> Critic["Lớp 2.1: CriticAgent <br/> (Lập kế hoạch JSON: search_queries, key_objectives, instructions)"]
        
        Critic --> CombineStr["Gộp search_queries (Max 2) <br/> + instructions thành 1 chuỗi duy nhất"]
        
        CombineStr --> PlanGuard["Lớp 2.1b: Centralized Plan Guardrail <br/> (InputGuardrail.verify_combined_plan)"]
        
        PlanGuard -- Bị chặn --> RejectPlan[Dừng xử lý & Ghi log lỗi an toàn]
        
        PlanGuard -- Thông qua --> DDG["Lớp 2.2: DuckDuckGo HTML Search <br/> (Giải mã link chuyển hướng uddg)"]
        
        DDG --> Deduplicate{"So khớp URL với blog_posts.json <br/> (Check trường link / url)"}
        
        Deduplicate -- Đã tồn tại --> SkipURL[Bỏ qua URL trùng lặp]
        
        Deduplicate -- URL Mới --> Scrape["Lớp 2.2b: Page Scraper (BeautifulSoup4) <br/> (Ưu tiên entry-content, post-content, article, main, body. Dọn Regex & Snippet Fallback < 200 chars)"]
        
        Scrape --> Indexing{"Văn bản cào đạt chất lượng <br/> (≥ 200 ký tự)?"}
        
        Indexing -- Có --> SaveLocal["💾 Lập chỉ mục cục bộ (Local Indexing) <br/> 1. Đóng gói bài viết mới -> blog_posts.json <br/> 2. Mã hóa Vector 1536 chiều -> SQLite embeddings.db"]
        
        SaveLocal --> Researcher["Lớp 2.2: ResearcherAgent <br/> (Tổng hợp bài viết nghiên cứu từ Web)"]
        Indexing -- Không --> Researcher
    end

    %% LỚP 3: RAG HYBRID & AGENT EVALUATION (BƯỚC VỪA THÊM)
    subgraph RAG_Evaluation ["📚 LỚP 3: BM25 SEARCH & CROSS-SEMANTIC EVALUATION"]
        Researcher --> L3_1["Lớp 3.1: Tìm kiếm từ khóa thô (BM25Search) <br/> (Tìm trong local_knowledge.json -> Trích 4 tài liệu ứng viên original_docs)"]
        
        L3_1 --> L3_1b["Context Compression (Nén dữ liệu) <br/> (Tạo simplified_docs: index, title, snippet 150 ký tự)"]
        
        L3_1b --> L3_2["Lớp 3.2: AgentEvaluator <br/> (LLM So sánh ngữ nghĩa chéo giữa 4 tài liệu với chủ đề)"]
        
        L3_2 --> ParseJSON{"Parse kết quả JSON <br/> & Kiểm tra lỗi?"}
        
        ParseJSON -- Thành công --> Extract2["Trích xuất ĐÚNG 2 tài liệu gốc đầy đủ <br/> từ mảng 4 tài liệu ban đầu"]
        ParseJSON -- "Lỗi Parse / Lỗi Kết nối" --> Fallback["🛡️ Cơ chế Fallback <br/> (Mặc định lấy 2 tài liệu BM25 thô đầu tiên)"]
        
        Extract2 --> FinalWriter["Lớp 3.3: Tổng hợp Blog Cuối cùng (WriterAgent) <br/> (Hợp nhất Web Research + 2 Tài liệu Sách trích dẫn)"]
        Fallback --> FinalWriter
    end

    %% LOGGING & TELEMETRY
    subgraph Observability ["📊 THEO DÕI & GIÁM SÁT (Observability)"]
        HitReturn --> Log[LocalTraceLogger: Ghi log chi tiết vào trace_logs.json]
        LK --> Log
        FinalWriter --> Log
        Reject1 --> Log
        Reject2 --> Log
        Reject3 --> Log
        RejectPlan --> Log
        
        Log --> LF[("🌐 Langfuse Dashboard <br/> (Giám sát Real-time & Token Usage)")]
        Log --> UI[("🖥️ Admin UI: AdminLogs.tsx <br/> (Hiển thị Vết từng bước Step Tracing)")]
    end
```
</details>

---

## 📁 Cấu trúc Thư mục Dự án

```
Blog_Agent/
├── back-end/               # Server FastAPI Backend
│   ├── agent/              # Hệ thống Agent & RAG Core
│   │   ├── agents/         # SearchAgent đơn lẻ
│   │   ├── evaluation/     # AgentEvaluator (So sánh ngữ nghĩa chéo)
│   │   ├── guardrail/      # Security Guardrails (Lớp 1.1, 1.2, 1.3, 2.1b)
│   │   ├── multi/          # Multi-Agent Systems (Router, CriticAgent, ResearcherAgent)
│   │   ├── rag/            # Vector Embeddings, SQLite DB, Cosine Similarity, BM25Search
│   │   └── system_prompt/  # Tập hợp Centralized System Prompts
│   ├── config/             # Cấu hình môi trường & Langfuse Telemetry
│   ├── controllers/        # FastAPI API Endpoints (Chat, Admin Logs)
│   ├── dtos/               # Pydantic Schemas & DTOs
│   ├── services/           # Business Logic Services & Local Trace Logger
│   └── main.py             # File khởi chạy FastAPI App
├── front-end/              # Client Dashboard UI (Next.js / React)
│   └── src/components/     # BlogAssistant, AdminLogs, Timeline, ReflectionEditor
├── data/                   # Kho dữ liệu cục bộ (blog_posts.json, local_knowledge.json, trace_logs.json)
├── README.md               # Sơ đồ kiến trúc & Hướng dẫn sử dụng
└── start.sh                # Script khởi chạy đồng thời Backend & Frontend
```

---

## ⚡ Hướng dẫn Khởi chạy Dự án

```bash
# Cài đặt và khởi chạy toàn bộ hệ thống (FastAPI Backend + Next.js Frontend)
./start.sh
```
