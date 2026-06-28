"use client";

import type { ReactNode } from "react";

interface Props {
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  skeleton: ReactNode;
  children: ReactNode;
}

/**
 * Renders a skeleton while loading, a retryable error panel on failure, or the
 * children on success.
 */
export function AsyncBoundary({
  loading,
  error,
  onRetry,
  skeleton,
  children,
}: Props) {
  if (loading) return <>{skeleton}</>;
  if (error) {
    return (
      <div className="card card-pad flex flex-col items-start gap-3 border-rose-500/20">
        <div className="flex items-center gap-2 text-rose-300">
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.7}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            />
          </svg>
          <p className="font-semibold">Could not load data</p>
        </div>
        <p className="text-sm text-slate-400">{error}</p>
        {onRetry && (
          <button onClick={onRetry} className="btn-primary">
            Retry
          </button>
        )}
      </div>
    );
  }
  return <>{children}</>;
}
