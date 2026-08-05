/**
 * Viral Growth — referral, access-gate, leaderboard and network
 * momentum components powering the Prophet Program.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from './utils'

// ═══════════════════════════════════════════════════════════════════════
// ExclusiveAccessGate — FOMO-driven invitation / waitlist gate
// ═══════════════════════════════════════════════════════════════════════

interface ExclusiveAccessGateProps {
  waitlistPosition: number
  totalWaitlist: number
  estimatedWaitTime?: string
  onJoinWaitlist?: () => void
  onUseInviteCode?: (code: string) => void
}

export const ExclusiveAccessGate: React.FC<ExclusiveAccessGateProps> = ({
  waitlistPosition,
  totalWaitlist,
  estimatedWaitTime,
  onJoinWaitlist,
  onUseInviteCode,
}) => {
  const [inviteCode, setInviteCode] = React.useState('')

  const handleSubmit = () => {
    if (inviteCode.trim()) onUseInviteCode?.(inviteCode.trim())
  }

  const progress = Math.min((waitlistPosition / Math.max(totalWaitlist, 1)) * 100, 100)

  return (
    <div className="max-w-lg mx-auto px-6 py-24 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="rounded-3xl bg-gradient-to-br from-purple-900/60 to-blue-900/40 border border-purple-500/40 p-10 shadow-2xl"
      >
        <div className="text-5xl mb-4">🔐</div>
        <h1 className="text-3xl font-bold text-white mb-3">By Invitation Only</h1>
        <p className="text-gray-300 mb-6">
          FundCast is currently in private beta for verified SaaS founders.
        </p>

        {/* Waitlist position */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-300 mb-2">
            <span>Your position</span>
            <span className="text-purple-300 font-semibold">
              #{waitlistPosition.toLocaleString()} of {totalWaitlist.toLocaleString()}
            </span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 1 }}
            />
          </div>
          {estimatedWaitTime && (
            <p className="text-xs text-gray-400 mt-2">Estimated wait: {estimatedWaitTime}</p>
          )}
        </div>

        <button
          onClick={onJoinWaitlist}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:opacity-90 transition-opacity mb-4"
        >
          Join the Waitlist
        </button>

        <div className="text-xs text-gray-500 mb-2">— or enter an invite code —</div>
        <div className="flex gap-2">
          <input
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="INVITE CODE"
            className="flex-1 px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 uppercase"
          />
          <button
            onClick={handleSubmit}
            className="px-4 py-2 rounded-lg bg-white text-slate-900 font-semibold hover:bg-gray-200 transition-colors"
          >
            Redeem
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// ReferralDashboard — Prophet Program stats and share tools
// ═══════════════════════════════════════════════════════════════════════

export interface ReferralStats {
  totalReferrals: number
  qualifiedReferrals: number
  lifetimeCommission: number
  monthlyCommission: number
  tier: string
  nextTierThreshold: number
}

interface ReferralDashboardProps {
  stats: ReferralStats
  referralCode: string
  onGenerateLink?: () => void
  onShare?: (platform: string) => void
}

export const ReferralDashboard: React.FC<ReferralDashboardProps> = ({
  stats,
  referralCode,
  onGenerateLink,
  onShare,
}) => {
  const sharePlatforms = ['twitter', 'linkedin', 'copy']

  const tierProgress = Math.min(stats.totalReferrals / Math.max(stats.nextTierThreshold, 1), 1)

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Stats */}
      <div className="rounded-2xl bg-slate-800/70 border border-slate-700 p-6">
        <h3 className="text-xl font-bold text-white mb-4">Prophet Program</h3>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Stat label="Total referrals" value={stats.totalReferrals} />
          <Stat label="Qualified" value={stats.qualifiedReferrals} />
          <Stat label="Lifetime commission" value={`$${stats.lifetimeCommission.toLocaleString()}`} />
          <Stat label="Monthly" value={`$${stats.monthlyCommission.toLocaleString()}`} />
        </div>
        <div className="mb-2 flex justify-between text-sm text-gray-400">
          <span>{stats.tier}</span>
          <span>Next tier at {stats.nextTierThreshold}</span>
        </div>
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400"
            initial={{ width: 0 }}
            animate={{ width: `${tierProgress * 100}%` }}
          />
        </div>
      </div>

      {/* Share tools */}
      <div className="rounded-2xl bg-slate-800/70 border border-slate-700 p-6">
        <h3 className="text-xl font-bold text-white mb-4">Your referral link</h3>
        <div className="flex items-center gap-2 mb-4">
          <code className="flex-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-600 text-green-400 text-sm">
            FUNDCAST/{referralCode}
          </code>
          <button
            onClick={onGenerateLink}
            className="px-3 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-500 transition-colors"
          >
            New link
          </button>
        </div>
        <div className="flex gap-2">
          {sharePlatforms.map((platform) => (
            <button
              key={platform}
              onClick={() => onShare?.(platform)}
              className="flex-1 py-2 rounded-lg bg-slate-700 text-white text-sm font-medium capitalize hover:bg-slate-600 transition-colors"
            >
              {platform === 'copy' ? '📋 Copy' : platform === 'twitter' ? '𝕏 Share' : '💼 Share'}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// CompetitionLeaderboard — competitive tournament standings
// ═══════════════════════════════════════════════════════════════════════

export interface LeaderboardEntry {
  rank: number
  username: string
  netPnL: number
  winRate: number
  totalVolume: number
  streak: number
  badges: string[]
  isCurrentUser?: boolean
}

interface CompetitionLeaderboardProps {
  entries: LeaderboardEntry[]
  timeframe: 'daily' | 'weekly' | 'monthly'
  prizePool?: number
  onTimeframeChange?: (timeframe: 'daily' | 'weekly' | 'monthly') => void
}

export const CompetitionLeaderboard: React.FC<CompetitionLeaderboardProps> = ({
  entries,
  timeframe,
  prizePool,
  onTimeframeChange,
}) => {
  const timeframes: Array<'daily' | 'weekly' | 'monthly'> = ['daily', 'weekly', 'monthly']

  return (
    <div className="rounded-2xl bg-slate-800/70 border border-slate-700 overflow-hidden">
      <div className="p-6 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">🏆 Competition Arena</h3>
          {prizePool && (
            <p className="text-sm text-gray-400 mt-1">
              Prize pool: <span className="text-amber-400 font-semibold">${prizePool.toLocaleString()}</span>
            </p>
          )}
        </div>
        <div className="flex gap-1">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => onTimeframeChange?.(tf)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors',
                tf === timeframe ? 'bg-purple-600 text-white' : 'bg-slate-700 text-gray-300 hover:bg-slate-600',
              )}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-slate-700/70">
        {entries.map((entry) => (
          <div
            key={entry.username}
            className={cn(
              'flex items-center gap-4 px-6 py-4',
              entry.isCurrentUser && 'bg-purple-600/10',
            )}
          >
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
              entry.rank === 1 ? 'bg-amber-500 text-white' :
              entry.rank === 2 ? 'bg-gray-400 text-white' :
              entry.rank === 3 ? 'bg-orange-600 text-white' :
              'bg-slate-700 text-gray-300',
            )}>
              {entry.rank}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold flex items-center gap-2">
                {entry.username}
                {entry.isCurrentUser && <span className="text-xs text-purple-300">(you)</span>}
                <span className="text-sm">{entry.badges.join(' ')}</span>
              </div>
              <div className="text-xs text-gray-400">
                {Math.round(entry.winRate * 100)}% win • ${entry.totalVolume.toLocaleString()} vol
                {entry.streak > 0 && ` • 🔥 ${entry.streak}`}
              </div>
            </div>
            <div className={cn('font-bold', entry.netPnL >= 0 ? 'text-green-400' : 'text-red-400')}>
              {entry.netPnL >= 0 ? '+' : ''}${entry.netPnL.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// NetworkMomentumDisplay — network-wide momentum indicators
// ═══════════════════════════════════════════════════════════════════════

interface RecentWin {
  amount: number
  username: string
  market: string
}

interface TrendingMarket {
  name: string
  volume: number
  participants: number
}

interface NetworkMomentumDisplayProps {
  activeUsers: number
  totalVolume: number
  recentWins: RecentWin[]
  trendinMarkets: TrendingMarket[]
}

export const NetworkMomentumDisplay: React.FC<NetworkMomentumDisplayProps> = ({
  activeUsers,
  totalVolume,
  recentWins,
  trendinMarkets,
}) => {
  return (
    <div className="rounded-2xl bg-slate-800/70 border border-slate-700 p-6 space-y-6">
      <div>
        <h3 className="text-lg font-bold text-white mb-3">📈 Network Momentum</h3>
        <div className="grid grid-cols-2 gap-4">
          <Stat label="Active founders" value={activeUsers.toLocaleString()} />
          <Stat label="Total volume" value={`$${(totalVolume / 1e6).toFixed(1)}M`} />
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-gray-300 mb-2">Recent wins</h4>
        <div className="space-y-2">
          {recentWins.map((win, i) => (
            <div key={i} className="text-sm flex items-center justify-between">
              <span className="text-gray-300">
                <span className="font-semibold text-white">{win.username}</span> • {win.market}
              </span>
              <span className="text-green-400 font-semibold">+${win.amount.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-gray-300 mb-2">Trending markets</h4>
        <div className="space-y-2">
          {trendinMarkets.map((market, i) => (
            <div key={i} className="text-sm flex items-center justify-between">
              <span className="text-gray-300">{market.name}</span>
              <span className="text-gray-400">
                ${(market.volume / 1e6).toFixed(1)}M • {market.participants} traders
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════
// Shared stat cell
// ═══════════════════════════════════════════════════════════════════════

interface StatProps {
  label: string
  value: string | number
}

const Stat: React.FC<StatProps> = ({ label, value }) => (
  <div className="rounded-xl bg-slate-900/60 p-4">
    <div className="text-2xl font-bold text-white">{value}</div>
    <div className="text-xs text-gray-400 mt-1">{label}</div>
  </div>
)
