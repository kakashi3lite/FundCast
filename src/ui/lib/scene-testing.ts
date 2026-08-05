/**
 * Scene Testing — helpers for exercising the Scene System in tests and
 * in-browser demos: scene registry inspection, simulated transitions,
 * and telemetry snapshots.
 */

import { SceneSystem, SceneDefinition, FUNDCAST_SCENES } from './scene-system'

/**
 * Build an isolated SceneSystem pre-loaded with the default FundCast
 * scenes, ready for unit tests.
 */
export function createTestSceneSystem(initialScene = 'landing'): SceneSystem {
  const system = new SceneSystem(initialScene)
  Object.values(FUNDCAST_SCENES).forEach((scene) => system.register(scene))
  return system
}

/** Return the registry of known scene definitions. */
export function getSceneRegistry(): SceneDefinition[] {
  return Object.values(FUNDCAST_SCENES)
}

/** Simulate a full navigation round-trip through every registered scene. */
export function simulateTransition(
  system: SceneSystem,
  targets: string[],
): Array<{ from: string; to: string }> {
  const log: Array<{ from: string; to: string }> = []
  const recorded: string[] = []
  const unsubscribe = system.subscribe((scene) => recorded.push(scene))
  targets.forEach((target) => {
    const from = system.current
    system.transitionTo(target)
    log.push({ from, to: system.current })
  })
  unsubscribe()
  return log
}

/**
 * Snapshot telemetry: current scene plus navigation history recorded by a
 * subscription during the provided callback.
 */
export function getTelemetrySnapshot(
  system: SceneSystem,
  run: () => void,
): { current: string; visited: string[] } {
  const visited: string[] = []
  const unsubscribe = system.subscribe((scene) => visited.push(scene))
  run()
  unsubscribe()
  return { current: system.current, visited }
}
