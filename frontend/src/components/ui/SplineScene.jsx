import { lazy, Suspense } from 'react'

const Spline = lazy(() => import('@splinetool/react-spline'))

export function SplineScene({ scene, className = '' }) {
  return (
    <Suspense
      fallback={
        <div className="w-full h-full flex items-center justify-center">
          <span className="loader text-white/30 text-sm">Loading 3D scene...</span>
        </div>
      }
    >
      <Spline scene={scene} className={className} />
    </Suspense>
  )
}
