/**
 * Realtime Integration — WebSocket subscription hook, live price
 * component, and scene-transition helper.
 *
 * Uses a module-level WebSocket manager so hooks work with or without an
 * explicit provider. The connection is lazily opened on first subscribe.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useSceneSystem } from './scene-system'
import { SceneTransitionConfig } from './scene-system'

// ═══════════════════════════════════════════════════════════════════════
// WebSocket manager (singleton)
// ═══════════════════════════════════════════════════════════════════════

type MessageHandler = (data: unknown) => void

class RealtimeManager {
  private ws: WebSocket | null = null
  private url: string | null = null
  private handlers = new Map<string, Set<MessageHandler>>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private shouldReconnect = true
  private subscribers = 0

  configure(url: string): void {
    if (this.url === url) return
    this.url = url
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  subscribe(topic: string, handler: MessageHandler): () => void {
    this.subscribers += 1
    if (!this.handlers.has(topic)) this.handlers.set(topic, new Set())
    this.handlers.get(topic)!.add(handler)
    this.ensureConnected()
    return () => {
      this.subscribers = Math.max(0, this.subscribers - 1)
      this.handlers.get(topic)?.delete(handler)
      if (this.subscribers === 0) this.disconnect()
    }
  }

  private ensureConnected(): void {
    if (this.ws || !this.url) return
    try {
      this.ws = new WebSocket(this.url)
      this.ws.onmessage = (event) => {
        let payload: unknown
        try {
          payload = JSON.parse(event.data as string)
        } catch {
          payload = event.data
        }
        const message = (payload ?? {}) as Record<string, unknown>
        const topic = String(message.topic ?? 'default')
        const handlers = this.handlers.get(topic) ?? new Set<MessageHandler>()
        handlers.forEach((handler) => handler(message.data ?? message))
      }
      this.ws.onclose = () => {
        this.ws = null
        if (this.shouldReconnect && this.subscribers > 0) {
          this.reconnectTimer = setTimeout(() => this.ensureConnected(), 3000)
        }
      }
      this.ws.onerror = () => {
        this.ws?.close()
      }
    } catch {
      this.ws = null
    }
  }

  private disconnect(): void {
    this.shouldReconnect = false
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
    this.shouldReconnect = true
  }
}

const manager = new RealtimeManager()
manager.configure('ws://localhost:8000/ws')

/**
 * Configure the shared WebSocket URL (used by the provider at mount).
 */
export function configureRealtime(url: string): void {
  manager.configure(url)
}

// ═══════════════════════════════════════════════════════════════════════
// useRealtimeSubscription
// ═══════════════════════════════════════════════════════════════════════

interface RealtimeOptions {
  throttle?: number
  wsUrl?: string
}

export function useRealtimeSubscription<T = unknown>(
  topic: string,
  callback: (data: T) => void,
  options?: RealtimeOptions,
): void {
  const callbackRef = useRef(callback)
  callbackRef.current = callback
  const lastCall = useRef(0)

  useEffect(() => {
    if (options?.wsUrl) manager.configure(options.wsUrl)
  }, [options?.wsUrl])

  useEffect(() => {
    const throttleMs = options?.throttle ?? 0
    const handler: MessageHandler = (data) => {
      if (throttleMs <= 0) {
        callbackRef.current(data as T)
        return
      }
      const now = Date.now()
      if (now - lastCall.current >= throttleMs) {
        lastCall.current = now
        callbackRef.current(data as T)
      }
    }
    return manager.subscribe(topic, handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic, options?.throttle])
}

// ═══════════════════════════════════════════════════════════════════════
// RealtimePrice — subscribes to price updates for a market
// ═══════════════════════════════════════════════════════════════════════

interface RealtimePriceProps {
  marketId: string
  format?: (price: number) => string
  className?: string
}

export const RealtimePrice: React.FC<RealtimePriceProps> = ({
  marketId,
  format,
  className,
}) => {
  const [price, setPrice] = useState<number | null>(null)

  useRealtimeSubscription<{ market_id?: string; price?: number }>(
    'price-update',
    (data) => {
      if (data?.market_id === marketId && typeof data.price === 'number') {
        setPrice(data.price)
      }
    },
    { throttle: 250 },
  )

  if (price === null) {
    return <span className={className}>—</span>
  }
  return <span className={className}>{format ? format(price) : price.toFixed(2)}</span>
}

// ═══════════════════════════════════════════════════════════════════════
// useSceneTransition — transition helper targeting a scene
// ═══════════════════════════════════════════════════════════════════════

export function useSceneTransition(
  target: string,
  _transition?: SceneTransitionConfig,
): { transitionTo: () => void } {
  const { transition } = useSceneSystem()
  const transitionTo = useCallback(() => transition(target), [target, transition])
  return { transitionTo }
}
