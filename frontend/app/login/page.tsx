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
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 w-full max-w-sm">
        <p className="font-black text-lg tracking-wide text-slate-900 text-center mb-1">
          VIGIL<span className="text-sky-700">.AI</span>
        </p>
        <h1 className="font-playfair font-bold text-2xl text-slate-900 text-center mb-1">
          Acesso ao Dashboard
        </h1>
        <p className="text-slate-500 text-sm text-center mb-7">Restrito à equipe Vigil.AI</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="E-mail"
            required
            className="w-full bg-slate-50 border border-slate-200 rounded px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-700 transition-colors text-sm"
          />
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Senha"
            required
            className="w-full bg-slate-50 border border-slate-200 rounded px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-700 transition-colors text-sm"
          />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-900 hover:bg-sky-700 disabled:opacity-50 text-white font-bold py-3 rounded transition-colors text-sm"
          >
            {loading ? 'Entrando…' : 'Entrar →'}
          </button>
        </form>
      </div>
    </div>
  )
}
