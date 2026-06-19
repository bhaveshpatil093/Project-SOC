import React from 'react';
import PropTypes from 'prop-types';
import { AlertCircle, RefreshCw } from 'lucide-react';

export const ErrorBanner = ({ message, onRetry }) => {
  return (
    <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 w-full animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="flex items-start gap-4">
        <div className="p-2 bg-red-500/20 rounded-full text-red-500 shrink-0">
          <AlertCircle className="h-6 w-6" />
        </div>
        <div>
          <h3 className="text-red-400 font-bold mb-1">System Error Encountered</h3>
          <p className="text-slate-300 text-sm leading-relaxed max-w-3xl">{message || "An unexpected network or system error occurred."}</p>
        </div>
      </div>
      
      {onRetry && (
        <button 
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg text-sm transition-colors shrink-0"
        >
          <RefreshCw className="h-4 w-4" />
          Retry Connection
        </button>
      )}
    </div>
  );
};

ErrorBanner.propTypes = {
  message: PropTypes.string.isRequired,
  onRetry: PropTypes.func
};
