export function formatTime(seconds) {
  if (typeof seconds !== 'number' || isNaN(seconds)) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

export function scoreColor(score) {
  if (score >= 80) return '#ef4444' // red-500
  if (score >= 60) return '#f97316' // orange-500
  if (score >= 40) return '#eab308' // yellow-500
  if (score >= 20) return '#22c55e' // green-500
  return '#10b981' // emerald-500
}

export function severityColor(severity) {
  const map = {
    Critical: '#ef4444',
    Severe: '#f97316',
    Moderate: '#eab308',
    Mild: '#22c55e',
    Low: '#10b981',
  }
  return map[severity] || '#6b7280'
}

export function decisionColor(decision) {
  if (decision === 'Violation') return { bg: 'from-red-600 to-pink-600', text: 'text-red-400' }
  if (decision === 'Review Required') return { bg: 'from-amber-600 to-orange-600', text: 'text-amber-400' }
  return { bg: 'from-green-600 to-emerald-600', text: 'text-green-400' }
}
