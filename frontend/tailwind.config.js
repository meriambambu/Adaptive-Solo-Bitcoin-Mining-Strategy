/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          purple: '#7c3aed',
          'purple-light': '#a78bfa',
        },
        surface: {
          900: '#0d0d0f',
          800: '#141417',
          700: '#1c1c21',
          600: '#252529',
          500: '#2e2e34',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}

