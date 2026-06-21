import React from 'react'
import { usePreferencesStore } from '../../store/preferencesStore'
import {
  Moon,
  Sun,
  Volume2,
  VolumeX,
  Bell,
  BellOff,
  RefreshCw,
  Eye,
  User,
  Save,
  RotateCcw,
} from 'lucide-react'

export const PreferencesForm = () => {
  const store = usePreferencesStore()

  const handleInputChange = (key, value) => {
    store.setPreference(key, value)
  }

  const handleColumnToggle = (column) => {
    store.setAlertColumn(column, !store.alertColumns[column])
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex justify-between items-center bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-[var(--text_primary)]">Analyst Preferences</h2>
          <p className="text-sm text-[var(--text_secondary)] mt-1">
            Customize your workspace and notification thresholds.
          </p>
        </div>
        <button
          onClick={() => store.resetPreferences()}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--bg_tertiary)] hover:bg-red-500/20 text-[var(--text_primary)] hover:text-red-400 border border-[var(--border)] rounded-lg text-sm transition-colors"
        >
          <RotateCcw className="h-4 w-4" /> Reset to Defaults
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Display Settings */}
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm space-y-6">
          <div className="flex items-center gap-3 border-b border-[var(--border)] pb-4">
            <Eye className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-bold text-[var(--text_primary)]">Display</h3>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">Theme</label>
              <div className="flex bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg p-1">
                <button
                  onClick={() => handleInputChange('theme', 'light')}
                  className={`p-1.5 rounded-md flex items-center gap-2 text-sm ${store.theme === 'light' ? 'bg-blue-500 text-white' : 'text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}
                >
                  <Sun className="h-4 w-4" /> Light
                </button>
                <button
                  onClick={() => handleInputChange('theme', 'dark')}
                  className={`p-1.5 rounded-md flex items-center gap-2 text-sm ${store.theme === 'dark' ? 'bg-blue-500 text-white' : 'text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}
                >
                  <Moon className="h-4 w-4" /> Dark
                </button>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Alerts Page Size
              </label>
              <select
                value={store.alertsPageSize}
                onChange={(e) => handleInputChange('alertsPageSize', parseInt(e.target.value))}
                className="bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-sm rounded-lg px-3 py-2 outline-none focus:border-blue-500"
              >
                <option value={20}>20 rows</option>
                <option value={50}>50 rows</option>
                <option value={100}>100 rows</option>
                <option value={500}>500 rows</option>
              </select>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Default Sort By
              </label>
              <select
                value={store.defaultAlertSort}
                onChange={(e) => handleInputChange('defaultAlertSort', e.target.value)}
                className="bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-sm rounded-lg px-3 py-2 outline-none focus:border-blue-500"
              >
                <option value="timestamp">Timestamp</option>
                <option value="threat_score">Threat Score</option>
                <option value="host_id">Host</option>
              </select>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Show Low Severity Alerts
              </label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={store.showLowAlerts}
                  onChange={(e) => handleInputChange('showLowAlerts', e.target.checked)}
                />
                <div className="w-11 h-6 bg-[var(--bg_tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm space-y-6">
          <div className="flex items-center gap-3 border-b border-[var(--border)] pb-4">
            <Bell className="h-5 w-5 text-orange-500" />
            <h3 className="text-lg font-bold text-[var(--text_primary)]">Notifications</h3>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)] flex items-center gap-2">
                {store.notificationsEnabled ? (
                  <Bell className="h-4 w-4 text-green-500" />
                ) : (
                  <BellOff className="h-4 w-4" />
                )}
                Desktop Notifications
              </label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={store.notificationsEnabled}
                  onChange={(e) => {
                    handleInputChange('notificationsEnabled', e.target.checked)
                    if (e.target.checked && Notification.permission !== 'granted') {
                      Notification.requestPermission()
                    }
                  }}
                />
                <div className="w-11 h-6 bg-[var(--bg_tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
              </label>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Notify for Level
              </label>
              <select
                value={store.notifyForLevel}
                onChange={(e) => handleInputChange('notifyForLevel', e.target.value)}
                disabled={!store.notificationsEnabled && !store.soundEnabled}
                className="bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-sm rounded-lg px-3 py-2 outline-none focus:border-blue-500 disabled:opacity-50"
              >
                <option value="all">All Alerts</option>
                <option value="medium">Medium & Above</option>
                <option value="high">High & Critical</option>
                <option value="critical">Critical Only</option>
              </select>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-[var(--border)]/50">
              <label className="text-sm font-medium text-[var(--text_secondary)] flex items-center gap-2">
                {store.soundEnabled ? (
                  <Volume2 className="h-4 w-4 text-blue-500" />
                ) : (
                  <VolumeX className="h-4 w-4" />
                )}
                Sound Alerts
              </label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={store.soundEnabled}
                  onChange={(e) => handleInputChange('soundEnabled', e.target.checked)}
                />
                <div className="w-11 h-6 bg-[var(--bg_tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </label>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Volume ({store.soundVolume}%)
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={store.soundVolume}
                onChange={(e) => handleInputChange('soundVolume', parseInt(e.target.value))}
                disabled={!store.soundEnabled}
                className="w-1/2 accent-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Dashboard & SLM Settings */}
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm space-y-6">
          <div className="flex items-center gap-3 border-b border-[var(--border)] pb-4">
            <RefreshCw className="h-5 w-5 text-purple-500" />
            <h3 className="text-lg font-bold text-[var(--text_primary)]">Dashboard & Workflow</h3>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Dashboard Refresh (seconds)
              </label>
              <div className="flex items-center gap-3 w-1/2">
                <input
                  type="range"
                  min="10"
                  max="300"
                  step="10"
                  value={store.dashboardRefreshInterval}
                  onChange={(e) =>
                    handleInputChange('dashboardRefreshInterval', parseInt(e.target.value))
                  }
                  className="w-full accent-purple-500"
                />
                <span className="text-sm font-mono text-[var(--text_primary)]">
                  {store.dashboardRefreshInterval}s
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Show Live Alert Stream
              </label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={store.showLiveStream}
                  onChange={(e) => handleInputChange('showLiveStream', e.target.checked)}
                />
                <div className="w-11 h-6 bg-[var(--bg_tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
              </label>
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Default Time Range
              </label>
              <select
                value={store.defaultTimeRange}
                onChange={(e) => handleInputChange('defaultTimeRange', e.target.value)}
                className="bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-sm rounded-lg px-3 py-2 outline-none focus:border-purple-500"
              >
                <option value="1h">Last 1 Hour</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>

            <div className="pt-4 border-t border-[var(--border)]/50 flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)] flex items-center gap-2">
                <User className="h-4 w-4" /> Analyst Signature
              </label>
              <input
                type="text"
                placeholder="e.g. John Doe"
                value={store.defaultAnalystName}
                onChange={(e) => handleInputChange('defaultAnalystName', e.target.value)}
                className="bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-sm rounded-lg px-3 py-2 outline-none focus:border-purple-500 w-1/2"
              />
            </div>

            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-[var(--text_secondary)]">
                Auto-load SLM Context
              </label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={store.autoLoadAlertContext}
                  onChange={(e) => handleInputChange('autoLoadAlertContext', e.target.checked)}
                />
                <div className="w-11 h-6 bg-[var(--bg_tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Table Columns */}
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm space-y-6">
          <div className="flex items-center gap-3 border-b border-[var(--border)] pb-4">
            <Eye className="h-5 w-5 text-green-500" />
            <h3 className="text-lg font-bold text-[var(--text_primary)]">Alert Table Columns</h3>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {Object.entries(store.alertColumns).map(([col, isVisible]) => (
              <label key={col} className="flex items-center gap-3 cursor-pointer">
                <div className="relative flex items-center">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={isVisible}
                    onChange={() => handleColumnToggle(col)}
                    disabled={col === 'host' || col === 'score'} // Prevent hiding core columns
                  />
                  <div className="w-5 h-5 border-2 border-[var(--text_secondary)] rounded flex items-center justify-center peer-checked:bg-green-500 peer-checked:border-green-500 peer-disabled:opacity-50">
                    <svg
                      className={`w-3 h-3 text-white ${isVisible ? 'block' : 'hidden'}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                </div>
                <span
                  className={`text-sm ${isVisible ? 'text-[var(--text_primary)]' : 'text-[var(--text_secondary)]'}`}
                >
                  {col.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
