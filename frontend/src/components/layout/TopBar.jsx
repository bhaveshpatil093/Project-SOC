import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Clock, CheckCircle } from 'lucide-react';

export const TopBar = () => {
  const location = useLocation();
  const [time, setTime] = useState(new Date());
  
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const getPageTitle = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return 'Dashboard Analytics';
    if (path.startsWith('/alerts')) return 'Security Alerts';
    if (path.startsWith('/investigation')) return 'AI Investigation';
    if (path.startsWith('/feedback')) return 'Analyst Feedback';
    if (path.startsWith('/training')) return 'Model Tuning';
    if (path.startsWith('/settings')) return 'System Diagnostics';
    return 'SOC Platform';
  };

  return (
    <header className="h-16 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60 flex items-center justify-between px-6 sticky top-0 z-30 shadow-sm">
      <div className="flex items-center">
        <h2 className="text-lg font-bold text-white tracking-wide">{getPageTitle()}</h2>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="hidden md:flex items-center gap-2 text-slate-400 text-sm font-mono bg-slate-900/50 px-3 py-1.5 rounded-lg border border-slate-800">
          <Clock className="h-4 w-4 text-blue-500" />
          {time.toLocaleTimeString()}
        </div>
        
        <div className="flex items-center gap-2 bg-green-500/5 border border-green-500/20 px-3 py-1.5 rounded-lg">
          <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
          <span className="text-xs font-bold text-green-400 hidden sm:block uppercase tracking-wider">Operational</span>
        </div>
      </div>
    </header>
  );
};
