import { useState } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { severityColor } from '../utils/formatters'
import ViolationModal from './ViolationModal'
import GlassCard from './ui/GlassCard'
import { StyledTooltip, axisProps } from '../design/chartHelpers'
import { animation } from '../design/tokens'

export default function ViolationTimeline({ violations }) {
  const [selectedViolation, setSelectedViolation] = useState(null)

  if (!violations || violations.length === 0) return null

  const timeViolations = violations.filter((v) => v.start_seconds !== undefined)
  const textViolations = violations.filter((v) => v.sentence_index !== undefined)

  const chartData = []
  if (timeViolations.length > 0) {
    const maxTime = Math.max(...timeViolations.map((v) => v.end_seconds || v.start_seconds || 0))
    for (let t = 0; t <= maxTime + 1; t += 0.5) {
      let score = 0
      for (const v of timeViolations) {
        if (t >= (v.start_seconds || 0) && t <= (v.end_seconds || v.start_seconds || 0)) {
          score = Math.max(score, v.peak_score || v.confidence || 50)
        }
      }
      chartData.push({ time: t, score })
    }
  }

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/60 mb-4">Violation Timeline</h3>

      {chartData.length > 0 && (
        <div className="h-40 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="violationGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" {...axisProps}
                tickFormatter={(v) => `${Math.floor(v / 60)}:${String(Math.floor(v % 60)).padStart(2, '0')}`}
              />
              <YAxis {...axisProps} domain={[0, 100]} />
              <Tooltip
                content={<StyledTooltip />}
                labelFormatter={(v) => `${Math.floor(v / 60)}:${String(Math.floor(v % 60)).padStart(2, '0')}`}
              />
              <Area type="monotone" dataKey="score" stroke="#ef4444" fill="url(#violationGradient)" strokeWidth={2} />
              {timeViolations.map((v, i) => (
                <ReferenceLine key={i} x={v.start_seconds} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.4} />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Violation list */}
      <div className="space-y-2">
        {violations.map((v, i) => {
          const sevColor = severityColor(v.severity)
          return (
            <motion.div
              key={i}
              {...animation.stagger(i)}
              onClick={() => setSelectedViolation(v)}
              className="flex items-center gap-3 p-3 rounded-xl glass-card !p-3 hover:bg-white/[0.03]
                cursor-pointer transition-colors group"
            >
              {/* Left severity bar */}
              <div className="w-1 h-8 rounded-full flex-shrink-0" style={{ backgroundColor: sevColor }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-white/50 uppercase">{v.modality}</span>
                  {v.start_time && (
                    <span className="text-xs text-white/25">
                      {v.start_time}{v.end_time ? ` - ${v.end_time}` : ''}
                    </span>
                  )}
                </div>
                <p className="text-sm text-white/60 truncate mt-0.5">{v.reason}</p>
              </div>
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{ color: sevColor, backgroundColor: `${sevColor}12` }}
              >
                {v.severity}
              </span>
            </motion.div>
          )
        })}
      </div>

      {textViolations.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/[0.06]">
          <h4 className="text-xs font-medium text-white/30 mb-2">Text Violations</h4>
          {textViolations.map((v, i) => (
            <div
              key={`text-${i}`}
              onClick={() => setSelectedViolation(v)}
              className="p-2.5 text-sm text-white/50 bg-white/[0.02] rounded-lg mb-1 cursor-pointer
                hover:bg-white/[0.04] transition-colors border border-white/[0.04]"
            >
              <span className="text-red-400 font-medium">Sentence {v.sentence_index + 1}:</span>{' '}
              {v.sentence?.substring(0, 80)}{v.sentence?.length > 80 ? '...' : ''}
            </div>
          ))}
        </div>
      )}

      <ViolationModal violation={selectedViolation} onClose={() => setSelectedViolation(null)} />
    </GlassCard>
  )
}
