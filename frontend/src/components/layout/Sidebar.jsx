import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useUiStore } from '../../store/uiStore';
import { LayoutDashboard, ShieldAlert, Search, MessageSquare, Activity, Settings, ChevronLeft, ChevronRight } from 'lucide-react';

export const Sidebar = () => {
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const location = useLocation();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/alerts', label: 'Alerts', icon: ShieldAlert },
    { path: '/investigation', label: 'Investigation', icon: Search },
    { path: '/feedback', label: 'Feedback Loop', icon: MessageSquare },
    { path: '/training', label: 'ML Training', icon: Activity },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Bottom Tab Bar */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-slate-950/95 backdrop-blur-md border-t border-slate-800 z-50 flex items-center justify-around px-2 shadow-[0_-4px_20px_rgba(0,0,0,0.5)]">
        {navItems.map(item => {
          const isActive = location.pathname.startsWith(item.path);
          const Icon = item.icon;
          return (
            <NavLink key={item.path} to={item.path} className={`flex flex-col items-center justify-center w-full h-full space-y-1 relative ${isActive ? 'text-blue-500' : 'text-slate-500 hover:text-slate-300'}`}>
              {isActive && <div className="absolute top-0 w-8 h-0.5 bg-blue-500 rounded-b-full"></div>}
              <Icon className="h-5 w-5" />
              <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Desktop Sidebar */}
      <div className={`hidden md:flex flex-col fixed top-0 left-0 bottom-0 bg-slate-950 border-r border-slate-800 transition-all duration-300 z-40 shadow-2xl ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        <div className="h-16 flex items-center px-4 border-b border-slate-800/60 shrink-0">
          <div className="w-10 h-10 bg-blue-600/20 border border-blue-500/30 rounded-xl flex items-center justify-center shrink-0 shadow-inner">
            <ShieldAlert className="h-5 w-5 text-blue-500" />
          </div>
          {sidebarOpen && <span className="ml-3 font-black text-white tracking-widest uppercase truncate">ISRO SOC</span>}
        </div>

        <nav className="flex-1 py-6 px-3 space-y-2 overflow-y-auto overflow-x-hidden">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center px-3 py-3 rounded-xl transition-all duration-200 group relative ${
                  isActive ? 'bg-blue-600/15 text-blue-400 font-bold border border-blue-500/20' : 'text-slate-400 font-medium hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
                }`}
                title={!sidebarOpen ? item.label : undefined}
              >
                {isActive && sidebarOpen && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-500 rounded-r-full"></div>}
                <Icon className={`h-5 w-5 shrink-0 ${isActive ? 'text-blue-500' : 'text-slate-500 group-hover:text-slate-300'} ${sidebarOpen ? 'ml-1' : 'mx-auto'}`} />
                {sidebarOpen && <span className="ml-3 whitespace-nowrap">{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800/60 shrink-0 flex justify-end">
          <button 
            onClick={toggleSidebar} 
            className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-slate-800 transition-colors w-full flex justify-center border border-transparent hover:border-slate-700"
          >
            {sidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
          </button>
        </div>
      </div>
    </>
  );
};
