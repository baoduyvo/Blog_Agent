"use client";

import React, { useState, useEffect, useRef } from "react";
import { X, HelpCircle, Save, ArrowLeft, Plus } from "lucide-react";
import { Reflection, MOODS, REFLECTION_PROMPTS, saveReflection } from "@/utils/storage";
import styles from "./ReflectionEditor.module.css";

interface ReflectionEditorProps {
  editingReflection?: Reflection;
  onSave: () => void;
  onCancel: () => void;
}

export default function ReflectionEditor({
  editingReflection,
  onSave,
  onCancel,
}: ReflectionEditorProps) {
  const [title, setTitle] = useState("");
  const [mood, setMood] = useState(3);
  const [moodNote, setMoodNote] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [error, setError] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Initialize fields if editing
  useEffect(() => {
    if (editingReflection) {
      setTitle(editingReflection.title);
      setMood(editingReflection.mood);
      setMoodNote(editingReflection.moodNote || "");
      setContent(editingReflection.content);
      setTags(editingReflection.tags || []);
    } else {
      // Default title with today's date
      const today = new Date();
      const dateStr = today.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
      setTitle(`Phản tư ngày ${dateStr}`);
      setMood(3);
      setMoodNote("");
      setContent("");
      setTags(["Cá nhân"]);
    }
  }, [editingReflection]);

  // Handle tags keyboard actions (Enter or Comma)
  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const cleaned = tagInput.trim().replace(/,/g, "");
      if (cleaned && !tags.includes(cleaned)) {
        setTags([...tags, cleaned]);
        setTagInput("");
      }
    }
  };

  const handleAddTagClick = () => {
    const cleaned = tagInput.trim().replace(/,/g, "");
    if (cleaned && !tags.includes(cleaned)) {
      setTags([...tags, cleaned]);
      setTagInput("");
    }
  };

  const removeTag = (indexToRemove: number) => {
    setTags(tags.filter((_, index) => index !== indexToRemove));
  };

  // Insert prompt into content
  const handlePromptClick = (prompt: string) => {
    const promptText = `\n\n*Hỏi: ${prompt}*\nTrả lời: `;
    setContent((prev) => prev + promptText);
    
    // Focus back on text area and scroll it
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(
          textareaRef.current.value.length,
          textareaRef.current.value.length
        );
      }
    }, 50);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Vui lòng nhập tiêu đề cho bài phản tư.");
      return;
    }

    if (!content.trim()) {
      setError("Nội dung bài viết không được để trống.");
      return;
    }

    // Save reflection
    saveReflection({
      id: editingReflection?.id,
      title: title.trim(),
      content: content.trim(),
      mood,
      moodNote: moodNote.trim(),
      tags,
      createdAt: editingReflection?.createdAt,
    });

    onSave();
  };

  return (
    <form onSubmit={handleSubmit} className={`${styles.container} animate-fade-in`}>
      {/* Main Form */}
      <div className={`glass-card ${styles.editorCard}`}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "16px", marginBottom: "10px" }}>
          <button type="button" className="btn btn-secondary" style={{ padding: "8px 12px" }} onClick={onCancel}>
            <ArrowLeft size={16} /> Quay lại
          </button>
          <h2 style={{ fontSize: "20px" }}>
            {editingReflection ? "Chỉnh sửa bài viết" : "Tạo bài phản tư mới"}
          </h2>
        </div>

        {error && (
          <div style={{ padding: "12px", background: "rgba(244, 63, 94, 0.15)", border: "1px solid rgba(244, 63, 94, 0.3)", borderRadius: "var(--radius-md)", color: "#f43f5e", fontSize: "14px" }}>
            {error}
          </div>
        )}

        {/* Title */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Tiêu đề</label>
          <input
            type="text"
            className="input-field"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Nhập tiêu đề..."
          />
        </div>

        {/* Mood Selector */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Tâm trạng hiện tại của bạn</label>
          <div className="emoji-selector">
            {MOODS.map((m) => {
              const isActive = mood === m.value;
              return (
                <button
                  key={m.value}
                  type="button"
                  className={`emoji-btn ${isActive ? `active-${m.value}` : ""}`}
                  onClick={() => setMood(m.value)}
                >
                  <div>{m.emoji}</div>
                  <span>{m.label}</span>
                </button>
              );
            })}
          </div>

          <input
            type="text"
            className={`input-field ${styles.moodNoteInput}`}
            value={moodNote}
            onChange={(e) => setMoodNote(e.target.value)}
            placeholder="Ghi chú thêm về cảm xúc hôm nay (ví dụ: Năng suất, có chút mệt mỏi...)"
          />
        </div>

        {/* Tags */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Thẻ phân loại (tags)</label>
          <div className={styles.tagInputWrapper}>
            {tags.map((tag, index) => (
              <span key={index} className={styles.tagBadge}>
                #{tag}
                <button type="button" onClick={() => removeTag(index)}>
                  <X size={12} />
                </button>
              </span>
            ))}
            <input
              type="text"
              className={styles.tagInput}
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              placeholder="Nhập tag và ấn Enter..."
            />
            {tagInput.trim() && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "4px 8px", borderRadius: "var(--radius-sm)" }}
                onClick={handleAddTagClick}
              >
                <Plus size={14} /> Thêm
              </button>
            )}
          </div>
        </div>

        {/* Content Editor */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Bài phản tư tự do</label>
          <textarea
            ref={textareaRef}
            className="textarea-field"
            style={{ minHeight: "260px", resize: "vertical", fontFamily: "inherit" }}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Nhập những suy nghĩ, bài học hoặc trải nghiệm của bạn ở đây... Bạn có thể bấm vào các câu hỏi gợi ý bên phải để bắt đầu."
          />
          <span className={styles.charCount}>
            {content.length} ký tự | {content.split(/\s+/).filter(Boolean).length} từ
          </span>
        </div>

        {/* Action Buttons */}
        <div className={styles.buttonRow}>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Hủy bỏ
          </button>
          <button type="submit" className="btn btn-primary">
            <Save size={18} /> Lưu bài viết
          </button>
        </div>
      </div>

      {/* Prompts Sidebar */}
      <div className={`glass-card ${styles.sidebarCard}`}>
        <h3 className={styles.sidebarTitle}>
          <HelpCircle size={18} /> Gợi Ý Phản Tư
        </h3>
        <p style={{ fontSize: "13px", color: "hsl(var(--text-muted))" }}>
          Nếu chưa biết bắt đầu từ đâu, hãy click vào các câu hỏi bên dưới để chèn trực tiếp câu hỏi gợi ý vào bài viết của bạn:
        </p>

        <div className={styles.promptList}>
          {REFLECTION_PROMPTS.map((prompt, index) => (
            <button
              key={index}
              type="button"
              className={styles.promptItem}
              onClick={() => handlePromptClick(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>

        <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "16px", marginTop: "10px" }}>
          <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "8px", color: "#fff" }}>
            💡 Mẹo viết phản tư:
          </h4>
          <ul className={styles.tipsList}>
            <li>Thành thật tuyệt đối với cảm xúc cá nhân của mình.</li>
            <li>Tập trung phân tích nguyên nhân thay vì chỉ liệt kê sự kiện.</li>
            <li>Rút ra ít nhất 1 bài học hành động nhỏ cho ngày mai.</li>
            <li>Sử dụng cấu trúc: Sự việc diễn ra ➔ Suy nghĩ/Cảm xúc của tôi ➔ Bài học rút ra.</li>
          </ul>
        </div>
      </div>
    </form>
  );
}
