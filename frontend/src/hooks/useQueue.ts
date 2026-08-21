import { useCallback, useEffect, useState } from "react";
import { getQueue } from "../api/client";
import type { QueueItem } from "../api/types";
import seed from "../mocks/queue.json";

const LIVE = new Set(["queued", "running", "needs_review", "error"]);

export function useQueue() {
  const [items, setItems] = useState<QueueItem[]>(() =>
    (seed as QueueItem[]).filter((i) => LIVE.has(i.status)),
  );
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const rows = await getQueue();
      setItems(rows);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No cuadra");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { items, error, refresh };
}
