"use client";

import { useEffect, useMemo, useState } from "react";
import { animate, motion } from "motion/react";
import { ArrowRight, Check, FileText, Server, TreePine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  crimeName,
  featureName,
  formatMonths,
  formatSlot,
  isMissing,
  SECTION_NAMES,
  SLOT_LABELS,
} from "@/lib/labels";
import type { AnalyzeResult } from "@/lib/types";
import { cn } from "@/lib/utils";

/* ---------- helpers ---------- */

export function useCountUp(target: number, duration = 1.1, delay = 0) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    const controls = animate(0, target, {
      duration,
      delay,
      ease: "easeOut",
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [target, duration, delay]);
  return value;
}

function Count({ to, digits = 0, delay = 0, duration = 1.1 }: { to: number; digits?: number; delay?: number; duration?: number }) {
  const v = useCountUp(to, duration, delay);
  return <span className="tabular-nums">{v.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits })}</span>;
}

function useAfter(ms: number) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setOn(true), ms);
    return () => clearTimeout(id);
  }, [ms]);
  return on;
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-background px-3 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{children}</p>
    </div>
  );
}

/* ---------- 1. upload ---------- */

export function UploadStage({ file, ready }: { file: File; ready: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 pt-10">
      <div className="flex items-center gap-6">
        <span className="flex size-14 items-center justify-center rounded-xl border bg-background">
          <FileText className="size-6" />
        </span>
        <div className="relative h-px w-40 bg-border">
          <motion.span
            className="absolute -top-1 size-2 rounded-full bg-accent-brand"
            animate={{ left: ["0%", "100%"] }}
            transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        <span className="flex size-14 items-center justify-center rounded-xl border bg-background">
          <Server className="size-6" />
        </span>
      </div>
      <p className="text-sm text-muted-foreground">
        {file.name} · {(file.size / 1024).toFixed(0)} KB · {ready ? "received" : "sending"}
      </p>
    </div>
  );
}

/* ---------- 2. extract ---------- */

export function ExtractStage({ result }: { result: AnalyzeResult }) {
  const { extraction } = result;
  const lines = useMemo(
    () => extraction.text.split("\r\n").filter((l) => l.trim()).slice(6, 20),
    [extraction.text],
  );
  const page = useCountUp(extraction.pages, 1.3);
  const showMatch = useAfter(1300);

  return (
    <div className="grid gap-5 lg:grid-cols-[150px_1fr]">
      <div className="flex flex-col items-center gap-3">
        <div className="relative h-40 w-28">
          {[2, 1, 0].map((offset) => (
            <motion.div
              key={offset}
              className="absolute inset-0 rounded-md border bg-background shadow-xs"
              initial={{ x: 0, y: 0 }}
              animate={{ x: offset * 6, y: offset * 6 }}
              transition={{ delay: 0.1 * offset }}
            >
              {offset === 0 && (
                <div className="space-y-1.5 p-3">
                  {Array.from({ length: 11 }).map((_, i) => (
                    <motion.div
                      key={i}
                      className="h-1 rounded-full bg-muted-foreground/30"
                      style={{ width: `${55 + ((i * 37) % 40)}%` }}
                      initial={{ opacity: 0.2 }}
                      animate={{ opacity: [0.2, 1, 0.35] }}
                      transition={{ delay: i * 0.08, duration: 0.6, repeat: Infinity, repeatDelay: 0.6 }}
                    />
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          page {Math.max(1, Math.round(page))} of {extraction.pages}
        </p>
      </div>
      <div className="min-w-0 space-y-3">
        <div className="h-56 overflow-hidden rounded-lg border bg-muted/40 p-3 font-mono text-[11px] leading-[1.55]">
          {lines.map((line, i) => (
            <motion.p
              key={i}
              className="truncate whitespace-pre"
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.07 }}
            >
              {line}
            </motion.p>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Lines"><Count to={extraction.lines} /></Stat>
          <Stat label="Characters"><Count to={extraction.chars} /></Stat>
          <Stat label="Words"><Count to={extraction.words} /></Stat>
        </div>
        {showMatch && <MatchBadge result={result} />}
      </div>
    </div>
  );
}

export function MatchBadge({ result }: { result: AnalyzeResult }) {
  const m = result.extraction.match;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
        m.exact ? "border-success/40 bg-success/5" : "bg-muted/40",
      )}
    >
      {m.exact ? <Check className="size-4 text-success" /> : <FileText className="size-4 text-muted-foreground" />}
      {m.exact === true && <span>Byte for byte identical to the source txt</span>}
      {m.exact === false && <span>Differs from the source txt</span>}
      {m.exact === null && <span>Source txt not available for comparison</span>}
      <span className="ml-auto font-mono text-[11px] text-muted-foreground">sha256 {result.extraction.sha256.slice(0, 12)}</span>
    </motion.div>
  );
}

/* ---------- 3. preprocess ---------- */

function Strike({ text, delay }: { text: string; delay: number }) {
  return (
    <span className="relative inline-block">
      <motion.span initial={{ opacity: 1 }} animate={{ opacity: 0.35 }} transition={{ delay: delay + 0.45 }}>
        {text}
      </motion.span>
      <motion.span
        className="absolute top-1/2 left-0 h-px bg-removed"
        initial={{ width: "0%" }}
        animate={{ width: "100%" }}
        transition={{ delay, duration: 0.45 }}
      />
    </span>
  );
}

function Morph({ from, to, delay }: { from: string; to: string; delay: number }) {
  const swapped = useAfter(delay * 1000 + 500);
  return (
    <span className="relative inline-flex">
      {!swapped ? (
        <motion.span
          className="rounded bg-removed/10 px-1 text-removed"
          initial={{ opacity: 0.6 }}
          animate={{ opacity: 1 }}
          transition={{ delay }}
        >
          {from}
        </motion.span>
      ) : (
        <motion.span
          className="rounded bg-accent-brand-soft px-1 font-mono text-accent-brand"
          initial={{ opacity: 0, scale: 0.85, rotateX: 90 }}
          animate={{ opacity: 1, scale: 1, rotateX: 0 }}
        >
          {to}
        </motion.span>
      )}
    </span>
  );
}

function Row({ n, title, note, delay, children }: { n: string; title: string; note: string; delay: number; children: React.ReactNode }) {
  return (
    <motion.div
      className="rounded-lg border p-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-medium">
          <span className="mr-2 font-mono text-xs text-muted-foreground">{n}</span>
          {title}
        </p>
        <span className="text-xs text-muted-foreground">{note}</span>
      </div>
      <div className="font-mono text-xs leading-relaxed">{children}</div>
    </motion.div>
  );
}

export function PreprocessStage({ result }: { result: AnalyzeResult }) {
  const s = result.task1.steps;
  const citation = s.citations.example;
  const nameExample = s.names.example;
  const name = nameExample?.match;
  let snippet: [string, string] | null = null;
  if (citation) {
    const at = citation.before.indexOf(citation.match);
    const left = citation.before.slice(Math.max(0, at - 42), at);
    const right = citation.before.slice(at + citation.match.length, at + citation.match.length + 22);
    snippet = [left, right];
  }
  return (
    <div className="space-y-3">
      <Row n="A" title="Remove page noise" note="watermark, header, disclaimer, page marks" delay={0}>
        <div className="space-y-0.5">
          {s.clean.removed_lines.slice(0, 3).map((line, i) => (
            <div key={i}>
              <Strike text={line} delay={0.25 + i * 0.18} />
            </div>
          ))}
        </div>
      </Row>
      {citation && snippet && (
        <Row n="B" title="Mask legal citations" note={`${s.citations.count} citations`} delay={0.7}>
          <span className="text-muted-foreground">…{snippet[0]}</span>
          <Morph from={citation.match} to="[PASAL]" delay={1.0} />
          <span className="text-muted-foreground">{snippet[1]}…</span>
        </Row>
      )}
      {name && (
        <Row n="C" title="Pseudonymize names" note={`${s.names.count} mentions`} delay={1.35}>
          <span className="text-muted-foreground">…{nameExample?.left}</span>
          <Morph from={name} to="[NAMA]" delay={1.6} />
          <span className="text-muted-foreground">{nameExample?.right}…</span>
        </Row>
      )}
      <motion.div
        className="flex items-center gap-3 text-xs text-muted-foreground"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.0 }}
      >
        <span className="font-mono">{s.clean.raw_chars.toLocaleString("en-US")} chars</span>
        <ArrowRight className="size-3.5" />
        <span className="font-mono text-foreground">{s.view.chars.toLocaleString("en-US")} chars</span>
        <span>model input view, verdict section cut</span>
      </motion.div>
    </div>
  );
}

/* ---------- 4. tf-idf ---------- */

export function TfidfStage({ result }: { result: AnalyzeResult }) {
  const t = result.task1.steps.tfidf;
  const max = Math.max(...t.top_words.map((w) => w.weight));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Word 1 to 2 grams used">
          <Count to={t.word_features} /> <span className="text-muted-foreground">of {t.vocabulary.word.toLocaleString("en-US")}</span>
        </Stat>
        <Stat label="Character 3 to 5 grams used">
          <Count to={t.char_features} /> <span className="text-muted-foreground">of {t.vocabulary.char.toLocaleString("en-US")}</span>
        </Stat>
      </div>
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground">Highest weighted word n-grams in this document</p>
        {t.top_words.slice(0, 8).map((w, i) => (
          <div key={w.term} className="grid grid-cols-[150px_1fr_48px] items-center gap-3 text-xs">
            <span className="truncate font-mono">{w.term}</span>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-foreground/80"
                initial={{ width: 0 }}
                animate={{ width: `${(w.weight / max) * 100}%` }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <span className="text-right font-mono text-muted-foreground tabular-nums">{w.weight.toFixed(3)}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground">
        <span className="font-mono">weight = (1 + log tf) × idf</span>, then L2 normalised. Rare words such as place
        names get a high idf, so they rank high here even when they say little about the crime.
      </p>
    </div>
  );
}

/* ---------- 5. svm ---------- */

export function SvmStage({ result }: { result: AnalyzeResult }) {
  const t = result.task1;
  const scores = t.steps.svm.scores.slice(0, 6);
  const lo = Math.min(...scores.map((s) => s.margin));
  const hi = Math.max(...scores.map((s) => s.margin));
  const revealed = useAfter(900);
  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground">SVM margin per crime type, higher is more likely</p>
        {scores.map((s, i) => (
          <div key={s.label} className="grid grid-cols-[170px_1fr_56px] items-center gap-3 text-xs">
            <span className={cn("truncate", i === 0 && revealed && "font-medium")}>{crimeName(s.label)}</span>
            <div className="h-2.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn("h-full rounded-full", i === 0 && revealed ? "bg-accent-brand" : "bg-muted-foreground/40")}
                initial={{ width: 0 }}
                animate={{ width: `${8 + ((s.margin - lo) / (hi - lo || 1)) * 92}%` }}
                transition={{ delay: 0.1 + i * 0.06, duration: 0.55 }}
              />
            </div>
            <span className="text-right font-mono text-muted-foreground tabular-nums">
              {s.margin > 0 ? "+" : ""}
              {s.margin.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
      {revealed && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg border p-3">
          <p className="text-xs text-muted-foreground">Words that pushed the score toward {crimeName(t.label)}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {t.steps.svm.evidence.map((e, i) => (
              <motion.span
                key={e.term}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
              >
                <Badge variant="outline" className="font-mono">{e.term}</Badge>
              </motion.span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

/* ---------- 6. sections and tagging ---------- */

export function SectionsStage({ result }: { result: AnalyzeResult }) {
  const t = result.task2;
  const total = t.sections.reduce((a, s) => a + s.paragraphs, 0) || 1;
  const spans = t.bert?.spans ?? {};
  const pick = ["DEMAND", "AGE", "ARTICLE", "INJURY", "LOSS", "VICTIM"].find((k) => spans[k]?.length);
  const words = pick ? spans[pick][0].split(/\s+/).filter(Boolean).slice(0, 9) : [];
  const showBert = useAfter(1050);

  return (
    <div className="space-y-5">
      <div>
        <p className="mb-2 text-xs text-muted-foreground">
          {t.paragraphs} paragraphs split into {t.sections.length} sections
        </p>
        <div className="flex h-7 overflow-hidden rounded-md border">
          {t.sections.map((s, i) => (
            <motion.div
              key={s.name}
              className={cn("h-full border-r last:border-r-0", i % 2 ? "bg-muted" : "bg-muted-foreground/15")}
              initial={{ width: 0 }}
              animate={{ width: `${(s.paragraphs / total) * 100}%` }}
              transition={{ delay: i * 0.08, duration: 0.35 }}
            />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {t.sections.map((s, i) => (
            <motion.span
              key={s.name}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.08 }}
            >
              <Badge variant="secondary">
                {SECTION_NAMES[s.name] ?? s.name} <span className="font-mono text-muted-foreground">{s.paragraphs}</span>
              </Badge>
            </motion.span>
          ))}
        </div>
      </div>

      {showBert && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg border p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium">IndoBERT BIO tagger</p>
            <span className="text-xs text-muted-foreground">
              {t.bert?.skipped
                ? "skipped for this crime type"
                : `${t.bert?.windows ?? 0} windows of 256 tokens over a ${(t.bert?.excerpt_chars ?? 0).toLocaleString("en-US")} char excerpt`}
            </span>
          </div>
          {pick ? (
            <div className="mt-4 flex flex-wrap gap-x-1.5 gap-y-3">
              {words.map((w, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <motion.span
                    className="rounded bg-accent-brand-soft px-1.5 py-0.5 font-mono text-xs text-accent-brand"
                    initial={{ backgroundColor: "rgba(0,0,0,0)" }}
                    animate={{ backgroundColor: "var(--accent-brand-soft)" }}
                    transition={{ delay: 0.2 + i * 0.08 }}
                  >
                    {w}
                  </motion.span>
                  <motion.span
                    className="font-mono text-[10px] text-muted-foreground"
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + i * 0.08 }}
                  >
                    {i === 0 ? "B" : "I"}-{pick}
                  </motion.span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              {t.bert?.skipped ? "Victim slots do not apply, the rules fill every slot." : "No span was tagged."}
            </p>
          )}
        </motion.div>
      )}
    </div>
  );
}

/* ---------- 7. slots ---------- */

export function SlotsStage({ result }: { result: AnalyzeResult }) {
  const t = result.task2;
  const slots = Object.keys(SLOT_LABELS);
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {slots.map((slot, i) => {
        const value = t.record[slot];
        const route = t.route[slot];
        return (
          <motion.div
            key={slot}
            className="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.09 }}
          >
            <div className="min-w-0">
              <p className="text-[11px] text-muted-foreground">{SLOT_LABELS[slot]}</p>
              <motion.p
                className={cn("truncate text-sm", isMissing(value) ? "text-muted-foreground" : "font-medium")}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.09 + 0.2 }}
              >
                {Array.isArray(value) ? `${value.length} code${value.length === 1 ? "" : "s"}` : formatSlot(slot, value)}
              </motion.p>
            </div>
            <Badge variant={route === "bert" ? "default" : "outline"} className="shrink-0">
              {route === "bert" ? "IndoBERT" : route === "rule" ? "Rule" : "n/a"}
            </Badge>
          </motion.div>
        );
      })}
    </div>
  );
}

/* ---------- 8. sentence ---------- */

export function SentenceStage({ result }: { result: AnalyzeResult }) {
  const t3 = result.task3;
  const keys = ["crime_type", "demand_any", "age", "n_aggravating", "n_mitigating", "n_articles"];
  const feats = t3.features.filter((f) => keys.includes(f.feature));
  const showModel = useAfter(800);
  const showOut = useAfter(1300);
  const months = useCountUp(showOut ? t3.live.months : 0, 0.8);

  return (
    <div className="grid items-center gap-4 lg:grid-cols-[1fr_auto_150px_auto_1fr]">
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground">{t3.n_features} features, key ones shown</p>
        {feats.map((f, i) => (
          <motion.div
            key={f.feature}
            className="flex items-center justify-between gap-3 rounded-md border px-2.5 py-1.5 text-xs"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <span className="text-muted-foreground">{featureName(f.feature)}</span>
            <span className="font-mono">
              {f.value === null ? "missing" : f.feature === "crime_type" ? crimeName(String(f.value)) : f.value}
            </span>
          </motion.div>
        ))}
      </div>
      <ArrowRight className="mx-auto size-4 text-muted-foreground" />
      <motion.div
        className="flex flex-col items-center gap-2 rounded-xl border p-4 text-center"
        initial={{ opacity: 0.3 }}
        animate={{ opacity: showModel ? 1 : 0.3 }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              animate={showModel ? { y: [0, -3, 0] } : {}}
              transition={{ delay: i * 0.12, duration: 0.5, repeat: showModel && !showOut ? Infinity : 0 }}
            >
              <TreePine className="size-5" />
            </motion.span>
          ))}
        </div>
        <p className="text-xs font-medium">LightGBM S2</p>
        <p className="text-[11px] text-muted-foreground">1,500 trees</p>
      </motion.div>
      <ArrowRight className="mx-auto size-4 text-muted-foreground" />
      <div className="rounded-xl border p-4 text-center">
        <p className="text-xs text-muted-foreground">Live prediction</p>
        <p className="mt-1 font-mono text-3xl font-semibold tabular-nums">{months.toFixed(1)}</p>
        <p className="text-xs text-muted-foreground">months</p>
        {showOut && t3.champion?.months != null && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="mt-3 border-t pt-2 text-xs text-muted-foreground"
          >
            Champion H4 {formatMonths(t3.champion.months)}
          </motion.p>
        )}
      </div>
    </div>
  );
}
