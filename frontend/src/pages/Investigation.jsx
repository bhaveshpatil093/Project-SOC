import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Bot, Send, Trash2, ChevronRight, Activity, Zap, FileText, Share2, Search, ShieldAlert, CheckCircle, AlertTriangle, CheckSquare, Square } from 'lucide-react';

import { getAlert } from '../api/alerts';
import { sendMessage, clearConversation, getSlmStatus } from '../api/slm';
import { useAlertStore } from '../store/alertStore';
import { ThreatGauge } from '../components/common/ThreatGauge';
import { MitrePanel } from '../components/common/MitrePanel';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const Investigation = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const alertIdParam = searchParams.get('alert_id');
    
    const [conversationId, setConversationId] = useState(null);
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Welcome! I'm your SOC investigation assistant powered by Phi-3-mini. How can I help you analyze today's anomalies?" }
    ]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [searchId, setSearchId] = useState('');
    
    const messagesEndRef = useRef(null);
    const alerts = useAlertStore((state) => state.alerts);
    const recentAlerts = alerts.filter(a => a.status === 'open').slice(0, 10);
    
    const { data: alertContext, isLoading: isAlertLoading } = useQuery({
        queryKey: ['alert', alertIdParam],
        queryFn: () => getAlert(alertIdParam),
        enabled: !!alertIdParam
    });
    
    const { data: slmStatus } = useQuery({
        queryKey: ['slmStatus'],
        queryFn: getSlmStatus
    });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSend = async (customMessage = null) => {
        const text = customMessage || input;
        if (!text.trim() || isTyping) return;
        
        if (!customMessage) setInput('');
        
        const newMsg = { role: 'user', content: text };
        setMessages(prev => [...prev, newMsg]);
        setIsTyping(true);
        
        try {
            const resp = await sendMessage(text, alertIdParam, conversationId);
            if (!conversationId) {
                setConversationId(resp.conversation_id);
            }
            
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: resp.message.content,
                sources: resp.sources,
                tools: resp.tools_used,
                parsed: resp.parsed_response
            }]);
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "I'm sorry, I encountered an error communicating with the SLM Engine."
            }]);
        } finally {
            setIsTyping(false);
        }
    };
    
    const handleNewChat = async () => {
        if (conversationId) {
            try {
                await clearConversation(conversationId);
            } catch (e) {}
        }
        setConversationId(null);
        setMessages([{ role: 'assistant', content: "New conversation started. How can I assist you?" }]);
    };

    return (
        <div className="flex h-[calc(100vh-80px)] overflow-hidden gap-6 p-6 bg-slate-900">
            {/* Left Panel: Alert Context */}
            <div className="w-2/5 flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="w-5 h-5 text-blue-500" /> Alert Context
                </h2>
                
                {!alertIdParam ? (
                    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                        <p className="text-slate-400 mb-4 text-sm">Enter an Alert ID or select from recent incidents to bind explicit context onto the AI logic map.</p>
                        <div className="flex gap-2 mb-6">
                            <input
                                type="text"
                                placeholder="Enter Alert ID..."
                                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                value={searchId}
                                onChange={(e) => setSearchId(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && setSearchParams({ alert_id: searchId })}
                            />
                            <button 
                                onClick={() => setSearchParams({ alert_id: searchId })}
                                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg"
                            >
                                <Search className="w-4 h-4" />
                            </button>
                        </div>
                        
                        <h3 className="text-sm font-semibold text-slate-300 mb-3">Recent Open Alerts</h3>
                        <div className="space-y-2">
                            {recentAlerts.map(a => (
                                <button
                                    key={a.id}
                                    onClick={() => setSearchParams({ alert_id: a.id })}
                                    className="w-full text-left bg-slate-900/50 hover:bg-slate-700 p-3 rounded-lg border border-slate-700 transition-colors flex justify-between items-center group"
                                >
                                    <span className="text-sm font-medium text-slate-200 group-hover:text-blue-400 truncate">{a.entity_key}</span>
                                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${a.threat_level === 'critical' ? 'bg-red-500/20 text-red-500' : 'bg-orange-500/20 text-orange-500'}`}>
                                        {Math.round(a.threat_score * 100)}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : isAlertLoading ? (
                    <div className="flex justify-center py-10"><LoadingSpinner size="lg" /></div>
                ) : alertContext ? (
                    <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 flex flex-col items-center">
                            <ThreatGauge score={alertContext.threat_score * 100} size={120} />
                            <h3 className="text-lg font-bold text-white mt-4">{alertContext.entity_key}</h3>
                            <p className="text-sm text-slate-400">{new Date(alertContext.timestamp).toLocaleString()}</p>
                            
                            <Link to={`/alerts/${alertContext.id}`} className="mt-4 text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center gap-1">
                                View Full Alert <ChevronRight className="w-4 h-4" />
                            </Link>
                        </div>
                        
                        <MitrePanel tactics={alertContext.mitre_tactics} techniques={alertContext.mitre_techniques} />
                        
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Top Triggered Rules</h3>
                            <ul className="list-disc pl-5 space-y-2 text-sm text-slate-400">
                                {alertContext.triggered_rules?.slice(0,3).map((r, i) => (
                                    <li key={i}>{r}</li>
                                )) || <li>{alertContext.top_rule}</li>}
                            </ul>
                        </div>
                        
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Top SHAP Features</h3>
                            <div className="space-y-3">
                                {Object.entries(alertContext.shap_values || {}).slice(0, 3).map(([key, val], idx) => {
                                    const pct = Math.min(Math.abs(val) * 100, 100);
                                    return (
                                        <div key={idx} className="flex flex-col gap-1">
                                            <div className="flex justify-between text-xs">
                                                <span className="text-slate-300">{key}</span>
                                                <span className="text-slate-400">{val.toFixed(3)}</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
                                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="bg-slate-800 rounded-xl p-6 border border-red-900/50">
                        <p className="text-red-400 text-sm">Alert not found.</p>
                        <button onClick={() => setSearchParams({})} className="mt-4 text-sm text-blue-400">Clear Selection</button>
                    </div>
                )}
            </div>

            {/* Right Panel: Chat Interface */}
            <div className="w-3/5 bg-slate-800 rounded-xl border border-slate-700 flex flex-col overflow-hidden">
                <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
                    <div className="flex items-center gap-3">
                        <div className="bg-blue-500/20 p-2 rounded-lg">
                            <Bot className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">SOC AI Assistant</h2>
                            <p className="text-xs text-slate-400 flex items-center gap-1">
                                Powered by {slmStatus?.model_name || 'Phi-3-mini'} 
                                {slmStatus?.model_loaded ? <span className="w-2 h-2 rounded-full bg-green-500 inline-block ml-1" /> : null}
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={handleNewChat}
                        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-700"
                    >
                        <Trash2 className="w-4 h-4" /> New Chat
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-slate-900/20">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center mr-3 shrink-0">
                                    <Bot className="w-4 h-4 text-blue-400" />
                                </div>
                            )}
                            <div className={`max-w-[85%] rounded-2xl px-5 py-3 shadow-sm ${
                                msg.role === 'user' 
                                    ? 'bg-blue-600 text-white rounded-tr-sm' 
                                    : 'bg-slate-700 text-slate-200 rounded-tl-sm'
                            }`}>
                                {msg.role === 'user' ? (
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                ) : (
                                    msg.parsed ? (
                                        <div className="flex flex-col gap-4 text-sm">
                                            {msg.parsed.verdict && msg.parsed.verdict !== "UNKNOWN" && (
                                                <div className="flex gap-2 items-center">
                                                    {msg.parsed.verdict === "TRUE_POSITIVE" ? (
                                                        <span className="flex items-center gap-1 bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-1 rounded-md font-bold text-[10px] uppercase"><ShieldAlert className="w-3 h-3"/> TRUE POSITIVE</span>
                                                    ) : (
                                                        <span className="flex items-center gap-1 bg-green-500/20 text-green-400 border border-green-500/30 px-2 py-1 rounded-md font-bold text-[10px] uppercase"><CheckCircle className="w-3 h-3"/> FALSE POSITIVE</span>
                                                    )}
                                                    {msg.parsed.urgency && (
                                                        <span className={`px-2 py-1 rounded-md font-bold text-[10px] uppercase border ${msg.parsed.urgency === 'IMMEDIATE' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 'bg-slate-700 text-slate-300 border-slate-600'}`}>{msg.parsed.urgency}</span>
                                                    )}
                                                </div>
                                            )}
                                            
                                            {msg.parsed.summary && (
                                                <blockquote className="border-l-4 border-blue-500 pl-3 italic text-slate-200 bg-slate-800/50 py-2 pr-2 rounded-r-md">
                                                    {msg.parsed.summary}
                                                </blockquote>
                                            )}
                                            
                                            {msg.parsed.evidence_points && msg.parsed.evidence_points.length > 0 && (
                                                <div>
                                                    <h4 className="font-semibold text-white mb-2 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4 text-yellow-500"/> Evidence</h4>
                                                    <ul className="space-y-1.5">
                                                        {msg.parsed.evidence_points.map((pt, i) => (
                                                            <li key={i} className="flex gap-2 items-start text-slate-300">
                                                                <span className="text-yellow-500 mt-0.5">•</span>
                                                                <span>{pt}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            
                                            {msg.parsed.action_items && msg.parsed.action_items.length > 0 && (
                                                <div>
                                                    <h4 className="font-semibold text-white mb-2 flex items-center gap-1.5"><CheckSquare className="w-4 h-4 text-green-400"/> Action Items</h4>
                                                    <ul className="space-y-2">
                                                        {msg.parsed.action_items.map((act, i) => (
                                                            <li key={i} className="flex gap-2 items-start text-slate-300 bg-slate-800/40 p-2 rounded border border-slate-700/50">
                                                                <Square className="w-4 h-4 text-slate-500 mt-0.5 shrink-0"/>
                                                                <span>{act}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            
                                            {msg.parsed.mitre_techniques && msg.parsed.mitre_techniques.length > 0 && (
                                                <div className="flex flex-wrap gap-2 mt-2">
                                                    {msg.parsed.mitre_techniques.map((t, i) => (
                                                        <span key={i} className="text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-1 rounded cursor-pointer hover:bg-purple-500/30">
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                            
                                            {!msg.parsed.summary && !msg.parsed.evidence_points?.length && !msg.parsed.action_items?.length && (
                                                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                            )}
                                        </div>
                                    ) : (
                                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    )
                                )}
                                
                                {msg.tools && msg.tools.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-slate-600/50 flex flex-wrap gap-2">
                                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold w-full">Tools Executed:</span>
                                        {msg.tools.map(t => (
                                            <span key={t} className="text-[10px] bg-slate-800 text-blue-300 px-2 py-0.5 rounded border border-slate-600">
                                                {t}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {isTyping && (
                        <div className="flex justify-start">
                            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center mr-3 shrink-0">
                                <Bot className="w-4 h-4 text-blue-400" />
                            </div>
                            <div className="bg-slate-700 text-slate-200 rounded-2xl rounded-tl-sm px-5 py-4 flex gap-1 items-center">
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                
                <div className="p-4 bg-slate-800 border-t border-slate-700">
                    <div className="flex flex-wrap gap-2 mb-3">
                        <button onClick={() => handleSend(`Explain alert ${alertIdParam || 'this'} in detail`)} className="text-xs bg-slate-900 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full hover:bg-slate-700 hover:text-white flex items-center gap-1 transition-colors">
                            <FileText className="w-3 h-3" /> Explain this Alert
                        </button>
                        <button onClick={() => handleSend(`Show me the raw logs for this entity`)} className="text-xs bg-slate-900 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full hover:bg-slate-700 hover:text-white flex items-center gap-1 transition-colors">
                            <Activity className="w-3 h-3" /> Get Raw Logs
                        </button>
                        <button onClick={() => handleSend(`Find similar historical incidents`)} className="text-xs bg-slate-900 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full hover:bg-slate-700 hover:text-white flex items-center gap-1 transition-colors">
                            <Share2 className="w-3 h-3" /> Similar Incidents
                        </button>
                        <button onClick={() => handleSend(`What actions should I take for this alert?`)} className="text-xs bg-slate-900 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full hover:bg-slate-700 hover:text-white flex items-center gap-1 transition-colors">
                            <Zap className="w-3 h-3" /> Recommend Actions
                        </button>
                    </div>
                    
                    <div className="relative">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSend();
                                }
                            }}
                            placeholder="Ask Phi-3 about alerts, logs, or mitigations..."
                            className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-4 pr-12 py-3 text-sm text-white focus:outline-none focus:border-blue-500 resize-none custom-scrollbar"
                            rows={2}
                        />
                        <button
                            onClick={() => handleSend()}
                            disabled={!input.trim() || isTyping}
                            className="absolute right-3 bottom-3 p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
