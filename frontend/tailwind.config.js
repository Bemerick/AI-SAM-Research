/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary colors for opportunity management
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // Fit score colors
        score: {
          high: '#10b981',    // green - fit_score >= 6
          medium: '#f59e0b',  // yellow - fit_score 4-6
          low: '#ef4444',     // red - fit_score < 4
        },
        // Match status colors
        match: {
          pending: '#6b7280',   // gray
          confirmed: '#10b981', // green
          rejected: '#ef4444',  // red
          needsInfo: '#f59e0b', // yellow
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
