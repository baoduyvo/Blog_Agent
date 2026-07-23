import os
import json
import re
import urllib.parse
import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from config.trace_config import TraceConfig
from agent.system_prompt.prompts import SYSTEM_PROMPT_RESEARCHER

class SearchProvider:
    @staticmethod
    def get_indexed_urls() -> set[str]:
        """
        Đọc tất cả các liên kết URL/Link đã từng được cào và lập chỉ mục trong blog_posts.json.
        """
        indexed_urls = set()
        blog_path = os.path.join(TraceConfig.ROOT_DIR, "data", "blog_posts.json")
        if os.path.exists(blog_path):
            try:
                with open(blog_path, "r", encoding="utf-8") as f:
                    blogs = json.load(f)
                    for b in blogs:
                        if b.get("link"):
                            indexed_urls.add(b["link"].strip().lower())
                        if b.get("url"):
                            indexed_urls.add(b["url"].strip().lower())
                        for ref in b.get("references", []):
                            if ref.startswith("http://") or ref.startswith("https://"):
                                indexed_urls.add(ref.strip().lower())
            except Exception as e:
                print(f"Lỗi đọc file blog_posts.json: {str(e)}")
        return indexed_urls

    @staticmethod
    def save_new_indexed_blog(title: str, url: str, content: str) -> None:
        """
        Lập chỉ mục cục bộ (Local Indexing):
        Nếu văn bản cào được đạt chất lượng (>= 200 ký tự), đóng gói dữ liệu thành cấu trúc bài viết,
        lưu thêm vào blog_posts.json và tự động tạo + lưu vector nhúng vào CSDL SQLite embeddings.db.
        """
        blog_path = os.path.join(TraceConfig.ROOT_DIR, "data", "blog_posts.json")
        blogs = []
        if os.path.exists(blog_path):
            try:
                with open(blog_path, "r", encoding="utf-8") as f:
                    blogs = json.load(f)
            except Exception:
                blogs = []
                
        # Kiểm tra trùng lặp URL
        for b in blogs:
            if b.get("link", "").strip().lower() == url.strip().lower() or b.get("url", "").strip().lower() == url.strip().lower():
                return
                
        new_id = f"BLOG-{len(blogs) + 1:03d}"
        new_blog = {
            "id": new_id,
            "title": title,
            "content": content[:1800],
            "category": "safe",
            "link": url,
            "references": [
                f"Nguồn bài viết: {title}",
                url
            ]
        }
        blogs.append(new_blog)
        
        try:
            with open(blog_path, "w", encoding="utf-8") as f:
                json.dump(blogs, f, ensure_ascii=False, indent=4)
            print(f"-> [LOCAL INDEXED] Đã đóng gói và lập chỉ mục bài viết mới vào blog_posts.json: '{title}' ({new_id})")
            
            # Tự động tạo Vector Embedding và lưu vào SQLite embeddings.db
            from agent.rag import VectorEmbedder, EmbeddingDatabase
            embedding, _ = VectorEmbedder.get_embedding(title)
            if embedding:
                EmbeddingDatabase.save_embedding(title, embedding)
                print(f"-> [EMBEDDING CACHED] Đã lưu vector nhúng bài viết mới vào SQLite embeddings.db: '{title}'")
        except Exception as e:
            print(f"Lỗi khi đóng gói bài viết mới vào blog_posts.json: {str(e)}")

    @staticmethod
    def scrape_page_content(url: str, fallback_snippet: str = "") -> str:
        """
        Cào nội dung thực tế từ trang web (Scrape Page):
        - Ưu tiên tìm kiếm nội dung văn bản chính trong các thẻ bài viết phổ biến:
          class="entry-content", class="post-content", <article>, <main> hoặc <body>.
        - Dọn dẹp khoảng trắng, dòng trống dư thừa bằng Regex.
        - Dự phòng (Snippet fallback): Nếu trang web chặn bot cào hoặc trả về văn bản trống/quá ngắn (< 200 ký tự),
          hệ thống lấy chuỗi mô tả (snippet) từ kết quả tìm kiếm làm nội dung thế chỗ.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Loại bỏ các thẻ rác, quảng cáo, menu điều hướng
                for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "iframe"]):
                    tag.decompose()
                    
                # Ưu tiên tìm thẻ container chứa nội dung chính theo thứ tự ưu tiên
                container = (
                    soup.find(class_="entry-content") or
                    soup.find(class_="post-content") or
                    soup.find("article") or
                    soup.find("main") or
                    soup.find("body")
                )
                
                if container:
                    paragraphs = [p.get_text(strip=True) for p in container.find_all("p") if len(p.get_text(strip=True)) > 25]
                    content_text = "\n".join(paragraphs)
                else:
                    content_text = soup.get_text(separator="\n", strip=True)
                    
                # Dọn dẹp khoảng trắng và ngắt dòng dư thừa bằng Regex
                cleaned_text = re.sub(r'[ \t]+', ' ', content_text)
                cleaned_text = re.sub(r'\n\s*\n+', '\n', cleaned_text).strip()
                
                # Nếu văn bản thu thập đủ độ dài (>= 200 ký tự)
                if len(cleaned_text) >= 200:
                    return cleaned_text[:1800]
        except Exception as e:
            print(f"Lỗi khi cào nội dung từ trang web {url}: {str(e)}")
            
        # Dự phòng (Snippet fallback): Nếu bị chặn cào hoặc văn bản < 200 ký tự
        print(f"-> [FALLBACK SNIPPET] Trang {url} không cào đủ văn bản (< 200 ký tự) -> Sử dụng Snippet dự phòng.")
        return fallback_snippet

    @classmethod
    def search_web(cls, query: str) -> list[dict]:
        """
        Tìm kiếm Web bằng DuckDuckGo HTML Search:
        So khớp trường link/url trong file blog_posts.json. 
        Nếu chưa từng cào trước đó ➔ Thực hiện Cào nội dung trang web (Scrape Page).
        """
        indexed_urls = cls.get_indexed_urls()
        
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            res = requests.post(ddg_url, data={"q": query}, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                results = []
                
                # Trích xuất các liên kết kết quả và đoạn tóm tắt từ HTML
                result_elements = soup.find_all("a", class_="result__a")
                snippet_elements = soup.find_all("a", class_="result__snippet")
                
                for i, elem in enumerate(result_elements):
                    # Tối đa 2 liên kết mới hợp lệ cho mỗi từ khóa
                    if len(results) >= 2:
                        break
                        
                    title = elem.text.strip()
                    raw_href = elem.get("href", "")
                    
                    # Giải mã tham số chuyển hướng URL 'uddg' lấy URL thực tế
                    real_url = raw_href
                    if "uddg=" in raw_href:
                        parsed_uddg = re.search(r'uddg=([^&]+)', raw_href)
                        if parsed_uddg:
                            real_url = urllib.parse.unquote(parsed_uddg.group(1))
                    elif raw_href.startswith("//"):
                        real_url = "https:" + raw_href
                        
                    # SO KHỚP VỚI ĐÃ LẬP CHỈ MỤC: Bỏ qua nếu URL đã tồn tại trong blog_posts.json
                    if real_url.strip().lower() in indexed_urls:
                        print(f"-> [SKIP] Bỏ qua cào lại URL đã lập chỉ mục trước đó trong blog_posts.json: {real_url}")
                        continue
                        
                    snippet = ""
                    if i < len(snippet_elements):
                        snippet = snippet_elements[i].text.strip()
                        
                    # BƯỚC CÀO NỘI DUNG TRANG WEB (Scrape Page với Snippet Fallback)
                    print(f"-> [SCRAPING PAGE] Đang cào nội dung trang web: {real_url}")
                    page_text = cls.scrape_page_content(real_url, fallback_snippet=snippet)
                    
                    # LẬP CHỈ MỤC CỤC BỘ (Local Indexing): Đóng gói bài viết mới nếu cào đạt chất lượng (>= 200 ký tự)
                    if page_text and page_text != snippet and len(page_text) >= 200:
                        cls.save_new_indexed_blog(title, real_url, page_text)
                    
                    results.append({
                        "title": title,
                        "url": real_url,
                        "snippet": snippet,
                        "page_content": page_text
                    })
                    
                if results:
                    return results
        except Exception as e:
            print(f"Lỗi khi tìm kiếm DuckDuckGo HTML: {str(e)}")

        return []

class ResearcherAgent:
    @staticmethod
    def execute_research(query: str, critic_plan: dict) -> tuple[str, dict]:
        """
        Tác nhân Nghiên cứu (Researcher Agent):
        Tiếp nhận kế hoạch nghiên cứu từ Critic Agent (search_queries, key_objectives, instructions),
        thực hiện tìm kiếm thông qua DuckDuckGo HTML Search, cào nội dung chi tiết bài viết (Scrape Page)
        và tổng hợp kết quả chuyên sâu dưới dạng Markdown.
        """
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        api_key = TraceConfig.OPENAI_API_KEY
        
        # Giới hạn tối đa 2 từ khóa tìm kiếm đầu tiên để đảm bảo tốc độ phản hồi và tránh bị chặn IP
        queries_to_search = critic_plan.get('search_queries', [])[:2]
        objectives = critic_plan.get('key_objectives', [])
        instructions = critic_plan.get('instructions', '')
        
        # Thực hiện tìm kiếm web & cào nội dung thực tế cho từng từ khóa
        live_search_findings = []
        for q in queries_to_search:
            web_results = SearchProvider.search_web(q)
            if web_results:
                live_search_findings.append({
                    "query": q,
                    "results": web_results
                })
        
        if not api_key:
            mock_result = (
                f"### [Mock Mode] Kết quả nghiên cứu cho: '{query}'\n\n"
                f"Dựa trên chỉ dẫn từ Critic Agent:\n"
                f"- **Từ khóa đã tra cứu:** {', '.join(queries_to_search)}\n"
                f"- **Mục tiêu đạt được:** {', '.join(objectives)}\n\n"
                f"**Nội dung cào thực tế từ Web (Page Content):**\n"
                + json.dumps(live_search_findings, ensure_ascii=False, indent=2)
            )
            return mock_result, empty_usage

        try:
            client = OpenAI(api_key=api_key)
            
            with TraceConfig.get_langfuse_client().start_as_current_observation(
                as_type="generation",
                name="researcher-agent-execution",
                model=TraceConfig.DEFAULT_MODEL,
                input={"query": query, "plan": critic_plan, "web_findings": live_search_findings}
            ) as generation:
                
                user_prompt = (
                    f"Câu hỏi của người dùng: {query}\n\n"
                    f"Kế hoạch nghiên cứu từ Critic Agent:\n"
                    f"- Từ khóa tìm kiếm: {json.dumps(queries_to_search, ensure_ascii=False)}\n"
                    f"- Mục tiêu nghiên cứu: {json.dumps(objectives, ensure_ascii=False)}\n"
                    f"- Chỉ dẫn chi tiết: {instructions}\n\n"
                    f"Nội dung cào chi tiết thu thập từ các trang web (Page Content):\n"
                    f"{json.dumps(live_search_findings, ensure_ascii=False, indent=2)}\n\n"
                    f"Hãy đóng vai Tác nhân Nghiên cứu (Researcher Agent) dựa vào nội dung cào thực tế trên để tổng hợp dữ liệu, trích dẫn liên kết nguồn thực tế và trả về bài nghiên cứu hoàn chỉnh dưới định dạng Markdown mượt mà."
                )
                
                response = client.chat.completions.create(
                    model=TraceConfig.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_RESEARCHER},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                usage_data = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
                generation.update(
                    output=result_text,
                    usage=usage_data
                )
                
                return result_text, usage_data
                
        except Exception as e:
            error_msg = f"Lỗi khi ResearcherAgent thực thi: {str(e)}"
            print(error_msg)
            return error_msg, empty_usage
