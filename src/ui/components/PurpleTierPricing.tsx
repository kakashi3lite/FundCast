/**
 * Purple Tier Pricing Component - Psychology-optimized subscription interface
 * 
 * Implements proven pricing psychology principles:
 * - Anchoring effect with Kingmaker tier
 * - Social proof and scarcity
 * - Purple tier spotlight and FOMO
 * - Annual discount psychology
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSceneSystem } from '../lib/scene-provider'
import { Glass, Interactive } from '../lib/scene-system'
import { AnimatedNumber, StaggerList } from '../lib/advanced-animations'
import { DopamineTrigger } from '../lib/gambling-psychology'
import { cn } from '../lib/utils'

// ═══════════════════════════════════════════════════════════════════════════════════
// TYPES & INTERFACES
// ═══════════════════════════════════════════════════════════════════════════════════

interface SubscriptionTier {
  id: string
  name: string
  slug: string
  tagline: string
  monthly_price: number
  annual_price?: number
  monthly_price_display: string
  annual_price_display?: string
  annual_savings?: {
    savings_amount: number
    savings_percentage: number
    effective_monthly_price: number
  }
  features: string[]
  highlight_features: string[]
  max_position_size: number
  is_featured: boolean
  is_purple_tier: boolean
}

interface PricingData {
  tiers: SubscriptionTier[]
  recommended_tier: string
  popular_tier: string
  annual_discount_message: string
  purple_spotlight: {
    tagline: string
    benefit: string
    social_proof: string
  }
  upgrade_incentives: Record<string, string>
}

// ═══════════════════════════════════════════════════════════════════════════════════
// MAIN PRICING COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════════

interface PurpleTierPricingProps {
  currentTier?: string
  onSelectTier: (tierSlug: string, billingCycle: 'monthly' | 'annual') => void
  className?: string
}

export const PurpleTierPricing: React.FC<PurpleTierPricingProps> = ({
  currentTier,
  onSelectTier,
  className
}) => {
  const { trackEvent } = useSceneSystem()
  const [pricingData, setPricingData] = useState<PricingData | null>(null)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('annual')
  const [loading, setLoading] = useState(true)
  const [hoveredTier, setHoveredTier] = useState<string | null>(null)
  
  // Load pricing data
  useEffect(() => {
    const loadPricingData = async () => {
      try {
        const response = await fetch('/api/subscriptions/tiers/comparison')
        const data = await response.json()
        setPricingData(data)
      } catch (error) {
        console.error('Failed to load pricing data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadPricingData()
  }, [])
  
  const handleTierSelect = async (tier: SubscriptionTier) => {
    trackEvent('tier-selected', { 
      tier: tier.slug, 
      billing_cycle: billingCycle,
      is_upgrade: currentTier ? tier.slug !== currentTier : false
    })
    
    onSelectTier(tier.slug, billingCycle)
  }
  
  const handleBillingToggle = (cycle: 'monthly' | 'annual') => {
    setBillingCycle(cycle)
    trackEvent('billing-cycle-changed', { cycle })
  }
  
  if (loading) {
    return <PricingLoadingState className={className} />
  }
  
  if (!pricingData) {
    return <PricingErrorState className={className} />
  }
  
  return (
    <div className={cn('py-16 px-6', className)}>
      <div className="max-w-7xl mx-auto">
        {/* Header with Psychology Hook */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your Level of Influence
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Join the most successful SaaS founders. Get the visibility, 
            networks, and insights that separate winners from wannabes.
          </p>
          
          {/* Billing Toggle with Annual Psychology */}
          <div className="flex items-center justify-center gap-4 mb-8">
            <span className={cn(
              'text-lg font-medium transition-colors',
              billingCycle === 'monthly' ? 'text-gray-900' : 'text-gray-500'
            )}>
              Monthly
            </span>
            
            <Interactive
              interaction={{
                trigger: 'billing-toggle',
                rules: { type: 'psychology-anchor' },
                feedback: { visual: 'highlight' }
              }}
            >
              <button
                onClick={() => handleBillingToggle(billingCycle === 'monthly' ? 'annual' : 'monthly')}
                className={cn(
                  'relative w-20 h-10 rounded-full transition-colors',
                  billingCycle === 'annual' ? 'bg-purple-600' : 'bg-gray-300'
                )}
              >
                <motion.div
                  className="absolute top-1 left-1 w-8 h-8 bg-white rounded-full shadow-md"
                  animate={{ x: billingCycle === 'annual' ? 40 : 0 }}
                  transition={{ duration: 0.2 }}
                />
              </button>
            </Interactive>
            
            <span className={cn(
              'text-lg font-medium transition-colors flex items-center gap-2',
              billingCycle === 'annual' ? 'text-gray-900' : 'text-gray-500'
            )}>
              Annual
              <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-sm font-bold">
                Save up to 30%
              </span>
            </span>
          </div>
        </div>
        
        {/* Pricing Cards */}
        <StaggerList
          staggerDelay="cards"
          direction="up"
          className="grid lg:grid-cols-4 gap-8 mb-16"
        >
          {pricingData.tiers.map((tier) => (
            <PricingCard
              key={tier.id}
              tier={tier}
              billingCycle={billingCycle}
              isRecommended={tier.slug === pricingData.recommended_tier}
              isPopular={tier.slug === pricingData.popular_tier}
              isCurrent={tier.slug === currentTier}
              isHovered={hoveredTier === tier.slug}
              onHover={setHoveredTier}
              onSelect={() => handleTierSelect(tier)}
              pricingData={pricingData}
            />
          ))}
        </StaggerList>
        
        {/* Purple Tier Spotlight */}
        <PurpleSpotlight 
          spotlightData={pricingData.purple_spotlight}
          onSelectPurple={() => {
            const purpleTier = pricingData.tiers.find(t => t.slug === 'purple')
            if (purpleTier) handleTierSelect(purpleTier)
          }}
        />
        
        {/* Feature Comparison */}
        <FeatureComparison tiers={pricingData.tiers} />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// PRICING CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════════

interface PricingCardProps {
  tier: SubscriptionTier
  billingCycle: 'monthly' | 'annual'
  isRecommended: boolean
  isPopular: boolean
  isCurrent: boolean
  isHovered: boolean
  onHover: (tierSlug: string | null) => void
  onSelect: () => void
  pricingData: PricingData
}

const PricingCard: React.FC<PricingCardProps> = ({
  tier,
  billingCycle,
  isRecommended,
  isPopular,
  isCurrent,
  isHovered,
  onHover,
  onSelect,
  pricingData
}) => {
  const price = billingCycle === 'annual' && tier.annual_price ? 
    tier.annual_price : tier.monthly_price
  
  const displayPrice = billingCycle === 'annual' && tier.annual_price_display ?
    tier.annual_price_display : tier.monthly_price_display
  
  const effectiveMonthlyPrice = billingCycle === 'annual' && tier.annual_savings ?
    tier.annual_savings.effective_monthly_price : tier.monthly_price
  
  return (
    <motion.div
      onHoverStart={() => onHover(tier.slug)}
      onHoverEnd={() => onHover(null)}
      whileHover={{ y: -8, scale: 1.02 }}
      className="relative"
    >
      {/* Badge for recommended/popular */}
      {(isRecommended || isPopular) && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10"
        >
          <span className={cn(
            'px-4 py-2 rounded-full text-sm font-bold text-white shadow-lg',
            isRecommended ? 'bg-purple-600' : 'bg-blue-600'
          )}>
            {isRecommended ? '⭐ RECOMMENDED' : '🔥 MOST POPULAR'}
          </span>
        </motion.div>
      )}
      
      <Glass
        intensity={tier.is_purple_tier ? 'strong' : 'medium'}
        tint={tier.is_purple_tier ? 'brand' : 'neutral'}
        className={cn(
          'p-8 h-full relative overflow-hidden',
          tier.is_purple_tier && 'border-2 border-purple-500 shadow-purple-100',
          isCurrent && 'ring-2 ring-green-500',
          isHovered && 'shadow-2xl'
        )}
      >
        {/* Purple tier special effects */}
        {tier.is_purple_tier && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-pink-600/10"
            animate={{ 
              background: isHovered ? 
                'linear-gradient(135deg, rgba(147, 51, 234, 0.2), rgba(219, 39, 119, 0.2))' :
                'linear-gradient(135deg, rgba(147, 51, 234, 0.1), rgba(219, 39, 119, 0.1))'
            }}
            transition={{ duration: 0.3 }}
          />
        )}
        
        {/* Tier Header */}
        <div className="relative z-10 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className={cn(
              'text-2xl font-bold',
              tier.is_purple_tier ? 'text-purple-600' : 'text-gray-900'
            )}>
              {tier.name}
            </h3>
            {tier.is_purple_tier && <span className="text-2xl">👑</span>}
          </div>
          
          <p className="text-gray-600 text-sm mb-4">
            {tier.tagline}
          </p>
          
          {/* Pricing */}
          <div className="mb-6">
            <div className="flex items-baseline gap-2">
              <AnimatedNumber
                value={effectiveMonthlyPrice}
                format={(n) => `$${n.toLocaleString()}`}
                className={cn(
                  'text-4xl font-bold',
                  tier.is_purple_tier ? 'text-purple-600' : 'text-gray-900'
                )}
              />
              <span className="text-gray-500 text-lg">
                /{billingCycle === 'annual' ? 'mo' : 'month'}
              </span>
            </div>
            
            {billingCycle === 'annual' && tier.annual_savings && (
              <DopamineTrigger
                event={{
                  type: 'big_win',
                  intensity: 'medium',
                  message: `Save $${tier.annual_savings.savings_amount.toLocaleString()}/year!`
                }}
              >
                <div className="text-green-600 font-medium text-sm">
                  Save ${tier.annual_savings.savings_amount.toLocaleString()} annually 
                  ({tier.annual_savings.savings_percentage}% off)
                </div>
              </DopamineTrigger>
            )}
            
            <div className="text-gray-400 text-sm mt-1">
              Max position: ${(tier.max_position_size / 100).toLocaleString()}
            </div>
          </div>
        </div>
        
        {/* Features List */}
        <div className="relative z-10 mb-8">
          <div className="space-y-3">
            {tier.highlight_features.slice(0, 5).map((feature, index) => (
              <motion.div
                key={feature}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center gap-3"
              >
                <div className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center text-white text-xs',
                  tier.is_purple_tier ? 'bg-purple-500' : 'bg-green-500'
                )}>
                  ✓
                </div>
                <span className="text-gray-700 text-sm">{feature}</span>
              </motion.div>
            ))}
            
            {tier.features.length > 5 && (
              <div className="text-gray-500 text-sm">
                + {tier.features.length - 5} more features
              </div>
            )}
          </div>
        </div>
        
        {/* CTA Button */}
        <div className="relative z-10">
          <Interactive
            interaction={{
              trigger: 'tier-selection',
              rules: { tier: tier.slug },
              feedback: { 
                visual: tier.is_purple_tier ? 'glow' : 'pulse',
                haptic: 'medium'
              }
            }}
          >
            <button
              onClick={onSelect}
              disabled={isCurrent}
              className={cn(
                'w-full py-4 rounded-lg font-bold text-lg transition-all duration-300',
                isCurrent 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : tier.is_purple_tier
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:shadow-lg hover:scale-105'
                    : 'bg-gray-900 text-white hover:bg-gray-800',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isCurrent ? 'Current Plan' : 
               tier.slug === 'founder' ? 'Get Started Free' :
               `Upgrade to ${tier.name}`}
            </button>
          </Interactive>
          
          {!isCurrent && (
            <div className="text-center text-gray-500 text-xs mt-2">
              {billingCycle === 'annual' ? 'Billed annually' : 'Billed monthly'} • Cancel anytime
            </div>
          )}
        </div>
      </Glass>
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// PURPLE TIER SPOTLIGHT
// ═══════════════════════════════════════════════════════════════════════════════════

interface PurpleSpotlightProps {
  spotlightData: PricingData['purple_spotlight']
  onSelectPurple: () => void
}

const PurpleSpotlight: React.FC<PurpleSpotlightProps> = ({
  spotlightData,
  onSelectPurple
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.4 }}
      className="relative mb-16"
    >
      <Glass
        intensity="strong"
        tint="brand"
        className="p-8 border-2 border-purple-500 bg-gradient-to-r from-purple-50 to-pink-50"
      >
        <div className="grid md:grid-cols-2 gap-8 items-center">
          <div>
            <h3 className="text-3xl font-bold text-purple-600 mb-4">
              💜 {spotlightData.tagline}
            </h3>
            <p className="text-gray-700 text-lg mb-4">
              {spotlightData.benefit}
            </p>
            <div className="flex items-center gap-2 text-green-600 font-medium mb-6">
              <span className="text-lg">✨</span>
              <span>{spotlightData.social_proof}</span>
            </div>
            
            <Interactive
              interaction={{
                trigger: 'purple-spotlight-cta',
                rules: { source: 'spotlight' },
                feedback: { visual: 'glow', haptic: 'heavy' }
              }}
            >
              <button
                onClick={onSelectPurple}
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-4 rounded-lg font-bold text-lg hover:shadow-lg hover:scale-105 transition-all duration-300"
              >
                Join the Purple Elite
              </button>
            </Interactive>
          </div>
          
          <div className="text-center">
            <div className="text-6xl mb-4">🏠</div>
            <div className="text-lg text-gray-600">
              Get featured on the home screen and be discovered by the right people
            </div>
          </div>
        </div>
      </Glass>
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// FEATURE COMPARISON TABLE
// ═══════════════════════════════════════════════════════════════════════════════════

interface FeatureComparisonProps {
  tiers: SubscriptionTier[]
}

const FeatureComparison: React.FC<FeatureComparisonProps> = ({ tiers }) => {
  const [showComparison, setShowComparison] = useState(false)
  
  // Get all unique features
  const allFeatures = Array.from(new Set(
    tiers.flatMap(tier => tier.features)
  ))
  
  return (
    <div className="text-center">
      <button
        onClick={() => setShowComparison(!showComparison)}
        className="text-purple-600 font-medium hover:text-purple-700 mb-8"
      >
        {showComparison ? 'Hide' : 'Show'} detailed feature comparison
      </button>
      
      <AnimatePresence>
        {showComparison && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Glass intensity="medium" className="overflow-x-auto">
              <table className="w-full min-w-4xl">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left p-4 font-bold">Features</th>
                    {tiers.map(tier => (
                      <th key={tier.id} className="text-center p-4 font-bold">
                        {tier.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allFeatures.map((feature, index) => (
                    <tr key={feature} className={index % 2 === 0 ? 'bg-gray-50/50' : ''}>
                      <td className="p-4 text-left font-medium">{feature}</td>
                      {tiers.map(tier => (
                        <td key={tier.id} className="p-4 text-center">
                          {tier.features.includes(feature) ? (
                            <span className="text-green-500 text-xl">✓</span>
                          ) : (
                            <span className="text-gray-300 text-xl">–</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Glass>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════════
// LOADING & ERROR STATES
// ═══════════════════════════════════════════════════════════════════════════════════

const PricingLoadingState: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('py-16 px-6', className)}>
    <div className="max-w-7xl mx-auto">
      <div className="text-center mb-16">
        <div className="h-12 bg-gray-200 rounded-lg w-96 mx-auto mb-4 animate-pulse" />
        <div className="h-6 bg-gray-200 rounded w-2/3 mx-auto animate-pulse" />
      </div>
      
      <div className="grid lg:grid-cols-4 gap-8">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-96 bg-gray-200 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  </div>
)

const PricingErrorState: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('py-16 px-6 text-center', className)}>
    <div className="text-red-500 text-lg">
      Failed to load pricing information. Please try again later.
    </div>
  </div>
)

export type { PurpleTierPricingProps, SubscriptionTier, PricingData }