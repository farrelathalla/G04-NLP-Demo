"use client";

import { motion } from "motion/react";
import { Check, Download, Gavel, ListChecks, Scale, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  crimeName,
  FACTOR_NAMES,
  featureName,
  formatMonths,
  formatSlot,
  isMissing,
  SECTION_NAMES,
  SLOT_GROUPS,
  SLOT_LABELS,
} from "@/lib/labels";
import type { AnalyzeResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MatchBadge, useCountUp } from "./stages";

const rise = (i: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.12, duration: 0.4 },
});

export function Results({ result }: { result: AnalyzeResult }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{result.file_name}</span>
        <span>·</span>
        <span>{result.extraction.pages} pages</span>
        <span>·</span>
        <span>{result.extraction.words.toLocaleString("en-US")} words</span>
        {result.task1.split && (
          <>
            <span>·</span>
            <Badge variant="outline">{result.task1.split} split</Badge>
          </>
        )}
        <span className="ml-auto font-mono text-xs">
          processed in {Object.values(result.timings_ms).reduce((a, b) => a + b, 0).toLocaleString("en-US")} ms
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <motion.div {...rise(0)}><CrimeCard result={result} /></motion.div>
        <motion.div {...rise(1)}><FactsCard result={result} /></motion.div>
        <motion.div {...rise(2)}><SentenceCard result={result} /></motion.div>
      </div>

      <motion.div {...rise(3)}><RecordCard result={result} /></motion.div>

      <motion.div {...rise(4)}><Details result={result} /></motion.div>
    </div>
  );
}

function TaskLabel({ n, icon: Icon, title }: { n: number; icon: typeof Scale; title: string }) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
      <span className="flex size-6 items-center justify-center rounded-md border bg-background">
        <Icon className="size-3.5" />
      </span>
      Task {n} · {title}
    </div>
  );
}

function Verdict({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs", ok ? "text-success" : "text-removed")}>
      {ok ? <Check className="size-3.5" /> : <X className="size-3.5" />}
      {children}
    </span>
  );
}

/* ---------- Task 1 ---------- */

function CrimeCard({ result }: { result: AnalyzeResult }) {
  const t = result.task1;
  const [first, second] = t.steps.svm.scores;
  const lead = first.margin - second.margin;
  return (
    <Card className="h-full">
      <CardHeader>
        <TaskLabel n={1} icon={Scale} title="Crime type" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-3xl font-semibold tracking-tight">{crimeName(t.label)}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{t.label}</p>
        </div>
        {t.true_label && (
          <Verdict ok={t.true_label === t.label}>
            Label in the dataset is {crimeName(t.true_label)}
          </Verdict>
        )}
        <div className="space-y-1.5">
          {t.top.map((s, i) => (
            <div key={s.label} className="grid grid-cols-[1fr_64px] items-center gap-2 text-xs">
              <div>
                <div className="flex justify-between">
                  <span className={i === 0 ? "font-medium" : "text-muted-foreground"}>{crimeName(s.label)}</span>
                  <span className="font-mono text-muted-foreground">{(s.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    className={cn("h-full rounded-full", i === 0 ? "bg-accent-brand" : "bg-muted-foreground/40")}
                    initial={{ width: 0 }}
                    animate={{ width: `${s.confidence * 100}%` }}
                    transition={{ delay: 0.3 + i * 0.1, duration: 0.6 }}
                  />
                </div>
              </div>
              <span className="text-right font-mono text-muted-foreground">
                {s.margin > 0 ? "+" : ""}
                {s.margin.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Margin lead over the runner up is <span className="font-mono text-foreground">{lead.toFixed(2)}</span>. The
          percentage is a softmax over SVM margins, a relative score and not a calibrated probability.
        </p>
      </CardContent>
    </Card>
  );
}

/* ---------- Task 2 summary ---------- */

function FactsCard({ result }: { result: AnalyzeResult }) {
  const r = result.task2.record;
  const slots = Object.keys(SLOT_LABELS);
  const filled = slots.filter((s) => !isMissing(r[s])).length;
  const agg = Array.isArray(r.aggravating_factors) ? r.aggravating_factors : [];
  const mit = Array.isArray(r.mitigating_factors) ? r.mitigating_factors : [];
  return (
    <Card className="h-full">
      <CardHeader>
        <TaskLabel n={2} icon={ListChecks} title="Case facts" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-3xl font-semibold tracking-tight">{formatSlot("prosecutor_demand_months", r.prosecutor_demand_months)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Prosecutor demand, {formatSlot("prosecutor_demand_type", r.prosecutor_demand_type)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <MiniStat label="Slots filled" value={`${filled} of ${slots.length}`} />
          <MiniStat label="Defendant age" value={formatSlot("defendant_age", r.defendant_age)} />
          <MiniStat label="Aggravating" value={`${agg.length} factor${agg.length === 1 ? "" : "s"}`} />
          <MiniStat label="Mitigating" value={`${mit.length} factor${mit.length === 1 ? "" : "s"}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Articles charged</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {Array.isArray(r.article_charged) ? (
              r.article_charged.map((a) => (
                <Badge key={a} variant="outline" className="font-mono">{a}</Badge>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">{formatSlot("article_charged", r.article_charged)}</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border px-2.5 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

/* ---------- Task 3 ---------- */

function SentenceCard({ result }: { result: AnalyzeResult }) {
  const t = result.task3;
  const champion = t.champion?.months ?? null;
  const truth = t.champion?.true_months ?? null;
  const headline = champion ?? t.live.months;
  const counted = useCountUp(headline, 1.2, 0.4);
  return (
    <Card className="h-full">
      <CardHeader>
        <TaskLabel n={3} icon={Gavel} title="Sentence" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-3xl font-semibold tracking-tight tabular-nums">
            {counted.toFixed(1)} <span className="text-lg font-normal text-muted-foreground">months</span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {champion !== null ? "Champion H4 blend, held out prediction" : "Live S2 prediction"}
          </p>
        </div>
        {truth !== null && (
          <Verdict ok={Math.abs(headline - truth) <= 3}>
            Actual sentence {formatMonths(truth)}, off by {Math.abs(headline - truth).toFixed(1)} months
          </Verdict>
        )}
        <div className="space-y-2 text-xs">
          <CompareRow label="Live S2 LightGBM on the extracted facts" value={t.live.months} max={Math.max(headline, t.live.months, truth ?? 0)} />
          {champion !== null && (
            <CompareRow label="Champion H4 blend" value={champion} max={Math.max(headline, t.live.months, truth ?? 0)} accent />
          )}
          {truth !== null && (
            <CompareRow label="Actual sentence" value={truth} max={Math.max(headline, t.live.months, truth)} muted />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CompareRow({ label, value, max, accent, muted }: { label: string; value: number; max: number; accent?: boolean; muted?: boolean }) {
  return (
    <div>
      <div className="flex justify-between gap-2">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{value.toFixed(1)}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className={cn("h-full rounded-full", accent ? "bg-accent-brand" : muted ? "bg-success" : "bg-foreground/70")}
          initial={{ width: 0 }}
          animate={{ width: `${(value / (max || 1)) * 100}%` }}
          transition={{ delay: 0.5, duration: 0.7 }}
        />
      </div>
    </div>
  );
}

/* ---------- Task 2 record ---------- */

function RecordCard({ result }: { result: AnalyzeResult }) {
  const t = result.task2;
  const r = t.record;
  const agg = Array.isArray(r.aggravating_factors) ? r.aggravating_factors : [];
  const mit = Array.isArray(r.mitigating_factors) ? r.mitigating_factors : [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Extracted sentencing record</CardTitle>
        <CardDescription>
          Hover a value to see the text it came from. Victim count, injury, and loss come from IndoBERT, the other slots
          from the rules, as chosen on the validation set.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-6 md:grid-cols-3">
          {SLOT_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="mb-2 text-xs font-medium text-muted-foreground">{group.title}</p>
              <div className="divide-y rounded-lg border">
                {group.slots.map((slot) => (
                  <SlotRow key={slot} slot={slot} result={result} />
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <FactorList title="Aggravating factors" codes={agg} evidence={t.evidence.aggravating_factors} tone="removed" />
          <FactorList title="Mitigating factors" codes={mit} evidence={t.evidence.mitigating_factors} tone="success" />
        </div>
      </CardContent>
    </Card>
  );
}

function SlotRow({ slot, result }: { slot: string; result: AnalyzeResult }) {
  const value = result.task2.record[slot];
  const route = result.task2.route[slot];
  const evidence = result.task2.evidence[slot === "prosecutor_demand_type" ? "prosecutor_demand_months" : slot];
  const content = (
    <div className="flex items-center justify-between gap-3 px-3 py-2">
      <div className="min-w-0">
        <p className="text-[11px] text-muted-foreground">{SLOT_LABELS[slot]}</p>
        <p className={cn("truncate text-sm", isMissing(value) ? "text-muted-foreground" : "font-medium")}>
          {formatSlot(slot, value)}
        </p>
      </div>
      <Badge variant={route === "bert" ? "default" : "outline"} className="shrink-0 text-[10px]">
        {route === "bert" ? "IndoBERT" : route === "rule" ? "Rule" : "n/a"}
      </Badge>
    </div>
  );
  if (!evidence?.length) return content;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="cursor-help hover:bg-muted/50">{content}</div>
      </TooltipTrigger>
      <TooltipContent className="max-w-sm font-mono text-xs">{evidence[0]}</TooltipContent>
    </Tooltip>
  );
}

function FactorList({ title, codes, evidence, tone }: { title: string; codes: string[]; evidence?: string[]; tone: "removed" | "success" }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium text-muted-foreground">{title}</p>
      {codes.length === 0 ? (
        <p className="text-sm text-muted-foreground">None found</p>
      ) : (
        <ul className="space-y-1.5">
          {codes.map((code, i) => (
            <li key={code} className="flex gap-3 rounded-md border px-3 py-2">
              <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", tone === "removed" ? "bg-removed" : "bg-success")} />
              <div className="min-w-0">
                <p className="text-sm font-medium">{FACTOR_NAMES[code] ?? code}</p>
                {evidence?.[i] && <p className="truncate text-xs text-muted-foreground">“{evidence[i]}”</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------- Task 2 details ---------- */

const ENTITY_TYPES: { tag: string; name: string; slot: string }[] = [
  { tag: "AGE", name: "Age", slot: "defendant_age" },
  { tag: "DEMAND", name: "Prosecutor demand", slot: "prosecutor_demand_months" },
  { tag: "ARTICLE", name: "Article", slot: "article_charged" },
  { tag: "VICTIM", name: "Victim count", slot: "victim_count" },
  { tag: "INJURY", name: "Injury", slot: "victim_injury" },
  { tag: "WEAPON", name: "Weapon", slot: "weapon_used" },
  { tag: "LOSS", name: "Loss value", slot: "loss_value" },
  { tag: "AGG", name: "Aggravating", slot: "aggravating_factors" },
  { tag: "MIT", name: "Mitigating", slot: "mitigating_factors" },
];

function Task2Details({ result }: { result: AnalyzeResult }) {
  const t = result.task2;
  const spans = t.bert?.spans ?? {};
  const maxParagraphs = Math.max(1, ...t.sections.map((s) => s.paragraphs));
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-6">
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">A. Preprocessing</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <MiniStat label="Words before cleaning" value={t.stats.raw_words.toLocaleString("en-US")} />
            <MiniStat label="Words after cleaning" value={t.stats.clean_words.toLocaleString("en-US")} />
            <MiniStat label="Names replaced" value={String(t.stats.pseudonym_replacements)} />
            <MiniStat label="Verdict parts masked" value={String(t.stats.verdict_masked)} />
          </div>
          {t.pseudonym_example && (
            <p className="mt-2 rounded-md border bg-muted/30 px-3 py-2 font-mono text-xs">{t.pseudonym_example}</p>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Crime type used for the rules: <span className="font-medium text-foreground">{crimeName(t.crime_type_used)}</span>
          </p>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">
            B. Sections found, {t.paragraphs} paragraphs in total
          </p>
          <div className="space-y-1.5">
            {t.sections.map((s) => (
              <Tooltip key={s.name}>
                <TooltipTrigger asChild>
                  <div className="grid cursor-help grid-cols-[130px_1fr_32px] items-center gap-3 text-xs">
                    <span className="truncate">{SECTION_NAMES[s.name] ?? s.name}</span>
                    <div className="h-2 rounded-full bg-muted">
                      <motion.div
                        className="h-2 rounded-full bg-accent-brand"
                        initial={{ width: 0 }}
                        animate={{ width: `${(s.paragraphs / maxParagraphs) * 100}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <span className="text-right font-mono text-muted-foreground">{s.paragraphs}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-sm font-mono text-xs">{s.preview}</TooltipContent>
              </Tooltip>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Hover a section to see its first line.</p>
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-muted-foreground">C. IndoBERT spans</p>
        {!t.bert || t.bert.skipped ? (
          <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
            IndoBERT was not run. {t.bert?.skipped ? `Reason: ${t.bert.skipped}.` : "The model weights are not loaded."}
          </p>
        ) : (
          <>
            <p className="mb-3 text-xs text-muted-foreground">
              {t.bert.windows} windows of 256 tokens over {t.bert.excerpt_chars?.toLocaleString("en-US")} characters.
              Spans marked Used fill the final record.
            </p>
            <div className="divide-y rounded-lg border">
              {ENTITY_TYPES.map((e) => {
                const found = spans[e.tag] ?? [];
                const used = t.route[e.slot] === "bert";
                return (
                  <div key={e.tag} className="space-y-1.5 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono text-[10px]">{e.tag}</Badge>
                      <span className="text-sm">{e.name}</span>
                      {used && <Badge className="ml-auto text-[10px]">Used</Badge>}
                    </div>
                    {found.length === 0 ? (
                      <p className="text-xs text-muted-foreground">No span found</p>
                    ) : (
                      found.map((span, i) => (
                        <p key={i} className="line-clamp-2 font-mono text-xs text-muted-foreground">
                          “{span}”
                        </p>
                      ))
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------- details ---------- */

function Details({ result }: { result: AnalyzeResult }) {
  const download = () => {
    const blob = new Blob([result.extraction.text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.doc_id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Card>
      <CardContent>
        <Tabs defaultValue="text">
          <TabsList>
            <TabsTrigger value="text">Extracted text</TabsTrigger>
            <TabsTrigger value="task1">Task 1 details</TabsTrigger>
            <TabsTrigger value="task2">Task 2 details</TabsTrigger>
            <TabsTrigger value="task3">Task 3 details</TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="mt-4 space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1"><MatchBadge result={result} /></div>
              <Button variant="outline" size="sm" onClick={download}>
                <Download /> Download txt
              </Button>
            </div>
            <ScrollArea className="h-96 rounded-lg border bg-muted/30">
              <pre className="p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap">{result.extraction.text}</pre>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="task1" className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">All 18 crime types</p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Crime type</TableHead>
                    <TableHead className="text-right">Margin</TableHead>
                    <TableHead className="text-right">Relative score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.task1.steps.svm.scores.map((s, i) => (
                    <TableRow key={s.label} className={i === 0 ? "font-medium" : undefined}>
                      <TableCell>{crimeName(s.label)}</TableCell>
                      <TableCell className="text-right font-mono">{s.margin.toFixed(3)}</TableCell>
                      <TableCell className="text-right font-mono">{(s.confidence * 100).toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="space-y-4">
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Model input view, first characters</p>
                <p className="rounded-lg border bg-muted/30 p-3 font-mono text-xs leading-relaxed">
                  {result.task1.steps.view.preview}…
                </p>
              </div>
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Highest weighted character n-grams</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.task1.steps.tfidf.top_chars.map((c) => (
                    <Badge key={c.term} variant="outline" className="font-mono whitespace-pre">
                      {JSON.stringify(c.term)} {c.weight.toFixed(3)}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="task2" className="mt-4">
            <Task2Details result={result} />
          </TabsContent>

          <TabsContent value="task3" className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                What moved the S2 prediction from its base of {result.task3.live.base_months.toFixed(1)} months
              </p>
              <div className="space-y-1.5">
                {result.task3.live.drivers.map((d) => {
                  const width = Math.min(100, Math.abs(d.effect) * 90);
                  return (
                    <div key={d.feature} className="grid grid-cols-[1fr_120px] items-center gap-3 text-xs">
                      <span className="truncate">{featureName(d.feature)}</span>
                      <div className="relative h-2 rounded-full bg-muted">
                        <span className="absolute top-0 left-1/2 h-2 w-px bg-border" />
                        <motion.span
                          className={cn("absolute top-0 h-2 rounded-full", d.effect < 0 ? "right-1/2 bg-success" : "left-1/2 bg-removed")}
                          initial={{ width: 0 }}
                          animate={{ width: `${width / 2}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                TreeSHAP contributions in log months. Green lowers the sentence, red raises it.
              </p>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">Feature values</p>
              <Table>
                <TableBody>
                  {result.task3.features.map((f) => (
                    <TableRow key={f.feature}>
                      <TableCell className="text-muted-foreground">{featureName(f.feature)}</TableCell>
                      <TableCell className="text-right font-mono">
                        {f.value === null ? "missing" : f.feature === "crime_type" ? crimeName(String(f.value)) : String(f.value)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {result.task3.regex_demand.phrase && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Parser demand phrase: <span className="font-mono">{result.task3.regex_demand.phrase}</span>
                </p>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
