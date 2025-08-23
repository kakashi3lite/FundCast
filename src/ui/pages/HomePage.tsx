import React from 'react';
import { FeaturedFounders } from '../components/FeaturedFounders';
import { SceneProvider } from '../lib/scene-provider';

export const HomePage: React.FC = () => {
  return (
    <SceneProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Hero Section */}
        <div className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-900/20 to-blue-900/20" />
          
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
            <div className="text-center">
              <h1 className="text-5xl md:text-7xl font-bold text-white mb-8">
                <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  FundCast
                </span>
              </h1>
              
              <p className="text-xl md:text-2xl text-slate-300 mb-12 max-w-3xl mx-auto">
                AI-first social funding + forecasting platform for SaaS founders.
                Connect, predict, and invest in the future of innovation.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button className="px-8 py-4 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition-all duration-200 transform hover:scale-105">
                  Start Predicting
                </button>
                
                <button className="px-8 py-4 border border-purple-400 text-purple-400 hover:bg-purple-400 hover:text-white font-semibold rounded-lg transition-all duration-200">
                  View Markets
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Featured Founders Section */}
        <FeaturedFounders />

        {/* Platform Stats */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <div className="text-3xl font-bold text-purple-400 mb-2">$2.4M+</div>
              <div className="text-slate-300">Total Volume</div>
            </div>
            
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <div className="text-3xl font-bold text-blue-400 mb-2">1,247</div>
              <div className="text-slate-300">Active Founders</div>
            </div>
            
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <div className="text-3xl font-bold text-green-400 mb-2">342</div>
              <div className="text-slate-300">Active Markets</div>
            </div>
            
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <div className="text-3xl font-bold text-yellow-400 mb-2">89.2%</div>
              <div className="text-slate-300">Accuracy Rate</div>
            </div>
          </div>
        </div>

        {/* Features Preview */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              Why Top Founders Choose FundCast
            </h2>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto">
              Join the elite community of SaaS founders making informed decisions through prediction markets
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-8 border border-slate-700 hover:border-purple-500 transition-colors">
              <div className="w-16 h-16 bg-purple-600 rounded-xl flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-4">AI-Powered Insights</h3>
              <p className="text-slate-300 mb-6">
                Leverage advanced AI to predict market trends and make informed investment decisions with unprecedented accuracy.
              </p>
              
              <div className="text-purple-400 font-semibold">Learn More →</div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-8 border border-slate-700 hover:border-blue-500 transition-colors">
              <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-4">Elite Network</h3>
              <p className="text-slate-300 mb-6">
                Connect with verified founders, investors, and industry leaders in exclusive prediction markets and discussions.
              </p>
              
              <div className="text-blue-400 font-semibold">Join Network →</div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-8 border border-slate-700 hover:border-green-500 transition-colors">
              <div className="w-16 h-16 bg-green-600 rounded-xl flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-4">Real Returns</h3>
              <p className="text-slate-300 mb-6">
                Earn real money while helping build the future of SaaS through informed market participation and accurate predictions.
              </p>
              
              <div className="text-green-400 font-semibold">Start Earning →</div>
            </div>
          </div>
        </div>
      </div>
    </SceneProvider>
  );
};