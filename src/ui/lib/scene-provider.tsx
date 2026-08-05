/**
 * Scene Provider — React context wiring for the Scene System.
 *
 * Exposes:
 * - `SceneProvider` — minimal provider (used by `App` / pages).
 * - `CompleteSceneSystemProvider` — full provider with telemetry,
 *   realtime + inspector wiring (used by the example apps).
 * - `useSceneSystem` — re-exported from `scene-system`.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  SceneSystem,
  SceneSystemContext,
  SceneSystemApi,
  SceneDefinition,
  SceneId,
  SceneTransitionConfig,
  FUNDCAST_SCENES,
} from './scene-system'
import { configureRealtime } from './realtime-integration'

export { SceneSystemContext } from './scene-system'
export { useSceneSystem } from './scene-system'

// ═══════════════════════════════════════════════════════════════════════
// SceneProvider — minimal provider
// ═══════════════════════════════════════════════════════════════════════

interface SceneProviderProps {
  children: React.ReactNode
}

export const SceneProvider: React.FC<SceneProviderProps> = ({ children }) => {
  const [sceneSystem] = useState(() => new SceneSystem('landing'))
  const [currentScene, setCurrentScene] = useState<SceneId>('landing')
  const scenesRef = React.useRef(new Map<SceneId, SceneDefinition>())

  // Register the default FundCast scenes.
  useEffect(() => {
    Object.values(FUNDCAST_SCENES).forEach((def) => sceneSystem.register(def))
  }, [sceneSystem])

  useEffect(() => {
    return sceneSystem.subscribe((scene) => setCurrentScene(scene))
  }, [sceneSystem])

  const api = useMemo<SceneSystemApi>(() => {
    const transition = (target: SceneId, _transition?: SceneTransitionConfig) => {
      sceneSystem.transitionTo(target)
    }
    const trackEvent = (event: string, data?: Record<string, unknown>) => {
      // Telemetry hook — wire to analytics in production.
      if (import.meta.env?.DEV) {
        console.debug(`[scene] ${event}`, data ?? {})
      }
    }
    const registerScene = (definition: SceneDefinition) => {
      scenesRef.current.set(definition.id, definition)
      sceneSystem.register(definition)
    }
    const getScene = (id: SceneId) => scenesRef.current.get(id)
    return { currentScene, transition, trackEvent, registerScene, getScene }
  }, [currentScene, sceneSystem])

  return (
    <SceneSystemContext.Provider value={api}>{children}</SceneSystemContext.Provider>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// CompleteSceneSystemProvider — full-featured provider
// ═══════════════════════════════════════════════════════════════════════

export interface SceneSystemConfig {
  initialScene?: SceneId
  enableTelemetry?: boolean
  enablePreloading?: boolean
  debugMode?: boolean
}

export interface RealtimeConfig {
  wsUrl?: string
  enableMetrics?: boolean
}

export interface InspectorConfig {
  enabled?: boolean
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  hotkey?: string
}

interface CompleteSceneSystemProviderProps {
  sceneConfig?: SceneSystemConfig
  realtimeConfig?: RealtimeConfig
  inspectorConfig?: InspectorConfig
  children: React.ReactNode
}

export const CompleteSceneSystemProvider: React.FC<CompleteSceneSystemProviderProps> = ({
  sceneConfig,
  realtimeConfig,
  inspectorConfig,
  children,
}) => {
  const initialScene = sceneConfig?.initialScene ?? 'landing'
  const [sceneSystem] = useState(() => new SceneSystem(initialScene))
  const [currentScene, setCurrentScene] = useState<SceneId>(initialScene)
  const scenesRef = React.useRef(new Map<SceneId, SceneDefinition>())

  useEffect(() => {
    Object.values(FUNDCAST_SCENES).forEach((def) => sceneSystem.register(def))
  }, [sceneSystem])

  useEffect(() => {
    return sceneSystem.subscribe((scene) => setCurrentScene(scene))
  }, [sceneSystem])

  const trackEvent = useCallback((event: string, data?: Record<string, unknown>) => {
    if (sceneConfig?.debugMode || sceneConfig?.enableTelemetry) {
      console.debug(`[scene:telemetry] ${event}`, data ?? {})
    }
  }, [sceneConfig?.debugMode, sceneConfig?.enableTelemetry])

  // Configure the realtime WebSocket manager when a URL is provided.
  useEffect(() => {
    if (realtimeConfig?.wsUrl) {
      configureRealtime(realtimeConfig.wsUrl)
    }
  }, [realtimeConfig?.wsUrl])

  const api = useMemo<SceneSystemApi>(() => ({
    currentScene,
    transition: (target) => sceneSystem.transitionTo(target),
    trackEvent,
    registerScene: (definition) => {
      scenesRef.current.set(definition.id, definition)
      sceneSystem.register(definition)
    },
    getScene: (id) => scenesRef.current.get(id),
  }), [currentScene, sceneSystem, trackEvent])

  return (
    <SceneSystemContext.Provider value={api}>
      {children}
      {inspectorConfig?.enabled && <SceneInspector position={inspectorConfig.position} hotkey={inspectorConfig.hotkey} />}
    </SceneSystemContext.Provider>
  )
}

// Lazy-import the inspector to avoid a circular dependency at module load.
import { SceneInspector } from './scene-inspector'
