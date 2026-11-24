"use client";

import { useState } from "react";
import { Download, FileText, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { crimeName } from "@/lib/labels";
import type { Sample } from "@/lib/types";

export function SampleList({ samples, onAnalyze }: { samples: Sample[]; onAnalyze: (file: File) => void }) {
  const [loading, setLoading] = useState<string | null>(null);

  const runSample = async (sample: Sample) => {
    setLoading(sample.id);
    try {
      const blob = await fetch(sample.pdf).then((r) => r.blob());
      onAnalyze(new File([blob], `${sample.id}.pdf`, { type: "application/pdf" }));
    } finally {
      setLoading(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sample decisions</CardTitle>
        <CardDescription>
          Five held out test documents rendered as PDF. None of them was used to train any model.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {samples.length === 0 &&
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
        {samples.map((s) => (
          <div
            key={s.id}
            className="group flex items-center gap-4 rounded-lg border p-3 transition-colors hover:bg-muted/50"
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-md border bg-background">
              <FileText className="size-5 text-muted-foreground" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-medium">{s.title}</p>
                <Badge variant="secondary">{crimeName(s.crime_type)}</Badge>
              </div>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {s.id}.pdf · {s.pages} pages · {s.year}
                {s.court ? ` · ${s.court}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 gap-1.5">
              <Button variant="ghost" size="icon-sm" asChild aria-label="Download PDF">
                <a href={s.pdf} download>
                  <Download />
                </a>
              </Button>
              <Button variant="outline" size="sm" onClick={() => runSample(s)} disabled={loading !== null}>
                <Play /> {loading === s.id ? "Loading" : "Run"}
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
