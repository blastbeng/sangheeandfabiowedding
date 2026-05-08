/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'wedding-azure': '#5B9BD5',
        'wedding-sky': '#87CEEB',
        'wedding-navy': '#2C3E50',
        'wedding-blush': '#F4C2C2',
        'wedding-gold': '#D4AF37',
        'wedding-cream': '#FFFDD0',
        'wedding-sage': '#9CAF88',
        'wedding-lavender': '#E6E6FA',
      },
    },
  },
  plugins: [],
}
