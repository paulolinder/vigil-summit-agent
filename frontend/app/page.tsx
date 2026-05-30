export const dynamic = 'force-dynamic'

import Navbar from '@/components/ui/Navbar'
import RegistrationForm from '@/components/landing/RegistrationForm'
import ChatbotWidget from '@/components/landing/ChatbotWidget'

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100">
      <Navbar variant="landing" />

      {/* HERO */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-screen-xl mx-auto px-8 py-20 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 bg-sky-700 rounded-full" />
              <span className="text-sky-700 text-xs font-bold tracking-[0.15em] uppercase">
                São Paulo · 15 Ago 2026 · Presencial
              </span>
            </div>
            <h1 className="font-playfair font-black text-5xl text-slate-900 leading-[1.1] tracking-tight mb-5">
              Vigil Summit<br />
              <span className="text-sky-700">Segurança para<br />a Era da IA</span>
            </h1>
            <p className="text-slate-500 text-lg leading-relaxed mb-8 max-w-xl">
              O encontro definitivo de CISOs, CTOs e líderes de segurança corporativa para discutir
              IA, Zero Trust e conformidade em 2026.
            </p>
            <div className="flex gap-3 mb-10">
              <a
                href="#inscricao"
                className="bg-slate-900 text-white font-bold text-sm px-7 py-3.5 rounded hover:bg-sky-700 transition-colors"
              >
                Garantir minha vaga →
              </a>
              <a
                href="#agenda"
                className="border-2 border-slate-200 text-slate-500 font-semibold text-sm px-5 py-3.5 rounded hover:border-slate-400 transition-colors"
              >
                Ver programação
              </a>
            </div>
            <div className="flex gap-8 border-t border-slate-100 pt-8">
              {[
                { num: '120', label: 'vagas exclusivas' },
                { num: '8h', label: 'de conteúdo' },
                { num: 'C-level', label: 'público-alvo' },
              ].map(({ num, label }) => (
                <div key={label}>
                  <div className="font-playfair font-black text-3xl text-slate-900 leading-none">{num}</div>
                  <div className="text-slate-400 text-xs font-medium mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div id="inscricao" className="bg-white rounded-xl border border-slate-200 p-8 shadow-md">
            <h2 className="text-slate-900 text-lg font-extrabold mb-1">Garante sua vaga</h2>
            <p className="text-slate-500 text-sm mb-5">Inscrições limitadas a 120 participantes.</p>
            <RegistrationForm />
          </div>
        </div>
      </section>

      {/* TRILHAS */}
      <section className="bg-slate-50 border-y border-slate-200 py-14" id="agenda">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                track: 'Track 01',
                title: 'Zero Trust',
                desc: 'Arquitetura moderna para ambientes híbridos e multicloud em empresas brasileiras.',
              },
              {
                track: 'Track 02',
                title: 'IA em Segurança',
                desc: 'Detecção e resposta com modelos de linguagem. O que realmente funciona em 2026.',
              },
              {
                track: 'Track 03',
                title: 'Conformidade',
                desc: 'LGPD, ISO 27001, SOC 2 na prática. Gestão de riscos para médias e grandes empresas.',
              },
            ].map(({ track, title, desc }) => (
              <div
                key={track}
                className="bg-white rounded-lg border border-slate-200 [border-top-width:3px] border-t-sky-700 p-6"
              >
                <p className="text-sky-700 text-xs font-bold tracking-[0.1em] uppercase mb-2">{track}</p>
                <p className="text-slate-900 font-extrabold text-base mb-2">{title}</p>
                <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PÚBLICO-ALVO */}
      <section className="bg-white py-16">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-0.5 bg-sky-700" />
            <span className="text-sky-700 text-xs font-bold tracking-[0.15em] uppercase">Para quem é</span>
          </div>
          <h2 className="font-playfair font-black text-3xl text-slate-900 mb-3 tracking-tight">
            Feito para quem decide em segurança
          </h2>
          <p className="text-slate-500 text-base leading-relaxed mb-8 max-w-xl">
            Evento exclusivo para executivos e gestores de empresas com mais de 200 funcionários.
          </p>
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'CISOs', highlight: true },
              { label: 'CTOs', highlight: true },
              { label: 'Diretores de TI', highlight: false },
              { label: 'Gestores de Risco', highlight: false },
              { label: 'VPs de Segurança', highlight: false },
              { label: 'Heads de Compliance', highlight: false },
            ].map(({ label, highlight }) => (
              <span
                key={label}
                className={`px-4 py-2 rounded-full text-sm font-semibold border-2 ${
                  highlight
                    ? 'border-sky-700 text-sky-700 bg-sky-50'
                    : 'border-slate-200 text-slate-600 bg-white'
                }`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-slate-900 py-5 px-8">
        <div className="max-w-screen-xl mx-auto flex items-center justify-between">
          <p className="text-slate-400 text-xs">
            <span className="text-white font-semibold">Vigil Summit 2026</span> · São Paulo · Evento corporativo exclusivo
          </p>
          <a href="#" className="text-sky-300 hover:text-sky-200 text-xs transition-colors">
            Política de privacidade
          </a>
        </div>
      </footer>

      <ChatbotWidget />
    </main>
  )
}
