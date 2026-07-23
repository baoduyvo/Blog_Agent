"use client";

import React, { useState } from "react";
import { Sparkles, BookOpen, ExternalLink, FileText, AlertTriangle, Coins, Cpu, CheckCircle, RotateCcw } from "lucide-react";
import styles from "./BlogAssistant.module.css";

interface Source {
  title: string;
  link: string;
  source: string;
}

interface SafetyStage {
  name: string;
  is_safe: boolean;
  latency_ms: number;
  reason: string;
  details: string;
}

interface LiveStep {
  step: string;
  status: "running" | "passed" | "failed";
  reason?: string;
}

export default function BlogAssistant() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [blogContent, setBlogContent] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [demoMode, setDemoMode] = useState(false);
  const [error, setError] = useState("");
  const [safetyAudit, setSafetyAudit] = useState<SafetyStage[]>([]);
  const [postSafetyAudit, setPostSafetyAudit] = useState<SafetyStage[]>([]);
  const [isBlocked, setIsBlocked] = useState(false);
  const [estimatedCost, setEstimatedCost] = useState(0.0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [stage, setStage] = useState("completed"); // completed, pending_review
  const [userFeedback, setUserFeedback] = useState("");
  const [liveSteps, setLiveSteps] = useState<LiveStep[]>([]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError("Vui lòng nhập nội dung muốn trò chuyện.");
      return;
    }

    setLoading(true);
    setError("");
    setBlogContent("");
    setLiveSteps([]);
    setSources([]);
    setSafetyAudit([]);
    setPostSafetyAudit([]);
    setIsBlocked(false);
    setEstimatedCost(0.0);
    setTotalTokens(0);
    setStage("completed");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: topic.trim() }),
      });

      if (!response.ok) {
        if (response.status === 400) {
          const errData = await response.json();
          throw new Error(errData.detail || "Yêu cầu không hợp lệ.");
        }
        throw new Error("Không thể kết nối đến server Backend. Vui lòng kiểm tra xem Backend FastAPI đã được chạy chưa.");
      }

      const data = await response.json();
      setBlogContent(data.message);
    } catch (err: any) {
      console.error("Error chatting with AI:", err);
      setError(err.message || "Đã xảy ra lỗi khi kết nối đến server.");
    } finally {
      setLoading(false);
    }
  };


  const handleHitlAction = async (action: "approve" | "rewrite") => {
    setLoading(true);
    setError("");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      const response = await fetch(`${apiUrl}/api/rag/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic: topic.trim(),
          stage: action,
          bypass_review: action === "approve",
          feedback: action === "rewrite" ? userFeedback.trim() : blogContent
        }),
      });

      if (!response.ok) {
        throw new Error("Lỗi khi xử lý phản hồi biên tập viên.");
      }

      const data = await response.json();
      setBlogContent(data.content);
      setSources(data.sources || []);
      setDemoMode(data.demo_mode || false);
      setSafetyAudit(data.safety_audit || []);
      setPostSafetyAudit(data.post_safety_audit || []);
      setIsBlocked(data.is_blocked || false);
      setEstimatedCost(data.estimated_cost_usd || 0.0);
      setTotalTokens(data.total_tokens || 0);
      setStage(data.stage || "completed");

      if (action === "approve") {
        setUserFeedback("");
      }
    } catch (err: any) {
      console.error("Error performing HITL action:", err);
      setError(err.message || "Đã xảy ra lỗi khi gửi phản hồi lên server.");
    } finally {
      setLoading(false);
    }
  };

  // Helper to parse bold (**text**) inline
  const parseInlineStyles = (text: string) => {
    if (!text.includes("**")) return text;
    const parts = text.split("**");
    return parts.map((part, i) => (i % 2 === 1 ? <strong key={i} style={{ color: "#fff", fontWeight: "600" }}>{part}</strong> : part));
  };

  // Custom lightweight markdown renderer to convert headers, bullet points, blockquotes and bold tags
  const renderMarkdown = (markdown: string) => {
    if (!markdown) return null;
    const lines = markdown.split("\n");

    return lines.map((line, idx) => {
      // Heading 1
      if (line.startsWith("# ")) {
        return (
          <h1 key={idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "10px", margin: "24px 0 16px 0", color: "#fff" }}>
            {line.slice(2)}
          </h1>
        );
      }

      // Heading 2
      if (line.startsWith("## ")) {
        return (
          <h2 key={idx} style={{ margin: "28px 0 14px 0", fontSize: "20px", color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={18} style={{ color: "hsl(var(--primary))" }} />
            {line.slice(3)}
          </h2>
        );
      }

      // Heading 3
      if (line.startsWith("### ")) {
        return (
          <h3 key={idx} style={{ margin: "20px 0 10px 0", fontSize: "16px", color: "hsl(var(--text-secondary))" }}>
            {line.slice(4)}
          </h3>
        );
      }

      // Blockquote
      if (line.startsWith("> ")) {
        return (
          <blockquote key={idx} style={{ borderLeft: "4px solid hsl(var(--primary))", paddingLeft: "16px", margin: "16px 0", color: "hsl(var(--text-secondary))", fontStyle: "italic", background: "rgba(255,255,255,0.02)", padding: "12px 16px", borderRadius: "0 var(--radius-sm) var(--radius-sm) 0" }}>
            {line.slice(2)}
          </blockquote>
        );
      }

      // Bullet points
      if (line.startsWith("- ") || line.startsWith("* ")) {
        return (
          <li key={idx} style={{ marginLeft: "24px", marginBottom: "8px", listStyleType: "square", color: "hsl(var(--text-secondary))" }}>
            {parseInlineStyles(line.slice(2))}
          </li>
        );
      }

      if (line.trim() === "") {
        return <div key={idx} style={{ height: "14px" }} />;
      }

      // Standard paragraph
      return (
        <p key={idx} style={{ marginBottom: "14px", color: "hsl(var(--text-secondary))" }}>
          {parseInlineStyles(line)}
        </p>
      );
    });
  };

  return (
    <div className={`${styles.container} animate-fade-in`}>
      {/* Input Form Card */}
      <div className={`glass-card ${styles.inputCard}`}>
        <h2 style={{ fontSize: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Sparkles size={22} style={{ color: "hsl(var(--primary))" }} />
          Trợ Lý AI Chat
        </h2>
        {/* <p style={{ fontSize: "14px", color: "hsl(var(--text-muted))" }}> */}
        {/* Trò chuyện trực tiếp với Trợ lý AI để chia sẻ tâm sự, phản tư cuộc sống hoặc thảo luận tìm kiếm thông tin học tập. */}
        {/* </p> */}

        {error && (
          <div style={{ padding: "12px", background: "rgba(244, 63, 94, 0.12)", border: "1px solid rgba(244, 63, 94, 0.25)", borderRadius: "var(--radius-md)", color: "#f43f5e", fontSize: "13px" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleGenerate} className={styles.inputGroup}>
          <input
            type="text"
            className="input-field"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Nhập nội dung bạn muốn chia sẻ với AI..."
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ whiteSpace: "nowrap" }}>
            <Sparkles size={16} /> Gửi tin nhắn
          </button>
        </form>
      </div>

      {/* Loading Spinner */}
      {loading && (
        <div className={`glass-card ${styles.glowingSpinner}`}>
          <div className={styles.spinner} />
          <div className={styles.spinnerText}>AI đang suy nghĩ, xử lý RAG và lưu trace log...</div>
        </div>
      )}


      {/* Generated Content Result */}
      {blogContent && !loading && (
        <div className={`glass-card ${styles.resultCard}`}>
          {/* Demo Mode Alert Banner */}
          {demoMode && (
            <div className={styles.demoBanner}>
              <AlertTriangle size={20} style={{ flexShrink: 0 }} />
              <div className={styles.demoBannerText}>
                <div className={styles.demoBannerTitle}>Chế độ mô phỏng RAG (Demo Mode)</div>
                Hệ thống đang hoạt động ở chế độ Demo vì chưa tìm thấy khóa `OPENAI_API_KEY` hợp lệ trong tệp `.env`. Cấu trúc RAG và kết quả khớp tài liệu vẫn hoạt động chuẩn xác với bài viết mẫu.
              </div>
            </div>
          )}

          {/* Generated Blog Body */}
          <div className={styles.blogBody}>
            {renderMarkdown(blogContent)}
          </div>

          {/* Safety Audit & Telemetry Tracing Dashboard */}
          {safetyAudit.length > 0 && (
            <div style={{ marginTop: "24px", display: "flex", flexDirection: "column", gap: "16px", padding: "20px", background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "var(--radius-md)" }}>
              <h4 style={{ fontSize: "14px", fontWeight: "700", display: "flex", alignItems: "center", gap: "8px", textTransform: "uppercase", letterSpacing: "0.05em", color: isBlocked ? "#ef4444" : "#10b981" }}>
                <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: isBlocked ? "#ef4444" : "#10b981", boxShadow: isBlocked ? "0 0 10px #ef4444" : "0 0 10px #10b981" }} />
                Safety Audit & Telemetry Tracing (Giám sát Bảo mật & Hiệu năng)
              </h4>

              {/* Cost and Tokens Badges */}
              {(totalTokens > 0 || estimatedCost > 0) && (
                <div style={{ display: "flex", gap: "12px", marginBottom: "4px" }}>
                  <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px", padding: "10px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "var(--radius-sm)" }}>
                    <Coins size={14} style={{ color: "hsl(var(--primary))" }} />
                    <span style={{ fontSize: "12px", color: "hsl(var(--text-muted))" }}>Chi phí API:</span>
                    <span style={{ fontSize: "12px", color: "#10b981", fontWeight: "700" }}>${estimatedCost.toFixed(6)} USD</span>
                  </div>
                  <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px", padding: "10px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "var(--radius-sm)" }}>
                    <Cpu size={14} style={{ color: "hsl(var(--primary))" }} />
                    <span style={{ fontSize: "12px", color: "hsl(var(--text-muted))" }}>Tổng số Tokens:</span>
                    <span style={{ fontSize: "12px", color: "#fff", fontWeight: "700" }}>{totalTokens.toLocaleString()} tokens</span>
                  </div>
                </div>
              )}

              {/* Human-in-the-Loop review panel if stage is pending_review */}
              {stage === "pending_review" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", border: "1px solid rgba(245, 158, 11, 0.3)", background: "rgba(245, 158, 11, 0.05)", padding: "18px", borderRadius: "var(--radius-sm)", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#f59e0b" }}>
                    <AlertTriangle size={18} />
                    <span style={{ fontWeight: "700", fontSize: "13px" }}>BÀI VIẾT CHƯA ĐẠT TIÊU CHUẨN (CẦN PHÊ DUYỆT THỦ CÔNG)</span>
                  </div>
                  <p style={{ fontSize: "12px", color: "hsl(var(--text-muted))", margin: 0, lineHeight: "1.5" }}>
                    Critic Agent đánh giá bài viết dưới 8.0 điểm. Hãy nhập ý kiến sửa bài viết phía dưới để bắt AI viết lại, hoặc bấm Duyệt Ghi Đè để xuất bản bản thảo này luôn.
                  </p>
                  <textarea
                    className="input-field"
                    style={{ minHeight: "80px", padding: "10px", fontSize: "12px", background: "rgba(0,0,0,0.2)", color: "#fff" }}
                    placeholder="Nhập yêu cầu sửa đổi (Ví dụ: hãy thêm phần kết luận cụ thể, đổi văn phong trang trọng hơn...)"
                    value={userFeedback}
                    onChange={(e) => setUserFeedback(e.target.value)}
                  />
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button onClick={() => handleHitlAction("rewrite")} className="btn btn-secondary" style={{ flex: 1, padding: "8px 12px", fontSize: "12px", gap: "6px" }} disabled={loading}>
                      <RotateCcw size={14} /> Gửi yêu cầu viết lại
                    </button>
                    <button onClick={() => handleHitlAction("approve")} className="btn btn-primary" style={{ flex: 1, padding: "8px 12px", fontSize: "12px", gap: "6px" }} disabled={loading}>
                      <CheckCircle size={14} /> Duyệt Ghi Đè (Approve)
                    </button>
                  </div>
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {safetyAudit.map((stage, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(255,255,255,0.02)", border: `1px solid ${stage.is_safe ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.25)"}`, padding: "14px 18px", borderRadius: "var(--radius-sm)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: "600", fontSize: "13px", color: stage.is_safe ? "#fff" : "#ef4444" }}>
                        {stage.name}
                      </span>
                      <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", background: "rgba(255,255,255,0.04)", padding: "3px 8px", borderRadius: "12px" }}>
                        Độ trễ: {stage.latency_ms} ms
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "hsl(var(--text-muted))", margin: "2px 0 0 0", lineHeight: "1.4" }}>
                      {stage.details}
                    </p>
                    <div style={{ fontSize: "12px", color: stage.is_safe ? "#10b981" : "#ef4444", marginTop: "4px", fontWeight: "600" }}>
                      Kết quả: {stage.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Output Safety Audit & Telemetry Tracing Dashboard */}
          {postSafetyAudit.length > 0 && (
            <div style={{ marginTop: "24px", display: "flex", flexDirection: "column", gap: "16px", padding: "20px", background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "var(--radius-md)" }}>
              <h4 style={{ fontSize: "14px", fontWeight: "700", display: "flex", alignItems: "center", gap: "8px", textTransform: "uppercase", letterSpacing: "0.05em", color: isBlocked && blogContent.includes("bộ lọc đầu ra") ? "#ef4444" : "#10b981" }}>
                <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: isBlocked && blogContent.includes("bộ lọc đầu ra") ? "#ef4444" : "#10b981", boxShadow: isBlocked && blogContent.includes("bộ lọc đầu ra") ? "0 0 10px #ef4444" : "0 0 10px #10b981" }} />
                Output Safety Audit & Telemetry (Giám sát Bảo mật & Đạo văn Đầu ra)
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {postSafetyAudit.map((stage, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(255,255,255,0.02)", border: `1px solid ${stage.is_safe ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.25)"}`, padding: "14px 18px", borderRadius: "var(--radius-sm)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: "600", fontSize: "13px", color: stage.is_safe ? "#fff" : "#ef4444" }}>
                        {stage.name}
                      </span>
                      <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", background: "rgba(255,255,255,0.04)", padding: "3px 8px", borderRadius: "12px" }}>
                        Độ trễ: {stage.latency_ms} ms
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "hsl(var(--text-muted))", margin: "2px 0 0 0", lineHeight: "1.4" }}>
                      {stage.details}
                    </p>
                    <div style={{ fontSize: "12px", color: stage.is_safe ? "#10b981" : "#ef4444", marginTop: "4px", fontWeight: "600" }}>
                      Kết quả: {stage.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources Grounding List */}
          {sources.length > 0 && (
            <div className={styles.sourcesSection}>
              <h4 className={styles.sourcesTitle}>
                <BookOpen size={16} style={{ color: "hsl(var(--secondary))" }} />
                Nguồn tài liệu đã tham khảo ({sources.length})
              </h4>
              <div className={styles.sourcesGrid}>
                {sources.map((src, i) => (
                  <div key={i} className={styles.sourceItem}>
                    <div className={styles.sourceInfo}>
                      <span className={styles.sourceName} title={src.title}>{src.title}</span>
                      <span className={styles.sourceMeta}>Nguồn: {src.source}</span>
                    </div>
                    {src.link && src.link !== "#" && (
                      <a href={src.link} target="_blank" rel="noopener noreferrer" className={styles.sourceLink} title="Xem bài viết gốc">
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
