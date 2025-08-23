# FundCast UI Components

## Purple Tier Subscription Integration

This directory contains the complete UI implementation for the Purple Tier premium subscription system with home screen featuring functionality.

### Key Components

#### 🎯 **Purple Tier Subscription**
- **PurpleTierPricing.tsx** - Psychology-optimized pricing component with anchoring effects
- **FeaturedFounders.tsx** - Home screen featuring display with real-time rotation
- **PricingPage.tsx** - Complete pricing page with social proof and FAQs

#### 🏠 **Main Application**
- **App.tsx** - Main application with navigation and routing
- **HomePage.tsx** - Landing page integrating featured founders
- **pages/** - Page components for different routes

#### 🎨 **Scene System (SST)**
- **scene-system.ts** - Motion-driven UI framework
- **scene-provider.tsx** - React context provider for scene management
- **advanced-animations.tsx** - Material Design + Apple HIG animations

#### 🎲 **Gambling Psychology Engine**
- **gambling-psychology.tsx** - Dopamine-driven engagement mechanics
- **viral-growth.tsx** - Prophet Program referral system

### Usage

```tsx
import { App, PurpleTierPricing, FeaturedFounders } from './ui';

// Main application
function MyApp() {
  return <App />;
}

// Individual components
function PricingSection() {
  return <PurpleTierPricing />;
}

function HomeHero() {
  return <FeaturedFounders />;
}
```

### Architecture

```
src/ui/
├── App.tsx                     # Main application shell
├── index.ts                    # Component exports
├── components/                 # Core UI components
│   ├── PurpleTierPricing.tsx  # Subscription pricing
│   └── FeaturedFounders.tsx   # Home screen featuring
├── pages/                      # Page components
│   ├── HomePage.tsx           # Landing page
│   └── PricingPage.tsx        # Pricing & plans
├── lib/                       # Advanced libraries
│   ├── scene-system.ts        # Motion framework
│   ├── gambling-psychology.tsx # Engagement mechanics
│   ├── viral-growth.tsx       # Growth engine
│   └── scene-provider.tsx     # Scene context
└── examples/                  # Demo components
    ├── scene-system-example.tsx
    └── market-domination-demo.tsx
```

### Features

#### 💎 **Purple Tier Benefits**
- Home screen featuring with algorithmic rotation
- Priority placement in search and discovery
- Custom bio and achievement highlighting
- Verified founder badge
- Enhanced networking tools

#### 🎭 **Psychology-Driven Design**
- Status signaling through tier hierarchy
- Anchoring effects in pricing display
- Social proof through member testimonials
- FOMO creation with limited-time offers
- Network effects amplification

#### 🚀 **Performance Optimizations**
- Scene-based motion system for smooth transitions
- Lazy loading for heavy components
- Optimized rendering with React patterns
- Real-time updates via WebSocket integration

### Integration with Backend

The UI components integrate with the subscription API endpoints:

```typescript
// Subscription management
POST /api/v1/subscriptions/checkout
GET  /api/v1/subscriptions/my-subscription
POST /api/v1/subscriptions/upgrade

// Purple tier featuring
GET  /api/v1/subscriptions/purple-featuring/current
POST /api/v1/subscriptions/purple-featuring/{id}/content
POST /api/v1/subscriptions/purple-featuring/{id}/track

// Payment processing via LemonSqueezy
POST /api/v1/subscriptions/webhooks/lemonsqueezy
```

### Development

The UI components are built with modern React patterns and TypeScript for type safety. They integrate seamlessly with the FundCast backend APIs and include comprehensive error handling and loading states.

For development, import the components from the main UI index file and use within your application shell.