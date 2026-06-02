'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

type Status = 'loading' | 'success' | 'already' | 'error'

function ConfirmContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [status, setStatus] = useState<Status>('loading')

  useEffect(() => {
    if (!token) { setStatus('error'); return }
    fetch('/api/leads/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async r => {
        if (r.status !== 200) { setStatus('error'); return }
        const data = await r.json().catch(() => ({}))
        setStatus(data.status === 'confirmed' ? 'success' : 'already')
      })
      .catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4">
      <div className="bg-white rounded-[20px] border border-slate-200 shadow-[0_16px_40px_rgba(15,42,52,0.08)] p-8 w-full max-w-md text-center">
        <p className="font-black text-base tracking-wide text-brand-navy mb-1">
          VIGIL<span className="text-brand-teal">.AI</span>
        </p>
        <h1 className="font-bold text-xl text-brand-text mb-5">Confirmação de Presença</h1>
        {status === 'loading' && <p className="text-slate-500 text-sm">Confirmando sua presença…</p>}
        {status === 'success' && (
          <div>
            <p className="text-brand-green font-semibold mb-2">Presença confirmada! ✓</p>
            <p className="text-slate-500 text-sm">Sua vaga no Vigil Summit está garantida. Em breve você recebe a agenda personalizada por email.</p>
          </div>
        )}
        {status === 'already' && (
          <div>
            <p className="text-brand-teal font-semibold mb-2">Presença já confirmada ✓</p>
            <p className="text-slate-500 text-sm">Você já está confirmado no Vigil Summit. Nos vemos lá!</p>
          </div>
        )}
        {status === 'error' && (
          <div>
            <p className="text-red-600 font-semibold mb-2">Não foi possível confirmar.</p>
            <p className="text-slate-500 text-sm">O link pode estar inválido. Use o botão do email mais recente, ou fale com a gente.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ConfirmPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-bg flex items-center justify-center">
        <p className="text-slate-500 text-sm">Carregando…</p>
      </div>
    }>
      <ConfirmContent />
    </Suspense>
  )
}
