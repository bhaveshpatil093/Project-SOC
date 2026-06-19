import React, { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAlertStats } from "../api/alerts";
import { fetchFeedbackStats } from "../api/feedback";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useNavigate } from "react-router-dom";
import { useWebSocketStore } from "../hooks/useWebSocket";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity, AlertOctagon, AlertTriangle, Clock, Percent, Pause, Play, ShieldAlert } from "lucide-react";
import { formatDate } from "../utils/formatters";
import { useUiStore } from "../store/uiStore";
import { THEMES } from "../utils/theme";

// Custom hook for count-up animation
function useCountUp(end, duration = 1000) {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);
  const endRef = useRef(end);

  useEffect(() => {
    if (end === countRef.current) return;
    
    let startTime = null;
    const startValue = countRef.current;
    const endValue = end;
    
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      // Easing function (easeOutQuart)
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      const current = Math.floor(startValue + (endValue - startValue) * easeProgress);
      
      setCount(current);
      countRef.current = current;
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setCount(endValue);
        countRef.current = endValue;
      }
    };
    
    requestAnimationFrame(animate);
  }, [end, duration]);

  return count;
}

const StatCard = ({ title, value, icon: Icon, colorClass, isCritical = false, flash = false, pulseIcon = false }) => {
  const [isFlashing, setIsFlashing] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (flash && value !== prevValue.current) {
      setIsFlashing(true);
      const timer = setTimeout(() => setIsFlashing(false), 500);
      prevValue.current = value;
      return () => clearTimeout(timer);
    }
  }, [value, flash]);

  const displayValue = typeof value === 'number' ? useCountUp(value) : value;

  return (
    <div className={`bg-[var(--bg_secondary)] p-6 rounded-xl border transition-colors duration-300 relative overflow-hidden flex flex-col justify-between h-32 ${isFlashing ? 'border-green-500 bg-[var(--bg_secondary)]/80 shadow-[0_0_15px_rgba(34,197,94,0.3)]' : 'border-[var(--border)]'}`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${colorClass} ${pulseIcon ? 'animate-pulse' : ''}`} />
          <h3 className="text-[var(--text_secondary)] text-sm font-medium">{title}</h3>
        </div>
        <div className="bg-[var(--bg_tertiary)]/50 text-[var(--text_secondary)] text-[10px] px-2 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider font-semibold">
          <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></div>
          Live
        </div>
      </div>
      <div className="flex items-end gap-3 mt-4">
        <p className={`text-4xl font-bold ${colorClass}`}>{displayValue}</p>
        {isCritical && parseInt(value, 10) > 0 && (
          <span className="flex h-3 w-3 relative mb-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
        )}
      </div>
    </div>
  );
};

const LiveMetricsTicker = () => {
  const { wsConnected, lastIngestion, lastScoring, ingestionRunning, scoringRunning } = useWebSocketStore();
  const [timeAgo, setTimeAgo] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      if (lastIngestion?.timestamp) {
        const diff = Math.floor((new Date() - new Date(lastIngestion.timestamp)) / 1000);
        setTimeAgo(`${diff}s ago`);
      } else {
        setTimeAgo("N/A");
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [lastIngestion]);

  return (
    <div className="w-full bg-[var(--bg_primary)] border-b border-[var(--border)] py-1.5 px-4 text-xs font-mono flex items-center justify-between shadow-sm overflow-x-auto whitespace-nowrap hide-scrollbar">
      <div className="flex items-center gap-4 sm:gap-6 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[var(--text_secondary)]">Last ingestion:</span>
          {ingestionRunning ? (
            <span className="text-blue-400 flex items-center gap-1"><LoadingSpinner size="h-3 w-3" /> Running...</span>
          ) : (
            <span className="text-[var(--text_secondary)]">{lastIngestion?.docs_indexed || 0} docs · {timeAgo}</span>
          )}
        </div>
        <div className="w-px h-3 bg-[var(--bg_tertiary)]"></div>
        <div className="flex items-center gap-2">
          <span className="text-[var(--text_secondary)]">Last scoring:</span>
          {scoringRunning ? (
            <span className="text-orange-400 flex items-center gap-1"><LoadingSpinner size="h-3 w-3" /> Running...</span>
          ) : (
            <span className="text-[var(--text_secondary)]">{lastScoring?.scored || 0} alerts</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 sm:gap-6 shrink-0 ml-4 sm:ml-0">
        <div className="flex items-center gap-2">
          <span className="text-[var(--text_secondary)]">Pipeline:</span>
          {wsConnected ? (
             <span className="text-green-500 font-bold flex items-center gap-1">
               <div className="h-1.5 w-1.5 rounded-full bg-green-500"></div> HEALTHY
             </span>
          ) : (
             <span className="text-red-500 font-bold flex items-center gap-1">
               <div className="h-1.5 w-1.5 rounded-full bg-red-500"></div> DISCONNECTED
             </span>
          )}
        </div>
        <div className="w-px h-3 bg-[var(--bg_tertiary)]"></div>
        <div className="flex items-center gap-2">
           <span className="text-[var(--text_secondary)]">SLM:</span>
           <span className="text-indigo-400 font-bold">Ready</span>
        </div>
      </div>
    </div>
  );
};

const LiveAlertFeed = () => {
  const { liveAlerts } = useWebSocketStore();
  const [isPaused, setIsPaused] = useState(false);
  const [displayedAlerts, setDisplayedAlerts] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isPaused) {
      setDisplayedAlerts(liveAlerts);
    }
  }, [liveAlerts, isPaused]);

  return (
    <div className="w-full xl:w-[300px] bg-[var(--bg_primary)] xl:border-l border-t xl:border-t-0 border-[var(--border)] flex flex-col xl:h-[calc(100vh-100px)] shrink-0 xl:sticky top-4 h-[400px]">
      <div className="p-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--bg_primary)]/50">
        <h3 className="text-sm font-bold text-[var(--text_primary)] flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-500" />
          Live Alert Stream
        </h3>
        <button 
          onClick={() => setIsPaused(!isPaused)}
          className={`p-1.5 rounded-md transition-colors ${isPaused ? 'bg-orange-500/20 text-orange-400' : 'bg-[var(--bg_secondary)] text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}
          title={isPaused ? "Resume stream" : "Pause stream"}
        >
          {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {displayedAlerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2">
             <ShieldAlert className="h-8 w-8 opacity-20" />
             <p className="text-xs">Waiting for live alerts...</p>
          </div>
        ) : (
          displayedAlerts.map((alert) => (
            <div 
              key={alert.id || alert._id} 
              onClick={() => navigate(`/alerts/${alert.id || alert._id}`)}
              className="bg-[var(--bg_secondary)] border border-[var(--border)] p-3 rounded-lg cursor-pointer hover:bg-[var(--bg_tertiary)] transition-all animate-in slide-in-from-top-2 fade-in duration-300 relative overflow-hidden group"
            >
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                  alert.threat_level === 'critical' ? 'bg-red-500' :
                  alert.threat_level === 'high' ? 'bg-orange-500' :
                  alert.threat_level === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
              }`}></div>
              <div className="flex justify-between items-start mb-1.5 ml-2">
                <span className="text-[10px] text-[var(--text_secondary)] font-mono">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                  alert.threat_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                  alert.threat_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                  alert.threat_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {alert.threat_level}
                </span>
              </div>
              <div className="ml-2">
                <h4 className="text-xs font-bold text-[var(--text_primary)] truncate group-hover:text-[var(--text_primary)] transition-colors">{alert.entity_key}</h4>
                <div className="flex justify-between items-end mt-2">
                   <p className="text-[10px] text-[var(--text_secondary)] truncate max-w-[150px]">{alert.log_type}</p>
                   <span className="text-xs font-mono text-[var(--text_secondary)]">{(alert.threat_score * 100).toFixed(0)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export const Dashboard = () => {
  const navigate = useNavigate();
  const { liveStats, scoringRunning } = useWebSocketStore();
  const { theme } = useUiStore();
  const colors = THEMES[theme];

  const { data: initialStats, isLoading: isLoadingStats, isError: isErrorStats } = useQuery({
    queryKey: ["alertStats"],
    queryFn: fetchAlertStats,
    refetchInterval: 60000, // Reduced to 60s since WS handles live updates
  });

  const { data: feedbackStats, isLoading: isLoadingFeedback, isError: isErrorFeedback } = useQuery({
    queryKey: ["feedbackStats"],
    queryFn: fetchFeedbackStats,
    refetchInterval: 60000,
  });

  if (isLoadingStats || isLoadingFeedback) return <LoadingSpinner />;
  if (isErrorStats || isErrorFeedback) return <ErrorBanner message="Failed to load dashboard data." />;

  // Prefer liveStats from WS over initial API fetch
  const stats = liveStats || initialStats;

  // Prepare Pie Chart Data
  const pieData = [
    { name: "Critical", value: stats?.critical || 0, color: colors.critical },
    { name: "High", value: stats?.high || 0, color: colors.high },
    { name: "Medium", value: stats?.medium || 0, color: colors.medium },
    { name: "Low", value: stats?.low || 0, color: colors.low },
  ].filter(d => d.value > 0);

  // Prepare Bar Chart Data
  const barData = (stats?.top_tactics || initialStats?.top_tactics || []).map(t => ({
    name: t.key || t.name || t,
    count: t.doc_count || t.count || 0
  }));

  const topHosts = stats?.top_hosts || initialStats?.top_hosts || [];
  const fpr = feedbackStats?.false_positive_rate || 0;

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg_primary)] -m-4 md:-m-8">
      {/* Absolute top edge ticker */}
      <LiveMetricsTicker />
      
      <div className="flex flex-col xl:flex-row flex-1 overflow-hidden">
        {/* Main Content Area */}
        <div className="flex-1 p-4 md:p-8 overflow-y-auto space-y-6 md:space-y-8">
          <div className="flex items-center justify-between">
            <h1 className="text-xl md:text-2xl font-bold">SOC Dashboard</h1>
          </div>

          {/* Stat Cards - Top Row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 md:gap-6">
            <StatCard title="Total Open Alerts" value={stats?.total || stats?.total_open || 0} icon={Activity} colorClass="text-blue-500" flash={true} />
            <StatCard title="Critical Alerts" value={stats?.critical || 0} icon={AlertOctagon} colorClass="text-red-500" isCritical={true} flash={true} pulseIcon={scoringRunning} />
            <StatCard title="High Alerts" value={stats?.high || 0} icon={AlertTriangle} colorClass="text-orange-500" flash={true} />
            <StatCard title="Alerts Last 24h" value={stats?.alerts_last_24h || initialStats?.alerts_last_24h || 0} icon={Clock} colorClass="text-purple-500" />
            <StatCard title="False Positive Rate" value={`${(fpr * 100).toFixed(1)}%`} icon={Percent} colorClass="text-[var(--text_primary)]" />
          </div>

          {/* Charts - Bottom Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {/* Threat Level Donut */}
            <div className="bg-[var(--bg_secondary)] p-4 md:p-6 rounded-xl border border-[var(--border)] h-[300px] md:h-[400px] flex flex-col relative">
              <h3 className="text-lg font-semibold mb-4 text-[var(--text_primary)]">Threat Level Distribution</h3>
              <div className="flex-1 relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      innerRadius={80}
                      outerRadius={120}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: colors.bg_secondary, borderColor: colors.border, borderRadius: '8px', color: colors.text_primary }}
                      itemStyle={{ color: colors.text_primary }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-4xl font-bold text-[var(--text_primary)]">{stats?.total || stats?.total_open || 0}</span>
                  <span className="text-sm text-[var(--text_secondary)]">Total Alerts</span>
                </div>
              </div>
            </div>

            {/* Top MITRE Tactis Bar Chart */}
            <div className="bg-[var(--bg_secondary)] p-4 md:p-6 rounded-xl border border-[var(--border)] h-[300px] md:h-[400px] flex flex-col">
              <h3 className="text-lg font-semibold mb-4 text-[var(--text_primary)]">Top MITRE Tactics</h3>
              <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={colors.border} horizontal={true} vertical={false} />
                    <XAxis type="number" stroke={colors.text_secondary} fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="name" stroke={colors.text_secondary} fontSize={12} tickLine={false} axisLine={false} width={120} />
                    <RechartsTooltip 
                      cursor={{ fill: colors.bg_tertiary, opacity: 0.4 }}
                      contentStyle={{ backgroundColor: colors.bg_secondary, borderColor: colors.border, borderRadius: '8px', color: colors.text_primary }}
                    />
                    <Bar dataKey="count" fill={colors.accent} radius={[0, 4, 4, 0]} barSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Top Hosts Table */}
          <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] overflow-hidden mt-6">
            <div className="px-6 py-5 border-b border-[var(--border)]">
              <h3 className="text-lg font-semibold text-[var(--text_primary)]">Top Hosts by Threat Volume</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-[var(--bg_primary)] border-b border-[var(--border)]">
                  <tr>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">Hostname</th>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">Critical</th>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">High</th>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">Medium</th>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">Low</th>
                    <th className="px-6 py-4 text-sm font-semibold text-[var(--text_secondary)]">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {topHosts.length > 0 ? (
                    topHosts.map((host, idx) => (
                      <tr 
                        key={idx} 
                        className="hover:bg-[var(--bg_tertiary)] transition-colors cursor-pointer group"
                        onClick={() => navigate(`/alerts?host_id=${host.key || host.hostname}`)}
                      >
                        <td className="px-6 py-4 text-sm font-medium text-blue-400 group-hover:text-blue-300 transition-colors">
                          {host.key || host.hostname}
                        </td>
                        <td className="px-6 py-4 text-sm text-red-500 font-medium">{host.critical || 0}</td>
                        <td className="px-6 py-4 text-sm text-orange-500 font-medium">{host.high || 0}</td>
                        <td className="px-6 py-4 text-sm text-yellow-500 font-medium">{host.medium || 0}</td>
                        <td className="px-6 py-4 text-sm text-green-500 font-medium">{host.low || 0}</td>
                        <td className="px-6 py-4 text-sm text-[var(--text_primary)] font-bold">{host.doc_count || host.total || 0}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="px-6 py-8 text-center text-[var(--text_secondary)]">No host data available.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Live Sidebar */}
        <LiveAlertFeed />
      </div>
    </div>
  );
};
