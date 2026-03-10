import { useState } from 'react'
import { motion } from 'framer-motion'
import { exportReport } from '../api/asyncClient'

export default function ExportButton({ jobId }) {
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)

  if (!jobId) return null

  const handleExport = async () => {
    try {
      setExporting(true)
      setError(null)
      await exportReport(jobId)
    } catch (err) {
      setError('Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleExport}
        disabled={exporting}
        className="py-2.5 px-4 rounded-xl text-xs font-medium border border-white/[0.08]
          text-white/50 hover:border-white/[0.15] hover:text-white/80 disabled:opacity-50 transition-all
          flex items-center gap-2 glass-card !p-0 !py-2.5 !px-4"
      >
        <motion.svg
          className="w-3.5 h-3.5"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
          animate={exporting ? { y: [0, 2, 0] } : {}}
          transition={exporting ? { duration: 0.6, repeat: Infinity } : {}}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </motion.svg>
        {exporting ? (
          <span className="flex items-center gap-1.5">
            <motion.span
              className="w-3 h-3 border-2 border-white/30 border-t-white/70 rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
            />
            Exporting...
          </span>
        ) : 'Export PDF'}
      </motion.button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  )
}
