import { motion } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import { animation } from '../design/tokens'

const decisionColors = {
  Violation: 'text-red-400 bg-red-500/10',
  'Review Required': 'text-yellow-400 bg-yellow-500/10',
  Review: 'text-yellow-400 bg-yellow-500/10',
  Verified: 'text-green-400 bg-green-500/10',
}

export default function AnalysisHistory({ history }) {
  if (!history || history.length === 0) {
    return (
      <GlassCard className="text-center py-12">
        <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-white/[0.04] flex items-center justify-center">
          <svg className="w-6 h-6 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-white/40">No analysis history yet. Run some analyses first.</p>
      </GlassCard>
    )
  }

  return (
    <motion.div {...animation.fadeInUp}>
      <GlassCard>
        <h3 className="text-sm font-semibold text-white/70 mb-4">Analysis History ({history.length})</h3>

        {/* Header */}
        <div className="grid grid-cols-5 gap-3 text-[10px] text-white/30 uppercase tracking-wider pb-2 border-b border-white/[0.06] mb-1">
          <span>Date</span>
          <span>Decision</span>
          <span>Confidence</span>
          <span>Modalities</span>
          <span className="text-right">Time</span>
        </div>

        {/* Rows */}
        <div className="max-h-[500px] overflow-y-auto">
          {history.map((entry, i) => {
            const colorClass = decisionColors[entry.decision] || 'text-white/50 bg-white/5'
            const date = new Date(entry.date)
            const dateStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            const timeStr = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })

            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.5) }}
                className="grid grid-cols-5 gap-3 py-2.5 border-b border-white/[0.04] last:border-0 items-center"
              >
                <div>
                  <p className="text-xs text-white/60">{dateStr}</p>
                  <p className="text-[10px] text-white/25">{timeStr}</p>
                </div>
                <div>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${colorClass}`}>
                    {entry.decision}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-white/60">{(entry.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex gap-1">
                  {(entry.modalities || []).map(m => (
                    <span key={m} className="text-[10px] text-white/30 bg-white/[0.04] px-1.5 py-0.5 rounded">
                      {m}
                    </span>
                  ))}
                </div>
                <div className="text-right">
                  <span className="text-xs text-white/40">
                    {entry.processing_time ? `${(entry.processing_time / 1000).toFixed(1)}s` : '—'}
                  </span>
                </div>
              </motion.div>
            )
          })}
        </div>
      </GlassCard>
    </motion.div>
  )
}
