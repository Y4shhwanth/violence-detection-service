import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import GlassCard from './ui/GlassCard'
import AnimatedCounter from './ui/AnimatedCounter'
import { StyledTooltip, gridProps, axisProps } from '../design/chartHelpers'
import { animation } from '../design/tokens'

const PIE_COLORS = ['#ef4444', '#f59e0b', '#22c55e']

export default function ModerationDashboard({ getStats, historyCount }) {
  // Recompute stats whenever historyCount changes (new analysis added)
  const stats = useMemo(() => getStats(30), [getStats, historyCount])

  if (!stats?.success) {
    return (
      <GlassCard className="text-center py-12">
        <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-white/[0.04] flex items-center justify-center">
          <svg className="w-6 h-6 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <p className="text-sm text-white/40">No data available yet. Run some analyses first.</p>
      </GlassCard>
    )
  }

  const { totals, daily } = stats
  const pieData = [
    { name: 'Violations', value: totals.violations || 0 },
    { name: 'Reviews', value: totals.reviews || 0 },
    { name: 'Verified', value: totals.verified || 0 },
  ].filter(d => d.value > 0)

  const statCards = [
    { label: 'Total Analyses', value: totals.total_analyses, color: 'text-white' },
    { label: 'Violations', value: totals.violations, color: 'text-red-400' },
    { label: 'False Positives', value: totals.false_positives, color: 'text-yellow-400' },
    { label: 'False Negatives', value: totals.false_negatives, color: 'text-orange-400' },
  ]

  return (
    <motion.div {...animation.fadeInUp} className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((card, i) => (
          <GlassCard key={card.label} index={i} padding="p-4" hover>
            <p className="text-xs text-white/35 mb-1">{card.label}</p>
            <AnimatedCounter value={card.value} className={`text-2xl font-bold ${card.color}`} />
          </GlassCard>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Distribution pie */}
        {pieData.length > 0 && (
          <GlassCard index={4}>
            <h3 className="text-sm font-semibold text-white/70 mb-4">Decision Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <defs>
                  {PIE_COLORS.map((color, i) => (
                    <linearGradient key={i} id={`pieGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor={color} stopOpacity={0.9} />
                      <stop offset="100%" stopColor={color} stopOpacity={0.6} />
                    </linearGradient>
                  ))}
                </defs>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  animationBegin={200} animationDuration={800}
                >
                  {pieData.map((_, i) => <Cell key={i} fill={`url(#pieGrad${i})`} stroke="none" />)}
                </Pie>
                <Tooltip content={<StyledTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </GlassCard>
        )}

        {/* Trend line */}
        {daily.length > 1 && (
          <GlassCard index={5}>
            <h3 className="text-sm font-semibold text-white/70 mb-4">Analysis Trend</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={[...daily].reverse()}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="date" {...axisProps} />
                <YAxis {...axisProps} />
                <Tooltip content={<StyledTooltip />} />
                <Line type="monotone" dataKey="total_analyses" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Analyses" />
                <Line type="monotone" dataKey="violations" stroke="#ef4444" strokeWidth={2} dot={false} name="Violations" />
              </LineChart>
            </ResponsiveContainer>
          </GlassCard>
        )}
      </div>
    </motion.div>
  )
}
