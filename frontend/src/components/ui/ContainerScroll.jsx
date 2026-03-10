import { useRef } from 'react'
import { useScroll, useTransform, motion } from 'framer-motion'

export function ContainerScroll({ titleComponent, children }) {
  const containerRef = useRef(null)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  })

  const scaleDimensions = useTransform(scrollYProgress, [0.05, 0.3], [0.85, 1])
  const rotate = useTransform(scrollYProgress, [0.05, 0.3], [20, 0])
  const translateY = useTransform(scrollYProgress, [0.05, 0.3], [100, 0])
  const opacity = useTransform(scrollYProgress, [0, 0.15], [0, 1])

  return (
    <div
      className="flex items-center justify-center relative py-10 md:py-20"
      ref={containerRef}
    >
      <div className="w-full relative" style={{ perspective: '1000px' }}>
        <Header translateY={translateY} opacity={opacity}>
          {titleComponent}
        </Header>
        <ContentCard rotate={rotate} scale={scaleDimensions}>
          {children}
        </ContentCard>
      </div>
    </div>
  )
}

function Header({ translateY, opacity, children }) {
  return (
    <motion.div
      style={{ translateY, opacity }}
      className="max-w-5xl mx-auto text-center mb-6"
    >
      {children}
    </motion.div>
  )
}

function ContentCard({ rotate, scale, children }) {
  return (
    <motion.div
      style={{
        rotateX: rotate,
        scale,
      }}
      className="max-w-5xl mx-auto w-full rounded-2xl border border-white/[0.08] bg-surface/50 shadow-glass overflow-hidden"
    >
      {children}
    </motion.div>
  )
}
