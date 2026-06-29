import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  ShieldAlert,
  MessageSquare,
  Menu,
  Network,
  Search,
  Activity,
  Settings,
  X,
} from 'lucide-react'

export const BottomTabBar = () => {
  const location = useLocation()
  const [isMoreOpen, setIsMoreOpen] = useState(false)

  const mainNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/alerts', label: 'Alerts', icon: ShieldAlert },
    { path: '/investigation', label: 'Chat', icon: MessageSquare }, // Maps Investigation to "Chat" as requested
  ]

  const moreNavItems = [
    { path: '/incidents', label: 'Incidents', icon: Network },
    { path: '/feedback', label: 'Feedback Loop', icon: Activity }, // Assuming Feedback was Activity or MessageSquare
    { path: '/training', label: 'ML Training', icon: Activity },
    { path: '/settings', label: 'Settings', icon: Settings },
  ]

  const toggleMore = () => setIsMoreOpen(!isMoreOpen)

  return (
    <>
      {/* Drawer Overlay */}
      {isMoreOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm sm:hidden"
          onClick={() => setIsMoreOpen(false)}
        />
      )}

      {/* Slide-up Drawer for "More..." items */}
      <div
        className={`fixed left-0 right-0 bottom-16 bg-[var(--bg-primary)] border-t border-[var(--border)] z-40 rounded-t-2xl shadow-[0_-10px_40px_rgba(0,0,0,0.5)] transition-transform duration-300 ease-in-out sm:hidden ${
          isMoreOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)]/50">
          <h3 className="font-bold text-[var(--text-primary)] tracking-wide">More Options</h3>
          <button
            onClick={() => setIsMoreOpen(false)}
            className="p-1 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-2 grid grid-cols-2 gap-2">
          {moreNavItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path)
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setIsMoreOpen(false)}
                className={`flex items-center gap-3 p-3 rounded-xl transition-colors ${
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'bg-[var(--bg-secondary)]/50 text-[var(--text-secondary)] border border-[var(--border)]/50 active:bg-[var(--bg-tertiary)]'
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span className="font-medium text-sm">{item.label}</span>
              </NavLink>
            )
          })}
        </div>
      </div>

      {/* Main Bottom Bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 h-16 bg-[var(--bg-primary)]/95 backdrop-blur-md border-t border-[var(--border)] z-50 flex items-center justify-around px-2 pb-safe shadow-[0_-4px_20px_rgba(0,0,0,0.5)]">
        {mainNavItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path)
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center w-full h-full space-y-1 relative ${
                isActive
                  ? 'text-blue-500'
                  : 'text-[var(--text-secondary)] active:text-[var(--text-secondary)]'
              }`}
            >
              {isActive && (
                <div className="absolute top-0 w-8 h-0.5 bg-blue-500 rounded-b-full shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
              )}
              <Icon className="h-5 w-5" />
              <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
            </NavLink>
          )
        })}

        {/* More Button */}
        <button
          onClick={toggleMore}
          className={`flex flex-col items-center justify-center w-full h-full space-y-1 relative outline-none ${
            isMoreOpen
              ? 'text-[var(--text-primary)]'
              : 'text-[var(--text-secondary)] active:text-[var(--text-secondary)]'
          }`}
        >
          {isMoreOpen && (
            <div className="absolute top-0 w-8 h-0.5 bg-slate-400 rounded-b-full"></div>
          )}
          <Menu className="h-5 w-5" />
          <span className="text-[10px] font-bold uppercase tracking-wider">More</span>
        </button>
      </div>
    </>
  )
}
