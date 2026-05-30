import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Vigil Summit — Segurança para a Era da IA',
  description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-950 text-white antialiased">{children}</body>
    </html>
  )
}
