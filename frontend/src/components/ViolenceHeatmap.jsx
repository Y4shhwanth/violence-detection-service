import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import GlassCard from './ui/GlassCard'
import { StyledTooltip, ChartGradients, gridProps, axisProps } from '../design/chartHelpers'
import { colors } from '../design/tokens'

export default function ViolenceHeatmap({ violations = [] }) {
  const chartData = useMemo(() => {
    if (!violations || violations.length === 0) return []

    const timePoints = new Map()
    violations.forEach(v => {
      const time = v.start_seconds ?? v.sentence_index ?? 0
      const key = Math.round(time)
      if (!timePoints.has(key)) {
        timePoints.set(key, { time: key, video: 0, audio: 0, text: 0 })
      }
      const point = timePoints.get(key)
      const confidence = v.confidence || 50
      if (v.modality === 'video') point.video = Math.max(point.video, confidence)
      else if (v.modality === 'audio') point.audio = Math.max(point.audio, confidence)
      else if (v.modality === 'text') point.text = Math.max(point.text, confidence)
    })

    return Array.from(timePoints.values()).sort((a, b) => a.time - b.time)
  }, [violations])

  if (chartData.length < 2) return null

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/70 mb-4">Violence Probability Timeline</h3>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <ChartGradients />
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="time" {...axisProps}
            label={{ value: 'Time (s)', position: 'bottom', fill: 'rgba(255,255,255,0.25)', fontSize: 10 }}
          />
          <YAxis domain={[0, 100]} {...axisProps}
            label={{ value: '%', angle: -90, position: 'insideLeft', fill: 'rgba(255,255,255,0.25)', fontSize: 10 }}
          />
          <Tooltip content={<StyledTooltip />} labelFormatter={v => `${v}s`} />
          <Legend wrapperStyle={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }} />
          <Line type="monotone" dataKey="video" stroke={colors.modality.video.base} strokeWidth={2} dot={false} name="Video" />
          <Line type="monotone" dataKey="audio" stroke={colors.modality.audio.base} strokeWidth={2} dot={false} name="Audio" />
          <Line type="monotone" dataKey="text" stroke={colors.modality.text.base} strokeWidth={2} dot={false} name="Text" />
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  )
}
