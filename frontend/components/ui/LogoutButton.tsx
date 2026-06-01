'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createBrowserClient } from '@supabase/ssr'

// Usa createBrowserClient (@supabase/ssr) — o MESMO do login — para que signOut()
// limpe os cookies de sessão que o middleware e os proxies server-side leem.
// O client de lib/supabase.ts (localStorage) NÃO limparia esses cookies.
export default function LogoutButton() {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleLogout() {
    setLoading(true)
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <button
      onClick={handleLogout}
      disabled={loading}
      className="text-white/50 hover:text-white/80 disabled:opacity-50 text-xs transition-colors"
    >
      {loading ? 'Saindo…' : 'Sair →'}
    </button>
  )
}
