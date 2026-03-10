import { motion } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import { colors } from '../design/tokens'

const stages = [
  { label: 'Video frames', color: colors.modality.video.base, delay: 0 },
  { label: 'Audio signals', color: colors.modality.audio.base, delay: 0.3 },
  { label: 'Text content', color: colors.modality.text.base, delay: 0.6 },
]

export default function AnalysisProgress({ progress }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      <GlassCard animate={false}>
        <div className="flex items-center gap-4 mb-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-6 h-6 border-2 border-red-500 border-t-transparent rounded-full"
          />
          <span className="text-sm font-medium text-white/70">
            {progress > 0 && progress < 100
              ? `Uploading... ${progress}%`
              : 'Analyzing content...'}
          </span>
        </div>

        {/* Gradient progress bar with shimmer */}
        <div className="w-full h-2 bg-white/[0.04] rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full relative"
            style={{ background: 'linear-gradient(90deg, #ef4444, #ec4899)' }}
            initial={{ width: '0%' }}
            animate={{ width: progress > 0 ? `${progress}%` : '100%' }}
            transition={progress > 0 ? { duration: 0.3 } : { duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            {...(progress === 0 && { style: { width: '30%', background: 'linear-gradient(90deg, #ef4444, #ec4899)', animation: 'pulse 2s ease-in-out infinite' } })}
          >
            <div className="absolute inset-0 shimmer opacity-50" />
          </motion.div>
        </div>

        {/* Analysis stages */}
        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          {stages.map(({ label, color, delay }) => (
            <div key={label} className="flex items-center gap-2">
              <motion.div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}40` }}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity, delay }}
              />
              <span className="text-white/40">{label}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </motion.div>
  )
}
