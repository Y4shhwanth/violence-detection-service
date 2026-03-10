/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: 'rgba(17, 17, 17, 0.8)',
          solid: '#111111',
          elevated: 'rgba(25, 25, 25, 0.9)',
          hover: 'rgba(255, 255, 255, 0.03)',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.06)',
          DEFAULT: 'rgba(255, 255, 255, 0.08)',
          strong: 'rgba(255, 255, 255, 0.12)',
        },
        card: {
          DEFAULT: 'rgba(17, 17, 17, 0.8)',
          foreground: 'rgba(255, 255, 255, 0.9)',
        },
        'muted-foreground': 'rgba(255, 255, 255, 0.4)',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'glow-red': '0 0 20px rgba(239, 68, 68, 0.15)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.15)',
        'glow-purple': '0 0 20px rgba(139, 92, 246, 0.15)',
      },
      animation: {
        shimmer: 'shimmer 2s infinite linear',
        'pulse-slow': 'pulse 3s infinite',
        'fade-in-up': 'fadeInUp 0.5s ease-out forwards',
        spotlight: 'spotlight 2s ease 0.75s 1 forwards',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        spotlight: {
          '0%': { opacity: '0', transform: 'translate(-72%, -62%) scale(0.5)' },
          '100%': { opacity: '1', transform: 'translate(-50%, -40%) scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
