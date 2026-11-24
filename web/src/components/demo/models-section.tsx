"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SLOT_LABELS } from "@/lib/labels";
import type { ModelsInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

const BLOCK_NAMES: Record<string, string> = { R: "Reference", T: "Text TF-IDF", A: "Text neural", S: "Structured", H: "Hybrid" };

export function ModelsSection() {
  const [info, setInfo] = useState<ModelsInfo | null>(null);
  useEffect(() => {
    fetch("/api/models")
      .then((r) => (r.ok ? r.json() : null))
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  return (
    <section id="models" className="scroll-mt-20 pt-20">
      <h2 className="text-2xl font-semibold tracking-tight">Models</h2>
      <p className="mt-1 text-sm text-muted-foreground">Scores on the held out test split, read from the exported artifacts.</p>
      {!info ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-72 rounded-xl" />)}
        </div>
      ) : (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <Task1Card info={info} />
          <Task2Card info={info} />
          <Task3Card info={info} />
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="font-mono text-lg font-semibold">{value}</p>
    </div>
  );
}

function Task1Card({ info }: { info: ModelsInfo }) {
  const m = info.task1.metrics.test;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Task 1 · Crime classification</CardTitle>
        <CardDescription>{info.task1.model.replaceAll("_", " ")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Macro F1" value={m.macro_f1.toFixed(3)} />
          <Metric label="Accuracy" value={m.accuracy.toFixed(3)} />
          <Metric label="Macro precision" value={m.macro_precision.toFixed(3)} />
          <Metric label="Macro recall" value={m.macro_recall.toFixed(3)} />
        </div>
        <ul className="space-y-1 text-xs text-muted-foreground">
          <li>A. {info.task1.classes} crime types</li>
          <li>B. {info.task1.features.word.toLocaleString("en-US")} word and {info.task1.features.char.toLocaleString("en-US")} character n-grams</li>
          <li>C. Trained on {info.task1.train_documents.toLocaleString("en-US")} decisions</li>
        </ul>
      </CardContent>
    </Card>
  );
}

function Task2Card({ info }: { info: ModelsInfo }) {
  const scores = Object.entries(info.task2.test_scores);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Task 2 · Information extraction</CardTitle>
        <CardDescription>Route selector over rules and IndoBERT, test score per slot</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {scores.map(([slot, score], i) => (
          <div key={slot} className="grid grid-cols-[130px_1fr_40px] items-center gap-2 text-xs">
            <span className="truncate text-muted-foreground">{SLOT_LABELS[slot]}</span>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn("h-full rounded-full", info.task2.selector.bert.includes(slot) ? "bg-accent-brand" : "bg-foreground/70")}
                initial={{ width: 0 }}
                whileInView={{ width: `${score}%` }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.03, duration: 0.5 }}
              />
            </div>
            <span className="text-right font-mono">{score.toFixed(0)}</span>
          </div>
        ))}
        <p className="pt-2 text-xs text-muted-foreground">
          Blue slots come from IndoBERT. Factor slots use micro F1, the others exact match.
        </p>
      </CardContent>
    </Card>
  );
}

function Task3Card({ info }: { info: ModelsInfo }) {
  const t = info.task3.summary.test;
  // The notebook picks the best model of each block on validation, then reports its test score.
  const best = new Map<string, { experiment: string; test_mae: number; val_mae: number }>();
  for (const row of info.task3.leaderboard) {
    const prev = best.get(row.block);
    if (!prev || row.val_mae < prev.val_mae) best.set(row.block, row);
  }
  const rows = [...best.entries()].sort((a, b) => a[1].test_mae - b[1].test_mae);
  const max = Math.max(...rows.map(([, r]) => r.test_mae));
  return (
    <Card>
      <CardHeader>
        <CardTitle>Task 3 · Sentence prediction</CardTitle>
        <CardDescription>Champion {info.task3.summary.champion.replaceAll("_", " ")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Test MAE (months)" value={t.test_mae.toFixed(2)} />
          <Metric label="Test R²" value={t.test_r2.toFixed(3)} />
        </div>
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">
            Test MAE of the best model per block, chosen on validation, lower is better
          </p>
          {rows.map(([block, r], i) => (
            <div key={block} className="grid grid-cols-[90px_1fr_40px] items-center gap-2 text-xs">
              <span className="text-muted-foreground">{BLOCK_NAMES[block] ?? block}</span>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className={cn("h-full rounded-full", block === "H" ? "bg-accent-brand" : "bg-foreground/60")}
                  initial={{ width: 0 }}
                  whileInView={{ width: `${(r.test_mae / max) * 100}%` }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.5 }}
                />
              </div>
              <span className="text-right font-mono">{r.test_mae.toFixed(1)}</span>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {info.task3.blend.map((b) => (
            <Badge key={b.model} variant="outline" className="font-mono text-[10px]">
              {b.model.split("_")[0]} {(b.weight * 100).toFixed(0)}%
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
