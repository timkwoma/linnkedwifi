import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-space)"],
        body: ["var(--font-manrope)"],
      },
      colors: {
        ink: "#0f172a",
        mist: "#f8fafc",
        cyan: "#06b6d4",
        coral: "#f97316",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(6,182,212,0.2), 0 20px 40px rgba(15,23,42,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;

