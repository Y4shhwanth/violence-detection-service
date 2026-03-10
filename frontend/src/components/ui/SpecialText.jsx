import { useEffect, useRef, useState } from 'react'
import { useInView } from 'motion/react'

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*'

export default function SpecialText({
  children,
  speed = 40,
  delay = 0,
  className = '',
  ...props
}) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  const [displayed, setDisplayed] = useState('')
  const text = typeof children === 'string' ? children : ''

  useEffect(() => {
    if (!inView || !text) return

    let timeout
    let frame = 0
    const total = text.length

    const startTimeout = setTimeout(() => {
      const scramble = () => {
        frame++
        const revealed = Math.floor(frame / 3)
        if (revealed >= total) {
          setDisplayed(text)
          return
        }
        let result = ''
        for (let i = 0; i < total; i++) {
          if (i < revealed) {
            result += text[i]
          } else if (text[i] === ' ') {
            result += ' '
          } else {
            result += CHARS[Math.floor(Math.random() * CHARS.length)]
          }
        }
        setDisplayed(result)
        timeout = setTimeout(scramble, speed)
      }
      scramble()
    }, delay * 1000)

    return () => {
      clearTimeout(startTimeout)
      clearTimeout(timeout)
    }
  }, [inView, text, speed, delay])

  return (
    <span ref={ref} className={className} {...props}>
      {displayed || text}
    </span>
  )
}
