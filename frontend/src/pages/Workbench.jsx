import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAlerts, useUpdateAlertStatus } from '../hooks/useAlerts';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { useFeedbackMutation } from '../api/feedback';
import { Badge } from '../components/common/Badge';
import { ThreatGauge } from '../components/common/ThreatGauge';
import { 
    Terminal, Clock, Server, Shield, HelpCircle, AlertTriangle, 
    CheckCircle, XCircle, ArrowRight, X, User, Activity, ToggleLeft, ToggleRight, FileText
} from 'lucide-react';
import { formatDate } from '../utils/formatters';

const Workbench = () => {
    const navigate = useNavigate();
    const { data: alertsData, isLoading } = useAlerts({ status: 'open', limit: 100 });
    const updateStatusMutation = useUpdateAlertStatus();
    const feedbackMutation = useFeedbackMutation();

    const [showUncertainOnly, setShowUncertainOnly] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [metrics, setMetrics] = useState({
        triagedToday: 0,
        totalTime: 0,
        tpCount: 0
    });
    const [startTime, setStartTime] = useState(Date.now());

    // Extract raw alerts
    const rawAlerts = useMemo(() => {
        let items = alertsData?.data || alertsData?.alerts || [];
        // Sort by uncertainty if available, then by threat score
        return items.sort((a, b) => {
            const aUncertain = a.uncertainty_score || 0;
            const bUncertain = b.uncertainty_score || 0;
            if (bUncertain !== aUncertain) return bUncertain - aUncertain;
            return b.threat_score - a.threat_score;
        });
    }, [alertsData]);

    const alerts = useMemo(() => {
        if (showUncertainOnly) {
            return rawAlerts.filter(a => a.uncertainty_score && a.uncertainty_score > 0.35);
        }
        return rawAlerts;
    }, [rawAlerts, showUncertainOnly]);

    const selectedAlert = alerts[selectedIndex];

    useEffect(() => {
        if (selectedIndex >= alerts.length && alerts.length > 0) {
            setSelectedIndex(0);
        }
        setStartTime(Date.now());
    }, [selectedIndex, alerts]);

    const handleTriageAction = (isTP, alert) => {
        if (!alert) return;
        const triageTime = Math.round((Date.now() - startTime) / 1000);
        
        feedbackMutation.mutate({
            alertId: alert._id || alert.id,
            isMalicious: isTP,
            analystNotes: `Triaged via Workbench (${triageTime}s)`
        });
        
        updateStatusMutation.mutate({
            id: alert._id || alert.id,
            status: 'closed'
        });

        setMetrics(prev => ({
            triagedToday: prev.triagedToday + 1,
            totalTime: prev.totalTime + triageTime,
            tpCount: prev.tpCount + (isTP ? 1 : 0)
        }));

        if (selectedIndex < alerts.length - 1) {
            setSelectedIndex(prev => prev + 1);
        }
    };

    useKeyboardShortcuts({
        't': () => handleTriageAction(true, selectedAlert),
        'f': () => handleTriageAction(false, selectedAlert),
        'b': () => handleTriageAction(false, selectedAlert),
        'i': () => { if (selectedAlert) navigate(`/investigation?alert_id=${selectedAlert._id || selectedAlert.id}`); },
        'e': () => { if (selectedAlert) updateStatusMutation.mutate({ id: selectedAlert._id || selectedAlert.id, status: 'in_progress' }); },
        'n': () => setSelectedIndex(prev => Math.min(prev + 1, alerts.length - 1)),
        'p': () => setSelectedIndex(prev => Math.max(prev - 1, 0)),
        's': () => { if (selectedAlert) navigate(`/investigation?alert_id=${selectedAlert._id || selectedAlert.id}`); },
        'c': () => { if (selectedAlert) updateStatusMutation.mutate({ id: selectedAlert._id || selectedAlert.id, status: 'closed' }); },
        '?': () => alert("Shortcuts:\\n[T] True Positive\\n[F]/[B] False Positive / Benign\\n[I]/[S] Investigate in SLM\\n[E] Escalate / In Progress\\n[N] Next Alert\\n[P] Previous Alert\\n[C] Close Alert")
    });

    const avgTime = metrics.triagedToday > 0 ? Math.round(metrics.totalTime / metrics.triagedToday) : 0;
    const tpRate = metrics.triagedToday > 0 ? Math.round((metrics.tpCount / metrics.triagedToday) * 100) : 0;

    return (
        <div className="h-[calc(100vh-4rem)] flex flex-col overflow-hidden bg-[var(--bg_primary)]">
            <div className="flex-1 flex overflow-hidden">
                {/* LEFT PANEL: Queue (30%) */}
                <div className="w-[30%] min-w-[350px] border-r border-[var(--border)] bg-[var(--bg_secondary)] flex flex-col">
                    <div className="p-4 border-b border-[var(--border)] flex flex-col gap-3">
                        <div className="flex justify-between items-center">
                            <h2 className="text-lg font-bold text-[var(--text_primary)]">Triage Queue</h2>
                            <Badge variant="info">{alerts.length} pending</Badge>
                        </div>
                        <button 
                            onClick={() => setShowUncertainOnly(!showUncertainOnly)}
                            className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg border transition-colors ${showUncertainOnly ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-400' : 'bg-[var(--bg_primary)] border-[var(--border)] text-[var(--text_secondary)]'}`}
                        >
                            {showUncertainOnly ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                            Show only uncertain alerts
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 space-y-2">
                        {isLoading ? (
                            <div className="p-4 text-center text-[var(--text_secondary)]">Loading queue...</div>
                        ) : alerts.length === 0 ? (
                            <div className="p-8 text-center text-[var(--text_secondary)] border border-dashed border-[var(--border)] rounded-lg m-2">
                                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500/50" />
                                <p>Queue is empty. Great job!</p>
                            </div>
                        ) : (
                            alerts.map((alert, idx) => {
                                const isSelected = idx === selectedIndex;
                                const levelColor = 
                                    alert.threat_level === 'critical' ? 'border-l-red-500' :
                                    alert.threat_level === 'high' ? 'border-l-orange-500' :
                                    alert.threat_level === 'medium' ? 'border-l-yellow-500' : 'border-l-green-500';

                                return (
                                    <div 
                                        key={alert._id || alert.id}
                                        onClick={() => setSelectedIndex(idx)}
                                        className={`cursor-pointer p-3 rounded-lg border-l-4 border-y border-r transition-all ${levelColor} ${isSelected ? 'bg-[var(--bg_tertiary)] border-y-blue-500/50 border-r-blue-500/50 shadow-md scale-[1.02]' : 'bg-[var(--bg_primary)] border-y-[var(--border)] border-r-[var(--border)] hover:bg-[var(--bg_tertiary)]'}`}
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="font-mono text-sm font-bold text-[var(--text_primary)] truncate pr-2">{alert.entity_key}</span>
                                            <span className={`text-xs font-bold ${alert.threat_score > 0.8 ? 'text-red-400' : 'text-orange-400'}`}>{(alert.threat_score * 100).toFixed(0)}</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs text-[var(--text_secondary)]">
                                            <div className="flex items-center gap-1">
                                                <Terminal className="h-3 w-3" />
                                                <span className="truncate max-w-[120px]">{alert.log_type}</span>
                                            </div>
                                            <span>{new Date(alert.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* RIGHT PANEL: Active Alert Detail (70%) */}
                <div className="flex-1 flex flex-col bg-[var(--bg_primary)] overflow-y-auto">
                    {selectedAlert ? (
                        <div className="p-6 md:p-8 max-w-5xl mx-auto w-full flex-1 flex flex-col">
                            {/* Header */}
                            <div className="flex items-start gap-6 bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm mb-6">
                                <ThreatGauge score={selectedAlert.threat_score * 100} size={100} showLabel={false} />
                                <div className="flex-1">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h1 className="text-2xl font-bold font-mono text-[var(--text_primary)] mb-2">{selectedAlert.entity_key}</h1>
                                            <div className="flex gap-4 text-sm text-[var(--text_secondary)]">
                                                <span className="flex items-center gap-1"><Server className="h-4 w-4"/> {selectedAlert.host_id || 'Unknown'}</span>
                                                <span className="flex items-center gap-1"><User className="h-4 w-4"/> {selectedAlert.user_name || 'Unknown'}</span>
                                            </div>
                                        </div>
                                        <Badge variant={selectedAlert.threat_level} className="text-sm px-3 py-1 uppercase">{selectedAlert.threat_level}</Badge>
                                    </div>
                                    
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {selectedAlert.mitre_tactics?.map(t => (
                                            <span key={t} className="px-2 py-1 bg-red-900/20 text-red-400 border border-red-900/50 rounded text-xs font-mono">{t}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Middle Content */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6 flex-1">
                                {/* Details & Explanation */}
                                <div className="lg:col-span-2 flex flex-col gap-6">
                                    <div className="bg-[var(--bg_secondary)] p-6 rounded-xl border border-[var(--border)] flex-1">
                                        <h3 className="text-sm font-bold text-[var(--text_secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <FileText className="h-4 w-4" /> AI Explanation
                                        </h3>
                                        <div className="text-[var(--text_primary)] text-sm leading-relaxed bg-[var(--bg_primary)] p-4 rounded-lg border border-[var(--border)] h-full max-h-[300px] overflow-y-auto">
                                            {selectedAlert.human_explanation || "No explanation available. Review raw features."}
                                        </div>
                                    </div>
                                </div>

                                {/* Features & Counterfactuals */}
                                <div className="flex flex-col gap-6">
                                    {selectedAlert.consensus_level && (
                                        <div className="bg-[var(--bg_secondary)] p-4 rounded-xl border border-[var(--border)]">
                                            <h3 className="text-sm font-bold text-[var(--text_secondary)] uppercase tracking-wider mb-3">Model Consensus</h3>
                                            <Badge variant={
                                                selectedAlert.consensus_level === 'strong' ? 'critical' :
                                                selectedAlert.consensus_level === 'split' ? 'warning' : 'info'
                                            } className="w-full justify-center py-2 text-sm">
                                                {selectedAlert.consensus_level.toUpperCase()}
                                            </Badge>
                                        </div>
                                    )}

                                    <div className="bg-[var(--bg_secondary)] p-4 rounded-xl border border-[var(--border)] flex-1">
                                        <h3 className="text-sm font-bold text-[var(--text_secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <Activity className="h-4 w-4" /> Key Drivers
                                        </h3>
                                        <div className="space-y-3">
                                            {selectedAlert.top_features?.slice(0, 5).map((f, i) => (
                                                <div key={i} className="flex justify-between items-center text-sm p-2 bg-[var(--bg_primary)] rounded border border-[var(--border)]">
                                                    <span className="font-mono text-[var(--text_secondary)] truncate max-w-[150px]">{typeof f === 'string' ? f : f.feature}</span>
                                                    <span className="text-red-400 font-mono">{(typeof f === 'string' ? 1 : f.value).toFixed(2)}</span>
                                                </div>
                                            ))}
                                            
                                            {/* Simulated Counterfactual Hint */}
                                            {selectedAlert.top_features?.length > 0 && (
                                                <div className="mt-4 p-3 bg-green-900/10 border border-green-500/30 rounded-lg">
                                                    <p className="text-xs text-green-400">
                                                        <span className="font-bold">Hint:</span> Would likely be scored Benign if <span className="font-mono">{typeof selectedAlert.top_features[0] === 'string' ? selectedAlert.top_features[0] : selectedAlert.top_features[0].feature}</span> decreased by 30%.
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Quick Action Bar */}
                            <div className="bg-[var(--bg_secondary)] p-4 rounded-xl border border-[var(--border)] flex flex-wrap gap-4 items-center justify-between mt-auto shadow-lg">
                                <div className="flex gap-2">
                                    <button onClick={() => handleTriageAction(true, selectedAlert)} className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors">
                                        <AlertTriangle className="h-4 w-4" />
                                        True Positive
                                        <kbd className="ml-2 px-1.5 py-0.5 bg-red-800 rounded text-xs">T</kbd>
                                    </button>
                                    <button onClick={() => handleTriageAction(false, selectedAlert)} className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors">
                                        <CheckCircle className="h-4 w-4" />
                                        False Positive
                                        <kbd className="ml-2 px-1.5 py-0.5 bg-green-800 rounded text-xs">F</kbd>
                                    </button>
                                </div>

                                <div className="flex gap-2 border-l border-[var(--border)] pl-4">
                                    <button onClick={() => navigate(`/investigation?alert_id=${selectedAlert._id || selectedAlert.id}`)} className="flex items-center gap-2 px-3 py-2 bg-[var(--bg_primary)] hover:bg-[var(--bg_tertiary)] border border-[var(--border)] text-[var(--text_primary)] rounded-lg text-sm transition-colors">
                                        Investigate
                                        <kbd className="ml-1 px-1.5 py-0.5 bg-[var(--bg_tertiary)] border border-[var(--border)] rounded text-xs text-[var(--text_secondary)]">I</kbd>
                                    </button>
                                    <button onClick={() => updateStatusMutation.mutate({ id: selectedAlert._id || selectedAlert.id, status: 'in_progress' })} className="flex items-center gap-2 px-3 py-2 bg-[var(--bg_primary)] hover:bg-[var(--bg_tertiary)] border border-[var(--border)] text-[var(--text_primary)] rounded-lg text-sm transition-colors">
                                        Escalate
                                        <kbd className="ml-1 px-1.5 py-0.5 bg-[var(--bg_tertiary)] border border-[var(--border)] rounded text-xs text-[var(--text_secondary)]">E</kbd>
                                    </button>
                                    <button onClick={() => setSelectedIndex(prev => Math.min(prev + 1, alerts.length - 1))} className="flex items-center gap-2 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/50 text-blue-400 rounded-lg text-sm transition-colors">
                                        Skip
                                        <kbd className="ml-1 px-1.5 py-0.5 bg-blue-900 rounded text-xs">N</kbd>
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-[var(--text_secondary)]">
                            Select an alert from the queue to begin triage.
                        </div>
                    )}
                </div>
            </div>

            {/* BOTTOM PANEL: Metrics Bar */}
            <div className="h-10 bg-[var(--bg_tertiary)] border-t border-[var(--border)] flex items-center px-6 justify-between text-xs text-[var(--text_secondary)] font-mono">
                <div className="flex items-center gap-6">
                    <span className="flex items-center gap-2">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        Triaged today: <strong className="text-[var(--text_primary)]">{metrics.triagedToday}</strong>
                    </span>
                    <span className="flex items-center gap-2">
                        <Clock className="h-3 w-3 text-blue-500" />
                        Avg triage time: <strong className="text-[var(--text_primary)]">{avgTime}s</strong>
                    </span>
                    <span className="flex items-center gap-2">
                        <Activity className="h-3 w-3 text-orange-500" />
                        TP Rate: <strong className="text-[var(--text_primary)]">{tpRate}%</strong>
                    </span>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-[var(--text_secondary)] opacity-50">Press '?' for all shortcuts</span>
                </div>
            </div>
        </div>
    );
};

export default Workbench;
