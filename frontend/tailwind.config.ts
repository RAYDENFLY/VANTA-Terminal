import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0B0D13",
          surface: "#12151E",
          card: "#171B26",
          sub: "#1D2230",
          border: "#232836",
          borderLight: "#363D52",
          amber: "#F59E0B",
          amberDark: "#D97706",
          amberGlow: "rgba(245, 158, 11, 0.15)",
          text: "#E2E8F0",
          muted: "#8E9BAE",
          dim: "#556073",
          positive: "#10B981",
          negative: "#EF4444",
          neutral: "#64748B",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "Consolas",
          "Roboto Mono",
          "monospace"
        ],
      },
    },
  },
  plugins: [],
};

export default config;
