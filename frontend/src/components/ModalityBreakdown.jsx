import { motion } from 'framer-motion'
import { scoreColor } from '../utils/formatters'
import GlassCard from './ui/GlassCard'
import { colors, animation } from '../design/tokens'

const modalityConfig = {
  Video: { color: colors.modality.video, icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' },
  Audio: { color: colors.modality.audio, icon: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z' },
  Text: { color: colors.modality.text, icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
}

export default function ModalityBreakdown({ video, audio, text, fused }) {
  const modalities = [
    { name: 'Video', data: video },
    { name: 'Audio', data: audio },
    { name: 'Text', data: text },
  ]

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/60 mb-4">Modality Breakdown</h3>

      <div className="space-y-4">
        {modalities.map((m, i) => {
          const data = m.data
          if (!data || data.class === 'Error') return null

          const confidence = data.confidence || 0
          const isViolent = data.class === 'Violence'
          const color = isViolent ? scoreColor(confidence) : '#22c55e'
          const weight = fused?.modality_weights?.[m.name.toLowerCase()]
          const cfg = modalityConfig[m.name]

          return (
            <motion.div key={m.name} {...animation.stagger(i)} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: cfg.color.glow }}
                  >
                    <svg className="w-3.5 h-3.5" style={{ color: cfg.color.base }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={cfg.icon} />
                    </svg>
                  </div>
                  <span className="text-sm text-white/70">{m.name}</span>
                  {weight && (
                    <span className="text-[10px] text-white/25">({(weight * 100).toFixed(0)}%)</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{ color, backgroundColor: `${color}12` }}
                  >
                    {isViolent ? 'Violence' : 'Safe'}
                  </span>
                  <span className="text-sm font-medium" style={{ color }}>
                    {confidence.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Gradient progress bar with shimmer */}
              <div className="w-full h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full relative"
                  style={{ background: `linear-gradient(90deg, ${color}80, ${color})` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(confidence, 100)}%` }}
                  transition={{ duration: 1, delay: 0.2 * i }}
                />
              </div>

              {data.reasoning && (
                <p className="text-xs text-white/30 line-clamp-2">{data.reasoning}</p>
              )}
            </motion.div>
          )
        })}
      </div>

      {fused && (
        <div className="mt-4 pt-4 border-t border-white/[0.06]">
          <div className="flex items-center justify-between text-xs text-white/30">
            <span>Fusion: {fused.fusion_method || 'weighted'}</span>
            {fused.cross_modal_reason && fused.cross_modal_reason !== 'none' && (
              <span className="text-white/20">{fused.cross_modal_reason}</span>
            )}
          </div>
        </div>
      )}
    </GlassCard>
  )
}
