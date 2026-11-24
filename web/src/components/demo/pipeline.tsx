"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, Check, FastForward, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AnalyzeResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  ExtractStage,
  PreprocessStage,
  SectionsStage,
  SentenceStage,
  SlotsStage,
  SvmStage,
  TfidfStage,
  UploadStage,
} from "./stages";

const STEPS = [
  { key: "upload", group: "Input", title: "Upload", detail: "Send the PDF to the server", ms: 900 },
  { key: "extract", group: "Input", title: "Extract text", detail: "Read the text layer page by page", ms: 1900 },
  { key: "clean", group: "Task 1", title: "Preprocess", detail: "Remove noise, mask citations and names", ms: 2700 },
  { key: "tfidf", group: "Task 1", title: "TF-IDF features", detail: "Weight word and character n-grams", ms: 1700 },
  { key: "svm", group: "Task 1", title: "Linear SVM", detail: "Score 18 crime types", ms: 1700 },
  { key: "sections", group: "Task 2", title: "Sections and tagging", detail: "Split the decision, run IndoBERT", ms: 2300 },
  { key: "slots", group: "Task 2", title: "Fill factor slots", detail: "Rules and tagger fill 14 slots", ms: 2000 },
  { key: "sentence", group: "Task 3", title: "Predict sentence", detail: "LightGBM on the case facts", ms: 2300 },
] as const;

type Props = {
  file: File;
  result: AnalyzeResult | null;
  error: string | null;
  onDone: () => void;
  onRetry: () => void;
};

export function Pipeline({ file, result, error, onDone, onRetry }: Props) {
  const [index, setIndex] = useState(0);
  const step = STEPS[index];

  useEffect(() => {
    if (error) return;
    if (index === 0 && !result) return;
    const id = setTimeout(() => {
      if (index === STEPS.length - 1) onDone();
      else setIndex((i) => i + 1);
    }, step.ms);
    return () => clearTimeout(id);
  }, [index, result, error, step.ms, onDone]);

  const progress = useMemo(() => Math.round(((index + (result ? 0.5 : 0.2)) / STEPS.length) * 100), [index, result]);

  if (error) {
    return (
      <Card className="items-center gap-3 py-12 text-center">
        <span className="flex size-11 items-center justify-center rounded-full border text-removed">
          <AlertTriangle className="size-5" />
        </span>
        <p className="font-medium">The document could not be processed</p>
        <p className="max-w-md text-sm text-muted-foreground">{error}</p>
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          Try another file
        </Button>
      </Card>
    );
  }

  return (
    <Card className="gap-0 py-0">
      <div className="flex items-center gap-4 border-b px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="shrink-0 font-mono text-xs text-muted-foreground tabular-nums">{progress}%</p>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-accent-brand"
              initial={{ width: "0%" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onDone} disabled={!result}>
          <FastForward /> Skip animation
        </Button>
      </div>

      <div className="grid md:grid-cols-[250px_1fr]">
        <ol className="border-b p-4 md:border-r md:border-b-0">
          {STEPS.map((s, i) => {
            const state = i < index ? "done" : i === index ? "active" : "pending";
            const showGroup = i === 0 || STEPS[i - 1].group !== s.group;
            return (
              <li key={s.key}>
                {showGroup && (
                  <p
                    className={cn(
                      "mb-1.5 px-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase",
                      i > 0 && "mt-4",
                    )}
                  >
                    {s.group}
                  </p>
                )}
                <div
                  className={cn(
                    "flex items-start gap-3 rounded-md px-2 py-1.5 transition-colors",
                    state === "active" && "bg-muted",
                  )}
                >
                  <span
                    className={cn(
                      "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
                      state === "done" && "border-foreground bg-foreground text-background",
                      state === "active" && "border-accent-brand text-accent-brand",
                      state === "pending" && "text-muted-foreground",
                    )}
                  >
                    {state === "done" ? (
                      <Check className="size-3" />
                    ) : state === "active" ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      i + 1
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className={cn("text-sm", state === "pending" ? "text-muted-foreground" : "font-medium")}>
                      {s.title}
                    </p>
                    {state === "active" && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="text-xs text-muted-foreground"
                      >
                        {s.detail}
                      </motion.p>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        <div className="relative min-h-[430px] overflow-hidden p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={step.key}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.25 }}
              className="h-full"
            >
              <StageHeader group={step.group} title={step.title} />
              {step.key === "upload" && <UploadStage file={file} ready={!!result} />}
              {result && step.key === "extract" && <ExtractStage result={result} />}
              {result && step.key === "clean" && <PreprocessStage result={result} />}
              {result && step.key === "tfidf" && <TfidfStage result={result} />}
              {result && step.key === "svm" && <SvmStage result={result} />}
              {result && step.key === "sections" && <SectionsStage result={result} />}
              {result && step.key === "slots" && <SlotsStage result={result} />}
              {result && step.key === "sentence" && <SentenceStage result={result} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </Card>
  );
}

function StageHeader({ group, title }: { group: string; title: string }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-medium text-accent-brand">{group}</p>
      <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
    </div>
  );
}
