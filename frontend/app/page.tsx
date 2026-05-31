export const dynamic = 'force-dynamic'

import Navbar from '@/components/ui/Navbar'
import RegistrationForm from '@/components/landing/RegistrationForm'
import ChatbotWidget from '@/components/landing/ChatbotWidget'
import { getEventServer } from '@/lib/event'

export default async function Home() {
  const { capacity, dateLabel: eventDateLabel } = await getEventServer()
  return (
    <main className="min-h-screen bg-brand-bg">
      <Navbar variant="landing" />

      {/* HERO */}
      <section className="bg-white border-b border-brand-border">
        <div className="max-w-screen-xl mx-auto px-8 py-20 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 bg-brand-teal rounded-full" />
              <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">
                São Paulo · {eventDateLabel} · Presencial
              </span>
            </div>
            <h1 className="font-extrabold text-5xl text-brand-text leading-[1.1] tracking-tight mb-5">
              Vigil Summit<br />
              <span className="text-brand-teal">Segurança para<br />a Era da IA</span>
            </h1>
            <p className="text-brand-muted text-lg leading-relaxed mb-8 max-w-xl">
              O encontro definitivo de CISOs, CTOs e líderes de segurança corporativa para discutir
              IA, Zero Trust e conformidade em 2026.
            </p>
            <div className="flex gap-3 mb-10">
              <a
                href="#inscricao"
                className="bg-brand-navy text-white font-bold text-sm px-7 py-3.5 rounded-[10px] hover:bg-brand-navy/90 transition-colors"
              >
                Garantir minha vaga →
              </a>
              <a
                href="#agenda"
                className="bg-brand-lime text-brand-navy font-bold text-sm px-5 py-3.5 rounded-[10px] hover:bg-brand-lime/90 transition-colors"
              >
                Ver programação
              </a>
            </div>
            <div className="flex gap-8 border-t border-brand-border pt-8">
              {[
                { num: String(capacity), label: 'vagas exclusivas' },
                { num: '8h', label: 'de conteúdo' },
                { num: 'C-level', label: 'público-alvo' },
              ].map(({ num, label }) => (
                <div key={label}>
                  <div className="font-extrabold text-3xl text-brand-text tracking-tight leading-none">{num}</div>
                  <div className="text-brand-muted text-xs font-medium mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div id="inscricao" className="bg-white rounded-[20px] border border-brand-border p-8 shadow-[0_16px_40px_rgba(15,42,52,0.08)]">
            <h2 className="text-brand-text text-lg font-extrabold mb-1">Garante sua vaga</h2>
            <p className="text-brand-muted text-sm mb-5">Inscrições limitadas a {capacity} participantes.</p>
            <RegistrationForm />
          </div>
        </div>
      </section>

      {/* TRILHAS */}
      <section className="bg-brand-bg border-y border-brand-border py-14" id="agenda">
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
                className="bg-white rounded-[16px] border border-brand-border border-t-[3px] border-t-brand-teal p-6"
              >
                <p className="text-brand-teal text-xs font-bold tracking-[0.1em] uppercase mb-2">{track}</p>
                <p className="text-brand-text font-extrabold text-base mb-2">{title}</p>
                <p className="text-brand-muted text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SPEAKERS */}
      <section className="bg-white py-16" id="speakers">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-0.5 bg-brand-teal" />
            <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">Palestrantes</span>
          </div>
          <h2 className="font-extrabold text-3xl text-brand-text mb-3 tracking-tight">
            Quem vai estar no palco
          </h2>
          <p className="text-brand-muted text-base leading-relaxed mb-8 max-w-xl">
            Line-up completo anunciado em breve. Uma seleção de líderes que estão definindo
            a segurança na era da IA.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { role: 'CISO', desc: 'Liderança de segurança de uma das maiores instituições financeiras do país.' },
              { role: 'Head de IA', desc: 'Especialista em detecção e resposta com modelos de linguagem em escala.' },
              { role: 'Head de Compliance', desc: 'Referência em LGPD, ISO 27001 e SOC 2 para grandes operações.' },
            ].map(({ role, desc }) => (
              <div
                key={role}
                className="bg-white rounded-[16px] border border-brand-border border-t-[3px] border-t-brand-teal p-6"
              >
                <div className="w-12 h-12 rounded-full bg-brand-bg border border-brand-border mb-4" />
                <p className="text-brand-text font-extrabold text-base mb-1">A anunciar</p>
                <p className="text-brand-teal text-xs font-bold tracking-[0.1em] uppercase mb-2">{role}</p>
                <p className="text-brand-muted text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* LOCAL */}
      <section className="bg-brand-bg border-y border-brand-border py-16" id="local">
        <div className="max-w-screen-xl mx-auto px-8 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-5 h-0.5 bg-brand-teal" />
              <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">Local</span>
            </div>
            <h2 className="font-extrabold text-3xl text-brand-text mb-3 tracking-tight">
              São Paulo · {eventDateLabel}
            </h2>
            <p className="text-brand-muted text-base leading-relaxed mb-6 max-w-xl">
              Evento presencial em São Paulo. O endereço completo será divulgado aos
              participantes confirmados por e-mail, alguns dias antes do evento.
            </p>
            <div className="flex flex-wrap gap-8">
              <div>
                <div className="font-extrabold text-2xl text-brand-text tracking-tight leading-none">{eventDateLabel}</div>
                <div className="text-brand-muted text-xs font-medium mt-1">data do evento</div>
              </div>
              <div>
                <div className="font-extrabold text-2xl text-brand-text tracking-tight leading-none">8h</div>
                <div className="text-brand-muted text-xs font-medium mt-1">de conteúdo</div>
              </div>
              <div>
                <div className="font-extrabold text-2xl text-brand-text tracking-tight leading-none">{capacity}</div>
                <div className="text-brand-muted text-xs font-medium mt-1">vagas presenciais</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-[16px] border border-brand-border p-8">
            <p className="text-brand-teal text-xs font-bold tracking-[0.1em] uppercase mb-3">Presencial · São Paulo</p>
            <p className="text-brand-text font-bold text-lg mb-2">Endereço a confirmar</p>
            <p className="text-brand-muted text-sm leading-relaxed">
              Região central de São Paulo, com fácil acesso por transporte público. Os detalhes
              logísticos são enviados após a confirmação da inscrição.
            </p>
          </div>
        </div>
      </section>

      {/* PÚBLICO-ALVO */}
      <section className="bg-white py-16">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-0.5 bg-brand-teal" />
            <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">Para quem é</span>
          </div>
          <h2 className="font-extrabold text-3xl text-brand-text mb-3 tracking-tight">
            Feito para quem decide em segurança
          </h2>
          <p className="text-brand-muted text-base leading-relaxed mb-8 max-w-xl">
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
                    ? 'border-brand-teal text-brand-teal bg-brand-teal/10'
                    : 'border-brand-border text-brand-muted bg-white'
                }`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-brand-navy py-5 px-8">
        <div className="max-w-screen-xl mx-auto flex items-center justify-between">
          <p className="text-white/40 text-sm">
            © 2026 Vigil.AI · Todos os direitos reservados
          </p>
          <a href="/deletion-confirm" className="text-brand-teal text-sm hover:text-brand-teal/80 transition-colors">
            Política de privacidade
          </a>
        </div>
      </footer>

      <ChatbotWidget />
    </main>
  )
}
