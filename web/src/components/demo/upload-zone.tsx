"use client";

import { useRef, useState } from "react";
import { motion } from "motion/react";
import { FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function UploadZone({ onFile }: { onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const accept = (files: FileList | null) => {
    setError(null);
    if (!files || files.length === 0) return;
    if (files.length > 1) {
      setError("Please drop one PDF at a time.");
      return;
    }
    const file = files[0];
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    onFile(file);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a decision</CardTitle>
        <CardDescription>One PDF with a text layer, up to 15 MB.</CardDescription>
      </CardHeader>
      <CardContent>
        <motion.div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            accept(e.dataTransfer.files);
          }}
          animate={{ scale: dragging ? 1.01 : 1 }}
          className={cn(
            "flex h-[312px] flex-col items-center justify-center rounded-lg border border-dashed text-center transition-colors",
            dragging ? "border-accent-brand bg-accent-brand-soft" : "bg-muted/30",
          )}
        >
          <motion.span
            animate={{ y: dragging ? -4 : 0 }}
            className="flex size-12 items-center justify-center rounded-full border bg-background"
          >
            <FileUp className="size-5" />
          </motion.span>
          <p className="mt-4 text-sm font-medium">Drop the PDF here</p>
          <p className="mt-1 text-xs text-muted-foreground">or choose it from your computer</p>
          <Button className="mt-5" size="sm" onClick={() => input.current?.click()}>
            Choose file
          </Button>
          {error && <p className="mt-3 text-xs text-removed">{error}</p>}
          <input
            ref={input}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => {
              accept(e.target.files);
              e.target.value = "";
            }}
          />
        </motion.div>
      </CardContent>
    </Card>
  );
}
