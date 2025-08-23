/**
 * Scene System Usage Example - Complete implementation showcase
 * 
 * Demonstrates the full capabilities of the Scene System (SST):
 * - Scene-based navigation with smooth transitions
 * - Glassmorphism components with micro-interactions
 * - Real-time data integration
 * - Advanced animations and gesture support
 * - Performance monitoring and debugging
 */

import React, { useState, useEffect } from 'react'
import { 
  CompleteSceneSystemProvider,
  Scene,
  Glass,
  Interactive,
  StaggerList,
  MorphingCard,
  AnimatedNumber,
  RealtimePrice,
  useSceneSystem,
  useSceneTransition,
  useRealtimeSubscription,
  FUNDCAST_SCENES
} from '../lib'

// ═══════════════════════════════════════════════════════════════════════════════════
// APP ROOT - Complete Scene System setup
// ═══════════════════════════════════════════════════════════════════════════════════

const SceneSystemExampleApp: React.FC = () => {
  return (
    <CompleteSceneSystemProvider
      sceneConfig={{
        initialScene: 'landing',
        enableTelemetry: true,
        enablePreloading: true,
        debugMode: true
      }}
      realtimeConfig={{
        wsUrl: 'ws://localhost:8000/ws',
        enableMetrics: true
      }}
      inspectorConfig={{
        enabled: true,
        position: 'bottom-right',
        hotkey: '`'
      }}
    >
      <SceneNavigator />
    </CompleteSceneSystemProvider>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// SCENE NAVIGATOR - Renders current scene with transitions
// ═══════════════════════════════════════════════════════════════════════════════════

const SceneNavigator: React.FC = () => {
  const { currentScene } = useSceneSystem()
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      {/* Landing Scene */}
      <Scene id="landing" definition={FUNDCAST_SCENES.landing}>
        <LandingSceneContent />
      </Scene>
      
      {/* Dashboard Scene */}
      <Scene id="dashboard" definition={FUNDCAST_SCENES.dashboard}>
        <DashboardSceneContent />
      </Scene>
      
      {/* Markets Scene */}
      <Scene id="markets" definition={FUNDCAST_SCENES.markets}>
        <MarketsSceneContent />
      </Scene>
      
      {/* Market Detail Scene */}
      <Scene id="market-detail" definition={FUNDCAST_SCENES['market-detail']}>
        <MarketDetailSceneContent />
      </Scene>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// LANDING SCENE - Hero with glass cards and micro-interactions
// ═══════════════════════════════════════════════════════════════════════════════════

const LandingSceneContent: React.FC = () => {
  const { transitionTo } = useSceneTransition('dashboard', {
    type: 'fade-through',
    duration: 'base'
  })
  
  const features = [
    { title: 'Prediction Markets', description: 'Trade on startup outcomes', icon: '📈' },
    { title: 'Social Funding', description: 'Community-driven investments', icon: '🤝' },
    { title: 'Compliance', description: 'SEC Reg CF & 506(c) ready', icon: '⚖️' }
  ]
  
  return (
    <div className="container mx-auto px-6 py-16 min-h-screen flex flex-col justify-center">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-6">
          FundCast ⚡
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          AI-first social funding + forecasting platform for SaaS founders
        </p>
        
        <Interactive
          interaction={{
            trigger: 'cta-click',
            rules: { target: 'dashboard' },
            feedback: { visual: 'pulse', haptic: 'medium' }
          }}
          className="inline-block"
        >
          <button
            onClick={transitionTo}
            className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-4 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transition-shadow"
          >
            Enter Dashboard
          </button>
        </Interactive>
      </div>
      
      {/* Feature Cards with Stagger Animation */}
      <StaggerList
        staggerDelay="cards"
        direction="up"
        className="grid md:grid-cols-3 gap-6"
      >
        {features.map((feature, index) => (
          <Glass
            key={feature.title}
            intensity="medium"
            tint="neutral"
            className="p-6 hover:scale-105 transition-transform cursor-pointer"
          >
            <div className="text-4xl mb-4">{feature.icon}</div>
            <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
            <p className="text-gray-600">{feature.description}</p>
          </Glass>
        ))}
      </StaggerList>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// DASHBOARD SCENE - Stats cards with real-time data
// ═══════════════════════════════════════════════════════════════════════════════════

const DashboardSceneContent: React.FC = () => {
  const { transitionTo: goToMarkets } = useSceneTransition('markets')
  const [portfolioValue, setPortfolioValue] = useState(15420.50)
  const [pnl, setPnl] = useState(1240.30)
  
  // Subscribe to real-time portfolio updates
  useRealtimeSubscription<{ value: number; pnl: number }>(
    'portfolio-update',
    (data) => {
      setPortfolioValue(data.value)
      setPnl(data.pnl)
    },
    { throttle: 500 }
  )
  
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-gray-600">Your trading overview and portfolio performance</p>
      </div>
      
      {/* Stats Cards */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <Glass intensity="medium" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Portfolio Value</p>
              <AnimatedNumber
                value={portfolioValue}
                format={(n) => `$${n.toLocaleString()}`}
                className="text-2xl font-bold"
                colorize={false}
              />
            </div>
            <div className="text-3xl">💰</div>
          </div>
        </Glass>
        
        <Glass intensity="medium" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Today's P&L</p>
              <AnimatedNumber
                value={pnl}
                format={(n) => `${n >= 0 ? '+' : ''}$${n.toLocaleString()}`}
                className="text-2xl font-bold"
                colorize={true}
              />
            </div>
            <div className="text-3xl">{pnl >= 0 ? '📈' : '📉'}</div>
          </div>
        </Glass>
        
        <Glass intensity="medium" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Active Positions</p>
              <div className="text-2xl font-bold">12</div>
            </div>
            <div className="text-3xl">🎯</div>
          </div>
        </Glass>
      </div>
      
      {/* Quick Actions */}
      <div className="flex gap-4">
        <Interactive
          interaction={{
            trigger: 'market-nav',
            rules: { route: 'markets' },
            feedback: { visual: 'highlight' }
          }}
        >
          <button
            onClick={goToMarkets}
            className="bg-blue-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            Explore Markets
          </button>
        </Interactive>
        
        <button className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors">
          View Portfolio
        </button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// MARKETS SCENE - Market discovery with real-time prices
// ═══════════════════════════════════════════════════════════════════════════════════

const MarketsSceneContent: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  
  const markets = [
    { id: 'tesla-q4', name: 'Tesla Q4 Revenue > $25B', category: 'earnings', price: 0.72 },
    { id: 'openai-valuation', name: 'OpenAI Valuation > $150B by 2025', category: 'startups', price: 0.45 },
    { id: 'crypto-regulation', name: 'Bitcoin ETF Approval in 2024', category: 'crypto', price: 0.89 }
  ]
  
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Prediction Markets</h1>
        <p className="text-gray-600">Discover and trade on market outcomes</p>
      </div>
      
      {/* Search and Filters */}
      <div className="mb-6">
        <Interactive
          interaction={{
            trigger: 'search-input',
            rules: { debounce: '300ms' },
            feedback: { visual: 'highlight' }
          }}
        >
          <input
            type="text"
            placeholder="Search markets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-4 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </Interactive>
      </div>
      
      {/* Markets List */}
      <StaggerList
        staggerDelay="list"
        className="space-y-4"
      >
        {markets.map((market) => (
          <MorphingCard
            key={market.id}
            state="collapsed"
            className="w-full"
          >
            <Glass intensity="subtle" className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">{market.name}</h3>
                  <p className="text-sm text-gray-500 capitalize">{market.category}</p>
                </div>
                
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-600 mb-1">
                    <RealtimePrice
                      marketId={market.id}
                      format={(price) => `${(price * 100).toFixed(0)}¢`}
                    />
                  </div>
                  <button className="bg-green-500 text-white px-4 py-2 rounded font-medium hover:bg-green-600 transition-colors">
                    Trade
                  </button>
                </div>
              </div>
            </Glass>
          </MorphingCard>
        ))}
      </StaggerList>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// MARKET DETAIL SCENE - Detailed market view with trading interface
// ═══════════════════════════════════════════════════════════════════════════════════

const MarketDetailSceneContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview')
  
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Tesla Q4 Revenue > $25B</h1>
        <p className="text-gray-600">Earnings prediction market</p>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8">
        {/* Price Chart Area */}
        <div className="md:col-span-2">
          <Glass intensity="medium" className="p-6 h-96">
            <div className="flex items-center justify-center h-full text-gray-500">
              📊 Chart Component Would Go Here
            </div>
          </Glass>
        </div>
        
        {/* Trading Panel */}
        <div>
          <Glass intensity="medium" className="p-6">
            <h3 className="font-semibold mb-4">Place Order</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Side</label>
                <div className="grid grid-cols-2 gap-2">
                  <button className="bg-green-500 text-white py-2 rounded font-medium">
                    Yes - 72¢
                  </button>
                  <button className="bg-red-500 text-white py-2 rounded font-medium">
                    No - 28¢
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Amount</label>
                <input
                  type="number"
                  placeholder="$100"
                  className="w-full p-3 rounded border border-gray-200 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <Interactive
                interaction={{
                  trigger: 'place-order',
                  rules: { validation: 'zod' },
                  feedback: { visual: 'pulse', haptic: 'medium' }
                }}
              >
                <button className="w-full bg-blue-500 text-white py-3 rounded-lg font-medium hover:bg-blue-600 transition-colors">
                  Place Order
                </button>
              </Interactive>
            </div>
          </Glass>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// EXPORT - Complete example application
// ═══════════════════════════════════════════════════════════════════════════════════

export default SceneSystemExampleApp