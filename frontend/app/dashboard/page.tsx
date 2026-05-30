export const dynamic = 'force-dynamic'

import FunnelBoard from '@/components/dashboard/FunnelBoard'

export default function DashboardPage() {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-screen-xl mx-auto">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-white text-2xl font-bold">Vigil Summit — Funil de Leads</h1>
            <p className="text-gray-500 text-sm mt-1">
              Atualização em tempo real via Supabase Realtime
            </p>
          </div>
          <a href="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
            ← Landing page
          </a>
        </div>
        <FunnelBoard apiKey={apiKey} />
      </div>
    </div>
  )
}
