/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#071426",
          900: "#0B1F3A",
          800: "#122D52",
          700: "#1B3E6E",
        },
        cream: {
          50: "#FAF8F3",
          100: "#F4EFE6",
          200: "#E8E0D1",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
