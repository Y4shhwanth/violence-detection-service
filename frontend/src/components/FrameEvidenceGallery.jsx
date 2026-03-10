import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import { animation } from '../design/tokens'

export default function FrameEvidenceGallery({ violentFrames = [] }) {
  const [selectedFrame, setSelectedFrame] = useState(null)

  if (!violentFrames || violentFrames.length === 0) return null

  return (
    <>
      <GlassCard>
        <h3 className="text-sm font-semibold text-white/70 mb-4">Frame Evidence</h3>

        <div className="grid grid-cols-3 gap-3">
          {violentFrames.slice(0, 6).map((frame, idx) => (
            <motion.button
              key={idx}
              {...animation.stagger(idx)}
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedFrame(frame)}
              className="relative glass-card !p-3 text-left hover:border-white/[0.12] transition-colors group"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-white/40">#{frame.frame_number}</span>
                <span className="text-xs text-white/25">{frame.timestamp}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/50 truncate flex-1">{frame.indicators?.join(', ')}</span>
                <div className="flex items-center gap-1">
                  <div
                    className="w-6 h-1.5 rounded-full overflow-hidden bg-white/[0.06]"
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${frame.score}%`,
                        background: frame.score > 60 ? 'linear-gradient(90deg, #ef4444, #ec4899)' : frame.score > 30 ? 'linear-gradient(90deg, #eab308, #f97316)' : 'linear-gradient(90deg, #22c55e, #10b981)',
                      }}
                    />
                  </div>
                  <span className={`text-xs font-bold ${frame.score > 60 ? 'text-red-400' : frame.score > 30 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {frame.score}
                  </span>
                </div>
              </div>
              {frame.ml_detection && (
                <p className="text-[10px] text-orange-400/70 mt-1 truncate">ML: {frame.ml_detection}</p>
              )}
            </motion.button>
          ))}
        </div>
      </GlassCard>

      {/* Modal */}
      <AnimatePresence>
        {selectedFrame && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-8"
            onClick={() => setSelectedFrame(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={animation.spring}
              className="glass-card p-6 max-w-lg w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-sm font-semibold text-white">
                  Frame #{selectedFrame.frame_number} @ {selectedFrame.timestamp}
                </h4>
                <button onClick={() => setSelectedFrame(null)} className="text-white/30 hover:text-white transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center p-2 rounded-lg bg-white/[0.03]">
                  <span className="text-white/40">Score</span>
                  <span className={`font-bold ${selectedFrame.score > 60 ? 'text-red-400' : 'text-yellow-400'}`}>
                    {selectedFrame.score}/100
                  </span>
                </div>
                <div>
                  <span className="text-white/40 block mb-1.5 text-xs">Indicators</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedFrame.indicators?.map((ind, i) => (
                      <span key={i} className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded-lg text-xs text-white/60">{ind}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-white/40 block mb-1 text-xs">Reasoning</span>
                  <p className="text-xs text-white/60">{selectedFrame.reasoning}</p>
                </div>
                {selectedFrame.ml_detection && (
                  <div>
                    <span className="text-white/40 block mb-1 text-xs">ML Detection</span>
                    <p className="text-xs text-orange-400/80">{selectedFrame.ml_detection} ({selectedFrame.ml_score?.toFixed(0)}%)</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
