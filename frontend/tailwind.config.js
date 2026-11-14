/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#06101E",
          900: "#0B1F3A",
          800: "#133157",
          700: "#1D4575",
        },
        cream: {
          50: "#FAF8F3",
          100: "#F3EDE2",
          200: "#E5DEC9",
        },
        brass: {
          50: "#FEF9EE",
          100: "#FBF0D6",
          400: "#DDA13C",
          500: "#C88A2E",
          600: "#A66E1B",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
        serif: ["Instrument Serif", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        editorial: "0 20px 50px -24px rgba(6, 16, 30, 0.22)",
        card: "0 10px 30px -18px rgba(6, 16, 30, 0.16)",
      },
    },
  },
  plugins: [],
};
