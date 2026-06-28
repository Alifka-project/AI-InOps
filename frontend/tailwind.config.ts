import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#041E42",
          50: "#E7ECF3",
          100: "#C2CFE0",
          700: "#0A2C55",
          800: "#072144",
          900: "#031428",
        },
        ink: "#0A1628",
        surface: "#0E1B2E",
        panel: "#13243B",
        accent: {
          DEFAULT: "#16D6C9",
          soft: "#13B7AC",
        },
        electric: "#2E9BFF",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.25)",
      },
      borderRadius: {
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
};

export default config;
