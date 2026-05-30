'use client'
import { useState, useRef, useEffect } from 'react'

interface Message { role: 'user' | 'assistant'; content: string }

const WELCOME_MESSAGE: Message = {
  role: 'assistant',
  content: 'Olá! Posso ajudar com dúvidas sobre o Vigil Summit ou sua inscrição. O que você precisa saber?',
}

function ChatIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  )
}

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => () => { abortRef.current?.abort() }, [])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

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
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-brand-navy text-white rounded-full shadow-lg flex items-center justify-center hover:bg-brand-teal transition-colors z-50"
        aria-label={open ? 'Fechar chat' : 'Abrir chat'}
      >
        {open
          ? <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          : <ChatIcon />
        }
      </button>

      {open && (
        <div
          className="fixed bottom-24 right-6 w-80 bg-white rounded-2xl shadow-2xl border border-brand-border z-50 flex flex-col"
          style={{ height: '420px' }}
        >
          <div className="px-4 py-3 border-b border-brand-border bg-brand-navy rounded-t-2xl">
            <p className="text-white font-semibold text-sm">Assistente Vigil Summit</p>
            <p className="text-white/50 text-xs">Resposta imediata</p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${
                  msg.role === 'user'
                    ? 'bg-brand-teal text-white'
                    : 'bg-slate-100 text-slate-700'
                }`}>
                  {msg.content || <span className="animate-pulse text-slate-400">…</span>}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div className="p-3 border-t border-brand-border flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Digite sua dúvida…"
              className="flex-1 bg-brand-bg text-brand-text text-sm p-2 rounded-[8px] border border-brand-border placeholder-brand-muted focus:outline-none focus:border-brand-teal"
            />
            <button
              onClick={sendMessage}
              disabled={loading}
              className="bg-brand-navy text-white px-3 py-2 rounded-[8px] text-sm hover:bg-brand-teal disabled:opacity-50 transition-colors"
            >
              →
            </button>
          </div>
        </div>
      )}
    </>
  )
}
