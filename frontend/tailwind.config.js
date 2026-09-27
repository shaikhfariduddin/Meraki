/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#FAF6EF",
        ink: "#1C1A17",
        muted: "#6B6559",
        accent: "#E3A008",
        line: "#E8E1D3",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "sans-serif"],
      },
      boxShadow: {
        soft: "0 8px 24px -8px rgba(28,26,23,0.12)",
        accent: "0 10px 24px -8px rgba(227,160,8,0.45)",
      },
      backgroundImage: {
        grid: "linear-gradient(to right, #EFE9DC 1px, transparent 1px), linear-gradient(to bottom, #EFE9DC 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
