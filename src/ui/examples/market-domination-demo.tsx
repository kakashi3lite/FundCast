/**
 * Market Domination Demo - Complete implementation of gambling psychology + viral growth
 * 
 * Showcases the full arsenal of addiction mechanics and viral growth strategies:
 * - Dopamine-optimized UI with near-miss effects and streak interruption
 * - Prophet Program referral system with financial incentives  
 * - Exclusive access gates and FOMO mechanics
 * - Competitive leaderboards and tournaments
 * - Social proof amplification and network effects
 * 
 * This is the complete playbook for market domination in action.
 */

import React, { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CompleteSceneSystemProvider,
  Scene,
  Glass,
  useSceneSystem,
  FUNDCAST_SCENES
} from '../lib'
import {
  DopamineTrigger,
  NearMissDetector,
  LiveSocialFeed,
  StreakTracker,
  VIPStatus,
  LossRecoveryPrompt
} from '../lib/gambling-psychology'
import {
  ReferralDashboard,
  ExclusiveAccessGate,
  CompetitionLeaderboard,
  NetworkMomentumDisplay
} from '../lib/viral-growth'

// ═══════════════════════════════════════════════════════════════════════════════════
// MARKET DOMINATION APP - Complete implementation
// ═══════════════════════════════════════════════════════════════════════════════════

const MarketDominationDemo: React.FC = () => {
  return (
    <CompleteSceneSystemProvider
      sceneConfig={{
        initialScene: 'exclusive-gate',
        enableTelemetry: true,
        enablePreloading: true,
        debugMode: true
      }}
      realtimeConfig={{
        wsUrl: 'ws://localhost:8000/ws/gambling',
        enableMetrics: true
      }}
      inspectorConfig={{
        enabled: true,
        position: 'bottom-right',
        hotkey: '`'
      }}
    >
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-green-900">
        <MarketDominationScenes />
      </div>
    </CompleteSceneSystemProvider>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// SCENE ORCHESTRATOR - Manages the gambling psychology journey
// ═══════════════════════════════════════════════════════════════════════════════════

const MarketDominationScenes: React.FC = () => {
  const { currentScene } = useSceneSystem()
  
  // Extended scene definitions for gambling psychology
  const gamblingScenes = {
    ...FUNDCAST_SCENES,
    'exclusive-gate': {
      id: 'exclusive-gate',
      purpose: 'Create FOMO and exclusive access desire',
      entry: ['/'],
      primaryLayout: 'exclusive access gate with social proof',
      transition: { type: 'fade', duration: 'base', easing: 'standard' },
      microInteractions: [],
      states: ['loading', 'success'],
      accessibility: {
        announceTransitions: true,
        reducedMotionFallback: { type: 'fade', duration: 'fast' },
        focusManagement: 'auto'
      }
    },
    'gambling-dashboard': {
      id: 'gambling-dashboard',
      purpose: 'Addiction-optimized trading interface with dopamine triggers',
      entry: ['/dashboard'],
      primaryLayout: 'psychology-optimized dashboard with streak tracking',
      transition: { type: 'container-transform', duration: 'base', easing: 'standard' },
      microInteractions: [],
      states: ['loading', 'success'],
      accessibility: {
        announceTransitions: true,
        reducedMotionFallback: { type: 'fade', duration: 'fast' },
        focusManagement: 'auto'
      }
    },
    'viral-referrals': {
      id: 'viral-referrals',
      purpose: 'Prophet Program viral growth engine',
      entry: ['/referrals'],
      primaryLayout: 'referral dashboard with social sharing tools',
      transition: { type: 'slide', direction: 'left', duration: 'base', easing: 'standard' },
      microInteractions: [],
      states: ['loading', 'success'],
      accessibility: {
        announceTransitions: true,
        reducedMotionFallback: { type: 'fade', duration: 'fast' },
        focusManagement: 'auto'
      }
    },
    'competition-arena': {
      id: 'competition-arena',  
      purpose: 'Competitive tournaments and leaderboards',
      entry: ['/compete'],
      primaryLayout: 'leaderboard with live competition data',
      transition: { type: 'shared-axis', direction: 'x', duration: 'base', easing: 'standard' },
      microInteractions: [],
      states: ['loading', 'success'],
      accessibility: {
        announceTransitions: true,
        reducedMotionFallback: { type: 'fade', duration: 'fast' },
        focusManagement: 'auto'
      }
    }
  }
  
  return (
    <>
      {/* Exclusive Access Gate */}
      <Scene id="exclusive-gate" definition={gamblingScenes['exclusive-gate']}>
        <ExclusiveAccessScene />
      </Scene>
      
      {/* Gambling Psychology Dashboard */}
      <Scene id="gambling-dashboard" definition={gamblingScenes['gambling-dashboard']}>
        <GamblingDashboardScene />
      </Scene>
      
      {/* Viral Growth Referrals */}
      <Scene id="viral-referrals" definition={gamblingScenes['viral-referrals']}>
        <ViralReferralsScene />
      </Scene>
      
      {/* Competition Arena */}
      <Scene id="competition-arena" definition={gamblingScenes['competition-arena']}>
        <CompetitionArenaScene />
      </Scene>
    </>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// EXCLUSIVE ACCESS SCENE - FOMO-driven invitation system
// ═══════════════════════════════════════════════════════════════════════════════════

const ExclusiveAccessScene: React.FC = () => {
  const { transition } = useSceneSystem()
  const [hasAccess, setHasAccess] = useState(false)
  
  const handleJoinWaitlist = () => {
    // Track conversion
    console.log('🎯 Waitlist conversion - adding founder to exclusive queue')
    
    // In real implementation, this would:
    // 1. Collect founder information
    // 2. Verify $1M+ ARR status
    // 3. Add to waitlist with position
  }
  
  const handleInviteCode = (code: string) => {
    // Simulate invite code validation
    if (code === 'PROPHET23' || code === 'WHALE100') {
      setHasAccess(true)
      setTimeout(() => {
        transition('gambling-dashboard')
      }, 2000)
    } else {
      // Show error with encouragement to get real invite
      console.log('🚫 Invalid code - encourage getting invite from existing member')
    }
  }
  
  return (
    <ExclusiveAccessGate
      waitlistPosition={2847}
      totalWaitlist={15420}
      estimatedWaitTime="2-3 weeks"
      onJoinWaitlist={handleJoinWaitlist}
      onUseInviteCode={handleInviteCode}
    />
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// GAMBLING PSYCHOLOGY DASHBOARD - Addiction-optimized interface
// ═══════════════════════════════════════════════════════════════════════════════════

const GamblingDashboardScene: React.FC = () => {
  const { transition } = useSceneSystem()
  
  // Simulate user gambling state
  const [userState, setUserState] = useState({
    currentStreak: 3,
    bestStreak: 7,
    portfolioValue: 15420.50,
    todayPnL: -1240.30,
    currentLoss: 1240.30,
    totalVolume: 47500,
    vipTier: 'Oracle' as const,
    vipProgress: 65
  })
  
  // Simulated market prediction
  const [predictionOutcome, setPredictionOutcome] = useState<number | null>(null)
  const [lastBet, setLastBet] = useState<{ amount: number; target: number } | null>(null)
  
  const handlePlaceBet = (amount: number, target: number) => {
    setLastBet({ amount, target })
    
    // Simulate outcome with near-miss psychology
    setTimeout(() => {
      // 30% chance of near-miss (within 5% of target)
      const nearMissRoll = Math.random()
      let outcome: number
      
      if (nearMissRoll < 0.3) {
        // Create near-miss - just short of winning
        const missDistance = (target * 0.04) * Math.random() 
        outcome = target - missDistance
      } else if (nearMissRoll < 0.5) {
        // Win (20% chance)
        outcome = target + (Math.random() * target * 0.1)
        setUserState(prev => ({
          ...prev,
          currentStreak: prev.currentStreak + 1,
          todayPnL: prev.todayPnL + amount * 0.8
        }))
      } else {
        // Regular loss
        outcome = target * (0.3 + Math.random() * 0.6)
        setUserState(prev => ({
          ...prev,
          currentStreak: 0,
          todayPnL: prev.todayPnL - amount,
          currentLoss: Math.abs(prev.todayPnL - amount)
        }))
      }
      
      setPredictionOutcome(outcome)
    }, 2000)
  }
  
  const handleStreakBreak = (brokenStreak: number) => {
    console.log(`💔 Streak of ${brokenStreak} broken - trigger recovery psychology`)
    // This would trigger recovery betting prompts
  }
  
  const handleRecoveryAttempt = (betAmount: number) => {
    console.log(`🎰 Recovery bet placed: $${betAmount} - double-down psychology engaged`)
    setUserState(prev => ({ ...prev, currentLoss: 0 }))
  }
  
  return (
    <div className="container mx-auto px-6 py-8 space-y-8">
      {/* Header with Navigation */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Founder's Casino</h1>
        <div className="flex gap-4">
          <button 
            onClick={() => transition('viral-referrals')}
            className="bg-green-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-600"
          >
            💰 Earn Commissions
          </button>
          <button 
            onClick={() => transition('competition-arena')}
            className="bg-purple-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-600"
          >
            🏆 Leaderboard
          </button>
        </div>
      </div>
      
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Trading Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current Prediction Market */}
          <Glass intensity="strong" className="p-6">
            <h3 className="text-xl font-bold text-white mb-4">🔥 Live Prediction</h3>
            <div className="bg-gradient-to-r from-blue-900 to-purple-900 p-6 rounded-lg">
              <div className="text-lg text-white mb-4">
                Will OpenAI's next funding round be valued at >$150B?
              </div>
              
              {!predictionOutcome ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => handlePlaceBet(1000, 150)}
                      className="bg-green-500 text-white py-3 rounded-lg font-bold hover:bg-green-600 transition-colors"
                    >
                      YES - 67¢
                    </button>
                    <button
                      onClick={() => handlePlaceBet(1000, 50)}
                      className="bg-red-500 text-white py-3 rounded-lg font-bold hover:bg-red-600 transition-colors"
                    >
                      NO - 33¢
                    </button>
                  </div>
                  <div className="text-center text-gray-300 text-sm">
                    Your bet: $1,000 • Potential win: $1,500
                  </div>
                </div>
              ) : lastBet ? (
                <NearMissDetector
                  actualOutcome={predictionOutcome}
                  winningThreshold={lastBet.target}
                  onNearMiss={(distance) => {
                    console.log(`😱 Near miss! Only ${distance} away from winning`)
                  }}
                >
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white mb-2">
                      Result: ${predictionOutcome.toFixed(1)}B
                    </div>
                    <div className={`text-lg font-bold ${
                      predictionOutcome >= lastBet.target ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {predictionOutcome >= lastBet.target ? '🎉 YOU WON!' : '💔 So Close!'}
                    </div>
                  </div>
                </NearMissDetector>
              ) : null}
            </div>
          </Glass>
          
          {/* Live Social Feed */}
          <Glass intensity="medium" className="p-6">
            <h3 className="text-lg font-bold text-white mb-4">🔥 Live Wins</h3>
            <LiveSocialFeed maxItems={5} />
          </Glass>
        </div>
        
        {/* Sidebar with Psychology Components */}
        <div className="space-y-6">
          {/* VIP Status */}
          <VIPStatus
            currentTier={userState.vipTier}
            progress={userState.vipProgress}
            totalVolume={userState.totalVolume}
            onUpgrade={(newTier) => {
              console.log(`🎊 Upgraded to ${newTier} tier!`)
            }}
          />
          
          {/* Streak Tracker */}
          <StreakTracker
            currentStreak={userState.currentStreak}
            bestStreak={userState.bestStreak}
            onStreakBreak={handleStreakBreak}
            onNewRecord={(newRecord) => {
              console.log(`🏆 New record streak: ${newRecord}!`)
            }}
          />
          
          {/* Network Momentum */}
          <NetworkMomentumDisplay
            activeUsers={1247}
            totalVolume={15420000}
            recentWins={[
              { amount: 25000, username: 'Sarah_K', market: 'Tesla Q4 Revenue' },
              { amount: 18000, username: 'Mike_R', market: 'AI Startup IPO' },
              { amount: 12000, username: 'Alex_P', market: 'Crypto Regulation' }
            ]}
            trendinMarkets={[
              { name: 'Next AI Unicorn', volume: 2500000, participants: 847 },
              { name: 'Tesla Q4 Earnings', volume: 1200000, participants: 523 },
              { name: 'Stripe IPO Timeline', volume: 950000, participants: 412 }
            ]}
          />
        </div>
      </div>
      
      {/* Loss Recovery Prompt */}
      {userState.currentLoss > 500 && (
        <LossRecoveryPrompt
          currentLoss={userState.currentLoss}
          onRecoveryAttempt={handleRecoveryAttempt}
        />
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// VIRAL REFERRALS SCENE - Prophet Program implementation
// ═══════════════════════════════════════════════════════════════════════════════════

const ViralReferralsScene: React.FC = () => {
  const { transition } = useSceneSystem()
  
  // Simulated referral stats
  const referralStats = {
    totalReferrals: 23,
    qualifiedReferrals: 15,
    lifetimeCommission: 47250,
    monthlyCommission: 12400,
    tier: 'Oracle' as const,
    nextTierThreshold: 25
  }
  
  const handleGenerateLink = () => {
    console.log('📱 Generated viral referral link with tracking')
  }
  
  const handleShare = (platform: string) => {
    console.log(`📢 Shared on ${platform} with optimized viral content`)
  }
  
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <button
          onClick={() => transition('gambling-dashboard')}
          className="text-blue-400 hover:text-blue-300 mb-4"
        >
          ← Back to Dashboard
        </button>
        <h1 className="text-3xl font-bold text-white mb-2">Prophet Program</h1>
        <p className="text-gray-300">Turn your network into a revenue stream</p>
      </div>
      
      <ReferralDashboard
        stats={referralStats}
        referralCode="PROPHET23"
        onGenerateLink={handleGenerateLink}
        onShare={handleShare}
      />
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// COMPETITION ARENA SCENE - Tournaments and leaderboards
// ═══════════════════════════════════════════════════════════════════════════════════

const CompetitionArenaScene: React.FC = () => {
  const { transition } = useSceneSystem()
  const [timeframe, setTimeframe] = useState('monthly')
  
  // Mock leaderboard data
  const leaderboardEntries = [
    { rank: 1, username: 'Sarah_K', netPnL: 67500, winRate: 0.73, totalVolume: 450000, streak: 12, badges: ['🏆', '🔥'], isCurrentUser: false },
    { rank: 2, username: 'Mike_R', netPnL: 54200, winRate: 0.68, totalVolume: 380000, streak: 8, badges: ['🥈', '💎'], isCurrentUser: false },
    { rank: 3, username: 'Alex_P', netPnL: 48900, winRate: 0.71, totalVolume: 320000, streak: 6, badges: ['🥉', '🎯'], isCurrentUser: false },
    { rank: 7, username: 'You', netPnL: 32100, winRate: 0.64, totalVolume: 275000, streak: 3, badges: ['🎲'], isCurrentUser: true },
    { rank: 8, username: 'Jordan_M', netPnL: 29800, winRate: 0.59, totalVolume: 250000, streak: 0, badges: [], isCurrentUser: false },
    // ... more entries
  ]
  
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <button
          onClick={() => transition('gambling-dashboard')}
          className="text-blue-400 hover:text-blue-300 mb-4"
        >
          ← Back to Dashboard
        </button>
      </div>
      
      <CompetitionLeaderboard
        entries={leaderboardEntries}
        timeframe={timeframe as any}
        prizePool={1000000}
        onTimeframeChange={setTimeframe}
      />
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// EXPORT - Market domination demo
// ═══════════════════════════════════════════════════════════════════════════════════

export default MarketDominationDemo