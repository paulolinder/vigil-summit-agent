'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createBrowserClient } from '@supabase/ssr'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      setError('Credenciais inválidas. Verifique e-mail e senha.')
      setLoading(false)
    } else {
      router.push('/dashboard')
      router.refresh()
    }
  }

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4">
      <div className="bg-white rounded-[20px] border border-brand-border shadow-[0_16px_40px_rgba(15,42,52,0.08)] p-8 w-full max-w-sm">
        <p className="font-black text-lg tracking-wide text-brand-navy text-center mb-1">
          VIGIL<span className="text-brand-teal">.AI</span>
        </p>
        <h1 className="font-bold text-2xl text-brand-text text-center mb-1">
          Acesso ao Dashboard
        </h1>
        <p className="text-brand-muted text-sm text-center mb-7">Restrito à equipe Vigil.AI</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="E-mail"
            required
            className="w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm"
          />
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Senha"
            required
            className="w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-navy hover:bg-brand-teal disabled:opacity-50 text-white font-bold py-3 rounded-[10px] transition-colors text-sm"
          >
            {loading ? 'Entrando…' : 'Entrar →'}
          </button>
        </form>
      </div>
    </div>
  )
}
