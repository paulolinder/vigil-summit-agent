import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Vigil Summit — Segurança para a Era da IA',
  description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.variable} bg-brand-bg text-brand-text antialiased`}>
        {children}
      </body>
    </html>
  )
}
