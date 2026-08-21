import { useEffect, useState } from "react";
import { getEngine, getUsage, isMocked, probeLive } from "../api/client";
import type { DayUsage, Engine } from "../api/types";

export function useEngine() {
  const [engine, setEngine] = useState<Engine | null>(null);
  const [usage, setUsage] = useState<DayUsage | null>(null);
  const [live, setLive] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let on = true;
    const tick = async () => {
      const ok = await probeLive();
      if (!on) return;
      setLive(ok);
      if (!ok) {
        setEngine(null);
        setReady(true);
        return;
      }
      try {
        const [e, u] = await Promise.all([getEngine(), getUsage()]);
        if (!on) return;
        setEngine(e);
        setUsage(u);
      } catch {
        if (on) setEngine(null);
      } finally {
        if (on) setReady(true);
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 4000);
    return () => {
      on = false;
      window.clearInterval(id);
    };
  }, []);

  return { engine, usage, live, ready, mocked: isMocked() };
}
