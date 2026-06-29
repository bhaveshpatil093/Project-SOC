import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { BottomTabBar } from './BottomTabBar'
import { useUiStore } from '../../store/uiStore'
import { useIsTablet } from '../../hooks/useMediaQuery'

export const Layout = () => {
  const { sidebarOpen } = useUiStore()
  const isTablet = useIsTablet()

  // On tablet and below, no margin needed since sidebar is overlay or hidden
  const marginLeftClass = isTablet ? 'ml-0' : sidebarOpen ? 'ml-64' : 'ml-20'

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-secondary)] flex">
      <Sidebar />
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${marginLeftClass} pb-16 sm:pb-0 relative z-10`}
      >
        <TopBar />
        <main className="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-8">
          <Outlet />
        </main>
      </div>
      <BottomTabBar />
    </div>
  )
}
