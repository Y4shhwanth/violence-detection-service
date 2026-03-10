// Design Tokens — single source of truth for the entire UI

export const colors = {
  // Backgrounds
  bg: {
    primary: '#0a0a0a',
    secondary: '#111111',
    card: 'rgba(17, 17, 17, 0.8)',
    cardSolid: '#111111',
    elevated: 'rgba(25, 25, 25, 0.9)',
    hover: 'rgba(255, 255, 255, 0.03)',
    overlay: 'rgba(0, 0, 0, 0.6)',
  },
  // Borders (unified hierarchy)
  border: {
    subtle: 'rgba(255, 255, 255, 0.06)',
    default: 'rgba(255, 255, 255, 0.08)',
    strong: 'rgba(255, 255, 255, 0.12)',
    accent: 'rgba(239, 68, 68, 0.2)',
  },
  // Text
  text: {
    primary: '#ffffff',
    secondary: 'rgba(255, 255, 255, 0.7)',
    tertiary: 'rgba(255, 255, 255, 0.5)',
    muted: 'rgba(255, 255, 255, 0.35)',
    disabled: 'rgba(255, 255, 255, 0.2)',
  },
  // Status / severity
  status: {
    safe: { base: '#22c55e', glow: 'rgba(34, 197, 94, 0.15)', text: '#4ade80' },
    low: { base: '#22c55e', glow: 'rgba(34, 197, 94, 0.12)', text: '#4ade80' },
    moderate: { base: '#eab308', glow: 'rgba(234, 179, 8, 0.12)', text: '#facc15' },
    high: { base: '#f97316', glow: 'rgba(249, 115, 22, 0.12)', text: '#fb923c' },
    critical: { base: '#ef4444', glow: 'rgba(239, 68, 68, 0.15)', text: '#f87171' },
    violation: { base: '#ef4444', glow: 'rgba(239, 68, 68, 0.2)', text: '#f87171' },
    verified: { base: '#22c55e', glow: 'rgba(34, 197, 94, 0.2)', text: '#4ade80' },
  },
  // Modality colors
  modality: {
    video: { base: '#8b5cf6', light: '#a78bfa', glow: 'rgba(139, 92, 246, 0.15)' },
    audio: { base: '#06b6d4', light: '#22d3ee', glow: 'rgba(6, 182, 212, 0.15)' },
    text: { base: '#f59e0b', light: '#fbbf24', glow: 'rgba(245, 158, 11, 0.15)' },
  },
  // Accent gradients
  gradient: {
    primary: 'linear-gradient(135deg, #ef4444, #ec4899)',
    safe: 'linear-gradient(135deg, #22c55e, #10b981)',
    danger: 'linear-gradient(135deg, #ef4444, #f97316)',
    warning: 'linear-gradient(135deg, #eab308, #f97316)',
    purple: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
    mesh: 'radial-gradient(ellipse at 20% 50%, rgba(239, 68, 68, 0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(139, 92, 246, 0.06) 0%, transparent 50%), radial-gradient(ellipse at 50% 80%, rgba(6, 182, 212, 0.04) 0%, transparent 50%)',
  },
}

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 12px rgba(0, 0, 0, 0.4)',
  lg: '0 8px 30px rgba(0, 0, 0, 0.5)',
  glow: {
    red: '0 0 20px rgba(239, 68, 68, 0.15)',
    green: '0 0 20px rgba(34, 197, 94, 0.15)',
    purple: '0 0 20px rgba(139, 92, 246, 0.15)',
    cyan: '0 0 20px rgba(6, 182, 212, 0.15)',
  },
  glass: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
}

export const animation = {
  fadeInUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] },
  },
  stagger: (index, delay = 0.06) => ({
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4, delay: index * delay, ease: [0.22, 1, 0.36, 1] },
  }),
  spring: { type: 'spring', stiffness: 300, damping: 25 },
  hover: { scale: 1.02, transition: { duration: 0.2 } },
  tap: { scale: 0.98 },
}

export const chartTheme = {
  tooltip: {
    contentStyle: {
      background: 'rgba(17, 17, 17, 0.95)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: '12px',
      padding: '10px 14px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      backdropFilter: 'blur(12px)',
    },
    labelStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 11, fontWeight: 500 },
    itemStyle: { color: 'rgba(255, 255, 255, 0.9)', fontSize: 12 },
  },
  grid: {
    strokeDasharray: '3 3',
    stroke: 'rgba(255, 255, 255, 0.06)',
  },
  axis: {
    tick: { fill: 'rgba(255, 255, 255, 0.35)', fontSize: 10 },
    axisLine: { stroke: 'rgba(255, 255, 255, 0.06)' },
  },
  colors: ['#ef4444', '#8b5cf6', '#06b6d4', '#f59e0b', '#22c55e', '#ec4899'],
}
