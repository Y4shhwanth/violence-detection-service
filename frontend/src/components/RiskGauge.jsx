import { motion } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import AnimatedCounter from './ui/AnimatedCounter'

export default function RiskGauge({ riskData }) {
  if (!riskData) return null

  const {
    violence_probability = 0,
    severity = 'Low',
    risk_level = 'Low',
    recommendation = '',
    modality_scores = {},
    contributing_factors = [],
  } = riskData

  const size = 180
  const strokeWidth = 14
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(100, Math.max(0, violence_probability))
  const dashOffset = circumference - (progress / 100) * circumference

  const getColor = (score) => {
    if (score >= 90) return '#dc2626'
    if (score >= 70) return '#f97316'
    if (score >= 40) return '#eab308'
    return '#22c55e'
  }

  const gaugeColor = getColor(violence_probability)

  return (
    <GlassCard>
      <h3 className="text-sm font-medium text-white/50 mb-4">Violence Risk Assessment</h3>

      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* SVG Circular Gauge */}
        <div className="relative flex-shrink-0">
          <svg width={size} height={size} className="transform -rotate-90">
            <circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={strokeWidth}
            />
            {/* Gradient arc */}
            <defs>
              <linearGradient id="riskGradient" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#22c55e" />
                <stop offset="50%" stopColor="#eab308" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>
            <motion.circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke={gaugeColor} strokeWidth={strokeWidth}
              strokeLinecap="round" strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
              style={{ filter: `drop-shadow(0 0 10px ${gaugeColor}40)` }}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <AnimatedCounter
              value={violence_probability}
              suffix="%"
              className="text-3xl font-bold"
            />
            <span className="text-xs text-white/30 mt-1">Risk Score</span>
          </div>
        </div>

        {/* Details panel */}
        <div className="flex-1 space-y-3 w-full">
          <div className="flex items-center gap-2">
            <span
              className="px-3 py-1 rounded-full text-xs font-semibold"
              style={{
                backgroundColor: `${gaugeColor}15`,
                color: gaugeColor,
                border: `1px solid ${gaugeColor}30`,
              }}
            >
              {risk_level}
            </span>
            <span className="text-xs text-white/30">severity</span>
          </div>

          {Object.keys(modality_scores).length > 0 && (
            <div className="space-y-2">
              {Object.entries(modality_scores).map(([modality, score]) => (
                <div key={modality} className="flex items-center gap-2">
                  <span className="text-xs text-white/40 w-12 capitalize">{modality}</span>
                  <div className="flex-1 bg-white/[0.04] rounded-full h-2 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: `linear-gradient(90deg, ${getColor(score)}80, ${getColor(score)})` }}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, score)}%` }}
                      transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                    />
                  </div>
                  <span className="text-xs text-white/40 w-10 text-right">
                    {score.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {recommendation && (
            <p className="text-xs text-white/40 leading-relaxed mt-2">{recommendation}</p>
          )}

          {contributing_factors.length > 0 && (
            <div className="mt-3 space-y-1">
              <span className="text-xs text-white/30">Contributing factors:</span>
              {contributing_factors.slice(0, 3).map((factor, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    factor.impact === 'high' ? 'bg-red-500' : 'bg-yellow-500'
                  }`} />
                  <span className="text-white/40">{factor.description}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  )
}
