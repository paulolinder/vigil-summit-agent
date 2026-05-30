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
      },
      colors: {
        brand: {
          navy:   '#0F2A34',
          teal:   '#48C2C5',
          green:  '#59BD75',
          lime:   '#DDEB4F',
          bg:     '#F7F9FB',
          border: '#E5EAF0',
          muted:  '#64748B',
          text:   '#102A34',
        },
      },
    },
  },
  plugins: [],
}
export default config
