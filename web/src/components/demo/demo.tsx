"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AnalyzeResult, Sample } from "@/lib/types";
import { SampleList } from "./sample-list";
import { UploadZone } from "./upload-zone";
import { Pipeline } from "./pipeline";
import { Results } from "./results";

type Phase =
  | { name: "idle" }
  | { name: "running"; file: File; result: AnalyzeResult | null; error: string | null }
  | { name: "done"; file: File; result: AnalyzeResult };

export function Demo() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [phase, setPhase] = useState<Phase>({ name: "idle" });

  useEffect(() => {
    fetch("/api/samples")
      .then((r) => (r.ok ? r.json() : []))
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  const analyze = useCallback(async (file: File) => {
    setPhase({ name: "running", file, result: null, error: null });
    document.getElementById("demo")?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/analyze", { method: "POST", body });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail ?? `The server answered with status ${response.status}`);
      }
      const result: AnalyzeResult = await response.json();
      setPhase((p) => (p.name === "running" && p.file === file ? { ...p, result } : p));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setPhase((p) => (p.name === "running" && p.file === file ? { ...p, error: message } : p));
    }
  }, []);

  const finish = useCallback(() => {
    setPhase((p) => (p.name === "running" && p.result ? { name: "done", file: p.file, result: p.result } : p));
    document.getElementById("demo")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const reset = () => setPhase({ name: "idle" });

  return (
    <section id="demo" className="scroll-mt-20">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Demo</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {phase.name === "idle"
              ? "A. Download a sample PDF. B. Upload it below, one file at a time."
              : phase.name === "running"
                ? "Processing the document"
                : "Analysis complete"}
          </p>
        </div>
        {phase.name !== "idle" && (
          <Button variant="outline" size="sm" onClick={reset}>
            <RotateCcw /> Analyze another document
          </Button>
        )}
      </div>

      <AnimatePresence mode="wait">
        {phase.name === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="grid gap-6 lg:grid-cols-[1.35fr_1fr]"
          >
            <SampleList samples={samples} onAnalyze={analyze} />
            <UploadZone onFile={analyze} />
          </motion.div>
        )}
        {phase.name === "running" && (
          <motion.div key="running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Pipeline file={phase.file} result={phase.result} error={phase.error} onDone={finish} onRetry={reset} />
          </motion.div>
        )}
        {phase.name === "done" && (
          <motion.div key="done" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Results result={phase.result} />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
