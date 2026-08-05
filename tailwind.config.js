/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/ui/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#7c3aed', // purple-600
          light: '#a78bfa',
        },
      },
      keyframes: {
        'dopamine-pulse': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.04)' },
        },
        'streak-flicker': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      animation: {
        'dopamine-pulse': 'dopamine-pulse 1.2s ease-in-out infinite',
        'streak-flicker': 'streak-flicker 1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
