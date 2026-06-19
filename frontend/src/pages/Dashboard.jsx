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

const COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

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
    <div className={`bg-slate-800 p-6 rounded-xl border transition-colors duration-300 relative overflow-hidden flex flex-col justify-between h-32 ${isFlashing ? 'border-green-500 bg-slate-800/80 shadow-[0_0_15px_rgba(34,197,94,0.3)]' : 'border-slate-700'}`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${colorClass} ${pulseIcon ? 'animate-pulse' : ''}`} />
          <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
        </div>
        <div className="bg-slate-700/50 text-slate-300 text-[10px] px-2 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider font-semibold">
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
    <div className="w-full bg-slate-900 border-b border-slate-800 py-1.5 px-4 text-xs font-mono flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Last ingestion:</span>
          {ingestionRunning ? (
            <span className="text-blue-400 flex items-center gap-1"><LoadingSpinner size="h-3 w-3" /> Running...</span>
          ) : (
            <span className="text-slate-300">{lastIngestion?.docs_indexed || 0} docs · {timeAgo}</span>
          )}
        </div>
        <div className="w-px h-3 bg-slate-700"></div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Last scoring:</span>
          {scoringRunning ? (
            <span className="text-orange-400 flex items-center gap-1"><LoadingSpinner size="h-3 w-3" /> Running...</span>
          ) : (
            <span className="text-slate-300">{lastScoring?.scored || 0} alerts</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Pipeline:</span>
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
        <div className="w-px h-3 bg-slate-700"></div>
        <div className="flex items-center gap-2">
           <span className="text-slate-500">SLM:</span>
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
    <div className="w-[300px] bg-slate-900 border-l border-slate-800 flex flex-col h-[calc(100vh-100px)] shrink-0 sticky top-4">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-500" />
          Live Alert Stream
        </h3>
        <button 
          onClick={() => setIsPaused(!isPaused)}
          className={`p-1.5 rounded-md transition-colors ${isPaused ? 'bg-orange-500/20 text-orange-400' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
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
              className="bg-slate-800 border border-slate-700 p-3 rounded-lg cursor-pointer hover:bg-slate-700 transition-all animate-in slide-in-from-top-2 fade-in duration-300 relative overflow-hidden group"
            >
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                  alert.threat_level === 'critical' ? 'bg-red-500' :
                  alert.threat_level === 'high' ? 'bg-orange-500' :
                  alert.threat_level === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
              }`}></div>
              <div className="flex justify-between items-start mb-1.5 ml-2">
                <span className="text-[10px] text-slate-400 font-mono">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                  alert.threat_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                  alert.threat_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                  alert.threat_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {alert.threat_level}
                </span>
              </div>
              <div className="ml-2">
                <h4 className="text-xs font-bold text-slate-200 truncate group-hover:text-white transition-colors">{alert.entity_key}</h4>
                <div className="flex justify-between items-end mt-2">
                   <p className="text-[10px] text-slate-500 truncate max-w-[150px]">{alert.log_type}</p>
                   <span className="text-xs font-mono text-slate-400">{(alert.threat_score * 100).toFixed(0)}</span>
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
    { name: "Critical", value: stats?.critical || 0, color: COLORS.critical },
    { name: "High", value: stats?.high || 0, color: COLORS.high },
    { name: "Medium", value: stats?.medium || 0, color: COLORS.medium },
    { name: "Low", value: stats?.low || 0, color: COLORS.low },
  ].filter(d => d.value > 0);

  // Prepare Bar Chart Data
  const barData = (stats?.top_tactics || initialStats?.top_tactics || []).map(t => ({
    name: t.key || t.name || t,
    count: t.doc_count || t.count || 0
  }));

  const topHosts = stats?.top_hosts || initialStats?.top_hosts || [];
  const fpr = feedbackStats?.false_positive_rate || 0;

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 -m-8">
      {/* Absolute top edge ticker */}
      <LiveMetricsTicker />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Main Content Area */}
        <div className="flex-1 p-8 overflow-y-auto space-y-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">SOC Dashboard</h1>
          </div>

          {/* Stat Cards - Top Row */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            <StatCard title="Total Open Alerts" value={stats?.total || stats?.total_open || 0} icon={Activity} colorClass="text-blue-500" flash={true} />
            <StatCard title="Critical Alerts" value={stats?.critical || 0} icon={AlertOctagon} colorClass="text-red-500" isCritical={true} flash={true} pulseIcon={scoringRunning} />
            <StatCard title="High Alerts" value={stats?.high || 0} icon={AlertTriangle} colorClass="text-orange-500" flash={true} />
            <StatCard title="Alerts Last 24h" value={stats?.alerts_last_24h || initialStats?.alerts_last_24h || 0} icon={Clock} colorClass="text-purple-500" />
            <StatCard title="False Positive Rate" value={`${(fpr * 100).toFixed(1)}%`} icon={Percent} colorClass="text-slate-200" />
          </div>

          {/* Charts - Bottom Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Threat Level Donut */}
            <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 h-[400px] flex flex-col relative">
              <h3 className="text-lg font-semibold mb-4 text-white">Threat Level Distribution</h3>
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
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                      itemStyle={{ color: '#f8fafc' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-4xl font-bold text-white">{stats?.total || stats?.total_open || 0}</span>
                  <span className="text-sm text-slate-400">Total Alerts</span>
                </div>
              </div>
            </div>

            {/* Top MITRE Tactis Bar Chart */}
            <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 h-[400px] flex flex-col">
              <h3 className="text-lg font-semibold mb-4 text-white">Top MITRE Tactics</h3>
              <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                    <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} width={120} />
                    <RechartsTooltip 
                      cursor={{ fill: '#334155', opacity: 0.4 }}
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                    />
                    <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Top Hosts Table */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden mt-6">
            <div className="px-6 py-5 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">Top Hosts by Threat Volume</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-900 border-b border-slate-700">
                  <tr>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">Hostname</th>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">Critical</th>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">High</th>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">Medium</th>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">Low</th>
                    <th className="px-6 py-4 text-sm font-semibold text-slate-300">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {topHosts.length > 0 ? (
                    topHosts.map((host, idx) => (
                      <tr 
                        key={idx} 
                        className="hover:bg-slate-750 transition-colors cursor-pointer group"
                        onClick={() => navigate(`/alerts?host_id=${host.key || host.hostname}`)}
                      >
                        <td className="px-6 py-4 text-sm font-medium text-blue-400 group-hover:text-blue-300 transition-colors">
                          {host.key || host.hostname}
                        </td>
                        <td className="px-6 py-4 text-sm text-red-500 font-medium">{host.critical || 0}</td>
                        <td className="px-6 py-4 text-sm text-orange-500 font-medium">{host.high || 0}</td>
                        <td className="px-6 py-4 text-sm text-yellow-500 font-medium">{host.medium || 0}</td>
                        <td className="px-6 py-4 text-sm text-green-500 font-medium">{host.low || 0}</td>
                        <td className="px-6 py-4 text-sm text-white font-bold">{host.doc_count || host.total || 0}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="px-6 py-8 text-center text-slate-500">No host data available.</td>
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
