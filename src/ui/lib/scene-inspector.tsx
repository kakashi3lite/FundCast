/**
 * Scene Inspector — developer overlay for debugging the Scene System.
 * Toggled with a configurable hotkey (default: backtick).
 */

import React, { useEffect, useState } from 'react'
import { useSceneSystem } from './scene-system'
import { FUNDCAST_SCENES } from './scene-system'

interface SceneInspectorProps {
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  hotkey?: string
}

const POSITION_CLASS: Record<string, string> = {
  'top-left': 'top-4 left-4',
  'top-right': 'top-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'bottom-right': 'bottom-4 right-4',
}

export const SceneInspector: React.FC<SceneInspectorProps> = ({
  position = 'bottom-right',
  hotkey = '`',
}) => {
  const { currentScene, transition, trackEvent } = useSceneSystem()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === hotkey && !event.metaKey && !event.ctrlKey) {
        setOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [hotkey])

  if (!open) return null

  const scenes = Object.values(FUNDCAST_SCENES)

  return (
    <div className={`fixed z-[100] ${POSITION_CLASS[position]} w-72 rounded-xl bg-slate-900/95 border border-slate-700 text-white shadow-2xl overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <span className="text-xs font-semibold tracking-wide uppercase text-purple-300">
          Scene Inspector
        </span>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white text-sm" aria-label="Close inspector">
          ✕
        </button>
      </div>

      <div className="px-4 py-3 border-b border-slate-700/60">
        <div className="text-xs text-gray-400 mb-1">Current scene</div>
        <div className="text-sm font-semibold text-white">{currentScene}</div>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {scenes.map((scene) => (
          <button
            key={scene.id}
            onClick={() => {
              transition(scene.id)
              trackEvent(`inspector:navigate`, { target: scene.id })
            }}
            className={`w-full text-left px-4 py-2 text-sm transition-colors ${
              scene.id === currentScene
                ? 'bg-purple-600/30 text-purple-200'
                : 'text-gray-300 hover:bg-slate-800'
            }`}
          >
            <span className="font-medium">{scene.id}</span>
            <span className="block text-xs text-gray-500 truncate">{scene.purpose}</span>
          </button>
        ))}
      </div>

      <div className="px-4 py-2 bg-slate-800/60 text-[10px] text-gray-500">
        Press <kbd className="px-1 rounded bg-slate-700 text-gray-300">{hotkey}</kbd> to toggle
      </div>
    </div>
  )
}
