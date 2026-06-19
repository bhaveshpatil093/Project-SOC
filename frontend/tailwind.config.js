/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          800: '#1e293b',
          900: '#0f172a',
        },
        blue: {
          500: '#3b82f6',
        },
        red: {
          500: '#ef4444',
        },
        orange: {
          500: '#f97316',
        },
        yellow: {
          500: '#eab308',
        },
        green: {
          500: '#22c55e',
        }
      }
    },
  },
  plugins: [],
}
