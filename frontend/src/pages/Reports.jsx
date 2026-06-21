import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getShiftReport } from '../api/reports';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { FileText, Copy, Download, ShieldAlert, Activity, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

const Reports = () => {
    const [activeTab, setActiveTab] = useState(8); // 8 = Shift, 24 = Daily, 168 = Weekly
    
    const { data: reportData, isLoading, isError } = useQuery({
        queryKey: ['shiftReport', activeTab],
        queryFn: () => getShiftReport(activeTab)
    });

    const report = reportData?.data;

    const copyForEmail = () => {
        if (!report) return;
        const text = `Shift Handover Report (${activeTab === 8 ? '8-Hour Shift' : activeTab === 24 ? 'Daily Summary' : 'Weekly Summary'})
Generated: ${new Date(report.generated_at).toLocaleString()}
Period: ${new Date(report.shift_start).toLocaleString()} to ${new Date(report.shift_end).toLocaleString()}

== METRICS ==
Total Alerts: ${report.total_alerts} (Critical: ${report.critical_alerts}, High: ${report.high_alerts})
Alerts Closed: ${report.alerts_closed} | Escalated: ${report.alerts_escalated}
New Incidents: ${report.new_incidents} | Active Incidents: ${report.active_incidents.length}

== NARRATIVE ==
${report.shift_narrative}

== KEY FINDINGS ==
${report.key_findings.map(f => `* ${f}`).join('\\n')}

== OPEN ITEMS / TODO ==
${report.open_items.map(o => `[ ] ${o}`).join('\\n')}

== RECOMMENDATIONS ==
${report.recommendations.map(r => `* ${r}`).join('\\n')}
`;
        navigator.clipboard.writeText(text);
        alert("Report copied to clipboard for email handover!");
    };

    const handlePrint = () => {
        window.print();
    };

    if (isLoading) return <LoadingSpinner />;
    if (isError || !report) return <ErrorBanner message="Failed to load report." />;

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-[var(--text_primary)] flex items-center gap-2">
                        <FileText className="h-6 w-6 text-blue-500" /> Automated SOC Reports
                    </h1>
                    <p className="text-[var(--text_secondary)] text-sm">System-generated narrative summaries for handover and review.</p>
                </div>
                
                <div className="flex gap-4 print:hidden">
                    <div className="bg-[var(--bg_secondary)] p-1 rounded-lg border border-[var(--border)] flex">
                        <button onClick={() => setActiveTab(8)} className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 8 ? 'bg-blue-600 text-white' : 'text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}>Shift (8h)</button>
                        <button onClick={() => setActiveTab(24)} className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 24 ? 'bg-blue-600 text-white' : 'text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}>Daily (24h)</button>
                        <button onClick={() => setActiveTab(168)} className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 168 ? 'bg-blue-600 text-white' : 'text-[var(--text_secondary)] hover:text-[var(--text_primary)]'}`}>Weekly (7d)</button>
                    </div>
                </div>
            </div>

            {/* Document Body */}
            <div className="bg-[var(--bg_primary)] border border-[var(--border)] rounded-xl shadow-lg print:border-none print:shadow-none bg-white print:bg-white text-black font-sans max-w-5xl mx-auto overflow-hidden">
                <div className="p-8 pb-4 border-b border-gray-200 flex justify-between items-end print:pb-8">
                    <div>
                        <h2 className="text-3xl font-black text-gray-900 tracking-tight uppercase">
                            {activeTab === 8 ? 'Shift Handover' : activeTab === 24 ? 'Daily Summary' : 'Weekly Summary'}
                        </h2>
                        <p className="text-gray-500 mt-1 font-mono text-sm">{report.report_id}</p>
                    </div>
                    <div className="text-right text-sm">
                        <p className="text-gray-600 font-bold mb-1">Period:</p>
                        <p className="text-gray-900 font-mono">{new Date(report.shift_start).toLocaleString()}</p>
                        <p className="text-gray-900 font-mono">to {new Date(report.shift_end).toLocaleString()}</p>
                    </div>
                </div>

                <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
                    
                    {/* Left Column: Metrics & Tables */}
                    <div className="md:col-span-1 space-y-6">
                        {/* Metrics Grid */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-gray-50 p-3 rounded border border-gray-200">
                                <p className="text-xs text-gray-500 uppercase font-bold mb-1">Total Alerts</p>
                                <p className="text-2xl font-black text-gray-900">{report.total_alerts}</p>
                            </div>
                            <div className="bg-red-50 p-3 rounded border border-red-100">
                                <p className="text-xs text-red-600 uppercase font-bold mb-1">Critical/High</p>
                                <p className="text-2xl font-black text-red-700">{report.critical_alerts + report.high_alerts}</p>
                            </div>
                            <div className="bg-green-50 p-3 rounded border border-green-100">
                                <p className="text-xs text-green-600 uppercase font-bold mb-1">Closed</p>
                                <p className="text-2xl font-black text-green-700">{report.alerts_closed}</p>
                            </div>
                            <div className="bg-orange-50 p-3 rounded border border-orange-100">
                                <p className="text-xs text-orange-600 uppercase font-bold mb-1">Escalated</p>
                                <p className="text-2xl font-black text-orange-700">{report.alerts_escalated}</p>
                            </div>
                            <div className="bg-purple-50 p-3 rounded border border-purple-100">
                                <p className="text-xs text-purple-600 uppercase font-bold mb-1">Active Incidents</p>
                                <p className="text-2xl font-black text-purple-700">{report.active_incidents.length}</p>
                            </div>
                            <div className="bg-blue-50 p-3 rounded border border-blue-100">
                                <p className="text-xs text-blue-600 uppercase font-bold mb-1">New Incidents</p>
                                <p className="text-2xl font-black text-blue-700">{report.new_incidents}</p>
                            </div>
                        </div>

                        {/* Top Threats */}
                        <div>
                            <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider border-b border-gray-300 pb-1 mb-2 flex items-center gap-1"><ShieldAlert className="w-3 h-3"/> Top Threats</h3>
                            <ul className="text-sm space-y-2">
                                {report.top_threats.map((t, i) => (
                                    <li key={i} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                                        <span className="font-medium text-blue-700 truncate w-32 cursor-pointer hover:underline" onClick={() => window.open(`/alerts/${t.id || t._id}`, '_blank')}>{t.entity_key}</span>
                                        <span className="bg-red-100 text-red-800 px-1.5 py-0.5 rounded text-xs font-bold">{Math.round(t.threat_score * 100)}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Right Column: Narrative */}
                    <div className="md:col-span-2 space-y-8">
                        <div>
                            <h3 className="text-lg font-black text-gray-900 border-b-2 border-black pb-1 mb-3 uppercase tracking-wider flex items-center gap-2">
                                <Activity className="w-5 h-5"/> Shift Narrative
                            </h3>
                            <p className="text-gray-800 leading-relaxed text-[15px] whitespace-pre-wrap">{report.shift_narrative}</p>
                        </div>

                        <div>
                            <h3 className="text-lg font-black text-gray-900 border-b-2 border-black pb-1 mb-3 uppercase tracking-wider flex items-center gap-2">
                                <AlertCircle className="w-5 h-5 text-red-600"/> Key Findings
                            </h3>
                            <ul className="list-disc pl-5 space-y-2 text-[15px] text-gray-800">
                                {report.key_findings.map((finding, idx) => (
                                    <li key={idx} className="pl-1">{finding}</li>
                                ))}
                            </ul>
                        </div>

                        <div>
                            <h3 className="text-lg font-black text-gray-900 border-b-2 border-black pb-1 mb-3 uppercase tracking-wider flex items-center gap-2">
                                <CheckCircle className="w-5 h-5 text-orange-500"/> Open Items / Handover
                            </h3>
                            <ul className="space-y-3">
                                {report.open_items.map((item, idx) => (
                                    <li key={idx} className="flex gap-3 items-start">
                                        <input type="checkbox" className="mt-1 shrink-0 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                                        <span className="text-[15px] text-gray-800 font-medium">{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div>
                            <h3 className="text-lg font-black text-gray-900 border-b-2 border-black pb-1 mb-3 uppercase tracking-wider flex items-center gap-2">
                                <Clock className="w-5 h-5 text-blue-600"/> Recommendations
                            </h3>
                            <ul className="list-disc pl-5 space-y-2 text-[15px] text-gray-800">
                                {report.recommendations.map((rec, idx) => (
                                    <li key={idx} className="pl-1 text-blue-900">{rec}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Print/Export Controls */}
                <div className="bg-gray-100 p-4 border-t border-gray-200 flex justify-end gap-4 print:hidden">
                    <button onClick={copyForEmail} className="flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 px-4 py-2 rounded shadow-sm text-sm font-bold transition-colors">
                        <Copy className="w-4 h-4" /> Copy for Email
                    </button>
                    <button onClick={handlePrint} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded shadow-sm text-sm font-bold transition-colors">
                        <Download className="w-4 h-4" /> Export PDF
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Reports;
