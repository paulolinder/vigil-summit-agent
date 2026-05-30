export const dynamic = 'force-dynamic'

import RegistrationForm from '@/components/landing/RegistrationForm'
import ChatbotWidget from '@/components/landing/ChatbotWidget'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950">
      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-20 pb-12 text-center">
        <p className="text-purple-400 text-sm font-semibold tracking-widest uppercase mb-4">
          São Paulo · Presencial · 120 vagas
        </p>
        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
          Vigil Summit<br />
          <span className="text-purple-400">Segurança para a Era da IA</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto leading-relaxed">
          O encontro definitivo de CISOs, CTOs e líderes de segurança para discutir IA, conformidade e Zero Trust em 2026.
        </p>
      </section>

      {/* Tópicos */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: '🛡️', title: 'Zero Trust', desc: 'Arquitetura moderna para ambientes híbridos' },
            { icon: '🤖', title: 'IA em Segurança', desc: 'Detecção e resposta com modelos de linguagem' },
            { icon: '📋', title: 'Conformidade', desc: 'LGPD, ISO 27001, SOC 2 na prática' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <span className="text-2xl">{icon}</span>
              <p className="text-white font-medium mt-2 text-sm">{title}</p>
              <p className="text-gray-500 text-xs mt-1">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Form */}
      <section className="max-w-lg mx-auto px-6 pb-24" id="inscricao">
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <h2 className="text-white text-xl font-semibold mb-6 text-center">Garanta sua vaga</h2>
          <RegistrationForm />
        </div>
      </section>

      <ChatbotWidget />
    </main>
  )
}
