"use client";

import { useRef, useState } from "react";
import type { InputDef } from "@/lib/inputs";
import { api } from "@/lib/api";

interface Props {
  def: InputDef;
  file: File | null;
  onFile: (file: File | null) => void;
}

export function UploadCard({ def, file, onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const downloadTemplate = async () => {
    try {
      const t = await api.getTemplate(def.kind);
      const blob = new Blob([t.csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = t.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Fallback: header-only template from known columns.
      const blob = new Blob([def.columns.join(",") + "\n"], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${def.kind}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div
      className={`card card-pad transition ${
        dragOver ? "ring-2 ring-accent/60" : ""
      } ${file ? "ring-1 ring-inset ring-emerald-500/30" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-white">{def.title}</h3>
            {def.required ? (
              <span className="chip bg-white/5 text-[10px] text-slate-400">required</span>
            ) : (
              <span className="chip bg-white/5 text-[10px] text-slate-500">optional</span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-slate-400">{def.brief}</p>
        </div>
        {file ? (
          <span className="chip shrink-0 bg-emerald-500/15 text-emerald-300">✓</span>
        ) : (
          <span className="chip shrink-0 bg-white/5 text-slate-500">—</span>
        )}
      </div>

      <p className="mt-2 truncate font-mono text-[11px] text-slate-500">
        {def.columns.join(", ")}
      </p>

      <div className="mt-3 flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          aria-label={`Upload ${def.title} CSV`}
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
        <button className="btn-ghost py-1.5 text-xs" onClick={() => inputRef.current?.click()}>
          {file ? "Replace" : "Choose CSV"}
        </button>
        <button
          className="text-xs text-accent hover:underline"
          onClick={downloadTemplate}
        >
          Template
        </button>
        {file && (
          <button
            className="ml-auto text-xs text-slate-500 hover:text-rose-300"
            onClick={() => onFile(null)}
            aria-label={`Remove ${def.title}`}
          >
            Remove
          </button>
        )}
      </div>
      {file && (
        <p className="mt-2 truncate text-[11px] text-slate-400" title={file.name}>
          {file.name} · {(file.size / 1024).toFixed(1)} KB
        </p>
      )}
    </div>
  );
}
