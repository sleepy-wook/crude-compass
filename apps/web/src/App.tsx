import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import DiscoveryPage from '@/routes/DiscoveryPage'
import MissionPage from '@/routes/MissionPage'
import YesterdayPage from '@/routes/YesterdayPage'

export default function App() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0 }}>
        <div className="stagger">
          <Routes>
            <Route path="/" element={<Navigate to="/discovery" replace />} />
            <Route path="/discovery" element={<DiscoveryPage />} />
            <Route path="/mission" element={<MissionPage />} />
            <Route path="/yesterday" element={<YesterdayPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
