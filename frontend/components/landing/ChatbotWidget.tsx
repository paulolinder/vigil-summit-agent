'use client'
import { useState, useRef, useEffect } from 'react'

interface Message { role: 'user' | 'assistant'; content: string }

const WELCOME_MESSAGE: Message = {
  role: 'assistant',
  content: 'Olá! Posso ajudar com dúvidas sobre o Vigil Summit ou sua inscrição. O que você precisa saber?',
}

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  // cancela stream pendente quando o widget desmonta
  useEffect(() => () => { abortRef.current?.abort() }, [])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // A mensagem de boas-vindas é só UI — a Anthropic API exige que o array
    // comece com role:'user', então filtramos a constante WELCOME_MESSAGE antes de enviar.
    const allMessages = [...messages, userMsg]
      .filter(m => m !== WELCOME_MESSAGE)
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    abortRef.current = new AbortController()

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: allMessages }),
        signal: abortRef.current.signal,
      })

      if (!res.ok || !res.body) {
        setMessages(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: 'Erro ao conectar. Tente novamente.' },
        ])
        setLoading(false)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        const lines = text.split('\n').filter(l => l.startsWith('data: '))
        for (const line of lines) {
          const data = line.replace('data: ', '')
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) {
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: 'Desculpe, ocorreu um erro. Tente novamente.' },
              ])
              break
            }
            if (parsed.text) {
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + parsed.text,
                }
                return updated
              })
            }
          } catch {}
        }
      }
    } catch (err) {
      // AbortError é esperado quando o widget fecha — não exibir mensagem de erro
      if (err instanceof Error && err.name !== 'AbortError') {
        setMessages(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: 'Erro de conexão. Verifique sua internet e tente novamente.' },
        ])
      }
    }

    setLoading(false)
  }

  return (
    <>
      <button onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-purple-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-purple-700 transition-colors text-2xl z-50">
        {open ? '✕' : '💬'}
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 w-80 bg-gray-900 rounded-2xl shadow-2xl border border-gray-700 z-50 flex flex-col" style={{ height: '420px' }}>
          <div className="px-4 py-3 border-b border-gray-700">
            <p className="text-white font-semibold text-sm">Assistente Vigil Summit</p>
            <p className="text-gray-400 text-xs">Resposta imediata</p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${msg.role === 'user' ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-200'}`}>
                  {msg.content || <span className="animate-pulse text-gray-400">...</span>}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div className="p-3 border-t border-gray-700 flex gap-2">
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Digite sua dúvida..."
              className="flex-1 bg-gray-800 text-white text-sm p-2 rounded-lg border border-gray-700 placeholder-gray-500" />
            <button onClick={sendMessage} disabled={loading}
              className="bg-purple-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50">
              →
            </button>
          </div>
        </div>
      )}
    </>
  )
}
