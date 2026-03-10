import React from 'react'
import { chartTheme } from './tokens'

// Shared styled tooltip for all Recharts charts
export function StyledTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null
  return (
    <div style={chartTheme.tooltip.contentStyle}>
      {label && <p style={chartTheme.tooltip.labelStyle}>{label}</p>}
      {payload.map((entry, i) => (
        <p key={i} style={{ ...chartTheme.tooltip.itemStyle, color: entry.color || chartTheme.tooltip.itemStyle.color }}>
          {entry.name}: {formatter ? formatter(entry.value) : entry.value}
        </p>
      ))}
    </div>
  )
}

// Gradient defs for SVG charts
export function ChartGradients() {
  return (
    <defs>
      <linearGradient id="gradientRed" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#ef4444" stopOpacity={0.4} />
        <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
      </linearGradient>
      <linearGradient id="gradientGreen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
        <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
      </linearGradient>
      <linearGradient id="gradientPurple" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} />
        <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.02} />
      </linearGradient>
      <linearGradient id="gradientCyan" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} />
        <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.02} />
      </linearGradient>
      <linearGradient id="gradientYellow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
        <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
      </linearGradient>
      <linearGradient id="gradientStrokeRed" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#ef4444" />
        <stop offset="100%" stopColor="#ec4899" />
      </linearGradient>
      <linearGradient id="gradientStrokeGreen" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#22c55e" />
        <stop offset="100%" stopColor="#10b981" />
      </linearGradient>
    </defs>
  )
}

// Shared grid/axis props
export const gridProps = {
  strokeDasharray: chartTheme.grid.strokeDasharray,
  stroke: chartTheme.grid.stroke,
}

export const axisProps = {
  tick: chartTheme.axis.tick,
  axisLine: chartTheme.axis.axisLine,
  tickLine: false,
}
