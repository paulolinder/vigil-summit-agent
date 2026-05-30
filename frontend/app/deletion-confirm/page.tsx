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
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800 w-full max-w-md text-center">
        <h1 className="text-white text-xl font-semibold mb-4">
          Exclusão de Dados — Vigil Summit
        </h1>

        {status === 'loading' && (
          <p className="text-gray-400 text-sm">Processando sua solicitação…</p>
        )}

        {status === 'success' && (
          <div>
            <p className="text-green-400 font-medium mb-2">Dados excluídos com sucesso.</p>
            <p className="text-gray-500 text-sm">
              Seus dados pessoais foram removidos do Vigil Summit. Você não receberá mais
              comunicações nossas.
            </p>
          </div>
        )}

        {status === 'error' && (
          <div>
            <p className="text-red-400 font-medium mb-2">Não foi possível processar.</p>
            <p className="text-gray-500 text-sm">{errorMsg}</p>
            <p className="text-gray-600 text-xs mt-4">
              Precisa de ajuda?{' '}
              <a href="mailto:privacidade@vigil.ai" className="underline">
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
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400 text-sm">Carregando…</p>
      </div>
    }>
      <DeletionConfirmContent />
    </Suspense>
  )
}
