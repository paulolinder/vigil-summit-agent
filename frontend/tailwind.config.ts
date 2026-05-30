import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        playfair: ['var(--font-playfair)', 'Georgia', 'serif'],
      },
      colors: {
        navy: {
          700: '#0369a1',
          950: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
export default config
