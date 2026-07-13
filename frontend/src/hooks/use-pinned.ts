import { useState } from "react";

const PINNED_STORAGE_KEY = "pinned_conversation_ids";

export function usePinned() {
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(PINNED_STORAGE_KEY) ?? "[]");
    } catch {
      return [];
    }
  });

  const isPinned = (id: string) => pinnedIds.includes(id);

  const toggle = (id: string) => {
    setPinnedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id];
      localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  return { pinnedIds, isPinned, toggle };
}
