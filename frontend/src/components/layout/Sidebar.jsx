import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useUiStore } from '../../store/uiStore'
import {
  LayoutDashboard,
  ShieldAlert,
  Search,
  MessageSquare,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  Network,
  Wrench,
  Crosshair,
  Server,
} from 'lucide-react'
import { useIsTablet, useIsMobile } from '../../hooks/useMediaQuery'
import { useAuth } from '../../contexts/AuthContext'

export const Sidebar = () => {
  const { sidebarOpen, toggleSidebar } = useUiStore()
  const location = useLocation()
  const isTablet = useIsTablet()
  const isMobile = useIsMobile()
  const { user } = useAuth()

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/alerts', label: 'Alerts', icon: ShieldAlert },
    { path: '/incidents', label: 'Incidents', icon: Network },
    { path: '/investigation', label: 'Investigation', icon: Search },
    { path: '/hunting', label: 'Threat Hunting', icon: Crosshair },
    { path: '/feedback', label: 'Feedback Loop', icon: MessageSquare },
    { path: '/training', label: 'ML Training', icon: Activity },
    { path: '/diagnostics', label: 'Diagnostics', icon: Server },
    { path: '/settings', label: 'Settings', icon: Settings },
  ]

  if (isMobile) return null // Handled by BottomTabBar

  return (
    <>
      {/* Tablet Overlay Backdrop */}
      {isTablet && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar - Desktop fixed, Tablet overlay */}
      <div
        className={`hidden sm:flex flex-col fixed top-0 left-0 bottom-0 bg-[var(--bg\_primary)] border-r border-[var(--border)] transition-transform duration-300 z-50 shadow-2xl ${
          isTablet
            ? sidebarOpen
              ? 'translate-x-0 w-64'
              : '-translate-x-full w-64'
            : sidebarOpen
              ? 'w-64'
              : 'w-20'
        }`}
      >
        <div className="h-16 flex items-center px-4 border-b border-[var(--border)]/60 shrink-0">
          <div className="w-10 h-10 bg-blue-600/20 border border-blue-500/30 rounded-xl flex items-center justify-center shrink-0 shadow-inner">
            <ShieldAlert className="h-5 w-5 text-blue-500" />
          </div>
          {sidebarOpen && (
            <span className="ml-3 font-black text-[var(--text\_primary)] tracking-widest uppercase truncate">
              ISRO SOC
            </span>
          )}
        </div>

        <nav className="flex-1 py-6 px-3 space-y-2 overflow-y-auto overflow-x-hidden">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path)
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => isTablet && toggleSidebar()}
                className={`flex items-center px-3 py-3 rounded-xl transition-all duration-200 group relative ${
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 font-bold border border-blue-500/20'
                    : 'text-[var(--text\_secondary)] font-medium hover:bg-[var(--bg\_secondary)]/60 hover:text-[var(--text\_primary)] border border-transparent'
                }`}
                title={!sidebarOpen && !isTablet ? item.label : undefined}
              >
                {isActive && sidebarOpen && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-500 rounded-r-full"></div>
                )}
                <Icon
                  className={`h-5 w-5 shrink-0 ${isActive ? 'text-blue-500' : 'text-[var(--text\_secondary)] group-hover:text-[var(--text\_secondary)]'} ${sidebarOpen ? 'ml-1' : 'mx-auto'}`}
                />
                {sidebarOpen && <span className="ml-3 whitespace-nowrap">{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Desktop Toggle Button */}
        <div className="border-t border-[var(--border)]/60 shrink-0 flex flex-col">
          {user?.role === 'admin' && (
            <div className="p-3">
              <NavLink
                to="/system"
                onClick={() => isTablet && toggleSidebar()}
                className={`flex items-center px-3 py-3 rounded-xl transition-all duration-200 group relative ${
                  location.pathname.startsWith('/system')
                    ? 'bg-orange-600/15 text-orange-400 font-bold border border-orange-500/20'
                    : 'text-[var(--text\\_secondary)] font-medium hover:bg-[var(--bg\\_secondary)]/60 hover:text-[var(--text\\_primary)] border border-transparent'
                }`}
                title={!sidebarOpen && !isTablet ? 'System Monitor' : undefined}
              >
                {location.pathname.startsWith('/system') && sidebarOpen && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-orange-500 rounded-r-full"></div>
                )}
                <Wrench
                  className={`h-5 w-5 shrink-0 ${location.pathname.startsWith('/system') ? 'text-orange-500' : 'text-[var(--text\\_secondary)] group-hover:text-[var(--text\\_secondary)]'} ${sidebarOpen ? 'ml-1' : 'mx-auto'}`}
                />
                {sidebarOpen && <span className="ml-3 whitespace-nowrap">System Monitor</span>}
              </NavLink>
            </div>
          )}
          {!isTablet && (
            <div className="p-4 border-t border-[var(--border)]/60 flex justify-end">
              <button
                onClick={toggleSidebar}
                className="p-2 rounded-xl text-[var(--text\\_secondary)] hover:text-[var(--text\\_primary)] hover:bg-[var(--bg\\_secondary)] transition-colors w-full flex justify-center border border-transparent hover:border-[var(--border)]"
              >
                {sidebarOpen ? (
                  <ChevronLeft className="h-5 w-5" />
                ) : (
                  <ChevronRight className="h-5 w-5" />
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
