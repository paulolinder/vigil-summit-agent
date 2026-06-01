import Link from 'next/link'
import LogoutButton from './LogoutButton'

interface NavbarProps {
  variant?: 'landing' | 'dashboard'
}

export default function Navbar({ variant = 'landing' }: NavbarProps) {
  return (
    <nav className="bg-brand-navy sticky top-0 z-50">
      <div className={`max-w-screen-xl mx-auto px-8 flex items-center justify-between ${variant === 'dashboard' ? 'h-14' : 'h-16'}`}>
        <div className="flex items-center gap-3">
          <Link href="/" className="font-black text-lg tracking-wide text-white">
            VIGIL<span className="text-brand-teal">.AI</span>
          </Link>
          {variant === 'dashboard' && (
            <>
              <div className="w-px h-5 bg-white/20" />
              <span className="font-bold text-white/70 text-[15px]">
                Vigil Summit — Funil de Leads
              </span>
            </>
          )}
        </div>

        {variant === 'landing' && (
          <div className="flex items-center gap-7">
            <a href="#agenda" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
              Agenda
            </a>
            <a href="#speakers" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
              Speakers
            </a>
            <a href="#local" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
              Local
            </a>
            <a
              href="#inscricao"
              className="bg-brand-lime text-brand-navy text-sm font-bold px-5 py-2.5 rounded-[10px] hover:bg-brand-lime/90 transition-colors"
            >
              Garantir vaga →
            </a>
          </div>
        )}

        {variant === 'dashboard' && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 bg-brand-teal/20 border border-brand-teal/40 text-brand-teal text-xs font-bold px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-brand-teal rounded-full animate-pulse inline-block" />
              Ao vivo
            </div>
            <Link href="/" className="text-white/50 hover:text-white/80 text-xs transition-colors">
              ← Landing page
            </Link>
            <div className="w-px h-4 bg-white/20" />
            <LogoutButton />
          </div>
        )}
      </div>
    </nav>
  )
}
