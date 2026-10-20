/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Urbanist", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        ink: { DEFAULT: "#f4eef3", 2: "#cfc4cc", muted: "#a39aa1", faint: "#71666e" },
        plum: { 50: "#f6e9f2", 200: "#e3bcd8", 300: "#d79bc7", 400: "#c78fb8", 500: "#a8679a", 600: "#7d4570", 700: "#5a2f51", 800: "#3a1f35", 900: "#22121f" },
        base: { DEFAULT: "#0b0709", frame: "#100c0f", panel: "#151015", raised: "#1c151b", line: "rgba(255,255,255,0.07)" },
        pos: "#4ade80",
        neg: "#f87171",
      },
      borderRadius: { card: "22px" },
    },
  },
  plugins: [],
};
