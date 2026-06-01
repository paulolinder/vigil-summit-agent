import type { Metadata } from 'next'
// Inter self-hospedada via npm (fontsource) em vez de next/font/google: evita o fetch
// ao Google Fonts em build time, que falha em builds Docker sem rede de saída (Dokploy).
// A var --font-inter (consumida pelo tailwind fontFamily.sans) é definida em globals.css.
import '@fontsource-variable/inter'
import './globals.css'

export const metadata: Metadata = {
  title: 'Vigil Summit — Segurança para a Era da IA',
  description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-brand-bg text-brand-text antialiased">
        {children}
      </body>
    </html>
  )
}
