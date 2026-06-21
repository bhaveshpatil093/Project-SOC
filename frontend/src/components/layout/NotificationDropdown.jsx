import React, { useState, useRef, useEffect } from 'react'
import {
  Bell,
  Settings,
  Volume2,
  BellRing,
  BellOff,
  VolumeX,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  Info,
  Check,
} from 'lucide-react'
import { useNotificationStore } from '../../store/notificationStore'
import { useNotifications } from '../../hooks/useNotifications'
import { formatDate } from '../../utils/formatters'
import { Link } from 'react-router-dom'

export const NotificationDropdown = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [view, setView] = useState('history') // 'history' | 'settings'
  const dropdownRef = useRef(null)

  const { settings, updateSettings, history, unreadCount, markAllRead } = useNotificationStore()
  const { requestPermission, notificationPermission, playAlertSound } = useNotifications()

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleToggleBrowserNotifications = async () => {
    if (!settings.browserEnabled && notificationPermission !== 'granted') {
      const perm = await requestPermission()
      if (perm === 'granted') {
        updateSettings({ browserEnabled: true })
      } else {
        alert('Browser notifications were denied. Please enable them in your browser settings.')
      }
    } else {
      updateSettings({ browserEnabled: !settings.browserEnabled })
    }
  }

  const handleTestSound = () => {
    playAlertSound('critical')
  }

  const getIconForLevel = (level) => {
    switch (level) {
      case 'critical':
        return <AlertOctagon className="h-4 w-4 text-red-500" />
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />
      case 'medium':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      default:
        return <Info className="h-4 w-4 text-blue-500" />
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          setIsOpen(!isOpen)
          setView('history')
          if (!isOpen && unreadCount > 0) markAllRead()
        }}
        className="relative p-2 rounded-lg text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:bg-[var(--bg\_secondary)] transition-colors focus:outline-none"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-[80vh]">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--bg\_secondary)]/50">
            <h3 className="font-bold text-[var(--text\_primary)] text-sm">
              {view === 'history' ? 'Notifications' : 'Notification Settings'}
            </h3>
            <div className="flex gap-2">
              {view === 'history' ? (
                <button
                  onClick={() => setView('settings')}
                  className="p-1.5 rounded-lg text-[var(--text\_secondary)] hover:bg-[var(--bg\_tertiary)] hover:text-[var(--text\_primary)] transition-colors"
                  title="Settings"
                >
                  <Settings className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={() => setView('history')}
                  className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Done
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {view === 'history' ? (
              <div className="flex flex-col">
                {history.length === 0 ? (
                  <div className="p-8 text-center text-[var(--text\_secondary)] text-sm">
                    No recent notifications.
                  </div>
                ) : (
                  history.map((notif, idx) => (
                    <div
                      key={notif.id || idx}
                      className="px-4 py-3 border-b border-[var(--border)] hover:bg-[var(--bg\_secondary)]/50 transition-colors flex items-start gap-3"
                    >
                      <div className="shrink-0 mt-0.5">{getIconForLevel(notif.level)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <p className="text-sm font-semibold text-[var(--text\_primary)] truncate pr-2">
                            {notif.title}
                          </p>
                          <span className="text-[10px] text-[var(--text\_secondary)] shrink-0">
                            {formatDate(notif.timestamp)}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--text\_secondary)] truncate mb-2">
                          {notif.body}
                        </p>
                        {notif.alert_id && (
                          <Link
                            to={`/alerts/${notif.alert_id}`}
                            onClick={() => setIsOpen(false)}
                            className="text-[10px] uppercase tracking-wider font-bold text-blue-400 hover:text-blue-300"
                          >
                            [View Alert]
                          </Link>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="p-4 space-y-6">
                {/* Browser Notifications Toggle */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--text\_primary)] flex items-center gap-2">
                      <BellRing className="h-4 w-4 text-[var(--text\_secondary)]" />
                      Browser Push
                    </h4>
                    <p className="text-xs text-[var(--text\_secondary)] mt-1">
                      Receive native desktop alerts.
                    </p>
                  </div>
                  <button
                    onClick={handleToggleBrowserNotifications}
                    className={`w-11 h-6 rounded-full transition-colors relative focus:outline-none ${settings.browserEnabled ? 'bg-blue-500' : 'bg-[var(--bg\_tertiary)]'}`}
                  >
                    <span
                      className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform ${settings.browserEnabled ? 'translate-x-5' : 'translate-x-0'}`}
                    />
                  </button>
                </div>

                {/* Sound Alerts Toggle */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--text\_primary)] flex items-center gap-2">
                      {settings.soundEnabled ? (
                        <Volume2 className="h-4 w-4 text-[var(--text\_secondary)]" />
                      ) : (
                        <VolumeX className="h-4 w-4 text-[var(--text\_secondary)]" />
                      )}
                      Sound Alerts
                    </h4>
                    <p className="text-xs text-[var(--text\_secondary)] mt-1">
                      Play sounds for new alerts.
                    </p>
                  </div>
                  <button
                    onClick={() => updateSettings({ soundEnabled: !settings.soundEnabled })}
                    className={`w-11 h-6 rounded-full transition-colors relative focus:outline-none ${settings.soundEnabled ? 'bg-blue-500' : 'bg-[var(--bg\_tertiary)]'}`}
                  >
                    <span
                      className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform ${settings.soundEnabled ? 'translate-x-5' : 'translate-x-0'}`}
                    />
                  </button>
                </div>

                {/* Volume Slider */}
                {settings.soundEnabled && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-[var(--text\_secondary)]">
                      <span>Volume</span>
                      <span>{settings.volume}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={settings.volume}
                      onChange={(e) => updateSettings({ volume: parseInt(e.target.value, 10) })}
                      className="w-full accent-blue-500"
                    />
                  </div>
                )}

                {/* Threshold Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-[var(--text\_primary)] block">
                    Alert Threshold
                  </label>
                  <p className="text-xs text-[var(--text\_secondary)] mb-2">
                    Only notify for alerts at or above this level.
                  </p>
                  <select
                    value={settings.threshold}
                    onChange={(e) => updateSettings({ threshold: e.target.value })}
                    className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text\_primary)] focus:outline-none focus:border-blue-500"
                  >
                    <option value="all">All Alerts (Noisy)</option>
                    <option value="medium">Medium and above</option>
                    <option value="high">High and above</option>
                    <option value="critical">Critical only</option>
                  </select>
                </div>

                <div className="pt-4 border-t border-[var(--border)]">
                  <button
                    onClick={handleTestSound}
                    className="w-full py-2 bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] text-[var(--text\_secondary)] rounded-lg text-sm font-medium transition-colors"
                  >
                    Test Critical Sound
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer actions for History view */}
          {view === 'history' && history.length > 0 && (
            <div className="p-2 border-t border-[var(--border)] bg-[var(--bg\_primary)] text-center">
              <button
                onClick={() => useNotificationStore.getState().clearHistory()}
                className="text-xs text-[var(--text\_secondary)] hover:text-[var(--text\_secondary)] transition-colors"
              >
                Clear History
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
