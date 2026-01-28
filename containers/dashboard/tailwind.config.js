/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,js,py}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        heading: ["Outfit", "sans-serif"],
      },
      colors: {
        silva: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
        dark: {
          bg: "#020617", // Slate 950 base
          surface: "#0f172a", // Slate 900
          surface_light: "#1e293b", // Slate 800
          border: "#1e293b", // Slate 800
        },
      },
      boxShadow: {
        neon: '0 0 5px theme("colors.silva.400"), 0 0 20px theme("colors.silva.900")',
        glass: "0 4px 30px rgba(0, 0, 0, 0.1)",
      },
    },
  },
  plugins: [],
}
