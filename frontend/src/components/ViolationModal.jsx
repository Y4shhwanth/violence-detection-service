import { AnimatePresence, motion } from 'framer-motion'
import { severityColor } from '../utils/formatters'
import { animation } from '../design/tokens'

export default function ViolationModal({ violation, onClose }) {
  if (!violation) return null

  const sevColor = severityColor(violation.severity)

  return (
    <AnimatePresence>
      {violation && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={animation.spring}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="glass-card p-6 max-w-lg w-full shadow-2xl">
              {/* Severity color bar */}
              <div className="h-1 rounded-full mb-4 -mx-6 -mt-6" style={{ background: `linear-gradient(90deg, ${sevColor}, transparent)`, margin: '-1.5rem -1.5rem 1rem' , borderRadius: '16px 16px 0 0' }} />

              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: sevColor, boxShadow: `0 0 8px ${sevColor}40` }} />
                  <h3 className="font-semibold text-white">Violation Details</h3>
                </div>
                <button onClick={onClose} className="text-white/30 hover:text-white transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-2">
                <InfoRow label="Type" value={violation.type?.replace(/_/g, ' ')} />
                <InfoRow label="Modality" value={violation.modality?.toUpperCase()} />
                <InfoRow label="Severity" value={violation.severity} valueColor={sevColor} />
                {violation.start_time && (
                  <InfoRow label="Time Range" value={`${violation.start_time} - ${violation.end_time || violation.start_time}`} />
                )}
                {violation.peak_score !== undefined && (
                  <InfoRow label="Peak Score" value={`${violation.peak_score.toFixed(1)}`} />
                )}
                {violation.confidence !== undefined && (
                  <InfoRow label="Confidence" value={`${violation.confidence.toFixed(1)}%`} />
                )}
                <InfoRow label="Reason" value={violation.reason} />
                {violation.sentence && (
                  <div className="pt-2">
                    <span className="text-xs text-white/30 block mb-1">Flagged Text</span>
                    <p className="text-sm text-white/60 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 italic">
                      "{violation.sentence}"
                    </p>
                  </div>
                )}
                {violation.detected_sounds?.length > 0 && (
                  <div className="pt-2">
                    <span className="text-xs text-white/30 block mb-1.5">Detected Sounds</span>
                    <div className="flex flex-wrap gap-1.5">
                      {violation.detected_sounds.map((s, i) => (
                        <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-red-500/[0.08] text-red-400 border border-red-500/15">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {violation.keywords?.length > 0 && (
                  <div className="pt-2">
                    <span className="text-xs text-white/30 block mb-1.5">Keywords</span>
                    <div className="flex flex-wrap gap-1.5">
                      {violation.keywords.map((k, i) => (
                        <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-orange-500/[0.08] text-orange-400 border border-orange-500/15">{k}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={onClose}
                className="mt-6 w-full py-2.5 rounded-xl text-sm font-medium
                  bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.06] transition-colors"
              >
                Close
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function InfoRow({ label, value, valueColor }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04] last:border-0">
      <span className="text-xs text-white/30">{label}</span>
      <span className="text-sm font-medium" style={{ color: valueColor || 'rgba(255,255,255,0.7)' }}>
        {value}
      </span>
    </div>
  )
}
