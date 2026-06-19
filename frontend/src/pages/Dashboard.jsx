import { useQuery } from "@tanstack/react-query";
import { fetchAlertStats } from "../api/alerts";
import { fetchFeedbackStats } from "../api/feedback";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useNavigate } from "react-router-dom";
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
import { Activity, AlertOctagon, AlertTriangle, Clock, Percent } from "lucide-react";

const COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

const StatCard = ({ title, value, icon: Icon, colorClass, isCritical = false }) => (
  <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 relative overflow-hidden flex flex-col justify-between h-32">
    <div className="flex justify-between items-start">
      <div className="flex items-center gap-2">
        <Icon className={`h-5 w-5 ${colorClass}`} />
        <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
      </div>
      <div className="bg-slate-700/50 text-slate-300 text-[10px] px-2 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider font-semibold">
        <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></div>
        Live
      </div>
    </div>
    <div className="flex items-end gap-3 mt-4">
      <p className={`text-4xl font-bold ${colorClass}`}>{value}</p>
      {isCritical && parseInt(value, 10) > 0 && (
        <span className="flex h-3 w-3 relative mb-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </span>
      )}
    </div>
  </div>
);

export const Dashboard = () => {
  const navigate = useNavigate();

  const { data: stats, isLoading: isLoadingStats, isError: isErrorStats } = useQuery({
    queryKey: ["alertStats"],
    queryFn: fetchAlertStats,
    refetchInterval: 30000,
  });

  const { data: feedbackStats, isLoading: isLoadingFeedback, isError: isErrorFeedback } = useQuery({
    queryKey: ["feedbackStats"],
    queryFn: fetchFeedbackStats,
    refetchInterval: 30000,
  });

  if (isLoadingStats || isLoadingFeedback) return <LoadingSpinner />;
  if (isErrorStats || isErrorFeedback) return <ErrorBanner message="Failed to load dashboard data." />;

  // Prepare Pie Chart Data
  const pieData = [
    { name: "Critical", value: stats?.critical || 0, color: COLORS.critical },
    { name: "High", value: stats?.high || 0, color: COLORS.high },
    { name: "Medium", value: stats?.medium || 0, color: COLORS.medium },
    { name: "Low", value: stats?.low || 0, color: COLORS.low },
  ].filter(d => d.value > 0);

  // Prepare Bar Chart Data
  const barData = (stats?.top_tactics || []).map(t => ({
    name: t.key || t.name || t,
    count: t.doc_count || t.count || 0
  }));

  const topHosts = stats?.top_hosts || [];
  const fpr = feedbackStats?.false_positive_rate || 0;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SOC Dashboard</h1>
      </div>

      {/* Stat Cards - Top Row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        <StatCard title="Total Open Alerts" value={stats?.total_open || 0} icon={Activity} colorClass="text-blue-500" />
        <StatCard title="Critical Alerts" value={stats?.critical || 0} icon={AlertOctagon} colorClass="text-red-500" isCritical={true} />
        <StatCard title="High Alerts" value={stats?.high || 0} icon={AlertTriangle} colorClass="text-orange-500" />
        <StatCard title="Alerts Last 24h" value={stats?.alerts_last_24h || 0} icon={Clock} colorClass="text-purple-500" />
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
              <span className="text-4xl font-bold text-white">{stats?.total_open || 0}</span>
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
  );
};
