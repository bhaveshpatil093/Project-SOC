import React from 'react';
import PropTypes from 'prop-types';

export const PageHeader = ({ title, subtitle, actions }) => {
  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 border-b border-[var(--border)]/50 pb-6">
      <div>
        <h1 className="text-3xl font-bold text-[var(--text_primary)] tracking-tight">{title}</h1>
        {subtitle && <p className="text-[var(--text_secondary)] mt-2">{subtitle}</p>}
      </div>
      {actions && (
        <div className="flex items-center gap-3 w-full md:w-auto">
          {actions}
        </div>
      )}
    </div>
  );
};

PageHeader.propTypes = {
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  actions: PropTypes.node
};
