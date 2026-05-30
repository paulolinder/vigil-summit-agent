export const dynamic = 'force-dynamic'

import Navbar from '@/components/ui/Navbar'
import FunnelBoard from '@/components/dashboard/FunnelBoard'

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar variant="dashboard" />
      <FunnelBoard />
    </div>
  )
}
