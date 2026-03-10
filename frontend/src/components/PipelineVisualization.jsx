import { motion } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import { colors } from '../design/tokens'

const STEPS = [
  { key: 'upload', label: 'Upload', icon: '1' },
  { key: 'video', label: 'Video', icon: '2' },
  { key: 'audio', label: 'Audio', icon: '3' },
  { key: 'text', label: 'Text', icon: '4' },
  { key: 'fusion', label: 'Fusion', icon: '5' },
  { key: 'enhance', label: 'Enhance', icon: '6' },
  { key: 'complete', label: 'Complete', icon: '7' },
]

const STEP_MAP = {
  'Uploading...': 0,
  'Queued for processing': 0,
  'Starting analysis': 1,
  'Extracting video frames': 1,
  'Analyzing video content': 1,
  'Analyzing audio content': 2,
  'Analyzing text content': 3,
  'Fusing modality results': 4,
  'Enhancing results': 5,
  'Storing results': 6,
  'Generating report': 6,
  'Complete': 6,
}

export default function PipelineVisualization({ currentStep, progress }) {
  const activeIdx = STEP_MAP[currentStep] ?? Math.floor((progress / 100) * 6)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard animate={false}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-medium text-white/70">
            {currentStep || 'Processing...'}
          </span>
          <span className="text-xs text-white/35">{progress}%</span>
        </div>

        {/* Gradient progress bar with shimmer */}
        <div className="w-full h-2 bg-white/[0.04] rounded-full overflow-hidden mb-6">
          <motion.div
            className="h-full rounded-full relative"
            style={{ background: 'linear-gradient(90deg, #ef4444, #ec4899)' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          >
            <div className="absolute inset-0 shimmer opacity-50" />
          </motion.div>
        </div>

        {/* Pipeline steps with connecting lines */}
        <div className="flex items-center justify-between relative">
          {/* Connecting line */}
          <div className="absolute top-4 left-4 right-4 h-[2px] bg-white/[0.04]">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #22c55e, #ef4444)' }}
              animate={{ width: `${(activeIdx / (STEPS.length - 1)) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>

          {STEPS.map((step, idx) => {
            const isActive = idx === activeIdx
            const isDone = idx < activeIdx
            const isPending = idx > activeIdx

            return (
              <div key={step.key} className="flex flex-col items-center gap-2 flex-1 relative z-10">
                <motion.div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold
                    border-2 transition-all duration-300
                    ${isDone ? 'bg-green-500/20 border-green-500/40 text-green-400' : ''}
                    ${isActive ? 'border-red-500/60 text-white' : ''}
                    ${isPending ? 'bg-white/[0.02] border-white/[0.06] text-white/25' : ''}
                  `}
                  style={isActive ? { background: 'linear-gradient(135deg, rgba(239,68,68,0.3), rgba(236,72,153,0.3))' } : undefined}
                  animate={isActive ? { scale: [1, 1.12, 1], boxShadow: ['0 0 0px rgba(239,68,68,0)', '0 0 16px rgba(239,68,68,0.3)', '0 0 0px rgba(239,68,68,0)'] } : {}}
                  transition={isActive ? { duration: 1.5, repeat: Infinity } : {}}
                >
                  {isDone ? (
                    <motion.svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 300 }}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </motion.svg>
                  ) : step.icon}
                </motion.div>
                <span className={`text-[10px] font-medium ${isActive ? 'text-red-400' : isDone ? 'text-green-400/70' : 'text-white/20'}`}>
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </GlassCard>
    </motion.div>
  )
}
