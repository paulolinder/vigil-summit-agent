'use client'
import { useState, useEffect } from 'react'
import { createLead, getEvents } from '@/lib/api'

interface FormState {
  name: string
  email: string
  company: string
  role: string
  phone: string
  has_companion: boolean
  companion_name: string
  consent: boolean
  whatsapp_consent: boolean
}

export default function RegistrationForm() {
  const [eventId, setEventId] = useState<string>('')
  const [eventError, setEventError] = useState(false)
  const [form, setForm] = useState<FormState>({
    name: '', email: '', company: '', role: '', phone: '',
    has_companion: false, companion_name: '',
    consent: false, whatsapp_consent: false,
  })
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'duplicate'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getEvents()
      .then((events: { id: string }[]) => {
        if (events.length > 0) setEventId(events[0].id)
        else setEventError(true)
      })
      .catch(() => setEventError(true))
  }, [])

  const set = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.consent || !eventId) return
    setStatus('loading')
    try {
      await createLead({
        event_id: eventId,
        name: form.name,
        email: form.email,
        company: form.company,
        role: form.role,
        phone: form.phone || undefined,
        has_companion: form.has_companion,
        companion_name: form.companion_name || undefined,
        consent: form.consent,
        whatsapp_consent: form.whatsapp_consent,
      })
      setStatus('success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('409') || msg.includes('cadastrado')) {
        setStatus('duplicate')
      } else {
        setErrorMsg('Erro ao realizar inscrição. Tente novamente.')
        setStatus('error')
      }
    }
  }

  if (status === 'success') {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-brand-green text-lg font-semibold">Inscrição confirmada ✓</p>
        <p className="text-brand-muted text-sm">Você receberá um e-mail de confirmação em breve.</p>
      </div>
    )
  }

  if (status === 'duplicate') {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-brand-teal text-lg font-semibold">Você já está inscrito ✓</p>
        <p className="text-brand-muted text-sm">Este e-mail já está cadastrado para o evento.</p>
      </div>
    )
  }

  const inputClass = 'w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm'

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input required value={form.name} onChange={set('name')}
        placeholder="Nome completo *" className={inputClass} />

      <input required type="email" value={form.email} onChange={set('email')}
        placeholder="E-mail corporativo *" className={inputClass} />

      <input value={form.phone} onChange={set('phone')}
        placeholder="Telefone (opcional)" className={inputClass} />

      <label className="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" checked={form.has_companion} onChange={set('has_companion')}
          className="w-4 h-4 accent-brand-teal flex-shrink-0" />
        <span className="text-brand-muted text-sm">Vou com acompanhante</span>
      </label>

      {form.has_companion && (
        <input value={form.companion_name} onChange={set('companion_name')}
          placeholder="Nome do acompanhante" className={inputClass} />
      )}

      <label className="flex items-start gap-3 cursor-pointer">
        <input required type="checkbox" checked={form.consent} onChange={set('consent')}
          className="w-4 h-4 mt-0.5 accent-brand-teal flex-shrink-0" />
        <span className="text-brand-muted text-xs leading-relaxed">
          Concordo com o tratamento dos meus dados pessoais pela Vigil.AI para fins de inscrição no
          Vigil Summit, conforme a LGPD. *
        </span>
      </label>

      <label className="flex items-start gap-3 cursor-pointer">
        <input type="checkbox" checked={form.whatsapp_consent} onChange={set('whatsapp_consent')}
          className="w-4 h-4 mt-0.5 accent-brand-teal flex-shrink-0" />
        <span className="text-brand-muted text-xs leading-relaxed">
          Aceito receber comunicações sobre o evento via WhatsApp.
        </span>
      </label>

      {status === 'error' && <p className="text-red-600 text-sm">{errorMsg}</p>}

      {eventError && (
        <p className="text-[#6b7a00] text-sm">
          Não foi possível carregar o evento. Verifique sua conexão e recarregue a página.
        </p>
      )}

      <button
        type="submit"
        disabled={status === 'loading' || !form.consent || !eventId}
        className="w-full bg-brand-navy hover:bg-brand-teal disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-[10px] transition-colors text-sm"
      >
        {status === 'loading' ? 'Inscrevendo…' : 'Confirmar inscrição →'}
      </button>
    </form>
  )
}
