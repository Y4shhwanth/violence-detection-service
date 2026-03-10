import { motion } from 'framer-motion'
import { scoreColor } from '../utils/formatters'
import AnimatedCounter from './ui/AnimatedCounter'

export default function ConfidenceMeter({ score, label }) {
  const radius = 60
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = scoreColor(score)

  // Tick marks
  const ticks = Array.from({ length: 40 }, (_, i) => {
    const angle = (i / 40) * 360 - 90
    const rad = (angle * Math.PI) / 180
    const inner = 52
    const outer = 56
    return {
      x1: 70 + Math.cos(rad) * inner,
      y1: 70 + Math.sin(rad) * inner,
      x2: 70 + Math.cos(rad) * outer,
      y2: 70 + Math.sin(rad) * outer,
      active: i / 40 <= score / 100,
    }
  })

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
          {/* Background circle */}
          <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="8" />
          {/* Tick marks */}
          {ticks.map((t, i) => (
            <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
              stroke={t.active ? color : 'rgba(255,255,255,0.06)'}
              strokeWidth="1" strokeLinecap="round"
            />
          ))}
          {/* Gradient progress circle */}
          <motion.circle
            cx="70" cy="70" r={radius}
            fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 8px ${color}50)` }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <AnimatedCounter
            value={score || 0}
            decimals={1}
            className="text-2xl font-bold"
            style={{ color }}
          />
          <span className="text-[10px] text-white/30 uppercase tracking-wider mt-0.5">
            {label || 'Score'}
          </span>
        </div>
      </div>
    </div>
  )
}
