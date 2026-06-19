import React from 'react';
import { Activity, Server, ShieldAlert, Cpu } from 'lucide-react';

export const AttackChain = React.memo(({ chainData }) => {
  if (!chainData || chainData.length === 0) {
    return <div className="text-[var(--text_secondary)] text-sm italic">No attack chain data available.</div>;
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
    if (score >= 0.8) return 'bg-red-500 text-[var(--text_primary)]';
    if (score >= 0.5) return 'bg-orange-500 text-[var(--text_primary)]';
    return 'bg-blue-500 text-[var(--text_primary)]';
  };

  const parseMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const match = timeStr.match(/T\+(\d+)m/);
    return match ? parseInt(match[1], 10) : 0;
  };

  const processedChainData = React.useMemo(() => {
    return chainData.map((stage, idx) => {
      const score = typeof stage.score === 'number' ? stage.score.toFixed(2) : stage.score;
      const isFast = idx > 0 && (parseMinutes(stage.time) - parseMinutes(chainData[idx - 1].time)) < 5;
      return { ...stage, parsedScore: score, isFast };
    });
  }, [chainData]);

  return (
    <div className="w-full py-8 overflow-x-auto">
      <div className="flex items-center min-w-max px-4">
        {processedChainData.map((stage, idx) => (
          <React.Fragment key={idx}>
            {/* Connection Line to previous node */}
            {idx > 0 && (
              <div className={`flex flex-col items-center justify-center w-24 -mt-8 ${stage.isFast ? 'text-red-500' : 'text-slate-600'}`}>
                <span className="text-xs font-mono font-medium bg-[var(--bg_primary)] px-2 rounded-full z-10">{stage.isFast ? 'FAST' : ''}</span>
                <div className={`h-1 w-full ${stage.isFast ? 'bg-red-500/50' : 'bg-[var(--bg_tertiary)]'} -mt-2`} />
              </div>
            )}
            
            {/* Node */}
            <div className="relative flex flex-col items-center w-36">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 border-slate-900 z-10 shadow-lg ${getScoreColor(stage.score)}`}>
                {getLogIcon(stage.log_type)}
              </div>
              
              <div className="mt-3 text-center">
                <span className="block text-xs font-bold text-[var(--text_secondary)] uppercase tracking-wider mb-1">
                  {stage.tactic}
                </span>
                <span className="block text-[10px] font-mono text-[var(--text_secondary)] bg-[var(--bg_secondary)] rounded px-2 py-0.5 inline-block border border-[var(--border)]">
                  {stage.time}
                </span>
                <div className="mt-1 flex justify-center">
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${stage.score >= 0.8 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-[var(--bg_secondary)] text-[var(--text_secondary)]'}`}>
                    {stage.parsedScore}
                  </span>
                </div>
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
});
