/**
 * Scene System + engagement libraries — public barrel.
 */
export {
  SceneSystem,
  SceneSystemContext,
  useSceneSystem,
  Scene,
  Glass,
  Interactive,
  FUNDCAST_SCENES,
} from './scene-system'
export type {
  SceneDefinition,
  SceneId,
  SceneTransitionConfig,
  SceneSystemApi,
  InteractionSpec,
} from './scene-system'

export {
  SceneProvider,
  CompleteSceneSystemProvider,
} from './scene-provider'
export type {
  SceneSystemConfig,
  RealtimeConfig,
  InspectorConfig,
} from './scene-provider'

export {
  StaggerList,
  SharedElement,
  MorphingCard,
  AnimatedNumber,
} from './advanced-animations'

export {
  DopamineTrigger,
  StreakTracker,
  NearMissDetector,
  LiveSocialFeed,
  VIPStatus,
  LossRecoveryPrompt,
} from './gambling-psychology'
export type { DopamineEvent, VipTier } from './gambling-psychology'

export {
  ExclusiveAccessGate,
  ReferralDashboard,
  CompetitionLeaderboard,
  NetworkMomentumDisplay,
} from './viral-growth'
export type { ReferralStats, LeaderboardEntry } from './viral-growth'

export {
  RealtimePrice,
  useRealtimeSubscription,
  useSceneTransition,
} from './realtime-integration'

export { SceneInspector } from './scene-inspector'

export {
  createTestSceneSystem,
  getSceneRegistry,
  simulateTransition,
  getTelemetrySnapshot,
} from './scene-testing'

export { cn } from './utils'
