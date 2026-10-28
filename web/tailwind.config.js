/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9eaff',
          200: '#bcdaff',
          300: '#8ec4ff',
          400: '#59a4ff',
          500: '#3382fb',
          600: '#1d63f0',
          700: '#174edc',
          800: '#1941b2',
          900: '#1a3a8c',
          950: '#142555',
        },
        accent: {
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        night: {
          950: '#060a14',
          900: '#0a1020',
          850: '#0d1526',
          800: '#111a2e',
          750: '#16213a',
          700: '#1c2946',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans Arabic', 'system-ui', 'sans-serif'],
        display: ['Sora', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 45px -12px rgba(51, 130, 251, 0.65)',
        card: '0 18px 45px -25px rgba(0, 0, 0, 0.55)',
      },
      backgroundImage: {
        'mesh-dark':
          'radial-gradient(ellipse at 12% 8%, rgba(29,99,240,0.28), transparent 45%), radial-gradient(ellipse at 85% 0%, rgba(6,182,212,0.18), transparent 40%), radial-gradient(ellipse at 50% 100%, rgba(168,85,247,0.12), transparent 45%)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-500px 0' },
          '100%': { backgroundPosition: '500px 0' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(51,130,251,0.45)' },
          '70%': { boxShadow: '0 0 0 12px rgba(51,130,251,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(51,130,251,0)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.35s ease-out both',
        shimmer: 'shimmer 1.6s linear infinite',
        'pulse-ring': 'pulse-ring 2s infinite',
      },
    },
  },
  plugins: [],
};
