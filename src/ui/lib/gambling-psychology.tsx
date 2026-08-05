/**
 * Engagement & Retention Mechanics
 *
 * Reusable engagement UI primitives: celebratory feedback triggers,
 * streak tracking, near-miss state rendering, social proof feeds,
 * VIP status, and strategy-review prompts.
 *
 * These components are engagement affordances (feedback, streaks, status)
 * — they render UI state and call caller-provided callbacks; they do not
 * execute any trading logic themselves.
 */

import React, { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from './utils'

// ═══════════════════════════════════════════════════════════════════════
// DopamineTrigger — wraps content with celebratory feedback
// ═══════════════════════════════════════════════════════════════════════

export interface DopamineEvent {
  type: 'big_win' | 'social_win' | 'achievement' | 'streak' | 'level_up'
  intensity: 'low' | 'medium' | 'high' | 'heavy'
  message?: string
}

interface DopamineTriggerProps {
  event: DopamineEvent
  children: React.ReactNode
  className?: string
}

export const DopamineTrigger: React.FC<DopamineTriggerProps> = ({ event, children, className }) => {
  const [pulsed, setPulsed] = useState(false)

  const emoji = useMemo(() => {
    switch (event.type) {
      case 'big_win': return '🎉'
      case 'social_win': return '🏆'
      case 'achievement': return '⭐'
      case 'streak': return '🔥'
      case 'level_up': return '🚀'
      default: return '✨'
    }
  }, [event.type])

  const scale = event.intensity === 'high' ? 1.06 : event.intensity === 'medium' ? 1.03 : event.intensity === 'heavy' ? 1.09 : 1.01

  return (
    <motion.div
      className={cn('relative', className)}
      animate={pulsed ? { scale: 1 } : { scale }}
      transition={{ type: 'spring', stiffness: 400, damping: 15 }}
      onAnimationComplete={() => setPulsed(true)}
      aria-label={event.message}
    >
      <span className="mr-1" aria-hidden>
        {emoji}
      </span>
      {children}
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// StreakTracker — displays current/best streaks with a flame indicator
// ═══════════════════════════════════════════════════════════════════════

interface StreakTrackerProps {
  currentStreak: number
  bestStreak: number
  onStreakBreak?: (streak: number) => void
  onNewRecord?: (newRecord: number) => void
}

export const StreakTracker: React.FC<StreakTrackerProps> = ({
  currentStreak,
  bestStreak,
  onStreakBreak,
  onNewRecord,
}) => {
  const isRecord = currentStreak > bestStreak && currentStreak > 0

  if (isRecord && onNewRecord) {
    React.useEffect(() => {
      onNewRecord(currentStreak)
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentStreak])
  }

  if (currentStreak === 0 && bestStreak > 0 && onStreakBreak) {
    React.useEffect(() => {
      onStreakBreak(currentStreak)
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
  }

  return (
    <div className="rounded-2xl bg-gradient-to-br from-orange-500/20 to-red-500/10 border border-orange-500/30 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">🔥 Streak</h3>
        <span className="text-xs text-orange-300">Best: {bestStreak}</span>
      </div>
      <div className="flex items-center gap-3">
        <motion.span
          key={currentStreak}
          initial={{ scale: 1.4 }}
          animate={{ scale: 1 }}
          className={cn('text-5xl font-bold', isRecord ? 'text-amber-400 animate-streak-flicker' : 'text-white')}
        >
          {currentStreak}
        </motion.span>
        <div className="text-sm text-orange-200">
          {isRecord ? 'New record! 🏆' : currentStreak > 0 ? 'day streak' : 'Start a new streak'}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// NearMissDetector — computes proximity to a threshold and surfaces it
// ═══════════════════════════════════════════════════════════════════════

interface NearMissDetectorProps {
  actualOutcome: number
  winningThreshold: number
  onNearMiss?: (distance: number) => void
  children: React.ReactNode
  nearMissBand?: number
}

export const NearMissDetector: React.FC<NearMissDetectorProps> = ({
  actualOutcome,
  winningThreshold,
  onNearMiss,
  children,
  nearMissBand = 0.1,
}) => {
  const distance = Math.abs(actualOutcome - winningThreshold)
  const won = actualOutcome >= winningThreshold
  const isNearMiss = !won && distance <= nearMissBand * Math.max(Math.abs(winningThreshold), 1)

  React.useEffect(() => {
    if (isNearMiss && onNearMiss) onNearMiss(distance)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNearMiss])

  return (
    <div className={cn(isNearMiss && 'relative')}>
      {isNearMiss && (
        <div className="absolute -top-3 right-3 px-2 py-0.5 rounded-full bg-amber-500 text-white text-xs font-semibold">
          So close — {distance.toFixed(1)} away
        </div>
      )}
      {children}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// LiveSocialFeed — social proof stream of recent wins/activity
// ═══════════════════════════════════════════════════════════════════════

interface SocialFeedItem {
  id: string
  username: string
  action: string
  detail: string
  timeAgo: string
  emoji?: string
}

interface LiveSocialFeedProps {
  maxItems?: number
  items?: SocialFeedItem[]
}

const DEFAULT_FEED_ITEMS: SocialFeedItem[] = [
  { id: '1', username: 'Sarah_K', action: 'won', detail: '$25,000 on Tesla Q4', timeAgo: '2m', emoji: '🎉' },
  { id: '2', username: 'Mike_R', action: 'predicted', detail: 'AI Startup IPO', timeAgo: '5m', emoji: '🎯' },
  { id: '3', username: 'Alex_P', action: 'earned', detail: '$12,000 commission', timeAgo: '9m', emoji: '💰' },
]

export const LiveSocialFeed: React.FC<LiveSocialFeedProps> = ({ maxItems = 5, items }) => {
  const feed = items ?? DEFAULT_FEED_ITEMS

  return (
    <div className="space-y-3">
      <AnimatePresence>
        {feed.slice(0, maxItems).map((item, index) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="flex items-center gap-3 text-sm"
          >
            <span className="text-lg" aria-hidden>{item.emoji ?? '✨'}</span>
            <div className="min-w-0">
              <div className="text-white truncate">
                <span className="font-semibold">{item.username}</span>{' '}
                <span className="text-gray-300">{item.action} {item.detail}</span>
              </div>
              <div className="text-xs text-gray-400">{item.timeAgo} ago</div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// VIPStatus — tier status card with progress to the next tier
// ═══════════════════════════════════════════════════════════════════════

export type VipTier = 'Oracle' | 'Whale' | 'Purple' | 'Kingmaker'

interface VIPStatusProps {
  currentTier: VipTier
  progress: number // 0..1 progress toward next tier
  totalVolume: number
  onUpgrade?: (newTier: VipTier) => void
}

const TIER_ORDER: VipTier[] = ['Oracle', 'Whale', 'Purple', 'Kingmaker']

export const VIPStatus: React.FC<VIPStatusProps> = ({
  currentTier,
  progress,
  totalVolume,
  onUpgrade,
}) => {
  const nextTier = TIER_ORDER[TIER_ORDER.indexOf(currentTier) + 1]

  return (
    <div className="rounded-2xl bg-gradient-to-br from-purple-600/30 to-blue-600/20 border border-purple-500/30 p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-white">💎 {currentTier}</h3>
        <span className="text-xs text-purple-300">VIP</span>
      </div>
      <div className="text-sm text-gray-300 mb-4">
        Total volume: <span className="text-white font-semibold">${totalVolume.toLocaleString()}</span>
      </div>

      <div className="mb-2 flex items-center justify-between text-xs text-gray-400">
        <span>{currentTier}</span>
        <span>{nextTier ?? 'Max tier'}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden mb-4">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500"
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(progress * 100, 100)}%` }}
          transition={{ duration: 0.6 }}
        />
      </div>

      {nextTier && onUpgrade && (
        <button
          onClick={() => onUpgrade(nextTier)}
          className="w-full py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Upgrade to {nextTier}
        </button>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// LossRecoveryPrompt — surfaces a strategy-review panel after losses
// ═══════════════════════════════════════════════════════════════════════

interface LossRecoveryPromptProps {
  currentLoss: number
  onRecoveryAttempt?: (betAmount: number) => void
  onDismiss?: () => void
}

export const LossRecoveryPrompt: React.FC<LossRecoveryPromptProps> = ({
  currentLoss,
  onRecoveryAttempt,
  onDismiss,
}) => {
  const [visible, setVisible] = useState(true)

  const handleDismiss = () => {
    setVisible(false)
    onDismiss?.()
  }

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          className="fixed bottom-6 right-6 w-80 rounded-2xl bg-slate-800/95 backdrop-blur border border-amber-500/40 p-5 shadow-2xl z-50"
        >
          <div className="flex items-start justify-between mb-3">
            <h4 className="font-bold text-amber-400">Review your strategy</h4>
            <button onClick={handleDismiss} className="text-gray-400 hover:text-white text-sm" aria-label="Dismiss">
              ✕
            </button>
          </div>
          <p className="text-sm text-gray-300 mb-1">
            Current drawdown: <span className="font-semibold text-amber-300">${currentLoss.toLocaleString()}</span>
          </p>
          <p className="text-xs text-gray-400 mb-4">
            Consider reviewing your position sizing and taking a short break before your next trade.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => { onRecoveryAttempt?.(currentLoss); handleDismiss() }}
              className="flex-1 py-2 rounded-lg bg-amber-500 text-slate-900 text-sm font-semibold hover:bg-amber-400 transition-colors"
            >
              Review markets
            </button>
            <button
              onClick={handleDismiss}
              className="px-3 py-2 rounded-lg border border-gray-600 text-gray-300 text-sm hover:bg-gray-700 transition-colors"
            >
              Take a break
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
