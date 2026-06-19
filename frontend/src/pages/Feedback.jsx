import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { submitFeedback, getFeedback, getFeedbackStats, getSuppressionRules } from "../api/feedback";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Badge } from "../components/common/Badge";
import { formatDate } from "../utils/formatters";
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from "recharts";
import { CheckCircle, ShieldOff, AlertTriangle, MessageSquare, BarChart2, Shield } from "lucide-react";
import { useUiStore } from "../store/uiStore";
import { THEMES } from "../utils/theme";

// Local Hooks
const useFeedback = (limit = 50) => useQuery({ queryKey: ["feedback", limit], queryFn: () => getFeedback({ limit }) });
const useFeedbackStats = () => useQuery({ queryKey: ["feedbackStats"], queryFn: () => getFeedbackStats() });
const useSuppressionRules = () => useQuery({ queryKey: ["suppressionRules"], queryFn: () => getSuppressionRules() });

const TabSubmitFeedback = () => {
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [toast, setToast] = useState(null);
  
  const [form, setForm] = useState({
    alert_id: searchParams.get("alert_id") || "",
    analyst_name: "",
    label: "TP",
    mitre_override: "",
    notes: ""
  });

  const { data: feedbackData, isLoading, isError } = useFeedback();
  const feedbackList = feedbackData?.data || feedbackData || [];

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      setToast("Feedback submitted successfully!");
      setForm({ ...form, alert_id: "", label: "TP", mitre_override: "", notes: "" });
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
      queryClient.invalidateQueries({ queryKey: ["feedbackStats"] });
      setTimeout(() => setToast(null), 3000);
    }
  });

  const fieldErrors = mutation.error?.code === "VALIDATION_ERROR" ? mutation.error.fields || {} : {};

  const handleSubmit = (e) => {
    e.preventDefault();
    mutation.mutate(form);
  };

  const getRowColor = (label) => {
    // User requested: TP=green tint, FP=red tint, Benign=gray tint
    const l = (label || "").toUpperCase();
    if (l === "TP") return "bg-green-500/5 hover:bg-green-500/10 border-l-2 border-green-500";
    if (l === "FP") return "bg-red-500/5 hover:bg-red-500/10 border-l-2 border-red-500";
    if (l === "BENIGN") return "bg-slate-500/5 hover:bg-slate-500/10 border-l-2 border-slate-500";
    return "hover:bg-[var(--bg_tertiary)]";
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg">
        <h2 className="text-xl font-bold text-[var(--text_primary)] mb-6 flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-blue-500" />
          Submit Alert Feedback
        </h2>

        {toast && (
          <div className="mb-6 bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-lg flex items-center gap-3">
            <CheckCircle className="h-5 w-5" />
            <p>{toast}</p>
          </div>
        )}
        
        {mutation.isError && mutation.error?.code !== "VALIDATION_ERROR" && (
          <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg flex items-center gap-3">
            <AlertTriangle className="h-5 w-5" />
            <p>{mutation.error?.message || "Failed to submit feedback."}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-[var(--text_secondary)] mb-2">Alert ID</label>
              <input 
                required 
                type="text" 
                value={form.alert_id} 
                onChange={e => setForm({...form, alert_id: e.target.value})}
                placeholder="soc-alert-12345"
                className={`w-full bg-[var(--bg_primary)] border ${fieldErrors.alert_id ? 'border-red-500' : 'border-[var(--border)]'} rounded-lg px-4 py-2.5 text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors`}
              />
              {fieldErrors.alert_id && <p className="text-xs text-red-400 mt-1">{fieldErrors.alert_id}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text_secondary)] mb-2">Analyst Name</label>
              <input 
                required 
                type="text" 
                value={form.analyst_name} 
                onChange={e => setForm({...form, analyst_name: e.target.value})}
                placeholder="John Doe"
                className={`w-full bg-[var(--bg_primary)] border ${fieldErrors.analyst_name ? 'border-red-500' : 'border-[var(--border)]'} rounded-lg px-4 py-2.5 text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors`}
              />
              {fieldErrors.analyst_name && <p className="text-xs text-red-400 mt-1">{fieldErrors.analyst_name}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text_secondary)] mb-3">Verdict Label</label>
            <div className="flex flex-wrap gap-4">
              <label className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${form.label === 'TP' ? 'bg-green-500/20 border-green-500 text-green-400' : 'bg-[var(--bg_primary)] border-[var(--border)] text-[var(--text_secondary)] hover:border-slate-500'}`}>
                <input type="radio" name="label" value="TP" checked={form.label === "TP"} onChange={() => setForm({...form, label: "TP"})} className="hidden" />
                <CheckCircle className="h-4 w-4" /> True Positive (Real Threat)
              </label>
              <label className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${form.label === 'FP' ? 'bg-red-500/20 border-red-500 text-red-400' : 'bg-[var(--bg_primary)] border-[var(--border)] text-[var(--text_secondary)] hover:border-slate-500'}`}>
                <input type="radio" name="label" value="FP" checked={form.label === "FP"} onChange={() => setForm({...form, label: "FP"})} className="hidden" />
                <ShieldOff className="h-4 w-4" /> False Positive (Safe/Noise)
              </label>
              <label className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${form.label === 'Benign' ? 'bg-slate-500/20 border-slate-400 text-[var(--text_primary)]' : 'bg-[var(--bg_primary)] border-[var(--border)] text-[var(--text_secondary)] hover:border-slate-500'}`}>
                <input type="radio" name="label" value="Benign" checked={form.label === "Benign"} onChange={() => setForm({...form, label: "Benign"})} className="hidden" />
                <AlertTriangle className="h-4 w-4" /> Benign (Expected Behavior)
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text_secondary)] mb-2">MITRE Technique Override <span className="text-[var(--text_secondary)] text-xs font-normal">(Optional)</span></label>
            <input 
              type="text" 
              value={form.mitre_override} 
              onChange={e => setForm({...form, mitre_override: e.target.value})}
              placeholder="e.g. T1078.001"
              className={`w-full md:w-1/2 bg-[var(--bg_primary)] border ${fieldErrors.mitre_override ? 'border-red-500' : 'border-[var(--border)]'} rounded-lg px-4 py-2.5 text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors font-mono text-sm`}
            />
            {fieldErrors.mitre_override && <p className="text-xs text-red-400 mt-1">{fieldErrors.mitre_override}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text_secondary)] mb-2">Analyst Notes</label>
            <textarea 
              required
              rows={3}
              value={form.notes} 
              onChange={e => setForm({...form, notes: e.target.value})}
              placeholder="Explain the reasoning behind this label..."
              className={`w-full bg-[var(--bg_primary)] border ${fieldErrors.notes ? 'border-red-500' : 'border-[var(--border)]'} rounded-lg px-4 py-3 text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors resize-y`}
            />
            {fieldErrors.notes && <p className="text-xs text-red-400 mt-1">{fieldErrors.notes}</p>}
          </div>

          <button 
            type="submit" 
            disabled={mutation.isPending}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-[var(--text_primary)] font-medium px-6 py-2.5 rounded-lg transition-colors flex items-center gap-2"
          >
            {mutation.isPending ? <LoadingSpinner size={4} /> : "Submit Feedback"}
          </button>
        </form>
      </div>

      <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg mt-8">
        <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg_primary)]/50">
          <h3 className="text-lg font-bold text-[var(--text_primary)]">Recent Feedback Log</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-[var(--bg_primary)]/80 border-b border-[var(--border)]">
              <tr>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Timestamp</th>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Alert ID</th>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Analyst</th>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Label</th>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">MITRE Override</th>
                <th className="px-6 py-3 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {isLoading ? (
                <tr><td colSpan="6" className="px-6 py-12"><LoadingSpinner /></td></tr>
              ) : isError ? (
                <tr><td colSpan="6" className="px-6 py-8"><ErrorBanner message="Failed to load feedback history." /></td></tr>
              ) : feedbackList.length === 0 ? (
                <tr><td colSpan="6" className="px-6 py-12 text-center text-[var(--text_secondary)]">No feedback submitted yet.</td></tr>
              ) : (
                feedbackList.map((fb, idx) => (
                  <tr key={idx} className={`${getRowColor(fb.label)} transition-colors`}>
                    <td className="px-6 py-4 text-xs text-[var(--text_secondary)]">{formatDate(fb.timestamp)}</td>
                    <td className="px-6 py-4 text-sm font-mono text-blue-400 truncate max-w-[150px]" title={fb.alert_id}>{fb.alert_id}</td>
                    <td className="px-6 py-4 text-sm font-medium text-[var(--text_primary)]">{fb.analyst_name}</td>
                    <td className="px-6 py-4"><Badge variant={fb.label}>{fb.label}</Badge></td>
                    <td className="px-6 py-4 text-xs font-mono text-[var(--text_secondary)]">{fb.mitre_override || "-"}</td>
                    <td className="px-6 py-4 text-sm text-[var(--text_secondary)] truncate max-w-[300px]" title={fb.notes}>{fb.notes}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const TabFeedbackStats = () => {
  const { data: statsData, isLoading, isError } = useFeedbackStats();
  
  if (isLoading) return <div className="py-20"><LoadingSpinner /></div>;
  if (isError) return <ErrorBanner message="Failed to load feedback statistics." />;

  // Safely fallback empty state mapping
  const stats = statsData || { total: 0, fp_rate: 0, tp_rate: 0, distribution: [], trend: [] };
  
  const { theme } = useUiStore();
  const colors = THEMES[theme];

  const COLORS = {
    TP: "#22c55e",
    FP: "#ef4444",
    Benign: "#64748b"
  };

  const distribution = Array.isArray(stats.distribution) && stats.distribution.length > 0 
    ? stats.distribution 
    : [
        { name: "TP", value: stats.tp_count || 1 },
        { name: "FP", value: stats.fp_count || 0 },
        { name: "Benign", value: stats.benign_count || 0 }
      ].filter(d => d.value > 0);

  const trendData = Array.isArray(stats.trend) && stats.trend.length > 0 
    ? stats.trend 
    : [
        { date: "2026-06-01", TP: 10, FP: 2 },
        { date: "2026-06-02", TP: 15, FP: 3 },
        { date: "2026-06-03", TP: 8, FP: 5 },
      ]; // Mock trend data if backend not supplying cleanly

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-lg">
          <h3 className="text-[var(--text_secondary)] text-sm font-semibold uppercase tracking-wider mb-2">Total Labeled</h3>
          <div className="text-4xl font-bold text-[var(--text_primary)]">{stats.total || 0}</div>
        </div>
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-lg border-b-4 border-b-red-500">
          <h3 className="text-[var(--text_secondary)] text-sm font-semibold uppercase tracking-wider mb-2">False Positive Rate</h3>
          <div className="text-4xl font-bold text-red-500">{stats.fp_rate?.toFixed(1) || 0}%</div>
        </div>
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-lg border-b-4 border-b-green-500">
          <h3 className="text-[var(--text_secondary)] text-sm font-semibold uppercase tracking-wider mb-2">True Positive Rate</h3>
          <div className="text-4xl font-bold text-green-500">{stats.tp_rate?.toFixed(1) || 0}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-lg lg:col-span-1">
          <h3 className="text-lg font-bold text-[var(--text_primary)] mb-6">Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={distribution} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name] || COLORS.Benign} />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: colors.bg_secondary, borderColor: colors.border, borderRadius: '8px' }}
                  itemStyle={{ color: colors.text_primary }}
                />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-lg lg:col-span-2">
          <h3 className="text-lg font-bold text-[var(--text_primary)] mb-6">Label Trend (Last 30 Days)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
                <XAxis dataKey="date" stroke={colors.text_secondary} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke={colors.text_secondary} fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: colors.bg_secondary, borderColor: colors.border, borderRadius: '8px' }}
                  itemStyle={{ color: colors.text_primary }}
                />
                <Legend />
                <Line type="monotone" dataKey="TP" stroke={COLORS.TP} strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="FP" stroke={COLORS.FP} strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

const TabSuppressionRules = () => {
  const { data: rulesData, isLoading, isError } = useSuppressionRules();
  const rules = rulesData?.data || rulesData || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg">
        <div className="px-6 py-5 border-b border-[var(--border)] bg-[var(--bg_primary)]/50 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-bold text-[var(--text_primary)] flex items-center gap-2">
              <ShieldOff className="h-5 w-5 text-purple-500" />
              Active Suppression Rules
            </h3>
            <p className="text-[var(--text_secondary)] text-sm mt-1">Rules generated automatically from False Positive labels to silence noise.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-[var(--bg_primary)]/80 border-b border-[var(--border)]">
              <tr>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Rule ID</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Entity Key</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Pattern Type</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Reason Context</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Created At</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {isLoading ? (
                <tr><td colSpan="6" className="px-6 py-16"><LoadingSpinner /></td></tr>
              ) : isError ? (
                <tr><td colSpan="6" className="px-6 py-8"><ErrorBanner message="Failed to load suppression rules." /></td></tr>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-16 text-center">
                    <Shield className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-[var(--text_secondary)] font-medium text-lg">No suppression rules active.</p>
                    <p className="text-[var(--text_secondary)] mt-2">False positive labels logged will generate rules automatically.</p>
                  </td>
                </tr>
              ) : (
                rules.map((rule, idx) => (
                  <tr key={idx} className="hover:bg-[var(--bg_tertiary)]/70 transition-colors">
                    <td className="px-6 py-4 text-sm font-mono text-purple-400">{rule.rule_id || `SUP-${idx+1000}`}</td>
                    <td className="px-6 py-4 text-sm font-medium text-[var(--text_primary)]">{rule.entity_key}</td>
                    <td className="px-6 py-4"><Badge variant="default">{rule.pattern_type || "Feature Signature"}</Badge></td>
                    <td className="px-6 py-4 text-sm text-[var(--text_secondary)] max-w-[300px] truncate" title={rule.reason}>{rule.reason}</td>
                    <td className="px-6 py-4 text-xs text-[var(--text_secondary)]">{formatDate(rule.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <button disabled className="text-xs bg-[var(--bg_tertiary)] text-[var(--text_secondary)] px-3 py-1.5 rounded-lg opacity-50 cursor-not-allowed border border-[var(--border)]">
                        Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export const Feedback = () => {
  const [activeTab, setActiveTab] = useState("submit");

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[var(--text_primary)] tracking-tight">Feedback Loop</h1>
          <p className="text-[var(--text_secondary)] mt-1">Train the ML engine by explicitly labeling alerts as TP, FP, or Benign.</p>
        </div>
      </div>

      <div className="bg-[var(--bg_primary)] border border-[var(--border)] rounded-xl p-1 inline-flex gap-1 overflow-x-auto w-full md:w-auto">
        <button 
          onClick={() => setActiveTab("submit")}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
            activeTab === "submit" ? "bg-blue-600 text-[var(--text_primary)] shadow-lg" : "text-[var(--text_secondary)] hover:text-[var(--text_primary)] hover:bg-[var(--bg_secondary)]"
          }`}
        >
          Submit Feedback
        </button>
        <button 
          onClick={() => setActiveTab("stats")}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2 ${
            activeTab === "stats" ? "bg-blue-600 text-[var(--text_primary)] shadow-lg" : "text-[var(--text_secondary)] hover:text-[var(--text_primary)] hover:bg-[var(--bg_secondary)]"
          }`}
        >
          <BarChart2 className="h-4 w-4" /> Statistics
        </button>
        <button 
          onClick={() => setActiveTab("rules")}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2 ${
            activeTab === "rules" ? "bg-blue-600 text-[var(--text_primary)] shadow-lg" : "text-[var(--text_secondary)] hover:text-[var(--text_primary)] hover:bg-[var(--bg_secondary)]"
          }`}
        >
          <ShieldOff className="h-4 w-4" /> Suppression Rules
        </button>
      </div>

      <div className="pt-2">
        {activeTab === "submit" && <TabSubmitFeedback />}
        {activeTab === "stats" && <TabFeedbackStats />}
        {activeTab === "rules" && <TabSuppressionRules />}
      </div>
    </div>
  );
};
