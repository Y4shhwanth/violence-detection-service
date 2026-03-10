import { motion } from 'framer-motion'
import { animation } from '../../design/tokens'

export default function GlassCard({
  children,
  className = '',
  animate = true,
  hover = false,
  index,
  padding = 'p-5',
  onClick,
  style,
}) {
  const motionProps = animate
    ? index !== undefined
      ? animation.stagger(index)
      : animation.fadeInUp
    : {}

  return (
    <motion.div
      {...motionProps}
      whileHover={hover ? animation.hover : undefined}
      whileTap={hover ? animation.tap : undefined}
      onClick={onClick}
      style={style}
      className={`glass-card ${padding} ${className}`}
    >
      {children}
    </motion.div>
  )
}
