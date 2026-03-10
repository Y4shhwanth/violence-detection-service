import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import GlassCard from './ui/GlassCard'
import { StyledTooltip } from '../design/chartHelpers'
import { colors } from '../design/tokens'

const MODALITY_COLORS = {
  video: colors.modality.video.base,
  audio: colors.modality.audio.base,
  text: colors.modality.text.base,
}

export default function ModalityContributions({ contributions }) {
  const chartData = useMemo(() => {
    if (!contributions) return []
    return Object.entries(contributions)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: Math.round(value),
        color: MODALITY_COLORS[key] || '#8b5cf6',
      }))
  }, [contributions])

  if (chartData.length === 0) return null

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/70 mb-4">Modality Contributions</h3>

      <div className="flex items-center gap-6">
        <ResponsiveContainer width={120} height={120}>
          <PieChart>
            <defs>
              {chartData.map((entry, i) => (
                <linearGradient key={i} id={`contribGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor={entry.color} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={entry.color} stopOpacity={0.5} />
                </linearGradient>
              ))}
            </defs>
            <Pie
              data={chartData}
              cx="50%" cy="50%"
              innerRadius={30} outerRadius={50}
              dataKey="value" strokeWidth={0}
              animationBegin={200} animationDuration={800}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={`url(#contribGrad${i})`} />
              ))}
            </Pie>
            <Tooltip content={<StyledTooltip formatter={(v) => `${v}%`} />} />
          </PieChart>
        </ResponsiveContainer>

        <div className="space-y-2.5">
          {chartData.map((entry, i) => (
            <motion.div
              key={entry.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 * i + 0.3 }}
              className="flex items-center gap-2.5"
            >
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: entry.color, boxShadow: `0 0 8px ${entry.color}30` }}
              />
              <span className="text-xs text-white/50">{entry.name}</span>
              <span className="text-xs font-bold text-white">{entry.value}%</span>
            </motion.div>
          ))}
        </div>
      </div>
    </GlassCard>
  )
}
