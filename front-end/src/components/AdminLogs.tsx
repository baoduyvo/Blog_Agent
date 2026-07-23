"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Activity, CheckCircle2, Search, RefreshCw, 
  ChevronDown, ChevronUp, Cpu, ShieldAlert, Database 
} from "lucide-react";
import styles from "./AdminLogs.module.css";

interface StepTrace {
  step: string;
  status: "passed" | "failed";
  reason?: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

interface LogEntry {
  timestamp: string;
  request_metadata: {
    http_method?: string;
    url?: string;
    client_host?: string;
  };
  input: string;
  guardrail: {
    is_safe: boolean;
    failed_step?: string;
    steps?: StepTrace[];
  };
  ai_response: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export default function AdminLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "safe" | "blocked">("all");
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({});

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    try {
      const response = await fetch(`${apiUrl}/api/admin/logs`);
      if (!response.ok) {
        throw new Error("Không thể tải logs từ Backend. Vui lòng đảm bảo Backend đang hoạt động.");
      }
      const data = await response.json();
      if (data.status === "success") {
        setLogs(data.logs || []);
      } else {
        throw new Error(data.message || "Lỗi tải logs.");
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Đã xảy ra lỗi không xác định.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const toggleExpand = (index: number) => {
    setExpandedIndices(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Tính toán số liệu thống kê
  const totalLogs = logs.length;
  const safeCount = logs.filter(log => log.guardrail.is_safe).length;
  const blockedCount = totalLogs - safeCount;
  const totalTokens = logs.reduce((acc, log) => acc + (log.usage?.total_tokens || 0), 0);
  const avgTokens = totalLogs > 0 ? Math.round(totalTokens / totalLogs) : 0;

  // Lọc logs
  const filteredLogs = logs.filter((log, index) => {
    // Lọc theo trạng thái
    if (statusFilter === "safe" && !log.guardrail.is_safe) return false;
    if (statusFilter === "blocked" && log.guardrail.is_safe) return false;
    
    // Lọc theo từ khóa tìm kiếm
    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      const inputMatch = log.input.toLowerCase().includes(query);
      const responseMatch = log.ai_response.toLowerCase().includes(query);
      const hostMatch = log.request_metadata?.client_host?.toLowerCase().includes(query) || false;
      return inputMatch || responseMatch || hostMatch;
    }
    
    return true;
  });

  const formatDateTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div>
          <h2 style={{ fontSize: "20px", display: "flex", alignItems: "center", gap: "8px", color: "#fff", margin: 0 }}>
            <Database size={22} style={{ color: "hsl(var(--primary))" }} />
            Giám sát Trace Logs Cục bộ
          </h2>
          <p style={{ fontSize: "14px", color: "hsl(var(--text-muted))", margin: "4px 0 0 0" }}>
            Quản trị viên theo dõi toàn bộ các hoạt động gọi API AI, kiểm duyệt Guardrail và tiêu thụ Token.
          </p>
        </div>
        <button 
          onClick={fetchLogs} 
          className="btn btn-secondary" 
          disabled={loading}
          style={{ padding: "8px 16px", display: "flex", alignItems: "center", gap: "8px", height: "fit-content" }}
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Làm mới
        </button>
      </div>

      {/* Stats Cards */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: "hsl(var(--primary))" }}>
            <Activity size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Tổng yêu cầu</span>
            <span className={styles.statValue}>{totalLogs}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: "#10b981" }}>
            <CheckCircle2 size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Hợp lệ (Safe)</span>
            <span className={styles.statValue}>{safeCount}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: "#ef4444" }}>
            <ShieldAlert size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Bị chặn (Blocked)</span>
            <span className={styles.statValue}>{blockedCount}</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ color: "hsl(var(--secondary))" }}>
            <Cpu size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statLabel}>Tokens trung bình</span>
            <span className={styles.statValue}>{avgTokens}</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className={styles.filterBar}>
        <div className={styles.filterGroup}>
          <button 
            onClick={() => setStatusFilter("all")} 
            className={`btn ${statusFilter === "all" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 12px", fontSize: "13px" }}
          >
            Tất cả
          </button>
          <button 
            onClick={() => setStatusFilter("safe")} 
            className={`btn ${statusFilter === "safe" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 12px", fontSize: "13px", color: statusFilter === "safe" ? "#fff" : "#10b981" }}
          >
            An toàn
          </button>
          <button 
            onClick={() => setStatusFilter("blocked")} 
            className={`btn ${statusFilter === "blocked" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 12px", fontSize: "13px", color: statusFilter === "blocked" ? "#fff" : "#ef4444" }}
          >
            Bị chặn
          </button>
        </div>

        <div className={styles.searchGroup}>
          <Search size={16} style={{ color: "rgba(255,255,255,0.4)" }} />
          <input 
            type="text" 
            className="input-field" 
            placeholder="Tìm kiếm theo từ khóa hoặc IP..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ margin: 0, padding: "8px 12px", fontSize: "13px" }}
          />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{ padding: "14px", background: "rgba(244, 63, 94, 0.12)", border: "1px solid rgba(244, 63, 94, 0.25)", borderRadius: "var(--radius-md)", color: "#f43f5e", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Logs List */}
      {loading ? (
        <div className={styles.noLogs}>Đang tải dữ liệu logs...</div>
      ) : filteredLogs.length === 0 ? (
        <div className={styles.noLogs}>Không có bản ghi log nào khớp với bộ lọc của bạn.</div>
      ) : (
        <div className={styles.logsList}>
          {filteredLogs.map((log, index) => {
            const isExpanded = !!expandedIndices[index];
            return (
              <div key={index} className={styles.logCard}>
                <div onClick={() => toggleExpand(index)} className={styles.logHeader}>
                  <div className={styles.logMeta}>
                    <span style={{ fontSize: "12px", fontWeight: "600", opacity: 0.8 }}>
                      {formatDateTime(log.timestamp)}
                    </span>
                    <span className={`${styles.badge} ${log.guardrail.is_safe ? styles.badgeSuccess : styles.badgeDanger}`}>
                      {log.guardrail.is_safe ? "Safe" : "Blocked"}
                    </span>
                    {!log.guardrail.is_safe && log.guardrail.failed_step && (
                      <span style={{ fontSize: "11px", padding: "2px 8px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "4px", color: "#ef4444", fontWeight: 500 }}>
                        {log.guardrail.failed_step}
                      </span>
                    )}
                    <span style={{ color: "rgba(255,255,255,0.4)" }}>|</span>
                    <span className={styles.logTextPreview}>
                      {log.input}
                    </span>
                  </div>
                  <div>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>
                </div>

                {isExpanded && (
                  <div className={styles.logDetails}>
                    <div className={styles.detailGrid}>
                      <div className={styles.detailBox}>
                        <span className={styles.detailTitle}>Người dùng hỏi (Input)</span>
                        <div className={styles.detailContent}>{log.input}</div>
                      </div>
                      
                      <div className={styles.detailBox}>
                        <span className={styles.detailTitle}>Phản hồi hệ thống (Output)</span>
                        <div className={styles.detailContent}>{log.ai_response}</div>
                      </div>
                    </div>

                    <div className={styles.detailGrid}>
                      <div className={styles.detailBox}>
                        <span className={styles.detailTitle}>HTTP Metadata</span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "13px", color: "hsl(var(--text-secondary))" }}>
                          <div><strong>Method:</strong> {log.request_metadata?.http_method || "N/A"}</div>
                          <div><strong>IP Host:</strong> {log.request_metadata?.client_host || "N/A"}</div>
                          <div><strong>API URL:</strong> <code style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "2px 6px", borderRadius: "3px" }}>{log.request_metadata?.url || "N/A"}</code></div>
                        </div>
                      </div>

                      <div className={styles.detailBox}>
                        <span className={styles.detailTitle}>Quan sát & Tiêu thụ (Usage)</span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "13px", color: "hsl(var(--text-secondary))" }}>
                          <div><strong>Trạng thái bảo mật:</strong> {log.guardrail.is_safe ? <span style={{ color: "#10b981" }}>AN TOÀN</span> : <span style={{ color: "#ef4444" }}>BỊ CHẶN</span>}</div>
                          <div><strong>Bước kiểm tra:</strong> <span style={{ color: log.guardrail.is_safe ? "#10b981" : "#ef4444", fontWeight: 600 }}>{log.guardrail.failed_step || "Hoàn thành kiểm tra"}</span></div>
                          <div><strong>Tổng số Token:</strong> {log.usage?.total_tokens !== undefined ? `${log.usage.total_tokens} tokens` : "N/A"}</div>
                          {log.usage && log.usage.total_tokens !== undefined && log.usage.total_tokens > 0 && (
                            <div style={{ fontSize: "11px", opacity: 0.6 }}>
                              (Prompt: {log.usage.prompt_tokens} | Completion: {log.usage.completion_tokens})
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Nhật ký chạy từng bước (Step Tracing) */}
                    {log.guardrail.steps && log.guardrail.steps.length > 0 && (
                      <div className={styles.detailBox} style={{ width: "100%" }}>
                        <span className={styles.detailTitle}>Nhật ký chạy từng bước (Step Tracing)</span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "10px" }}>
                          {log.guardrail.steps.map((stepItem, stepIdx) => (
                            <div 
                              key={stepIdx} 
                              style={{ 
                                display: "flex", 
                                justifyContent: "space-between", 
                                alignItems: "center", 
                                padding: "8px 12px", 
                                background: "rgba(255, 255, 255, 0.015)", 
                                border: "1px solid rgba(255, 255, 255, 0.03)", 
                                borderRadius: "4px" 
                              }}
                            >
                              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                <span style={{ fontSize: "13px", fontWeight: "600", color: "#fff" }}>
                                  {stepItem.step}
                                </span>
                                {stepItem.reason && (
                                  <span style={{ fontSize: "12px", color: stepItem.status === "passed" ? "#10b981" : "#ef4444" }}>
                                    Kết quả: {stepItem.reason}
                                  </span>
                                )}
                              </div>
                              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                {stepItem.usage && stepItem.usage.total_tokens !== undefined && stepItem.usage.total_tokens > 0 && (
                                  <span style={{ fontSize: "11px", opacity: 0.6 }}>
                                    ({stepItem.usage.prompt_tokens}p | {stepItem.usage.completion_tokens}c | {stepItem.usage.total_tokens}t)
                                  </span>
                                )}
                                <span 
                                  style={{ 
                                    fontSize: "10px", 
                                    fontWeight: "600", 
                                    padding: "2px 6px", 
                                    borderRadius: "8px", 
                                    textTransform: "uppercase",
                                    color: stepItem.status === "passed" ? "#10b981" : "#ef4444",
                                    background: stepItem.status === "passed" ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
                                    border: stepItem.status === "passed" ? "1px solid rgba(16, 185, 129, 0.15)" : "1px solid rgba(239, 68, 68, 0.15)"
                                  }}
                                >
                                  {stepItem.status}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
