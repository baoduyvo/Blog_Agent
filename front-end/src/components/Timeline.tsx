"use client";

import React, { useState } from "react";
import { Search, Edit2, Trash2, Calendar, ChevronDown, ChevronUp, AlertCircle, Filter } from "lucide-react";
import { Reflection, MOODS } from "@/utils/storage";
import styles from "./Timeline.module.css";

interface TimelineProps {
  reflections: Reflection[];
  onEdit: (entry: Reflection) => void;
  onDelete: (id: string) => void;
}

export default function Timeline({ reflections, onEdit, onDelete }: TimelineProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMood, setSelectedMood] = useState("all");
  const [selectedTag, setSelectedTag] = useState("all");
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({});

  // Get all unique tags from reflections
  const allTags = Array.from(
    new Set(reflections.flatMap((r) => r.tags || []))
  ).filter(Boolean);

  // Toggle expand/collapse of entry content
  const toggleExpand = (id: string) => {
    setExpandedEntries((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // Filter entries
  const filteredReflections = reflections.filter((entry) => {
    const matchesSearch =
      entry.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesMood = selectedMood === "all" || entry.mood.toString() === selectedMood;
    const matchesTag = selectedTag === "all" || entry.tags.includes(selectedTag);

    return matchesSearch && matchesMood && matchesTag;
  });

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm("Bạn có chắc chắn muốn xóa bài viết phản tư này? Hành động này không thể hoàn tác.")) {
      onDelete(id);
    }
  };

  const handleEditClick = (e: React.MouseEvent, entry: Reflection) => {
    e.stopPropagation();
    onEdit(entry);
  };

  // Helper to format date
  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("vi-VN", {
      weekday: "long",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className={`${styles.container} animate-fade-in`}>
      {/* Search & Filters */}
      <div className={`glass-card ${styles.filterCard}`}>
        <div className={styles.searchRow}>
          <div className={styles.searchIconWrapper}>
            <Search size={18} className={styles.searchIcon} />
            <input
              type="text"
              className={`input-field ${styles.searchInput}`}
              placeholder="Tìm kiếm theo tiêu đề, nội dung hoặc thẻ..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.filterRow}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "hsl(var(--text-muted))" }}>
            <Filter size={16} />
            <span style={{ fontSize: "14px", fontWeight: "500" }}>Bộ lọc:</span>
          </div>

          {/* Mood filter */}
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Tâm trạng</label>
            <select
              className={styles.selectField}
              value={selectedMood}
              onChange={(e) => setSelectedMood(e.target.value)}
            >
              <option value="all">Tất cả tâm trạng</option>
              {MOODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.emoji} {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Tag filter */}
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Thẻ phân loại</label>
            <select
              className={styles.selectField}
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
            >
              <option value="all">Tất cả thẻ</option>
              {allTags.map((tag) => (
                <option key={tag} value={tag}>
                  #{tag}
                </option>
              ))}
            </select>
          </div>

          {/* Reset button */}
          {(searchQuery || selectedMood !== "all" || selectedTag !== "all") && (
            <button
              className="btn btn-secondary"
              style={{ padding: "8px 14px", alignSelf: "flex-end" }}
              onClick={() => {
                setSearchQuery("");
                setSelectedMood("all");
                setSelectedTag("all");
              }}
            >
              Xóa bộ lọc
            </button>
          )}
        </div>
      </div>

      {/* Timeline List */}
      {filteredReflections.length > 0 ? (
        <div className={styles.timelineWrapper}>
          <div className={styles.timelineLine} />

          {filteredReflections.map((entry) => {
            const moodObj = MOODS.find((m) => m.value === entry.mood);
            const isExpanded = !!expandedEntries[entry.id];

            return (
              <div key={entry.id} className={styles.timelineItem}>
                {/* Dot marker on line */}
                <div
                  className={styles.timelineDot}
                  style={{
                    borderColor: moodObj?.color || "hsl(var(--primary))",
                    boxShadow: `0 0 10px ${moodObj?.color}40`,
                  }}
                >
                  {moodObj?.emoji || "📝"}
                </div>

                {/* Entry Card */}
                <div
                  className={`glass-card ${styles.entryCard}`}
                  onClick={() => toggleExpand(entry.id)}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.headerLeft}>
                      <span className={styles.dateText}>
                        <Calendar size={12} style={{ display: "inline", marginRight: "4px", verticalAlign: "middle" }} />
                        {formatDate(entry.createdAt)}
                      </span>
                      <h3 className={styles.entryTitle}>{entry.title}</h3>
                    </div>

                    <div className={styles.headerRight}>
                      {entry.moodNote && (
                        <span className={styles.moodNote} title={entry.moodNote}>
                          {entry.moodNote}
                        </span>
                      )}
                      <span
                        className={styles.moodBadge}
                        style={{
                          backgroundColor: `${moodObj?.color}15`,
                          color: moodObj?.color,
                          borderColor: `${moodObj?.color}30`,
                        }}
                      >
                        {moodObj?.emoji} {moodObj?.label}
                      </span>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className={`${styles.entryContent} ${!isExpanded ? styles.collapsedContent : ""}`}>
                    {entry.content}
                  </div>

                  {/* Expand/Collapse text trigger */}
                  <div className={styles.expandText}>
                    {isExpanded ? (
                      <>
                        <ChevronUp size={14} /> Thu gọn bài viết
                      </>
                    ) : (
                      <>
                        <ChevronDown size={14} /> Xem đầy đủ bài viết
                      </>
                    )}
                  </div>

                  {/* Card Footer with Tags & Action buttons */}
                  <div className={styles.cardFooter}>
                    <div className={styles.tagGroup}>
                      {entry.tags && entry.tags.map((tag) => (
                        <span key={tag} className={styles.tagMiniBadge}>
                          #{tag}
                        </span>
                      ))}
                    </div>

                    <div className={styles.actionButtons}>
                      <button
                        className={`${styles.iconBtn} ${styles.editBtn}`}
                        onClick={(e) => handleEditClick(e, entry)}
                        title="Chỉnh sửa bài viết"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        className={`${styles.iconBtn} ${styles.deleteBtn}`}
                        onClick={(e) => handleDeleteClick(e, entry.id)}
                        title="Xóa bài viết"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Empty State */
        <div className={`glass-card ${styles.emptyState}`}>
          <AlertCircle size={48} className={styles.emptyIcon} />
          <h3 style={{ fontSize: "18px", color: "hsl(var(--text-secondary))" }}>
            Không tìm thấy bài viết nào
          </h3>
          <p style={{ fontSize: "14px", color: "hsl(var(--text-muted))" }}>
            Hãy thử thay đổi từ khóa tìm kiếm hoặc điều chỉnh lại bộ lọc tâm trạng / thẻ phân loại.
          </p>
        </div>
      )}
    </div>
  );
}
