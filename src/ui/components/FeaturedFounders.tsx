/**
 * Featured Founders Display - Purple tier home screen showcasing
 * 
 * Core value proposition of Purple tier subscription:
 * - Hero carousel rotation
 * - Featured founder grid
 * - Success stories
 * - Optimized for FOMO and status signaling
 */

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSceneSystem } from '../lib/scene-provider'
import { Glass, Interactive } from '../lib/scene-system'
import { StaggerList, SharedElement } from '../lib/advanced-animations'
import { DopamineTrigger } from '../lib/gambling-psychology'
import { cn } from '../lib/utils'

// ═══════════════════════════════════════════════════════════════════════════════════
// TYPES & INTERFACES
// ═══════════════════════════════════════════════════════════════════════════════════

interface FeaturedFounder {
  user_id: string
  subscription_id: string
  name: string
  title: string
  company: string
  bio: string
  achievement: string
  avatar_url: string
  cover_url?: string
  profile_url: string
  badges: string[]
  tier: string
  member_since: string
  cta: string
  cta_url: string
  featuring_id: string
  featuring_type: 'hero' | 'grid' | 'story'
  featured_until: string
  metrics: {
    successful_predictions: number
    portfolio_value: string
    network_connections: number
    achievements_count: number
  }
}

interface FeaturedFoundersData {
  hero: FeaturedFounder | null
  grid: FeaturedFounder[]
  stories: FeaturedFounder[]
  updated_at: string
  next_rotation: string
}

// ═══════════════════════════════════════════════════════════════════════════════════
// MAIN FEATURED FOUNDERS COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════════

interface FeaturedFoundersProps {
  className?: string
  showUpgradePrompt?: boolean
  onUpgradeClick?: () => void
}

export const FeaturedFounders: React.FC<FeaturedFoundersProps> = ({
  className,
  showUpgradePrompt = false,
  onUpgradeClick
}) => {
  const { trackEvent } = useSceneSystem()
  const [featuredData, setFeaturedData] = useState<FeaturedFoundersData | null>(null)
  const [loading, setLoading] = useState(true)
  const [countdown, setCountdown] = useState('')
  
  // Load featured founders data
  const loadFeaturedFounders = useCallback(async () => {
    try {
      const response = await fetch('/api/subscriptions/purple-featuring/current')
      const data = await response.json()
      setFeaturedData(data)
      
      // Track view for analytics
      trackEvent('featured-founders-viewed')
    } catch (error) {
      console.error('Failed to load featured founders:', error)
    } finally {
      setLoading(false)
    }
  }, [trackEvent])
  
  // Load data and set up auto-refresh
  useEffect(() => {
    loadFeaturedFounders()
    
    // Refresh every 5 minutes
    const interval = setInterval(loadFeaturedFounders, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [loadFeaturedFounders])
  
  // Countdown to next rotation
  useEffect(() => {
    if (!featuredData?.next_rotation) return
    
    const updateCountdown = () => {
      const now = new Date()
      const nextRotation = new Date(featuredData.next_rotation)
      const diff = nextRotation.getTime() - now.getTime()
      
      if (diff > 0) {
        const hours = Math.floor(diff / (1000 * 60 * 60))
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
        setCountdown(`${hours}h ${minutes}m`)
      } else {
        setCountdown('Updating soon...')
        loadFeaturedFounders() // Refresh when rotation time passes
      }
    }
    
    updateCountdown()
    const interval = setInterval(updateCountdown, 60000) // Update every minute
    
    return () => clearInterval(interval)
  }, [featuredData?.next_rotation, loadFeaturedFounders])
  
  const handleFounderInteraction = async (founder: FeaturedFounder, interactionType: string) => {
    // Track interaction for analytics
    await fetch(`/api/subscriptions/purple-featuring/${founder.featuring_id}/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interaction_type: interactionType })
    })
    
    trackEvent('founder-interaction', {
      founder_id: founder.user_id,
      interaction_type: interactionType,
      featuring_type: founder.featuring_type
    })
  }
  
  if (loading) {
    return <FeaturedFoundersLoading className={className} />
  }
  
  if (!featuredData) {
    return <FeaturedFoundersError className={className} />
  }
  
  return (
    <div className={cn('py-12', className)}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              ⭐ Featured Founders
            </h2>
            <p className="text-gray-600">
              Spotlight on Purple tier members making moves in the startup ecosystem
            </p>
          </div>
          
          <div className="text-right text-sm text-gray-500">
            <div>Next rotation in {countdown}</div>
            <div>{featuredData.grid.length} founders featured</div>
          </div>
        </div>
        
        {/* Hero Founder Spotlight */}
        {featuredData.hero && (
          <HeroFounderSpotlight
            founder={featuredData.hero}
            onInteraction={(type) => handleFounderInteraction(featuredData.hero!, type)}
          />
        )}
        
        {/* Featured Founders Grid */}
        {featuredData.grid.length > 0 && (
          <FeaturedFoundersGrid
            founders={featuredData.grid}
            onInteraction={handleFounderInteraction}
          />
        )}
        
        {/* Success Stories */}
        {featuredData.stories.length > 0 && (
          <SuccessStories
            stories={featuredData.stories}
            onInteraction={handleFounderInteraction}
          />
        )}
        
        {/* Upgrade Prompt */}
        {showUpgradePrompt && (
          <PurpleUpgradePrompt onUpgradeClick={onUpgradeClick} />
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// HERO FOUNDER SPOTLIGHT
// ═══════════════════════════════════════════════════════════════════════════════════

interface HeroFounderSpotlightProps {
  founder: FeaturedFounder
  onInteraction: (type: string) => void
}

const HeroFounderSpotlight: React.FC<HeroFounderSpotlightProps> = ({
  founder,
  onInteraction
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-12"
    >
      <Glass
        intensity="strong"
        tint="brand"
        className="overflow-hidden relative"
      >
        <div className="grid md:grid-cols-2 gap-8 p-8">
          {/* Founder Info */}
          <div className="z-10 relative">
            <div className="flex items-center gap-4 mb-4">
              <motion.img
                src={founder.avatar_url}
                alt={founder.name}
                className="w-16 h-16 rounded-full object-cover border-2 border-purple-500"
                whileHover={{ scale: 1.1 }}
                onError={(e) => {
                  e.currentTarget.src = '/api/avatars/placeholder.jpg'
                }}
              />
              
              <div>
                <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  {founder.name}
                  <div className="flex gap-1">
                    {founder.badges.map(badge => (
                      <BadgeIcon key={badge} badge={badge} />
                    ))}
                  </div>
                </h3>
                <p className="text-gray-600">
                  {founder.title} at {founder.company}
                </p>
                <div className="text-sm text-purple-600 font-medium">
                  {founder.tier} Member • {formatMemberSince(founder.member_since)}
                </div>
              </div>
            </div>
            
            <div className="mb-6">
              <p className="text-gray-700 text-lg leading-relaxed mb-4">
                {founder.bio}
              </p>
              
              {founder.achievement && (
                <DopamineTrigger
                  event={{
                    type: 'social_win',
                    intensity: 'medium',
                    message: 'Inspiring success story!'
                  }}
                >
                  <div className="bg-gradient-to-r from-green-100 to-blue-100 p-4 rounded-lg">
                    <div className="text-sm font-medium text-gray-700">
                      🏆 Recent Achievement
                    </div>
                    <div className="text-green-700 font-medium">
                      {founder.achievement}
                    </div>
                  </div>
                </DopamineTrigger>
              )}
            </div>
            
            {/* Metrics */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {founder.metrics.successful_predictions}
                </div>
                <div className="text-xs text-gray-500">Predictions</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {founder.metrics.portfolio_value}
                </div>
                <div className="text-xs text-gray-500">Portfolio</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {founder.metrics.network_connections}
                </div>
                <div className="text-xs text-gray-500">Network</div>
              </div>
            </div>
            
            {/* CTA Button */}
            <Interactive
              interaction={{
                trigger: 'hero-founder-connect',
                rules: { founder_id: founder.user_id },
                feedback: { visual: 'glow', haptic: 'medium' }
              }}
            >
              <button
                onClick={() => {
                  onInteraction('connect')
                  window.open(founder.cta_url, '_blank')
                }}
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all duration-300"
              >
                {founder.cta} →
              </button>
            </Interactive>
          </div>
          
          {/* Visual Elements */}
          <div className="relative">
            <div className="text-center">
              <div className="text-8xl mb-4">🌟</div>
              <div className="text-purple-600 font-bold text-lg">
                Featured Founder Spotlight
              </div>
              <div className="text-gray-500 text-sm">
                24-hour rotation • Purple tier exclusive
              </div>
            </div>
            
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-10">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500 rounded-full blur-3xl" />
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-pink-500 rounded-full blur-2xl" />
            </div>
          </div>
        </div>
      </Glass>
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// FEATURED FOUNDERS GRID
// ═══════════════════════════════════════════════════════════════════════════════════

interface FeaturedFoundersGridProps {
  founders: FeaturedFounder[]
  onInteraction: (founder: FeaturedFounder, type: string) => void
}

const FeaturedFoundersGrid: React.FC<FeaturedFoundersGridProps> = ({
  founders,
  onInteraction
}) => {
  return (
    <div className="mb-12">
      <h3 className="text-2xl font-bold text-gray-900 mb-6">
        🏆 Featured Founder Network
      </h3>
      
      <StaggerList
        staggerDelay="cards"
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
      >
        {founders.map((founder) => (
          <FounderCard
            key={founder.user_id}
            founder={founder}
            onInteraction={(type) => onInteraction(founder, type)}
          />
        ))}
      </StaggerList>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// FOUNDER CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════════

interface FounderCardProps {
  founder: FeaturedFounder
  onInteraction: (type: string) => void
}

const FounderCard: React.FC<FounderCardProps> = ({ founder, onInteraction }) => {
  return (
    <Interactive
      interaction={{
        trigger: 'founder-card-click',
        rules: { founder_id: founder.user_id },
        feedback: { visual: 'highlight' }
      }}
    >
      <Glass
        intensity="medium"
        className="p-4 hover:shadow-lg transition-all duration-300 cursor-pointer group"
        onClick={() => onInteraction('click')}
      >
        <div className="text-center">
          <motion.img
            src={founder.avatar_url}
            alt={founder.name}
            className="w-16 h-16 rounded-full object-cover mx-auto mb-3 border-2 border-purple-200"
            whileHover={{ scale: 1.1 }}
            onError={(e) => {
              e.currentTarget.src = '/api/avatars/placeholder.jpg'
            }}
          />
          
          <h4 className="font-bold text-gray-900 mb-1 flex items-center justify-center gap-1">
            {founder.name}
            <div className="flex">
              {founder.badges.map(badge => (
                <BadgeIcon key={badge} badge={badge} size="sm" />
              ))}
            </div>
          </h4>
          
          <p className="text-sm text-gray-600 mb-2">
            {founder.title}
          </p>
          
          <p className="text-xs text-gray-500 mb-3">
            {founder.company}
          </p>
          
          {/* Quick Metrics */}
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <div>
              <div className="font-bold text-blue-600">
                {founder.metrics.successful_predictions}
              </div>
              <div className="text-gray-500">Predictions</div>
            </div>
            <div>
              <div className="font-bold text-green-600">
                {founder.metrics.network_connections}
              </div>
              <div className="text-gray-500">Network</div>
            </div>
          </div>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onInteraction('connect')
              window.open(founder.cta_url, '_blank')
            }}
            className="w-full bg-purple-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
          >
            {founder.cta}
          </button>
        </div>
      </Glass>
    </Interactive>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// SUCCESS STORIES SECTION
// ═══════════════════════════════════════════════════════════════════════════════════

interface SuccessStoriesProps {
  stories: FeaturedFounder[]
  onInteraction: (founder: FeaturedFounder, type: string) => void
}

const SuccessStories: React.FC<SuccessStoriesProps> = ({ stories, onInteraction }) => {
  return (
    <div className="mb-12">
      <h3 className="text-2xl font-bold text-gray-900 mb-6">
        🎯 Recent Success Stories
      </h3>
      
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stories.map((story) => (
          <SuccessStoryCard
            key={story.user_id}
            story={story}
            onInteraction={(type) => onInteraction(story, type)}
          />
        ))}
      </div>
    </div>
  )
}

const SuccessStoryCard: React.FC<{
  story: FeaturedFounder
  onInteraction: (type: string) => void
}> = ({ story, onInteraction }) => {
  return (
    <Glass intensity="medium" className="p-6">
      <div className="flex items-start gap-4 mb-4">
        <img
          src={story.avatar_url}
          alt={story.name}
          className="w-12 h-12 rounded-full object-cover"
          onError={(e) => {
            e.currentTarget.src = '/api/avatars/placeholder.jpg'
          }}
        />
        <div>
          <div className="font-bold text-gray-900 flex items-center gap-1">
            {story.name}
            <div className="flex">
              {story.badges.map(badge => (
                <BadgeIcon key={badge} badge={badge} size="sm" />
              ))}
            </div>
          </div>
          <div className="text-sm text-gray-600">{story.company}</div>
        </div>
      </div>
      
      <div className="mb-4">
        <div className="text-green-700 font-medium text-sm mb-2">
          🏆 {story.achievement}
        </div>
        <p className="text-gray-700 text-sm">{story.bio}</p>
      </div>
      
      <button
        onClick={() => {
          onInteraction('story_click')
          window.open(story.profile_url, '_blank')
        }}
        className="text-purple-600 font-medium text-sm hover:text-purple-700"
      >
        View Profile →
      </button>
    </Glass>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// PURPLE UPGRADE PROMPT
// ═══════════════════════════════════════════════════════════════════════════════════

interface PurpleUpgradePromptProps {
  onUpgradeClick?: () => void
}

const PurpleUpgradePrompt: React.FC<PurpleUpgradePromptProps> = ({ onUpgradeClick }) => {
  return (
    <DopamineTrigger
      event={{
        type: 'social_win',
        intensity: 'heavy',
        message: 'Your success deserves the spotlight!'
      }}
    >
      <Glass
        intensity="strong"
        tint="brand"
        className="p-8 border-2 border-purple-500 bg-gradient-to-r from-purple-50 to-pink-50"
      >
        <div className="text-center">
          <div className="text-4xl mb-4">👑</div>
          <h3 className="text-2xl font-bold text-purple-600 mb-4">
            Ready for Your Moment in the Spotlight?
          </h3>
          <p className="text-gray-700 mb-6 max-w-2xl mx-auto">
            Join these successful founders with Purple tier membership. 
            Get featured on the home screen, expand your network, and showcase your achievements.
          </p>
          
          <div className="flex justify-center gap-4">
            <button
              onClick={onUpgradeClick}
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all duration-300"
            >
              Upgrade to Purple
            </button>
            <button className="border border-gray-300 text-gray-700 px-8 py-3 rounded-lg font-medium hover:bg-gray-50">
              Learn More
            </button>
          </div>
        </div>
      </Glass>
    </DopamineTrigger>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// UTILITY COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════════

const BadgeIcon: React.FC<{ badge: string; size?: 'sm' | 'md' }> = ({ 
  badge, 
  size = 'md' 
}) => {
  const badgeIcons = {
    purple: '💜',
    kingmaker: '👑',
    verified: '✓',
    oracle: '🔮',
    whale: '🐋'
  }
  
  const badgeColors = {
    purple: 'bg-purple-500',
    kingmaker: 'bg-yellow-500', 
    verified: 'bg-blue-500',
    oracle: 'bg-purple-400',
    whale: 'bg-green-500'
  }
  
  const sizeClasses = size === 'sm' ? 'w-4 h-4 text-xs' : 'w-5 h-5 text-sm'
  
  return (
    <div
      className={cn(
        'rounded-full text-white flex items-center justify-center',
        badgeColors[badge as keyof typeof badgeColors] || 'bg-gray-500',
        sizeClasses
      )}
      title={badge.charAt(0).toUpperCase() + badge.slice(1)}
    >
      {badgeIcons[badge as keyof typeof badgeIcons] || badge.charAt(0)}
    </div>
  )
}

const formatMemberSince = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays < 30) {
    return `${diffDays} days ago`
  } else if (diffDays < 365) {
    const months = Math.floor(diffDays / 30)
    return `${months} month${months > 1 ? 's' : ''} ago`
  } else {
    const years = Math.floor(diffDays / 365)
    return `${years} year${years > 1 ? 's' : ''} ago`
  }
}

// ═══════════════════════════════════════════════════════════════════════════════════
// LOADING & ERROR STATES
// ═══════════════════════════════════════════════════════════════════════════════════

const FeaturedFoundersLoading: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('py-12', className)}>
    <div className="max-w-7xl mx-auto px-6">
      <div className="h-8 bg-gray-200 rounded w-64 mb-8 animate-pulse" />
      <div className="h-48 bg-gray-200 rounded-lg mb-8 animate-pulse" />
      <div className="grid grid-cols-4 gap-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-64 bg-gray-200 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  </div>
)

const FeaturedFoundersError: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('py-12 text-center', className)}>
    <div className="text-gray-500">
      Unable to load featured founders. Please try again later.
    </div>
  </div>
)

export type { 
  FeaturedFoundersProps, 
  FeaturedFounder, 
  FeaturedFoundersData 
}