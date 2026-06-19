import React from 'react';
import { Activity, Server, ShieldAlert, Cpu } from 'lucide-react';

export const AttackChain = ({ chainData }) => {
  if (!chainData || chainData.length === 0) {
    return <div className="text-slate-500 text-sm italic">No attack chain data available.</div>;
  }

  const getLogIcon = (logType) => {
    switch (logType?.toLowerCase()) {
      case 'network': return <Activity className="w-4 h-4" />;
      case 'process': return <Cpu className="w-4 h-4" />;
      case 'security': return <ShieldAlert className="w-4 h-4" />;
      default: return <Server className="w-4 h-4" />;
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'bg-red-500 text-white';
    if (score >= 0.5) return 'bg-orange-500 text-white';
    return 'bg-blue-500 text-white';
  };

  const parseMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const match = timeStr.match(/T\+(\d+)m/);
    return match ? parseInt(match[1], 10) : 0;
  };

  return (
    <div className="w-full py-8 overflow-x-auto">
      <div className="flex items-center min-w-max px-4">
        {chainData.map((stage, idx) => {
          const score = typeof stage.score === 'number' ? stage.score.toFixed(2) : stage.score;
          const isFast = idx > 0 && (parseMinutes(stage.time) - parseMinutes(chainData[idx - 1].time)) < 5;
          
          return (
            <React.Fragment key={idx}>
              {/* Connection Line to previous node */}
              {idx > 0 && (
                <div className={`flex flex-col items-center justify-center w-24 -mt-8 ${isFast ? 'text-red-500' : 'text-slate-600'}`}>
                  <span className="text-xs font-mono font-medium bg-slate-900 px-2 rounded-full z-10">{isFast ? 'FAST' : ''}</span>
                  <div className={`h-1 w-full ${isFast ? 'bg-red-500/50' : 'bg-slate-700'} -mt-2`} />
                </div>
              )}
              
              {/* Node */}
              <div className="relative flex flex-col items-center w-36">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 border-slate-900 z-10 shadow-lg ${getScoreColor(stage.score)}`}>
                  {getLogIcon(stage.log_type)}
                </div>
                
                <div className="mt-3 text-center">
                  <span className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                    {stage.tactic}
                  </span>
                  <span className="block text-[10px] font-mono text-slate-500 bg-slate-800 rounded px-2 py-0.5 inline-block border border-slate-700">
                    {stage.time}
                  </span>
                  <div className="mt-1 flex justify-center">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${stage.score >= 0.8 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-slate-800 text-slate-400'}`}>
                      {score}
                    </span>
                  </div>
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
