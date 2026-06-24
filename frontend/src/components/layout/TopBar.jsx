import React, { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Clock, CheckCircle, Menu, Sun, Moon } from 'lucide-react'
import { useUiStore } from '../../store/uiStore'
import { usePreferencesStore } from '../../store/preferencesStore'
import { NotificationDropdown } from './NotificationDropdown'
import { PlatformHealthDropdown } from "./PlatformHealthDropdown"

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { DatabaseBackup } from 'lucide-react'
import { formatDate } from '../../utils/formatters'

export const TopBar = () => {
  const location = useLocation()
  const { toggleSidebar } = useUiStore()
  const { theme, setPreference } = usePreferencesStore()
  const toggleTheme = () => setPreference('theme', theme === 'dark' ? 'light' : 'dark')
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const { data: backups } = useQuery({
    queryKey: ['backups_topbar'],
    queryFn: () => apiClient.get('/api/admin/backups'),
    retry: false,
    refetchInterval: 60000,
  })

  const lastBackup = backups?.length > 0 ? backups[0] : null;

  const getPageTitle = () => {
    const path = location.pathname
    if (path.startsWith('/dashboard')) return 'Dashboard Analytics'
    if (path.startsWith('/alerts')) return 'Security Alerts'
    if (path.startsWith('/investigation')) return 'AI Investigation'
    if (path.startsWith('/feedback')) return 'Analyst Feedback'
    if (path.startsWith('/training')) return 'Model Tuning'
    if (path.startsWith('/settings')) return 'System Diagnostics'
    return 'SOC Platform'
  }

  return (
    <header className="h-16 bg-[var(--bg\_primary)]/80 backdrop-blur-xl border-b border-[var(--border)]/60 flex items-center justify-between px-4 sm:px-6 sticky top-0 z-30 shadow-sm">
      <div className="flex items-center gap-3">
        {/* Hamburger visible only on tablet (sm to lg) */}
        <button
          onClick={toggleSidebar}
          className="hidden sm:block lg:hidden p-2 rounded-lg text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:bg-[var(--bg\_secondary)] transition-colors"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h2 className="text-lg font-bold text-[var(--text\_primary)] tracking-wide">
          {getPageTitle()}
        </h2>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden md:flex items-center gap-2 text-[var(--text\_secondary)] text-sm font-mono bg-[var(--bg\_primary)]/50 px-3 py-1.5 rounded-lg border border-[var(--border)]">
          <Clock className="h-4 w-4 text-blue-500" />
          {time.toLocaleTimeString()}
        </div>

        {lastBackup && (
          <div className="hidden lg:flex items-center gap-2 text-[var(--text\_secondary)] text-sm font-mono bg-[var(--bg\_primary)]/50 px-3 py-1.5 rounded-lg border border-[var(--border)]" title="Last successful backup">
            <DatabaseBackup className="h-4 w-4 text-purple-500" />
            {formatDate(new Date(lastBackup.start_time))}
          </div>
        )}

        <PlatformHealthDropdown />

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:bg-[var(--bg\_secondary)] transition-colors focus:outline-none"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        <NotificationDropdown />
      </div>
    </header>
  )
}
