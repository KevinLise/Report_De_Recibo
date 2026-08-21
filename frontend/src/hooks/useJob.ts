import { useEffect, useRef, useState } from "react";
import { pollJob } from "../api/client";
import type { Job, Stage } from "../api/types";
import { pulseField } from "../field/bus";

export function useJob(jobId: string | null, onDone: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const done = useRef(onDone);
  done.current = onDone;
  const lastStage = useRef<Stage | undefined>(undefined);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setError(null);
      return;
    }
    let on = true;
    setError(null);
    lastStage.current = undefined;
    void pollJob(jobId, (j) => {
      if (!on) return;
      if (j.stage && j.stage !== lastStage.current) {
        lastStage.current = j.stage;
        pulseField("stage");
      }
      setJob(j);
    })
      .then((j) => {
        if (!on) return;
        setJob(j);
        done.current(j);
      })
      .catch((e: unknown) => {
        if (on) setError(e instanceof Error ? e.message : "job");
      });
    return () => {
      on = false;
    };
  }, [jobId]);

  return { job, error };
}
