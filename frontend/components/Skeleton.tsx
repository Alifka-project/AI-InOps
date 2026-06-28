export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-white/5 ${className}`}
      aria-hidden="true"
    />
  );
}

export function CardSkeleton({ height = "h-72" }: { height?: string }) {
  return (
    <div className="card card-pad">
      <Skeleton className="mb-4 h-4 w-32" />
      <Skeleton className={`w-full ${height}`} />
    </div>
  );
}

export function KpiSkeletonRow({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card card-pad">
          <Skeleton className="mb-3 h-3 w-24" />
          <Skeleton className="mb-2 h-8 w-28" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}
