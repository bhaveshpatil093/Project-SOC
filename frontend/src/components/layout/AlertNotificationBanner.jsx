import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBannerStore } from '../../store/bannerStore'
import { ShieldAlert, X } from 'lucide-react'

const Banner = ({ alert, onDismiss }) => {
  const navigate = useNavigate()
  const isCritical = alert.threat_level?.toLowerCase() === 'critical'
  const score = parseFloat(alert.threat_score || 0) * 100

  // Auto-dismiss after 10 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(alert._ws_id)
    }, 10000)
    return () => clearTimeout(timer)
  }, [alert._ws_id, onDismiss])

  const handleView = () => {
    onDismiss(alert._ws_id)
    navigate(`/alerts/${alert.id || alert._id}`)
  }

  return (
    <div
      className={`pointer-events-auto flex items-center justify-between w-full max-w-2xl mx-auto shadow-2xl rounded-xl p-4 border ${
        isCritical ? 'bg-red-950/90 border-red-500/50' : 'bg-orange-950/90 border-orange-500/50'
      } backdrop-blur-md animate-in slide-in-from-top-10 fade-in duration-300`}
    >
      <div className="flex items-center gap-4 flex-1 overflow-hidden">
        <div
          className={`p-2 rounded-full shrink-0 ${isCritical ? 'bg-red-500/20 text-red-500 animate-pulse' : 'bg-orange-500/20 text-orange-500'}`}
        >
          <ShieldAlert className="h-6 w-6" />
        </div>
        <div className="flex flex-col truncate">
          <div className="flex items-center gap-2">
            <span
              className={`font-bold text-sm tracking-widest uppercase ${isCritical ? 'text-red-400' : 'text-orange-400'}`}
            >
              NEW {alert.threat_level} ALERT
            </span>
            <span className="text-[var(--text-secondary)] text-xs">—</span>
            <span className="text-[var(--text-primary)] font-medium text-sm truncate">
              {alert.host_id || 'Unknown Host'}
            </span>
          </div>
          <div className="text-[var(--text-secondary)] text-xs mt-1 truncate font-mono">
            Score:{' '}
            <span className={isCritical ? 'text-red-400 font-bold' : 'text-orange-400 font-bold'}>
              {score.toFixed(1)}
            </span>
            <span className="mx-2 opacity-50">|</span>
            Log: {alert.log_type || 'N/A'}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0 ml-4">
        <button
          onClick={handleView}
          className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
            isCritical
              ? 'bg-red-600 hover:bg-red-500 text-[var(--text-primary)]'
              : 'bg-orange-600 hover:bg-orange-500 text-[var(--text-primary)]'
          }`}
        >
          View Alert
        </button>
        <button
          onClick={() => onDismiss(alert._ws_id)}
          className="p-1.5 hover:bg-white/10 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          title="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

export const AlertNotificationBanner = () => {
  const { banners, removeBanner } = useBannerStore()

  if (banners.length === 0) return null

  return (
    <div className="fixed top-0 inset-x-0 z-50 flex flex-col items-center gap-2 pt-4 px-4 pointer-events-none">
      {banners.map((alert) => (
        <Banner key={alert._ws_id} alert={alert} onDismiss={removeBanner} />
      ))}
    </div>
  )
}
