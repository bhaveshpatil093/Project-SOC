import React from 'react';
import PropTypes from 'prop-types';
import { PackageOpen } from 'lucide-react';

export const EmptyState = ({ icon: Icon = PackageOpen, title, description, actionLabel, onAction }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-slate-800/50 rounded-xl border border-dashed border-slate-700 animate-in fade-in duration-300">
      <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4 border border-slate-700">
        <Icon className="h-8 w-8 text-slate-500" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-slate-400 max-w-sm text-sm leading-relaxed mb-6">{description}</p>
      {actionLabel && onAction && (
        <button 
          onClick={onAction}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

EmptyState.propTypes = {
  icon: PropTypes.elementType,
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  actionLabel: PropTypes.string,
  onAction: PropTypes.func
};
