import { useParams, Link, useNavigate } from "react-router-dom";
import { useAlert, useAlertTimeline, useUpdateAlertStatus } from "../hooks/useAlerts";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Badge } from "../components/common/Badge";
import { ThreatGauge } from "../components/common/ThreatGauge";
import { formatDate } from "../utils/formatters";
import { ArrowLeft, Bot, Shield, Clock, Terminal, User, Server, ExternalLink, AlertTriangle } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell
} from "recharts";

export const AlertDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: alert, isLoading, isError } = useAlert(id);
  const { data: timelineData } = useAlertTimeline(id);
  const updateStatusMutation = useUpdateAlertStatus();

  if (isLoading) return <LoadingSpinner />;
  if (isError || !alert) return <ErrorBanner message="Failed to load alert details. Alert may not exist." />;

  // Prepare SHAP Data
  const shapData = (alert.top_features || []).map(f => {
    if (typeof f === 'string') {
      return { name: f, value: 1, originalValue: 1, color: "#ef4444" };
    }
    return {
      name: f.feature || "Unknown",
      value: Math.abs(f.value || 0),
      originalValue: f.value || 0,
      color: f.direction === 'decreases_risk' ? '#22c55e' : '#ef4444'
    };
  });

  const timeline = timelineData?.alerts || timelineData || [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <Link to="/alerts" className="inline-flex items-center text-sm text-blue-500 hover:text-blue-400 font-medium">
        <ArrowLeft className="h-4 w-4 mr-1" /> Back to Alerts
      </Link>
      
      {/* SECTION 1: Alert Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-lg flex flex-col md:flex-row gap-8 items-start md:items-center justify-between">
        <div className="flex items-center gap-8 flex-1">
          <ThreatGauge score={alert.threat_score * 100} size={150} showLabel={false} />
          
          <div className="space-y-3 flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">{alert.entity_key || "Unknown Entity"}</h1>
              <Badge variant={alert.threat_level} className="uppercase tracking-wider px-3 py-1 text-xs">
                {alert.threat_level}
              </Badge>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center gap-2 text-slate-300">
                <Server className="h-4 w-4 text-slate-500" />
                <span className="font-medium">{alert.host_id || "N/A"}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <User className="h-4 w-4 text-slate-500" />
                <span className="font-medium">{alert.user_name || "N/A"}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Terminal className="h-4 w-4 text-slate-500" />
                <span className="font-medium">{alert.log_type || "N/A"}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Clock className="h-4 w-4 text-slate-500" />
                <span className="font-medium">{formatDate(alert.timestamp)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-4 min-w-[200px]">
          <div className="flex items-center gap-2 bg-slate-900 px-3 py-2 rounded-lg border border-slate-700 w-full">
            <span className="text-xs text-slate-400 font-medium">Status:</span>
            <select 
              value={alert.alert_status || "open"} 
              onChange={(e) => updateStatusMutation.mutate({ id: alert._id || alert.id, status: e.target.value })}
              className="flex-1 bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
            >
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <button 
            onClick={() => navigate(`/investigation?alert_id=${alert._id || alert.id}`)}
            className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-purple-900/20"
          >
            <Bot className="h-5 w-5" />
            Investigate with AI
          </button>
        </div>
      </div>

      {/* SECTION 2: Two Columns (SHAP + MITRE) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: SHAP Explanation */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 flex flex-col">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-500" />
            Why was this alert raised?
          </h3>
          
          <div className="h-[250px] mb-6">
            {shapData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={shapData} layout="vertical" margin={{ top: 0, right: 20, left: 20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} width={120} />
                  <RechartsTooltip 
                    cursor={{ fill: '#334155', opacity: 0.4 }}
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                    formatter={(value, name, props) => [parseFloat(props.payload.originalValue).toFixed(4), "SHAP Value"]}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                    {shapData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 border border-dashed border-slate-700 rounded-lg">
                No feature importance data available.
              </div>
            )}
          </div>

          <blockquote className="border-l-4 border-blue-500 bg-slate-900/50 p-4 rounded-r-lg text-slate-300 text-sm leading-relaxed italic">
            "{alert.human_explanation || "No automated explanation was generated for this alert. Please rely on the feature charts and rule triggers."}"
          </blockquote>
        </div>

        {/* Right: MITRE ATT&CK Panel */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 flex flex-col">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-500" />
            MITRE ATT&CK Mapping
          </h3>
          
          <div className="space-y-4 overflow-y-auto flex-1">
            {alert.mitre_technique_ids && alert.mitre_technique_ids.length > 0 ? (
              alert.mitre_technique_ids.map((technique, idx) => (
                <div key={idx} className="bg-slate-900 border border-slate-700 rounded-lg p-4 hover:border-slate-500 transition-colors group">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-sm font-bold text-red-400 font-mono">{technique}</span>
                      <p className="text-slate-200 font-medium mt-1">Matched Technique Signature</p>
                      <p className="text-xs text-slate-400 mt-1 capitalize">
                        Tactic: {(alert.mitre_tactics && alert.mitre_tactics[idx]) || "Unknown Tactic"}
                      </p>
                    </div>
                    <a 
                      href={`https://attack.mitre.org/techniques/${technique.replace('.', '/')}`} 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-slate-500 hover:text-blue-400 transition-colors p-1 bg-slate-800 rounded group-hover:bg-slate-700"
                      title="View on MITRE ATT&CK"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 border border-dashed border-slate-700 rounded-lg py-12">
                No MITRE ATT&CK techniques identified.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SECTION 3: Timeline & Rules */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold text-white">Entity Timeline & Triggers</h3>
        
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          {/* Vertical Timeline */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 xl:col-span-1 h-full max-h-[600px] overflow-y-auto">
            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6">Event Sequence</h4>
            <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
              {timeline.length > 0 ? timeline.map((tItem, idx) => {
                const isCurrent = (tItem._id || tItem.id) === (alert._id || alert.id);
                return (
                  <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow ${isCurrent ? 'bg-blue-500 border-blue-900 shadow-blue-500/50 z-10' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
                      {isCurrent ? <AlertTriangle className="h-4 w-4 text-white" /> : <Clock className="h-4 w-4" />}
                    </div>
                    <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border ${isCurrent ? 'bg-blue-900/20 border-blue-500/50' : 'bg-slate-900/50 border-slate-700'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant={tItem.threat_level}>{tItem.threat_level}</Badge>
                        <span className="text-xs text-slate-400 font-mono">{formatDate(tItem.timestamp)}</span>
                      </div>
                      <div className="text-sm text-slate-300 font-medium mt-2">{tItem.log_type}</div>
                      <Link to={`/alerts/${tItem._id || tItem.id}`} className="text-xs text-blue-400 hover:underline mt-2 inline-block">
                        View Details
                      </Link>
                    </div>
                  </div>
                );
              }) : (
                <p className="text-slate-500 text-sm italic">No recent timeline events found for this entity.</p>
              )}
            </div>
          </div>

          {/* Triggered Rules Table */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden xl:col-span-2">
            <div className="px-6 py-4 border-b border-slate-700">
              <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Triggered Rules</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap">
                <thead className="bg-slate-900/50 border-b border-slate-700">
                  <tr>
                    <th className="px-6 py-3 text-xs font-semibold text-slate-400">Rule ID</th>
                    <th className="px-6 py-3 text-xs font-semibold text-slate-400">Rule Details</th>
                    <th className="px-6 py-3 text-xs font-semibold text-slate-400">MITRE Technique</th>
                    <th className="px-6 py-3 text-xs font-semibold text-slate-400">Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {alert.triggered_rules && alert.triggered_rules.length > 0 ? (
                    alert.triggered_rules.map((rule, idx) => {
                      const isObj = typeof rule === 'object';
                      const ruleId = isObj ? rule.id : rule;
                      const ruleName = isObj ? rule.name : "Pattern Match Signature";
                      const technique = isObj ? rule.technique : (alert.mitre_technique_ids?.[idx] || "N/A");
                      const severity = isObj ? rule.severity : "High";

                      return (
                        <tr key={idx} className="hover:bg-slate-750/50 transition-colors">
                          <td className="px-6 py-4 text-sm font-mono text-blue-400">{ruleId}</td>
                          <td className="px-6 py-4 text-sm text-slate-300">{ruleName}</td>
                          <td className="px-6 py-4 text-xs font-mono text-slate-400">{technique}</td>
                          <td className="px-6 py-4">
                            <span className={`text-xs px-2 py-1 rounded-full border ${
                              severity === 'High' || severity === 'Critical' ? 'bg-red-500/10 border-red-500/50 text-red-400' : 'bg-orange-500/10 border-orange-500/50 text-orange-400'
                            }`}>
                              {severity} Contribution
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center text-slate-500">
                        No explicit rules triggered. Alert originated strictly from anomaly detection models.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
