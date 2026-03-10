export function SkeletonLine({ width = 'w-full', height = 'h-4', className = '' }) {
  return <div className={`skeleton rounded ${width} ${height} ${className}`} />
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`glass-card p-5 space-y-3 ${className}`}>
      <SkeletonLine width="w-1/3" height="h-4" />
      <SkeletonLine width="w-full" height="h-3" />
      <SkeletonLine width="w-2/3" height="h-3" />
    </div>
  )
}

export function SkeletonChart({ height = 'h-48', className = '' }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      <SkeletonLine width="w-1/4" height="h-4" className="mb-4" />
      <div className={`skeleton rounded-lg ${height}`} />
    </div>
  )
}

export function SkeletonCircle({ size = 'w-12 h-12', className = '' }) {
  return <div className={`skeleton rounded-full ${size} ${className}`} />
}
