import { lazy, Suspense, Component } from 'react'

const Spline = lazy(() => import('@splinetool/react-spline'))

class SplineErrorBoundary extends Component {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) return this.props.fallback
    return this.props.children
  }
}

const fallbackUI = (
  <div className="w-full h-full flex items-center justify-center">
    <div className="text-center space-y-2">
      <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-red-500/10 via-purple-500/10 to-cyan-500/10 border border-white/[0.06] flex items-center justify-center">
        <svg className="w-8 h-8 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <p className="text-xs text-white/20">3D scene unavailable</p>
    </div>
  </div>
)

export function SplineScene({ scene, className = '' }) {
  return (
    <SplineErrorBoundary fallback={fallbackUI}>
      <Suspense fallback={fallbackUI}>
        <Spline scene={scene} className={className} />
      </Suspense>
    </SplineErrorBoundary>
  )
}
