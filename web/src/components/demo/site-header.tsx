"use client";

import { useEffect, useState } from "react";
import { Scale } from "lucide-react";
import { cn } from "@/lib/utils";

type Status = "checking" | "online" | "offline";

export function SiteHeader() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let alive = true;
    const check = () =>
      fetch("/api/health")
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then(() => alive && setStatus("online"))
        .catch(() => alive && setStatus("offline"));
    check();
    const id = setInterval(check, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <a href="#" className="flex items-center gap-2 text-sm font-semibold">
          <span className="flex size-7 items-center justify-center rounded-md bg-foreground text-background">
            <Scale className="size-4" />
          </span>
          Judgment Analysis
        </a>
        <nav className="flex items-center gap-6 text-sm text-muted-foreground">
          <a href="#demo" className="hover:text-foreground">Demo</a>
          <a href="#models" className="hover:text-foreground">Models</a>
          <span className="flex items-center gap-2">
            <span
              className={cn(
                "size-2 rounded-full",
                status === "online" && "bg-success",
                status === "offline" && "bg-removed",
                status === "checking" && "animate-pulse bg-muted-foreground",
              )}
            />
            {status === "online" ? "Models ready" : status === "offline" ? "Backend offline" : "Connecting"}
          </span>
        </nav>
      </div>
    </header>
  );
}
