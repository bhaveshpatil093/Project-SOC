import React from 'react';
import PropTypes from 'prop-types';
import { useToastStore } from '../../hooks/useToast';
import { CheckCircle, AlertTriangle, Info, XCircle, X } from 'lucide-react';

export const Toast = ({ toast, onDismiss }) => {
  const icons = {
    success: <CheckCircle className="h-5 w-5 text-green-400" />,
    error: <XCircle className="h-5 w-5 text-red-400" />,
    warning: <AlertTriangle className="h-5 w-5 text-yellow-400" />,
    info: <Info className="h-5 w-5 text-blue-400" />
  };

  const bgs = {
    success: "bg-green-500/10 border-green-500/50 text-green-100",
    error: "bg-red-500/10 border-red-500/50 text-red-100",
    warning: "bg-yellow-500/10 border-yellow-500/50 text-yellow-100",
    info: "bg-blue-500/10 border-blue-500/50 text-blue-100"
  };

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-xl animate-in slide-in-from-bottom-8 fade-in duration-300 ${bgs[toast.type] || bgs.info}`}>
      {icons[toast.type] || icons.info}
      <p className="text-sm font-medium pr-4">{toast.message}</p>
      <button onClick={() => onDismiss(toast.id)} className="ml-auto opacity-60 hover:opacity-100 hover:bg-black/10 p-1 rounded transition-all">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

Toast.propTypes = {
  toast: PropTypes.shape({
    id: PropTypes.number.isRequired,
    message: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['success', 'error', 'warning', 'info'])
  }).isRequired,
  onDismiss: PropTypes.func.isRequired
};

export const ToastContainer = () => {
  const { toasts, removeToast } = useToastStore();
  
  if (toasts.length === 0) return null;
  
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
      {toasts.map(t => (
        <div key={t.id} className="pointer-events-auto">
          <Toast toast={t} onDismiss={removeToast} />
        </div>
      ))}
    </div>
  );
};
