import React from 'react';
import { PurpleTierPricing } from '../components/PurpleTierPricing';
import { SceneProvider } from '../lib/scene-provider';

export const PricingPage: React.FC = () => {
  return (
    <SceneProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Header Section */}
        <div className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-900/20 to-blue-900/20" />
          
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div className="text-center">
              <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
                <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  Choose Your Impact
                </span>
              </h1>
              
              <p className="text-xl md:text-2xl text-slate-300 mb-8 max-w-3xl mx-auto">
                Join the elite tier of founders shaping the future of SaaS through prediction markets.
                Get maximum visibility and unlock exclusive opportunities.
              </p>

              <div className="flex items-center justify-center space-x-4 mb-8">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-slate-300 text-sm">247 founders already featured</span>
                </div>
                
                <div className="w-1 h-4 bg-slate-600"></div>
                
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-purple-400 rounded-full"></div>
                  <span className="text-slate-300 text-sm">$2.4M+ in platform volume</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Purple Tier Pricing Component */}
        <PurpleTierPricing />

        {/* Social Proof & Success Stories */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              What Purple Tier Founders Are Saying
            </h2>
            <p className="text-slate-300 text-lg">
              Real results from founders who invested in maximum visibility
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-gradient-to-br from-purple-900/30 to-slate-800/30 backdrop-blur-sm rounded-xl p-6 border border-purple-500/30">
              <div className="flex items-center mb-4">
                <img 
                  src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&h=64&fit=crop&crop=face&auto=format" 
                  alt="Founder" 
                  className="w-12 h-12 rounded-full mr-4"
                />
                <div>
                  <div className="text-white font-semibold">Alex Chen</div>
                  <div className="text-purple-400 text-sm">SaaS Founder, $2M ARR</div>
                </div>
              </div>
              <p className="text-slate-300 mb-4">
                "Purple tier gave me 300% more profile views and directly led to $500K in new funding. 
                The home screen featuring is worth every penny."
              </p>
              <div className="flex text-yellow-400 text-sm">
                {'★'.repeat(5)}
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-900/30 to-slate-800/30 backdrop-blur-sm rounded-xl p-6 border border-blue-500/30">
              <div className="flex items-center mb-4">
                <img 
                  src="https://images.unsplash.com/photo-1494790108755-2616b612b665?w=64&h=64&fit=crop&crop=face&auto=format" 
                  alt="Founder" 
                  className="w-12 h-12 rounded-full mr-4"
                />
                <div>
                  <div className="text-white font-semibold">Sarah Martinez</div>
                  <div className="text-blue-400 text-sm">AI Startup CEO</div>
                </div>
              </div>
              <p className="text-slate-300 mb-4">
                "The network effect is incredible. Being featured connected me with 3 strategic partners 
                and 50+ qualified investors in my first month."
              </p>
              <div className="flex text-yellow-400 text-sm">
                {'★'.repeat(5)}
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-900/30 to-slate-800/30 backdrop-blur-sm rounded-xl p-6 border border-green-500/30">
              <div className="flex items-center mb-4">
                <img 
                  src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=64&h=64&fit=crop&crop=face&auto=format" 
                  alt="Founder" 
                  className="w-12 h-12 rounded-full mr-4"
                />
                <div>
                  <div className="text-white font-semibold">Michael Torres</div>
                  <div className="text-green-400 text-sm">FinTech Founder</div>
                </div>
              </div>
              <p className="text-slate-300 mb-4">
                "ROI was immediate. The Purple tier positioning helped me close Series A 2 months 
                faster than projected. Best investment I've made."
              </p>
              <div className="flex text-yellow-400 text-sm">
                {'★'.repeat(5)}
              </div>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-6">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h3 className="text-xl font-bold text-white mb-4">
                How often will I be featured on the home screen?
              </h3>
              <p className="text-slate-300">
                Purple tier members are featured in rotation based on our algorithmic system. 
                You'll appear on the home screen multiple times per week, with higher frequency 
                for longer-term subscribers and active community participants.
              </p>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h3 className="text-xl font-bold text-white mb-4">
                Can I customize my featuring content?
              </h3>
              <p className="text-slate-300">
                Yes! Purple tier members can customize their bio, highlight specific achievements, 
                and set custom call-to-action text for their featuring slots through the dashboard.
              </p>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h3 className="text-xl font-bold text-white mb-4">
                What's the average ROI for Purple tier members?
              </h3>
              <p className="text-slate-300">
                Based on our member surveys, Purple tier founders report an average of 12x ROI 
                within 6 months through new connections, funding opportunities, and strategic partnerships.
              </p>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h3 className="text-xl font-bold text-white mb-4">
                Can I switch between billing cycles?
              </h3>
              <p className="text-slate-300">
                Absolutely! You can switch between monthly and annual billing at any time. 
                Annual subscribers save up to 30% and receive priority featuring placement.
              </p>
            </div>
          </div>
        </div>

        {/* Final CTA */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 backdrop-blur-sm rounded-2xl p-8 border border-purple-500/30">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Join the Elite?
            </h2>
            <p className="text-slate-300 mb-8 text-lg">
              Don't let another day pass without maximum visibility. Your next breakthrough connection is waiting.
            </p>
            
            <button className="px-8 py-4 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg shadow-purple-500/25">
              Start Purple Tier Today
            </button>
            
            <p className="text-slate-400 text-sm mt-4">
              30-day money-back guarantee • Cancel anytime • Instant activation
            </p>
          </div>
        </div>
      </div>
    </SceneProvider>
  );
};