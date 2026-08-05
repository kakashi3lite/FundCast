/**
 * Scene System (SST) — scene definitions, registry, and core UI primitives.
 *
 * A "scene" is a named UI state with a declared purpose, entry routes,
 * transition metadata, and accessibility hints. The provider (see
 * `scene-provider.tsx`) tracks the active scene; `Scene` renders its
 * children only while active.
 */

import React, { useCallback, useContext } from 'react'
import { motion } from 'framer-motion'
import { cn } from './utils'

// ═══════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════

export interface SceneTransitionConfig {
  type?: 'fade' | 'slide' | 'container-transform' | 'shared-axis' | 'fade-through'
  direction?: 'left' | 'right' | 'up' | 'down' | 'x' | 'y'
  duration?: 'fast' | 'base' | 'slow' | string
  easing?: 'standard' | 'ease-in' | 'ease-out'
}

export interface SceneDefinition {
  id: string
  purpose: string
  entry: readonly string[]
  primaryLayout: string
  transition: SceneTransitionConfig
  microInteractions: readonly unknown[]
  states: readonly string[]
  accessibility: {
    announceTransitions: boolean
    reducedMotionFallback: SceneTransitionConfig
    focusManagement: 'auto' | 'manual' | string
  }
}

export type SceneId = string

export interface SceneSystemApi {
  currentScene: SceneId
  transition: (target: SceneId, transition?: SceneTransitionConfig) => void
  trackEvent: (event: string, data?: Record<string, unknown>) => void
  registerScene: (definition: SceneDefinition) => void
  getScene: (id: SceneId) => SceneDefinition | undefined
}

export const SceneSystemContext = React.createContext<SceneSystemApi | null>(null)

// ═══════════════════════════════════════════════════════════════════════
// Default scenes
// ═══════════════════════════════════════════════════════════════════════

const makeScene = (
  id: string,
  purpose: string,
  entry: string[],
  layout: string,
  transition: SceneTransitionConfig,
): SceneDefinition => ({
  id,
  purpose,
  entry,
  primaryLayout: layout,
  transition,
  microInteractions: [],
  states: ['loading', 'success'],
  accessibility: {
    announceTransitions: true,
    reducedMotionFallback: { type: 'fade', duration: 'fast' },
    focusManagement: 'auto',
  },
})

export const FUNDCAST_SCENES: Record<string, SceneDefinition> = {
  landing: makeScene('landing', 'Marketing and onboarding entry point', ['/'],
    'hero section with glass cards and CTA', { type: 'fade', duration: 'base', easing: 'standard' }),
  dashboard: makeScene('dashboard', 'User portfolio and trading overview', ['/dashboard'],
    'stats cards with real-time data', { type: 'container-transform', duration: 'base', easing: 'standard' }),
  markets: makeScene('markets', 'Market discovery and browsing', ['/markets'],
    'searchable market list with live prices', { type: 'slide', direction: 'left', duration: 'base', easing: 'standard' }),
  'market-detail': makeScene('market-detail', 'Individual market trading view', ['/markets/:id'],
    'price chart and order panel', { type: 'shared-axis', direction: 'x', duration: 'base', easing: 'standard' }),
}

// ═══════════════════════════════════════════════════════════════════════
// SceneSystem — imperative registry + transitions (framework-agnostic)
// ═══════════════════════════════════════════════════════════════════════

export class SceneSystem {
  private scenes = new Map<SceneId, SceneDefinition>()
  private listeners = new Set<(scene: SceneId) => void>()
  current = 'landing'
  private history: SceneId[] = []

  constructor(initialScene: SceneId = 'landing') {
    this.current = initialScene
  }

  register(definition: SceneDefinition): void {
    this.scenes.set(definition.id, definition)
  }

  get(id: SceneId): SceneDefinition | undefined {
    return this.scenes.get(id)
  }

  all(): SceneDefinition[] {
    return Array.from(this.scenes.values())
  }

  transitionTo(target: SceneId): void {
    if (target === this.current || !this.scenes.has(target)) return
    this.history.push(this.current)
    this.current = target
    this.listeners.forEach((listener) => listener(target))
  }

  back(): void {
    const previous = this.history.pop()
    if (previous) this.transitionTo(previous)
  }

  subscribe(listener: (scene: SceneId) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Hooks
// ═══════════════════════════════════════════════════════════════════════

export function useSceneSystem(): SceneSystemApi {
  const api = useContext(SceneSystemContext)
  if (!api) {
    // Safe no-op fallback so components can render outside a provider.
    return {
      currentScene: 'landing',
      transition: () => undefined,
      trackEvent: () => undefined,
      registerScene: () => undefined,
      getScene: () => undefined,
    }
  }
  return api
}

// ═══════════════════════════════════════════════════════════════════════
// Scene — renders children only while this scene is active
// ═══════════════════════════════════════════════════════════════════════

interface SceneProps {
  id: SceneId
  definition?: SceneDefinition
  children: React.ReactNode
}

export const Scene: React.FC<SceneProps> = ({ id, definition, children }) => {
  const { currentScene, registerScene } = useSceneSystem()

  React.useEffect(() => {
    if (definition) registerScene(definition)
  }, [definition, registerScene])

  if (currentScene !== id) return null

  const transition = definition?.transition ?? FUNDCAST_SCENES[id]?.transition
  const fade = !transition || transition.type === 'fade' || transition.type === 'fade-through'

  return (
    <motion.div
      initial={fade ? { opacity: 0, y: 8 } : { opacity: 0 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      {children}
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// Glass — glassmorphism surface
// ═══════════════════════════════════════════════════════════════════════

interface GlassProps extends React.HTMLAttributes<HTMLDivElement> {
  intensity?: 'subtle' | 'medium' | 'strong'
  tint?: 'neutral' | 'brand'
}

export const Glass: React.FC<GlassProps> = ({
  intensity = 'medium',
  tint = 'neutral',
  className,
  children,
  ...rest
}) => {
  const background =
    intensity === 'strong'
      ? 'bg-white/90 backdrop-blur-xl'
      : intensity === 'subtle'
        ? 'bg-white/40 backdrop-blur-sm'
        : 'bg-white/70 backdrop-blur-md'

  const border = tint === 'brand' ? 'border-purple-300/60' : 'border-white/60'

  return (
    <div
      className={cn('rounded-2xl shadow-sm border', background, border, className)}
      {...rest}
    >
      {children}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// Interactive — wraps children and reports interactions to telemetry
// ═══════════════════════════════════════════════════════════════════════

export interface InteractionSpec {
  trigger: string
  rules?: Record<string, unknown>
  feedback?: {
    visual?: 'pulse' | 'highlight' | 'glow' | 'scale'
    haptic?: 'low' | 'medium' | 'high' | 'heavy'
  }
}

interface InteractiveProps extends React.HTMLAttributes<HTMLDivElement> {
  interaction: InteractionSpec
}

export const Interactive: React.FC<InteractiveProps> = ({
  interaction,
  className,
  children,
  onClick,
  ...rest
}) => {
  const { trackEvent } = useSceneSystem()

  const handleClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      trackEvent(`interaction:${interaction.trigger}`, interaction.rules ?? {})
      onClick?.(event)
    },
    [interaction, onClick, trackEvent],
  )

  const visual = interaction.feedback?.visual

  return (
    <div
      className={cn(
        visual === 'pulse' && 'animate-dopamine-pulse',
        visual === 'glow' && 'hover:shadow-lg hover:shadow-purple-500/20',
        className,
      )}
      onClick={handleClick}
      {...rest}
    >
      {children}
    </div>
  )
}
