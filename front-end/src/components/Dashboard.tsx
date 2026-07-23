"use client";

import React from "react";
import { Flame, BookOpen, Heart, TrendingUp, Sparkles } from "lucide-react";
import { Reflection, MOODS, calculateStreak } from "@/utils/storage";
import styles from "./Dashboard.module.css";

interface DashboardProps {
  reflections: Reflection[];
  onStartReflection: () => void;
}

export default function Dashboard({ reflections, onStartReflection }: DashboardProps) {
  const totalEntries = reflections.length;
  const streak = calculateStreak(reflections);

  // Compute dominant mood
  const getDominantMood = () => {
    if (reflections.length === 0) return null;
    const moodCounts: Record<number, number> = {};
    reflections.forEach((r) => {
      moodCounts[r.mood] = (moodCounts[r.mood] || 0) + 1;
    });

    let dominantMoodVal = 3;
    let maxCount = 0;
    Object.entries(moodCounts).forEach(([mood, count]) => {
      if (count > maxCount) {
        maxCount = count;
        dominantMoodVal = Number(mood);
      }
    });

    return MOODS.find((m) => m.value === dominantMoodVal) || null;
  };

  const dominantMood = getDominantMood();

  // Prepare chart data (last 7 entries)
  const isMockData = reflections.length < 2;
  const chartEntries = isMockData
    ? [
        { date: "Thứ 3", mood: 3, label: "Bình thường" },
        { date: "Thứ 4", mood: 4, label: "Tốt" },
        { date: "Thứ 5", mood: 2, label: "Bất ổn" },
        { date: "Thứ 6", mood: 5, label: "Tuyệt vời" },
        { date: "Thứ 7", mood: 4, label: "Tốt" },
        { date: "Chủ Nhật", mood: 5, label: "Tuyệt vời" },
        { date: "Hôm nay", mood: 4, label: "Tốt" },
      ]
    : [...reflections]
        .slice(0, 7)
        .reverse()
        .map((r) => {
          const date = new Date(r.createdAt);
          const dateStr = `${date.getDate()}/${date.getMonth() + 1}`;
          const moodObj = MOODS.find((m) => m.value === r.mood);
          return {
            date: dateStr,
            mood: r.mood,
            label: moodObj?.label || "Bình thường",
          };
        });

  // SVG Chart parameters
  const svgWidth = 600;
  const svgHeight = 220;
  const paddingLeft = 40;
  const paddingRight = 30;
  const paddingTop = 20;
  const paddingBottom = 40;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;

  const points = chartEntries.map((entry, index) => {
    const x = paddingLeft + (index * chartWidth) / (chartEntries.length - 1);
    // Y: 5 is top (paddingTop), 1 is bottom (paddingTop + chartHeight)
    const y = paddingTop + ((5 - entry.mood) * chartHeight) / 4;
    return { x, y, ...entry };
  });

  const pathD = points.reduce(
    (acc, p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`),
    ""
  );

  const areaD =
    points.length > 0
      ? `${pathD} L ${points[points.length - 1].x} ${svgHeight - paddingBottom} L ${points[0].x} ${svgHeight - paddingBottom} Z`
      : "";

  return (
    <div className={`${styles.container} animate-fade-in`}>
      {/* Stats Cards */}
      <div className={styles.statsGrid}>
        {/* Streak */}
        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: "#f97316" }}>
            <Flame size={24} fill={streak > 0 ? "#f97316" : "none"} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{streak} ngày</span>
            <span className={styles.statLabel}>Chuỗi phản tư</span>
          </div>
        </div>

        {/* Total Reflections */}
        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: "hsl(var(--primary))" }}>
            <BookOpen size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{totalEntries} bài viết</span>
            <span className={styles.statLabel}>Tổng số phản tư</span>
          </div>
        </div>

        {/* Dominant Mood */}
        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: dominantMood ? dominantMood.color : "#3b82f6" }}>
            <Heart size={24} fill={dominantMood ? dominantMood.color : "none"} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>
              {dominantMood ? `${dominantMood.emoji} ${dominantMood.label}` : "Trống"}
            </span>
            <span className={styles.statLabel}>Tâm trạng phổ biến</span>
          </div>
        </div>
      </div>

      {/* Mood Trend Chart */}
      <div className={`glass-card ${styles.chartCard}`}>
        <div className={styles.chartHeader}>
          <div>
            <h3 className={styles.chartTitle}>
              <TrendingUp size={20} className={styles.chartTitleIcon} />
              Xu Hướng Tâm Trạng
            </h3>
            <span className={styles.chartSub}>
              {isMockData
                ? "Dữ liệu mô phỏng (Bạn cần ít nhất 2 bài nhật ký để vẽ biểu đồ thực tế)"
                : "Biểu đồ cảm xúc của 7 phiên gần nhất"}
            </span>
          </div>
        </div>

        <div className={styles.chartWrapper}>
          <svg className={styles.svgChart} viewBox={`0 0 ${svgWidth} ${svgHeight}`} width="100%" height="100%">
            <defs>
              {/* Gradients */}
              <linearGradient id="chartGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="hsl(var(--primary))" />
                <stop offset="100%" stopColor="hsl(var(--secondary))" />
              </linearGradient>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.4" />
                <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Horizontal Grid lines and Y labels */}
            {[1, 2, 3, 4, 5].map((level) => {
              const y = paddingTop + ((5 - level) * chartHeight) / 4;
              const moodObj = MOODS.find((m) => m.value === level);
              return (
                <g key={level}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={svgWidth - paddingRight}
                    y2={y}
                    className={styles.chartGridLine}
                  />
                  <text
                    x={paddingLeft - 12}
                    y={y + 4}
                    textAnchor="end"
                    className={styles.chartLabelY}
                  >
                    {moodObj ? moodObj.emoji : level}
                  </text>
                </g>
              );
            })}

            {/* Chart Area */}
            {points.length > 0 && <path d={areaD} className={styles.chartArea} />}

            {/* Chart Line */}
            {points.length > 0 && <path d={pathD} className={styles.chartLine} />}

            {/* Chart Dots & Interaction */}
            {points.map((p, i) => (
              <g key={i}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={5}
                  className={styles.chartDot}
                  style={{ "--dot-bg": MOODS.find((m) => m.value === p.mood)?.color || "hsl(var(--primary))" } as React.CSSProperties}
                  stroke={MOODS.find((m) => m.value === p.mood)?.color || "hsl(var(--primary))"}
                />
                {/* Text for dates below X axis */}
                <text
                  x={p.x}
                  y={svgHeight - paddingBottom + 20}
                  textAnchor="middle"
                  className={styles.chartLabelX}
                >
                  {p.date}
                </text>
                {/* Tooltip on hover (simple SVG title) */}
                <title>{`${p.date}: ${p.label}`}</title>
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* Daily Reflection Prompt Call to Action */}
      <div className={`glass-card ${styles.promptSuggestCard}`}>
        <div className={styles.promptSuggestText}>
          <h4 className={styles.promptSuggestTitle}>Khởi đầu ngày mới bằng việc Phản tư</h4>
          <p className={styles.promptSuggestDesc}>
            Dành ra 5 phút mỗi ngày để trò chuyện với bản thân sẽ giúp bạn cải thiện sức khỏe tinh thần, nâng cao sự tập trung và giảm bớt căng thẳng.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onStartReflection}>
          <Sparkles size={18} /> Viết Phản Tư Ngay
        </button>
      </div>
    </div>
  );
}
