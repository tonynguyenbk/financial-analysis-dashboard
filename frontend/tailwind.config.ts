import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        mint: "rgb(var(--color-mint) / <alpha-value>)",
        marine: "rgb(var(--color-marine) / <alpha-value>)",
        gold: "rgb(var(--color-gold) / <alpha-value>)",
        coral: "rgb(var(--color-coral) / <alpha-value>)"
      },
      boxShadow: {
        soft: "0 14px 40px rgb(var(--shadow-soft) / 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
