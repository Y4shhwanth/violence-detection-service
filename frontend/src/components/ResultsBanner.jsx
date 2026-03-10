import { motion } from 'framer-motion'
import AnimatedCounter from './ui/AnimatedCounter'
import { animation } from '../design/tokens'

export default function ResultsBanner({ decision, confidence, message }) {
  const isViolation = decision === 'Violation'
  const isReview = decision === 'Review Required'

  const config = isViolation
    ? { gradient: 'from-red-600 to-pink-600', glowClass: 'glow-border-red', text: 'text-red-400', bg: 'bg-red-500/[0.06]' }
    : isReview
    ? { gradient: 'from-amber-500 to-orange-600', glowClass: '', text: 'text-amber-400', bg: 'bg-amber-500/[0.06]' }
    : { gradient: 'from-green-500 to-emerald-600', glowClass: 'glow-border-green', text: 'text-green-400', bg: 'bg-green-500/[0.06]' }

  const title = isViolation ? 'Violation Detected' : isReview ? 'Review Required' : 'Verified Safe'

  return (
    <motion.div
      {...animation.scaleIn}
      className={`glass-card p-6 ${config.glowClass} ${config.bg}`}
    >
      <div className="flex items-center gap-4">
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className={`w-14 h-14 rounded-2xl flex items-center justify-center bg-gradient-to-br ${config.gradient} shadow-lg`}
          style={{ boxShadow: isViolation ? '0 0 24px rgba(239,68,68,0.2)' : isReview ? '0 0 24px rgba(245,158,11,0.2)' : '0 0 24px rgba(34,197,94,0.2)' }}
        >
          {isViolation ? (
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          ) : isReview ? (
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          ) : (
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </motion.div>

        <div className="flex-1">
          <motion.h2
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className={`text-2xl font-bold ${config.text}`}
          >
            {title}
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-sm text-white/50 mt-1 max-w-2xl"
          >
            {message}
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-right"
        >
          <AnimatedCounter
            value={confidence || 0}
            decimals={1}
            suffix="%"
            className={`text-3xl font-bold ${config.text}`}
          />
          <div className="text-xs text-white/30 mt-0.5">Confidence</div>
        </motion.div>
      </div>
    </motion.div>
  )
}
