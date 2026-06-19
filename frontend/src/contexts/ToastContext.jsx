import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { X, AlertOctagon, AlertTriangle, Info, CheckCircle } from 'lucide-react';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback(({ id, title, message, level = 'info', duration = 5000, persistent = false }) => {
    const toastId = id || Date.now().toString();
    
    setToasts((prev) => {
      // Don't add duplicate ids
      if (prev.some(t => t.id === toastId)) return prev;
      return [...prev, { id: toastId, title, message, level, persistent }];
    });

    if (!persistent) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toastId));
      }, duration);
    }
    
    return toastId;
  }, []);

  useEffect(() => {
    const handleApiToast = (e) => {
      if (e.detail) showToast(e.detail);
    };
    window.addEventListener('api-toast', handleApiToast);
    return () => window.removeEventListener('api-toast', handleApiToast);
  }, [showToast]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      {/* Toast Container */}
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[100] flex flex-col gap-3 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

const ToastItem = ({ toast, onRemove }) => {
  const icons = {
    critical: <AlertOctagon className="h-5 w-5 text-red-500" />,
    high: <AlertTriangle className="h-5 w-5 text-orange-500" />,
    medium: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
    info: <Info className="h-5 w-5 text-blue-500" />,
    success: <CheckCircle className="h-5 w-5 text-green-500" />
  };

  const borderColors = {
    critical: 'border-red-500/50',
    high: 'border-orange-500/50',
    medium: 'border-yellow-500/50',
    info: 'border-blue-500/50',
    success: 'border-green-500/50'
  };

  const bgColors = {
    critical: 'bg-red-950/80',
    high: 'bg-orange-950/80',
    medium: 'bg-yellow-950/80',
    info: 'bg-blue-950/80',
    success: 'bg-green-950/80'
  };

  return (
    <div className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border backdrop-blur-md shadow-2xl animate-in slide-in-from-right-8 fade-in duration-300 ${bgColors[toast.level] || bgColors.info} ${borderColors[toast.level] || borderColors.info}`}>
      <div className="shrink-0 mt-0.5">{icons[toast.level] || icons.info}</div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-bold text-[var(--text_primary)] tracking-wide truncate">{toast.title}</h4>
        {toast.message && <p className="text-xs text-[var(--text_secondary)] mt-1 line-clamp-2">{toast.message}</p>}
      </div>
      <button 
        onClick={() => onRemove(toast.id)}
        className="shrink-0 p-1 rounded-md text-[var(--text_secondary)] hover:bg-white/10 hover:text-[var(--text_primary)] transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
