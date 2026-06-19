import React from 'react';
import PropTypes from 'prop-types';
import { getMitreColor } from '../../utils/colors';
import { Shield } from 'lucide-react';

export const MitrePanel = ({ tactics = [], techniques = [] }) => {
  if ((!tactics || tactics.length === 0) && (!techniques || techniques.length === 0)) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 text-center text-slate-500">
        <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No MITRE ATT&CK alignments detected.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-lg">
      <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
        <Shield className="h-4 w-4 text-purple-500" />
        MITRE ATT&CK Matrix
      </h3>

      {tactics && tactics.length > 0 && (
        <div className="mb-5">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Tactics</h4>
          <div className="flex flex-wrap gap-2">
            {tactics.map((tactic, idx) => {
              const color = getMitreColor(tactic);
              return (
                <span 
                  key={idx} 
                  className="px-2.5 py-1 rounded-md text-xs font-bold text-white shadow-sm border border-black/20"
                  style={{ backgroundColor: color }}
                >
                  {tactic}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {techniques && techniques.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Techniques</h4>
          <div className="flex flex-wrap gap-2">
            {techniques.map((tech, idx) => (
              <a
                key={idx}
                href={`https://attack.mitre.org/techniques/${tech.replace('.', '/')}`}
                target="_blank"
                rel="noreferrer"
                className="px-2 py-1 bg-slate-900 hover:bg-slate-700 border border-slate-600 rounded text-xs font-mono text-blue-400 hover:text-blue-300 transition-colors"
                title={`View ${tech} on MITRE ATT&CK`}
              >
                {tech}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

MitrePanel.propTypes = {
  tactics: PropTypes.arrayOf(PropTypes.string),
  techniques: PropTypes.arrayOf(PropTypes.string)
};
