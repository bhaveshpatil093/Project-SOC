import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { Network, Settings, ShieldAlert, AlertTriangle, ArrowRight, Clock } from 'lucide-react';
import { formatRelativeTime, formatTimestamp, truncate } from '../../utils/formatters';
import { getThreatColor } from '../../utils/colors';
import { Badge } from './Badge';

export const EntityTimeline = ({ entityKey, alerts = [], currentAlertId, maxItems = 20, compact = false }) => {
  // Process and sort alerts
  const sortedAlerts = useMemo(() => {
    return [...alerts]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, maxItems);
  }, [alerts, maxItems]);

  // Attack chain detection (3+ events within 15 minutes)
  const attackChainDetected = useMemo(() => {
    if (sortedAlerts.length < 3) return false;
    for (let i = 0; i < sortedAlerts.length - 2; i++) {
      const t1 = new Date(sortedAlerts[i].timestamp).getTime();
      const t3 = new Date(sortedAlerts[i+2].timestamp).getTime();
      if (Math.abs(t1 - t3) <= 15 * 60 * 1000) {
        return true;
      }
    }
    return false;
  }, [sortedAlerts]);

  const getLogIcon = (type) => {
    const t = (type || "").toLowerCase();
    if (t.includes("network") || t.includes("syslog") || t.includes("firewall")) return <Network className="h-4 w-4" />;
    if (t.includes("process") || t.includes("system")) return <Settings className="h-4 w-4" />;
    return <ShieldAlert className="h-4 w-4" />;
  };

  if (sortedAlerts.length === 0) {
    return <div className="text-[var(--text_secondary)] text-sm italic p-4">No correlated events found for this entity.</div>;
  }

  const isCompact = compact || maxItems < 5;

  return (
    <div className="w-full">
      {attackChainDetected && !isCompact && (
        <div className="mb-6 bg-orange-500/10 border border-orange-500/50 rounded-lg p-3 flex items-center gap-3 animate-pulse">
          <AlertTriangle className="h-5 w-5 text-orange-500 shrink-0" />
          <p className="text-sm font-bold text-orange-400">
            POTENTIAL ATTACK CHAIN DETECTED: Rapid anomalous escalation observed on this entity.
          </p>
        </div>
      )}

      <div className="relative pl-6 border-l-2 border-[var(--border)]/50 space-y-6">
        {sortedAlerts.map((alert, idx) => {
          const isCurrent = (alert.id || alert._id) === currentAlertId;
          const threatLevel = (alert.threat_level || "low").toLowerCase();
          const colorObj = getThreatColor(threatLevel);
          const dotColor = colorObj.bg;
          
          const score = parseFloat(alert.threat_score || 0) * 100;
          
          if (isCompact) {
            return (
              <div key={alert.id || idx} className="relative group">
                {/* Dot */}
                <div 
                  className={`absolute -left-[29px] top-1.5 h-3 w-3 rounded-full border-2 border-slate-900 ${isCurrent ? 'ring-2 ring-blue-500 scale-125' : ''}`}
                  style={{ backgroundColor: dotColor }}
                />
                <div className={`flex items-center gap-3 text-sm ${isCurrent ? 'bg-[var(--bg_secondary)]/80 p-2 rounded-lg -ml-2 border border-[var(--border)]' : ''}`}>
                  <span className="text-[var(--text_secondary)] text-xs w-20 shrink-0">{formatRelativeTime(alert.timestamp)}</span>
                  <Badge variant={threatLevel}>{threatLevel}</Badge>
                  <span className="text-[var(--text_secondary)] truncate max-w-[200px]">{alert.top_rule || alert.log_type || "Unknown Rule"}</span>
                  <Link to={`/alerts/${alert.id || alert._id}`} className="ml-auto text-blue-400 hover:text-blue-300 text-xs flex items-center">
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            );
          }

          // Full Card Mode
          return (
            <div key={alert.id || idx} className="relative group">
              {/* Dot on the timeline */}
              <div 
                className={`absolute -left-[31px] top-4 h-4 w-4 rounded-full border-[3px] border-slate-900 z-10 transition-transform ${isCurrent ? 'ring-2 ring-blue-500 scale-125 ring-offset-2 ring-offset-slate-900' : 'group-hover:scale-110'}`}
                style={{ backgroundColor: dotColor }}
              />

              {/* Connecting bracket for attack chains (visually implied by proximity and the orange banner above, but we highlight the card border if it's high/crit) */}
              <div className={`ml-2 bg-[var(--bg_secondary)]/80 rounded-xl border ${isCurrent ? 'border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-[var(--border)]'} p-4 transition-all hover:border-slate-500`}>
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-[var(--bg_primary)] text-[var(--text_secondary)] border border-[var(--border)]">
                      {getLogIcon(alert.log_type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[var(--text_primary)] truncate max-w-[250px]" title={alert.top_rule || "Unknown Signature"}>
                        {truncate(alert.top_rule || "Generic Anomaly Detected", 40)}
                      </h4>
                      <div className="flex items-center gap-2 text-xs text-[var(--text_secondary)] mt-0.5">
                        <Clock className="h-3 w-3" />
                        <span title={formatTimestamp(alert.timestamp)}>{formatRelativeTime(alert.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <Badge variant={alert.status === "closed" ? "benign" : "tp"}>{alert.status || "open"}</Badge>
                    <Badge variant={threatLevel}>{threatLevel}</Badge>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4">
                  {/* Compact Threat Progress Bar */}
                  <div className="flex items-center gap-2 w-[120px]">
                    <span className="text-xs font-bold text-[var(--text_secondary)] w-6">{score.toFixed(0)}</span>
                    <div className="h-1.5 flex-1 bg-[var(--bg_primary)] rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: dotColor }} />
                    </div>
                  </div>

                  {!isCurrent && (
                    <Link 
                      to={`/alerts/${alert.id || alert._id}`}
                      className="text-xs font-medium text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1"
                    >
                      View Alert <ArrowRight className="h-3 w-3" />
                    </Link>
                  )}
                  {isCurrent && (
                    <span className="text-xs font-bold text-blue-500 flex items-center gap-1">
                      Current <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

EntityTimeline.propTypes = {
  entityKey: PropTypes.string,
  alerts: PropTypes.array,
  currentAlertId: PropTypes.string,
  maxItems: PropTypes.number,
  compact: PropTypes.bool
};
