"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, LayoutDashboard, History, PlusCircle, Database } from "lucide-react";
import { Reflection, getReflections, deleteReflection } from "@/utils/storage";
import Dashboard from "@/components/Dashboard";
import Timeline from "@/components/Timeline";
import ReflectionEditor from "@/components/ReflectionEditor";
import BlogAssistant from "@/components/BlogAssistant";
import AdminLogs from "@/components/AdminLogs";
import styles from "./page.module.css";

export default function Home() {
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [activeTab, setActiveTab] = useState<"dashboard" | "timeline" | "new" | "rag" | "admin">("rag");
  const [editingReflection, setEditingReflection] = useState<Reflection | undefined>(undefined);
  const [mounted, setMounted] = useState(false);

  // Prevent Next.js server-client hydration mismatch by loading localStorage data after mount
  useEffect(() => {
    setReflections(getReflections());
    setMounted(true);
  }, []);

  const refreshReflections = () => {
    setReflections(getReflections());
  };

  const handleSave = () => {
    refreshReflections();
    setEditingReflection(undefined);
    setActiveTab("timeline"); // Switch to timeline so they can see their entry
  };

  const handleCancel = () => {
    setEditingReflection(undefined);
    setActiveTab("dashboard");
  };

  const handleEdit = (entry: Reflection) => {
    setEditingReflection(entry);
    setActiveTab("new");
  };

  const handleDelete = (id: string) => {
    const updated = deleteReflection(id);
    setReflections(updated);
  };

  // Render a clean loader while mounting client-side
  if (!mounted) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", backgroundColor: "hsl(224, 71%, 4%)", color: "hsl(215, 20%, 75%)" }}>
        <div style={{ textAlign: "center" }}>
          <Sparkles className={styles.logoIcon} size={40} style={{ marginBottom: "16px" }} />
          <p>Đang tải ứng dụng...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      {/* Header Branding & Navigation */}
      <header className={styles.header}>
        <div className={styles.brand}>
          <Sparkles className={styles.logoIcon} size={32} />
          <div className={styles.brandText}>
            <h1 className={styles.title}>Self-Reflection</h1>
            <span className={styles.subtitle}>Không gian phản tư & Lắng nghe chính mình</span>
          </div>
        </div>

        {/* Tab Buttons */}
        <nav className={styles.tabs}>
          {/* 
          <button
            className={`${styles.tabButton} ${activeTab === "dashboard" ? styles.activeTab : ""}`}
            onClick={() => {
              setActiveTab("dashboard");
              setEditingReflection(undefined);
            }}
          >
            <LayoutDashboard size={16} />
            Bảng điều khiển
          </button>
          <button
            className={`${styles.tabButton} ${activeTab === "timeline" ? styles.activeTab : ""}`}
            onClick={() => {
              setActiveTab("timeline");
              setEditingReflection(undefined);
            }}
          >
            <History size={16} />
            Dòng thời gian
          </button>
          <button
            className={`${styles.tabButton} ${activeTab === "new" && !editingReflection ? styles.activeTab : ""}`}
            onClick={() => {
              setEditingReflection(undefined);
              setActiveTab("new");
            }}
          >
            <PlusCircle size={16} />
            Viết phản tư
          </button>
          */}
          <button
            className={`${styles.tabButton} ${activeTab === "rag" ? styles.activeTab : ""}`}
            onClick={() => {
              setEditingReflection(undefined);
              setActiveTab("rag");
            }}
          >
            <Sparkles size={16} />
            Trò chuyện AI
          </button>
          <button
            className={`${styles.tabButton} ${activeTab === "admin" ? styles.activeTab : ""}`}
            onClick={() => {
              setEditingReflection(undefined);
              setActiveTab("admin");
            }}
          >
            <Database size={16} />
            Quản trị Logs
          </button>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className={styles.main}>
        {activeTab === "dashboard" && (
          <Dashboard
            reflections={reflections}
            onStartReflection={() => {
              setEditingReflection(undefined);
              setActiveTab("new");
            }}
          />
        )}

        {activeTab === "timeline" && (
          <Timeline
            reflections={reflections}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        )}

        {activeTab === "new" && (
          <ReflectionEditor
            editingReflection={editingReflection}
            onSave={handleSave}
            onCancel={handleCancel}
          />
        )}

        {activeTab === "rag" && (
          <BlogAssistant />
        )}

        {activeTab === "admin" && (
          <AdminLogs />
        )}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div>
          © {new Date().getFullYear()} Self-Reflection. Đồng hành cùng sức khỏe tinh thần của bạn.
        </div>
        <div className={styles.footerLinks}>
          <a href="#" className={styles.footerLink}>Bảo mật</a>
          <a href="#" className={styles.footerLink}>Điều khoản</a>
          <a href="#" className={styles.footerLink}>Liên hệ</a>
        </div>
      </footer>
    </div>
  );
}
