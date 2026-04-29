/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dde8ff',
          200: '#b3c5ff',
          300: '#809cff',
          400: '#6279f8',
          500: '#4f6ef7',
          600: '#3b55e6',
          700: '#2d42cc',
          900: '#1a2575',
        }
      }
    }
  },
  plugins: []
}
