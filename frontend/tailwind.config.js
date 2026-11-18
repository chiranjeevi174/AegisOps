/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#100F0D",
        foreground: "#F5F0E8",
        obsidian: {
          950: "#100F0D", // Main background
          900: "#191714", // Header background
          850: "#211D19", // Sidebar background
          800: "#26211B", // Card background
          750: "#302920", // Elevated surfaces
          700: "#40372D", // Borders
          600: "#574B3D",
          500: "#756653",
          text: "#F5F0E8",
          secondary: "#B8AA99",
          muted: "#817565",
        },
        copper: {
          50: "#FDF8F3",
          100: "#FAF0E4",
          200: "#F4DFC5",
          300: "#ECC79B",
          400: "#E58A2B", // Primary copper
          500: "#D4771C",
          600: "#B85E10",
          700: "#8F450B",
          800: "#632D06",
          900: "#3B1903",
          950: "#240E01",
        },
        amber: {
          50: "#FFFBEB",
          100: "#FEF3C7",
          200: "#FDE68A",
          300: "#FCD34D",
          400: "#F5A623", // Secondary amber
          500: "#E59516",
          600: "#D97706",
          700: "#B45309",
          800: "#92400E",
          900: "#78350F",
          950: "#451A03",
        },
        ai: {
          violet: "#A78BFA",
          dark: "#2E1065",
          surface: "rgba(167, 139, 250, 0.08)",
          border: "rgba(167, 139, 250, 0.25)",
        },
        status: {
          healthy: "#4ADE80",
          warning: "#FBBF24",
          critical: "#FB7185",
          neutral: "#94A3B8",
        },
        card: {
          DEFAULT: "#26211B",
          foreground: "#F5F0E8",
        },
        primary: {
          DEFAULT: "#E58A2B",
          foreground: "#100F0D",
        },
        secondary: {
          DEFAULT: "#302920",
          foreground: "#F5F0E8",
        },
        muted: {
          DEFAULT: "#211D19",
          foreground: "#817565",
        },
        accent: {
          DEFAULT: "#302920",
          foreground: "#F5F0E8",
        },
        destructive: {
          DEFAULT: "#FB7185",
          foreground: "#100F0D",
        },
        border: "#40372D",
        input: "#191714",
        ring: "#E58A2B",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        "copper-sm": "0 1px 3px 0 rgba(229, 138, 43, 0.15)",
        "copper-md": "0 4px 12px 0 rgba(229, 138, 43, 0.2)",
        "copper-lg": "0 8px 24px 0 rgba(229, 138, 43, 0.25)",
        "obsidian-sm": "0 1px 3px 0 rgba(0, 0, 0, 0.5)",
        "obsidian-md": "0 4px 14px 0 rgba(0, 0, 0, 0.6)",
        "obsidian-lg": "0 10px 30px 0 rgba(0, 0, 0, 0.7)",
      },
    },
  },
  plugins: [],
}
