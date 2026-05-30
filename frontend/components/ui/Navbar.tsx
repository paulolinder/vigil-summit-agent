import Link from 'next/link'

interface NavbarProps {
  variant?: 'landing' | 'dashboard'
}

export default function Navbar({ variant = 'landing' }: NavbarProps) {
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-screen-xl mx-auto px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-black text-lg tracking-wide text-slate-900">
            VIGIL<span className="text-sky-700">.AI</span>
          </Link>
          {variant === 'dashboard' && (
            <>
              <div className="w-px h-5 bg-slate-200" />
              <span className="font-playfair font-bold text-slate-500 text-[15px]">
                Vigil Summit — Funil de Leads
              </span>
            </>
          )}
        </div>

        {variant === 'landing' && (
          <div className="flex items-center gap-7">
            <a href="#agenda" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Agenda
            </a>
            <a href="#speakers" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Speakers
            </a>
            <a href="#local" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Local
            </a>
            <a
              href="#inscricao"
              className="bg-slate-900 text-white text-sm font-bold px-5 py-2.5 rounded hover:bg-sky-700 transition-colors"
            >
              Garantir vaga →
            </a>
          </div>
        )}

        {variant === 'dashboard' && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 bg-green-50 border border-green-200 text-green-700 text-xs font-bold px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse inline-block" />
              Ao vivo
            </div>
            <Link href="/" className="text-slate-400 hover:text-slate-600 text-xs transition-colors">
              ← Landing page
            </Link>
          </div>
        )}
      </div>
    </nav>
  )
}
