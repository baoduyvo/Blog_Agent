export interface Reflection {
  id: string;
  title: string;
  content: string;
  mood: number; // 1 to 5
  moodNote?: string;
  tags: string[];
  createdAt: string; // ISO Date String
  updatedAt: string; // ISO Date String
}

export const MOODS = [
  { value: 1, emoji: "😢", label: "Tồi tệ", color: "#f43f5e" },
  { value: 2, emoji: "😕", label: "Bất ổn", color: "#f97316" },
  { value: 3, emoji: "😐", label: "Bình thường", color: "#eab308" },
  { value: 4, emoji: "🙂", label: "Tốt", color: "#3b82f6" },
  { value: 5, emoji: "😁", label: "Tuyệt vời", color: "#10b981" },
];

export const REFLECTION_PROMPTS = [
  "Hôm nay điều gì làm bạn cảm thấy biết ơn nhất?",
  "Bạn đã vượt qua khó khăn nào trong ngày và học được gì từ nó?",
  "Hôm nay bạn đã chăm sóc bản thân (thể chất/tinh thần) như thế nào?",
  "Có quyết định hay hành động nào hôm nay bạn muốn thay đổi nếu được làm lại?",
  "Hãy tả lại một khoảnh khắc yên bình hoặc hạnh phúc nhất trong ngày hôm nay.",
  "Bạn đã tiến gần hơn đến mục tiêu dài hạn của mình như thế nào trong hôm nay?",
];

const STORAGE_KEY = "self_reflection_entries";

export const getReflections = (): Reflection[] => {
  if (typeof window === "undefined") return [];
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return [];
    const parsed = JSON.parse(data);
    return Array.isArray(parsed) ? parsed.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()) : [];
  } catch (error) {
    console.error("Error reading reflections from localStorage:", error);
    return [];
  }
};

export const saveReflection = (entry: Omit<Reflection, "id" | "createdAt" | "updatedAt"> & { id?: string; createdAt?: string }): Reflection => {
  const reflections = getReflections();
  const now = new Date().toISOString();
  
  let updatedEntry: Reflection;
  
  if (entry.id) {
    // Edit mode
    const index = reflections.findIndex(r => r.id === entry.id);
    if (index !== -1) {
      const existing = reflections[index];
      updatedEntry = {
        ...existing,
        ...entry,
        id: entry.id,
        createdAt: entry.createdAt || existing.createdAt,
        updatedAt: now
      };
      reflections[index] = updatedEntry;
    } else {
      // Fallback if ID not found
      updatedEntry = {
        id: Math.random().toString(36).substring(2, 9),
        title: entry.title || "Chưa đặt tiêu đề",
        content: entry.content || "",
        mood: entry.mood,
        moodNote: entry.moodNote || "",
        tags: entry.tags || [],
        createdAt: entry.createdAt || now,
        updatedAt: now
      };
      reflections.push(updatedEntry);
    }
  } else {
    // Create new
    updatedEntry = {
      id: Math.random().toString(36).substring(2, 9),
      title: entry.title || "Chưa đặt tiêu đề",
      content: entry.content || "",
      mood: entry.mood,
      moodNote: entry.moodNote || "",
      tags: entry.tags || [],
      createdAt: entry.createdAt || now,
      updatedAt: now
    };
    reflections.unshift(updatedEntry);
  }
  
  localStorage.setItem(STORAGE_KEY, JSON.stringify(reflections));
  return updatedEntry;
};

export const deleteReflection = (id: string): Reflection[] => {
  const reflections = getReflections();
  const filtered = reflections.filter(r => r.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  return filtered;
};

export const calculateStreak = (reflections: Reflection[]): number => {
  if (reflections.length === 0) return 0;
  
  // Extract unique dates of reflections in YYYY-MM-DD format (local time)
  const uniqueDates = new Set<string>();
  reflections.forEach(r => {
    const dateStr = new Date(r.createdAt).toLocaleDateString("sv-SE"); // sv-SE format is YYYY-MM-DD
    uniqueDates.add(dateStr);
  });
  
  const sortedDates = Array.from(uniqueDates).sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
  
  const todayStr = new Date().toLocaleDateString("sv-SE");
  const yesterdayStr = new Date(Date.now() - 86400000).toLocaleDateString("sv-SE");
  
  // If no entry today or yesterday, streak is broken (0)
  if (!uniqueDates.has(todayStr) && !uniqueDates.has(yesterdayStr)) {
    return 0;
  }
  
  let streak = 0;
  let currentDate = new Date(sortedDates[0]);
  
  // If the latest entry was yesterday and not today, start counting from yesterday
  if (!uniqueDates.has(todayStr) && uniqueDates.has(yesterdayStr)) {
    currentDate = new Date(yesterdayStr);
  }
  
  while (true) {
    const checkDateStr = currentDate.toLocaleDateString("sv-SE");
    if (uniqueDates.has(checkDateStr)) {
      streak++;
      // Move to previous day
      currentDate.setDate(currentDate.getDate() - 1);
    } else {
      break;
    }
  }
  
  return streak;
};
