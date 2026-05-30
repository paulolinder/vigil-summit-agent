'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

type Status = 'loading' | 'success' | 'error'

function DeletionConfirmContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [status, setStatus] = useState<Status>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setErrorMsg('Link inválido ou expirado.')
      return
    }
    fetch('/api/leads/deletion-request/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async r => {
        if (r.status === 200) {
          setStatus('success')
        } else {
          const data = await r.json().catch(() => ({}))
          setStatus('error')
          setErrorMsg(
            r.status === 404
              ? 'Link expirado ou já utilizado.'
              : (data.detail || 'Erro ao processar solicitação.')
          )
        }
      })
      .catch(() => {
        setStatus('error')
        setErrorMsg('Erro de conexão. Tente novamente em instantes.')
      })
  }, [token])

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4">
      <div className="bg-white rounded-[20px] border border-slate-200 shadow-[0_16px_40px_rgba(15,42,52,0.08)] p-8 w-full max-w-md text-center">
        <p className="font-black text-base tracking-wide text-brand-navy mb-1">
          VIGIL<span className="text-brand-teal">.AI</span>
        </p>
        <h1 className="font-bold text-xl text-brand-text mb-5">
          Exclusão de Dados
        </h1>

        {status === 'loading' && (
          <p className="text-slate-500 text-sm">Processando sua solicitação…</p>
        )}

        {status === 'success' && (
          <div>
            <p className="text-brand-green font-semibold mb-2">Dados excluídos com sucesso.</p>
            <p className="text-slate-500 text-sm">
              Seus dados pessoais foram removidos do Vigil Summit. Você não receberá mais
              comunicações nossas.
            </p>
          </div>
        )}

        {status === 'error' && (
          <div>
            <p className="text-red-600 font-semibold mb-2">Não foi possível processar.</p>
            <p className="text-slate-500 text-sm">{errorMsg}</p>
            <p className="text-slate-400 text-xs mt-4">
              Precisa de ajuda?{' '}
              <a href="mailto:privacidade@vigil.ai" className="underline text-brand-teal">
                privacidade@vigil.ai
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function DeletionConfirmPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-bg flex items-center justify-center">
        <p className="text-slate-500 text-sm">Carregando…</p>
      </div>
    }>
      <DeletionConfirmContent />
    </Suspense>
  )
}
