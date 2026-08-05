/**
 * Advanced Animations — stagger, shared-element, morphing and number
 * animation primitives built on Framer Motion.
 */

import React, { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from './utils'

// ═══════════════════════════════════════════════════════════════════════
// StaggerList — animates children in with a stagger delay
// ═══════════════════════════════════════════════════════════════════════

interface StaggerListProps {
  staggerDelay?: 'base' | 'cards' | 'list' | number
  direction?: 'up' | 'down' | 'left' | 'right'
  className?: string
  children: React.ReactNode
}

const DELAY_MAP: Record<string, number> = {
  base: 0.05,
  cards: 0.08,
  list: 0.03,
}

export const StaggerList: React.FC<StaggerListProps> = ({
  staggerDelay = 'base',
  direction = 'up',
  className,
  children,
}) => {
  const delay = typeof staggerDelay === 'number' ? staggerDelay : DELAY_MAP[staggerDelay] ?? 0.05
  const offset = direction === 'up' ? 24 : direction === 'down' ? -24 : direction === 'left' ? -24 : 24

  const items = useMemo(() => React.Children.toArray(children), [children])

  return (
    <div className={className}>
      {items.map((child, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: offset, x: direction === 'left' || direction === 'right' ? offset : 0 }}
          animate={{ opacity: 1, y: 0, x: 0 }}
          transition={{ delay: index * delay, duration: 0.35, ease: 'easeOut' }}
        >
          {child}
        </motion.div>
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// SharedElement — enables shared-element transitions between scenes
// ═══════════════════════════════════════════════════════════════════════

interface SharedElementProps {
  id: string
  className?: string
  children: React.ReactNode
}

export const SharedElement: React.FC<SharedElementProps> = ({ id, className, children }) => {
  return (
    <motion.div
      layoutId={`shared-${id}`}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// MorphingCard — animates between collapsed/expanded states
// ═══════════════════════════════════════════════════════════════════════

interface MorphingCardProps {
  state?: 'collapsed' | 'expanded'
  className?: string
  children: React.ReactNode
}

export const MorphingCard: React.FC<MorphingCardProps> = ({
  state = 'collapsed',
  className,
  children,
}) => {
  const expanded = state === 'expanded'
  return (
    <motion.div
      layout
      animate={{ scale: expanded ? 1.02 : 1, borderRadius: expanded ? 16 : 12 }}
      transition={{ type: 'spring', stiffness: 260, damping: 26 }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// AnimatedNumber — smoothly animates between numeric values
// ═══════════════════════════════════════════════════════════════════════

interface AnimatedNumberProps {
  value: number
  format?: (value: number) => string
  className?: string
  colorize?: boolean
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  format,
  className,
  colorize = false,
}) => {
  const [display, setDisplay] = React.useState(value)

  React.useEffect(() => {
    const from = display
    const to = value
    if (from === to) return

    const start = performance.now()
    const duration = 500
    let raf = 0

    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3) // ease-out cubic
      setDisplay(from + (to - from) * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  const colorClass =
    colorize && display !== 0
      ? display > 0
        ? 'text-green-600'
        : 'text-red-600'
      : undefined

  const rendered = format ? format(display) : Math.round(display).toLocaleString()

  return <span className={cn(colorClass, className)}>{rendered}</span>
}

// ═══════════════════════════════════════════════════════════════════════
// AnimatePresence helper — portal for exit animations
// ═══════════════════════════════════════════════════════════════════════

export { AnimatePresence }
