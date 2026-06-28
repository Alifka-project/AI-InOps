"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { INPUT_DEFS } from "@/lib/inputs";
import { useScenarioStore } from "@/store/useScenarioStore";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { UploadCard } from "@/components/UploadCard";
import type { Dataset } from "@/lib/types";

type FileMap = Record<string, File | null>;
type Busy = "upload" | "sample" | "combined" | "template" | null;

export default function DataPage() {
  const router = useRouter();
  const dataset = useScenarioStore((s) => s.dataset);
  const setDataset = useScenarioStore((s) => s.setDataset);
  const clearDataset = useScenarioStore((s) => s.clearDataset);

  const [name, setName] = useState("My logistics network");
  const [files, setFiles] = useState<FileMap>({});
  const [busy, setBusy] = useState<Busy>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const combinedRef = useRef<HTMLInputElement>(null);

  const requiredKinds = INPUT_DEFS.filter((d) => d.required).map((d) => d.kind);
  const haveRequired = requiredKinds.every((k) => files[k]);

  const setFile = (kind: string, file: File | null) =>
    setFiles((f) => ({ ...f, [kind]: file }));

  const loadDataset = (ds: Dataset) => {
    setDataset(ds);
    setWarnings(ds.meta.warnings ?? []);
    setErrors([]);
  };

  const onUpload = async () => {
    setBusy("upload");
    setErrors([]);
    setWarnings([]);
    try {
      const picked: Record<string, File> = {};
      for (const [k, v] of Object.entries(files)) if (v) picked[k] = v;
      const res = await api.parseUpload(name, picked);
      if (res.ok && res.dataset) {
        loadDataset(res.dataset);
        router.push("/overview");
      } else {
        setErrors(res.errors.length ? res.errors : ["Validation failed."]);
        setWarnings(res.warnings ?? []);
      }
    } catch (err) {
      setErrors([err instanceof ApiError ? err.message : "Upload failed."]);
    } finally {
      setBusy(null);
    }
  };

  const onSample = async () => {
    setBusy("sample");
    setErrors([]);
    try {
      const ds = await api.getSample();
      loadDataset(ds);
      router.push("/overview");
    } catch (err) {
      setErrors([err instanceof ApiError ? err.message : "Could not load sample."]);
    } finally {
      setBusy(null);
    }
  };

  const onCombinedFile = async (file: File | null) => {
    if (!file) return;
    setBusy("combined");
    setErrors([]);
    setWarnings([]);
    try {
      const res = await api.parseCombined(name, file);
      if (res.ok && res.dataset) {
        loadDataset(res.dataset);
        router.push("/overview");
      } else {
        setErrors(res.errors.length ? res.errors : ["Could not read the file."]);
        setWarnings(res.warnings ?? []);
      }
    } catch (err) {
      setErrors([err instanceof ApiError ? err.message : "Upload failed."]);
    } finally {
      setBusy(null);
      if (combinedRef.current) combinedRef.current.value = "";
    }
  };

  const onDownloadTemplate = async (format: "xlsx" | "zip") => {
    setBusy("template");
    try {
      const blob = await api.downloadCombinedTemplate(format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `digital-twin-template.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrors([err instanceof ApiError ? err.message : "Template download failed."]);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data & Upload"
        description="The twin analyses your real data. Provide all eight input categories, or load the labelled sample to explore. Nothing is fabricated."
        actions={
          <button
            className="btn-ghost"
            onClick={onSample}
            disabled={busy !== null}
          >
            {busy === "sample" ? "Loading…" : "Load sample dataset"}
          </button>
        }
      />

      {dataset && (
        <div
          className={`card card-pad ${
            dataset.meta.is_sample
              ? "ring-1 ring-inset ring-amber-500/30"
              : "ring-1 ring-inset ring-emerald-500/30"
          }`}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="label">Active dataset</p>
              <p className="mt-0.5 font-semibold text-white">
                {dataset.meta.name}{" "}
                <span
                  className={
                    dataset.meta.is_sample ? "text-amber-300" : "text-emerald-300"
                  }
                >
                  · {dataset.meta.is_sample ? "SAMPLE" : "LIVE"}
                </span>
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {dataset.meta.n_periods} periods · {dataset.meta.n_suppliers} suppliers ·{" "}
                {dataset.meta.n_warehouses} warehouses · {dataset.meta.n_orders} orders
              </p>
            </div>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={() => router.push("/overview")}>
                Open analysis
              </button>
              <button className="btn-ghost" onClick={() => clearDataset()}>
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="card card-pad border-rose-500/20 ring-1 ring-inset ring-rose-500/30">
          <p className="font-semibold text-rose-300">Could not build dataset</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-rose-200">
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="card card-pad ring-1 ring-inset ring-amber-500/30">
          <p className="font-semibold text-amber-300">Warnings</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-200/90">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-1 max-w-md">
        <label htmlFor="ds-name" className="label">
          Dataset name
        </label>
        <input
          id="ds-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1.5 w-full rounded-lg border border-white/10 bg-ink/60 px-3 py-2 text-sm text-white focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/40"
        />
      </div>

      <Panel
        title="Upload everything in one file"
        description="The simplest option: one Excel workbook (a sheet per input), a ZIP of CSVs, or a previously exported JSON."
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={combinedRef}
              type="file"
              accept=".xlsx,.xls,.zip,.json"
              className="hidden"
              aria-label="Upload combined dataset file"
              onChange={(e) => onCombinedFile(e.target.files?.[0] ?? null)}
            />
            <button
              className="btn-primary"
              disabled={busy !== null}
              onClick={() => combinedRef.current?.click()}
            >
              {busy === "combined" ? "Validating…" : "Choose combined file"}
            </button>
            <span className="text-xs text-slate-400">.xlsx · .zip · .json</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400">Need the format?</span>
            <button
              className="btn-ghost py-1.5 text-xs"
              disabled={busy !== null}
              onClick={() => onDownloadTemplate("xlsx")}
            >
              {busy === "template" ? "…" : "Excel template"}
            </button>
            <button
              className="btn-ghost py-1.5 text-xs"
              disabled={busy !== null}
              onClick={() => onDownloadTemplate("zip")}
            >
              ZIP template
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          The Excel template has one sheet per input (sales, suppliers,
          transport_costs, external, inventory, orders, warehouse_params,
          transport_history, materials), pre-filled with the sample so you can
          see the exact columns. Replace the rows with your data and upload it
          here.
        </p>
      </Panel>

      <Panel
        title="Or upload each input separately"
        description="CSV files with flexible headers. Download a template for the exact columns. Drag a file onto a card or click Choose CSV."
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {INPUT_DEFS.map((def) => (
            <UploadCard
              key={def.kind}
              def={def}
              file={files[def.kind] ?? null}
              onFile={(f) => setFile(def.kind, f)}
            />
          ))}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            className="btn-primary"
            onClick={onUpload}
            disabled={!haveRequired || busy !== null}
          >
            {busy === "upload" ? "Validating…" : "Validate & load"}
          </button>
          <span className="text-xs text-slate-400">
            {haveRequired
              ? "All required inputs selected."
              : `Select all ${requiredKinds.length} required inputs to continue.`}
          </span>
        </div>
      </Panel>
    </div>
  );
}
