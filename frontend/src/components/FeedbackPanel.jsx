import { useState } from 'react'
import { motion } from 'framer-motion'
import { submitFeedback } from '../api/asyncClient'
import GlassCard from './ui/GlassCard'

const buttons = [
  { type: 'correct', label: 'Correct', color: 'green', icon: 'M5 13l4 4L19 7' },
  { type: 'false_positive', label: 'False Positive', color: 'yellow', icon: 'M12 9v2m0 4h.01' },
  { type: 'false_negative', label: 'False Negative', color: 'red', icon: 'M6 18L18 6M6 6l12 12' },
]

export default function FeedbackPanel({ jobId }) {
  const [submitted, setSubmitted] = useState(false)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  if (!jobId) return null

  const handleFeedback = async (type) => {
    try {
      setSubmitting(true)
      setError(null)
      await submitFeedback(jobId, type, comment)
      setSubmitted(true)
    } catch (err) {
      setError('Failed to submit feedback')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-4 text-center glow-border-green"
      >
        <motion.div
          initial={{ scale: 0 }} animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, delay: 0.1 }}
          className="w-10 h-10 mx-auto mb-2 rounded-full bg-green-500/10 flex items-center justify-center"
        >
          <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>
        <p className="text-sm text-green-400">Thank you for your feedback!</p>
      </motion.div>
    )
  }

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/70 mb-3">Was this analysis correct?</h3>

      <div className="flex gap-2 mb-3">
        {buttons.map(btn => (
          <button
            key={btn.type}
            onClick={() => handleFeedback(btn.type)}
            disabled={submitting}
            className={`flex-1 py-2 px-3 rounded-xl text-xs font-medium
              bg-${btn.color}-500/[0.06] border border-${btn.color}-500/20
              text-${btn.color}-400 hover:bg-${btn.color}-500/[0.12]
              disabled:opacity-50 transition-all flex items-center justify-center gap-1.5`}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={btn.icon} />
            </svg>
            {btn.label}
          </button>
        ))}
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment..."
        className="w-full h-16 bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2 text-xs
          text-white placeholder-white/20 resize-none focus:outline-none focus:border-white/[0.15] transition-colors"
      />

      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </GlassCard>
  )
}
