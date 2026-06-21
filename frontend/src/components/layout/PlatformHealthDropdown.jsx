import React, { useState, useRef, useEffect } from 'react'
import { Activity, AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { useUiStore } from '../../store/uiStore'
import { formatDistanceToNow } from 'date-fns'

export const PlatformHealthDropdown = () => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  
  const platformAlerts = useUiStore((state) => state.platformAlerts || [])
  const activeAlerts = platformAlerts.filter(a => a.is_active)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const getStatusInfo = () => {
    if (activeAlerts.length === 0) {
      return {
        color: 'green',
        pulse: 'shadow-[0_0_8px_rgba(34,197,94,0.6)]',
        label: 'Operational'
      }
    }
    const hasCritical = activeAlerts.some(a => a.severity === 'critical')
    if (hasCritical) {
      return {
        color: 'red',
        pulse: 'shadow-[0_0_8px_rgba(239,68,68,0.6)]',
        label: 'Critical Status'
      }
    }
    return {
      color: 'yellow',
      pulse: 'shadow-[0_0_8px_rgba(234,179,8,0.6)]',
      label: 'Degraded'
    }
  }

  const status = getStatusInfo()

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 bg-${status.color}-500/5 border border-${status.color}-500/20 px-3 py-1.5 rounded-lg hover:bg-${status.color}-500/10 transition-colors focus:outline-none`}
      >
        <div className={`h-2 w-2 bg-${status.color}-500 rounded-full animate-pulse ${status.pulse}`}></div>
        <span className={`text-xs font-bold text-${status.color}-400 hidden sm:block uppercase tracking-wider`}>
          {status.label}
        </span>
        {activeAlerts.length > 0 && (
          <span className={`ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-${status.color}-500 text-[10px] font-bold text-white`}>
            {activeAlerts.length}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl bg-[var(--bg\_secondary)] border border-[var(--border)] shadow-xl z-50 overflow-hidden transform opacity-100 scale-100 transition-all duration-200">
          <div className="p-3 border-b border-[var(--border)] bg-[var(--bg\_tertiary)] flex justify-between items-center">
            <h3 className="text-sm font-semibold text-[var(--text\_primary)] flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--text\_secondary)]" />
              Platform Health
            </h3>
            {activeAlerts.length === 0 && (
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full font-medium">100%</span>
            )}
          </div>
          
          <div className="max-h-[60vh] overflow-y-auto">
            {activeAlerts.length === 0 ? (
              <div className="p-6 text-center">
                <CheckCircle className="h-8 w-8 text-green-500/50 mx-auto mb-2" />
                <p className="text-sm text-[var(--text\_secondary)]">All systems operational.</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {activeAlerts.map((alert) => (
                  <div key={alert.alert_id} className="p-3 hover:bg-[var(--bg\_tertiary)]/50 transition-colors">
                    <div className="flex gap-3">
                      <div className="mt-0.5 flex-shrink-0">
                        {alert.severity === 'critical' ? (
                          <XCircle className="h-4 w-4 text-red-500" />
                        ) : alert.severity === 'warning' ? (
                          <AlertTriangle className="h-4 w-4 text-yellow-500" />
                        ) : (
                          <Info className="h-4 w-4 text-blue-500" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <p className="text-sm font-medium text-[var(--text\_primary)] truncate pr-2">
                            {alert.title}
                          </p>
                          <span className="text-[10px] font-mono text-[var(--text\_secondary)] whitespace-nowrap bg-[var(--bg\_primary)] px-1.5 py-0.5 rounded">
                            {formatDistanceToNow(new Date(alert.triggered_at), { addSuffix: true })}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--text\_secondary)] line-clamp-2 leading-relaxed">
                          {alert.description}
                        </p>
                        <div className="mt-2 flex gap-2">
                          <span className="inline-flex text-[10px] font-medium bg-[var(--bg\_primary)] border border-[var(--border)] px-1.5 py-0.5 rounded text-[var(--text\_secondary)] uppercase">
                            {alert.component}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
