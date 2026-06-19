import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getIncidents, getIncidentDetail, updateIncidentStatus, escalateIncident } from '../api/incidents';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { AttackChain } from '../components/common/AttackChain';
import { formatDate } from '../utils/formatters';
import { ShieldAlert, Clock, Activity, Target, Network, Zap, ChevronRight, Filter } from 'lucide-react';

const IncidentListCard = ({ incident, isSelected, onClick }) => {
  const getBorderColor = (score) => {
    if (score >= 0.8) return 'border-l-red-500 bg-red-500/5';
    if (score >= 0.6) return 'border-l-orange-500 bg-orange-500/5';
    if (score >= 0.4) return 'border-l-yellow-500 bg-yellow-500/5';
    return 'border-l-blue-500 bg-blue-500/5';
  };

  const getStageBadge = (stage) => {
    const colors = {
      reconnaissance: 'bg-slate-700 text-slate-300',
      initial_access: 'bg-blue-900 text-blue-300',
      execution: 'bg-indigo-900 text-indigo-300',
      persistence: 'bg-purple-900 text-purple-300',
      lateral_movement: 'bg-orange-900 text-orange-300',
      exfiltration: 'bg-red-900 text-red-300',
      multi_stage: 'bg-gradient-to-r from-red-600 to-purple-600 text-white border-none',
      unknown: 'bg-slate-800 text-slate-400'
    };
    return colors[stage] || colors.unknown;
  };

  return (
    <div 
      onClick={onClick}
      className={`p-4 border-b border-slate-800 cursor-pointer transition-all border-l-4 ${getBorderColor(incident.incident_threat_score)} ${isSelected ? 'bg-slate-800/80 shadow-inner' : 'hover:bg-slate-800/40'}`}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-mono text-sm font-bold text-slate-200 break-all">{incident.entity_key}</h4>
        {incident.is_multi_stage && (
          <span className="text-[10px] font-black tracking-widest bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30 flex items-center gap-1 shrink-0 ml-2">
            <Zap className="h-3 w-3" /> MULTI-STAGE
          </span>
        )}
      </div>
      
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider ${getStageBadge(incident.attack_stage)}`}>
          {incident.attack_stage.replace('_', ' ')}
        </span>
        <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold ${incident.status === 'active' ? 'bg-blue-500/20 text-blue-400' : incident.status === 'escalated' ? 'bg-orange-500/20 text-orange-400' : 'bg-slate-500/20 text-slate-400'}`}>
          {incident.status}
        </span>
      </div>

      <div className="flex justify-between items-end">
        <div className="space-y-1">
          <div className="flex items-center text-xs text-slate-400 gap-2">
            <ShieldAlert className="h-3 w-3" /> {incident.alert_count} alerts
          </div>
          <div className="flex items-center text-xs text-slate-400 gap-2">
            <Clock className="h-3 w-3" /> {Math.round(incident.duration_seconds / 60)}m duration
          </div>
        </div>
        
        {/* Compact Gauge */}
        <div className="flex flex-col items-center">
          <div className="text-[10px] text-slate-500 mb-1">MAX THREAT</div>
          <div className="relative w-10 h-10 rounded-full border-4 border-slate-800 flex items-center justify-center bg-slate-900">
            <span className={`text-xs font-bold ${incident.max_threat_score >= 0.8 ? 'text-red-500' : incident.max_threat_score >= 0.6 ? 'text-orange-500' : 'text-blue-500'}`}>
              {(incident.max_threat_score * 100).toFixed(0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

const MitrePanel = ({ tactics, techniques }) => (
  <div className="bg-slate-900 rounded-xl p-4 border border-slate-700">
    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
      <Target className="h-4 w-4 text-blue-400" />
      MITRE ATT&CK Mapping
    </h3>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Observed Tactics</h4>
        <div className="flex flex-wrap gap-2">
          {tactics.map(t => (
            <span key={t} className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-600">
              {t}
            </span>
          ))}
          {tactics.length === 0 && <span className="text-xs text-slate-600">None mapped</span>}
        </div>
      </div>
      <div>
        <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Observed Techniques</h4>
        <div className="flex flex-wrap gap-2">
          {techniques.map(t => (
            <span key={t} className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-600 font-mono">
              {t}
            </span>
          ))}
          {techniques.length === 0 && <span className="text-xs text-slate-600">None mapped</span>}
        </div>
      </div>
    </div>
  </div>
);

const IncidentDetailPanel = ({ incidentId }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: detail, isLoading, isError } = useQuery({
    queryKey: ['incidentDetail', incidentId],
    queryFn: () => getIncidentDetail(incidentId),
    enabled: !!incidentId,
    refetchInterval: 10000
  });

  const statusMutation = useMutation({
    mutationFn: ({ status }) => updateIncidentStatus(incidentId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentDetail', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    }
  });

  const escalateMutation = useMutation({
    mutationFn: ({ to, reason }) => escalateIncident(incidentId, to, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentDetail', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    }
  });

  if (isLoading) return <div className="h-full flex items-center justify-center"><LoadingSpinner /></div>;
  if (isError || !detail) return <div className="p-8"><ErrorBanner message="Failed to load incident details." /></div>;

  const handleInvestigate = () => {
    navigate(`/investigation?incident_id=${incidentId}`);
  };

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      {/* Header */}
      <div className="p-6 border-b border-slate-800 bg-slate-900/50 flex-shrink-0">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-start gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className={`text-xs px-2 py-1 rounded font-bold uppercase tracking-wider ${
                detail.threat_level === 'critical' ? 'bg-red-500/20 text-red-500 border border-red-500/50' : 
                detail.threat_level === 'high' ? 'bg-orange-500/20 text-orange-500 border border-orange-500/50' : 
                'bg-blue-500/20 text-blue-500 border border-blue-500/50'
              }`}>
                {detail.threat_level}
              </span>
              <span className="text-slate-500 font-mono text-xs">{detail.incident_id}</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-mono break-all">{detail.entity_key}</h2>
            <p className="text-sm text-slate-400 mt-1">First seen: {formatDate(detail.started_at)}</p>
          </div>
          
          <div className="flex flex-col items-end gap-2 shrink-0">
            <div className="flex gap-2">
              <select 
                value={detail.status} 
                onChange={(e) => statusMutation.mutate({ status: e.target.value })}
                disabled={statusMutation.isPending}
                className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
              >
                <option value="active">Active</option>
                <option value="resolved">Resolved</option>
                <option value="escalated">Escalated</option>
              </select>
              
              {detail.status !== 'escalated' && (
                <button 
                  onClick={() => escalateMutation.mutate({ to: 'L3', reason: 'Manual escalation via UI' })}
                  disabled={escalateMutation.isPending}
                  className="bg-orange-600/20 hover:bg-orange-600/40 text-orange-400 border border-orange-500/50 text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
                >
                  Escalate
                </button>
              )}
            </div>
            <button 
              onClick={handleInvestigate}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors shadow-lg flex items-center justify-center gap-2"
            >
              <Network className="h-4 w-4" /> Investigate with AI
            </button>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-6 mt-6 pt-4 border-t border-slate-800/50">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <ShieldAlert className="h-4 w-4 text-slate-500" />
            <span className="font-bold text-white">{detail.alert_count}</span> Alerts
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Clock className="h-4 w-4 text-slate-500" />
            <span className="font-bold text-white">{Math.round(detail.duration_seconds / 60)}</span> Min Duration
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Activity className="h-4 w-4 text-slate-500" />
            <span className="font-bold text-white">{detail.log_types_involved.length}</span> Log Sources
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {/* Attack Chain */}
        <div>
          <h3 className="text-lg font-bold text-white mb-4">Attack Chain Visualization</h3>
          <div className="bg-slate-900 rounded-xl border border-slate-700 shadow-inner">
            <AttackChain chainData={detail.attack_chain} />
          </div>
        </div>

        {/* MITRE Panel */}
        <MitrePanel tactics={detail.mitre_tactics} techniques={detail.mitre_techniques} />

        {/* Timeline List */}
        <div>
          <h3 className="text-lg font-bold text-white mb-4">Event Timeline</h3>
          <div className="space-y-3">
            {detail.timeline.map((evt, idx) => (
              <div key={idx} className="flex gap-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800 hover:border-slate-700 transition-colors">
                <div className="shrink-0 pt-0.5">
                  <div className="w-2 h-2 mt-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
                </div>
                <div>
                  <p className="text-sm text-slate-300 mb-1">{evt.event}</p>
                  <div className="flex gap-4 text-xs text-slate-500">
                    <span>{formatDate(evt.timestamp)}</span>
                    <span className="font-mono text-blue-500/70">{evt.alert_id}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export const Incidents = () => {
  const [filters, setFilters] = useState({ status: 'active', threat_level: '', attack_stage: '' });
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);

  const { data: listData, isLoading, isError } = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => getIncidents({ ...filters, limit: 50 }),
    refetchInterval: 15000
  });

  const incidents = listData?.incidents || [];

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col md:flex-row gap-6">
      
      {/* Left Panel: Incident List */}
      <div className="w-full md:w-[35%] lg:w-[30%] flex flex-col bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden shrink-0">
        
        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
          <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
            <Network className="h-5 w-5 text-blue-500" />
            Correlated Incidents
          </h2>
          
          <div className="space-y-2">
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5">
              <Filter className="h-4 w-4 text-slate-500" />
              <select 
                value={filters.status}
                onChange={e => setFilters({...filters, status: e.target.value})}
                className="bg-transparent text-sm text-slate-300 focus:outline-none flex-1"
              >
                <option value="">All Statuses</option>
                <option value="active">Active Only</option>
                <option value="resolved">Resolved</option>
                <option value="escalated">Escalated</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-8 flex justify-center"><LoadingSpinner /></div>
          ) : isError ? (
            <div className="p-4"><ErrorBanner message="Failed to load incidents" /></div>
          ) : incidents.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No incidents match current filters.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/50">
              {incidents.map(inc => (
                <IncidentListCard 
                  key={inc.incident_id}
                  incident={inc}
                  isSelected={selectedIncidentId === inc.incident_id}
                  onClick={() => setSelectedIncidentId(inc.incident_id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel: Incident Details */}
      <div className="flex-1 bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden hidden md:block">
        {selectedIncidentId ? (
          <IncidentDetailPanel incidentId={selectedIncidentId} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Network className="h-16 w-16 text-slate-800 mb-4" />
            <p className="text-lg">Select an incident to view the full attack chain</p>
          </div>
        )}
      </div>

      {/* Mobile Drawer (visible only on small screens when selected) */}
      {selectedIncidentId && (
        <div className="md:hidden fixed inset-0 z-50 bg-slate-950 flex flex-col">
          <div className="p-4 border-b border-slate-800 flex items-center gap-4 bg-slate-900">
            <button onClick={() => setSelectedIncidentId(null)} className="p-2 text-slate-400 hover:text-white bg-slate-800 rounded-lg">
              <ChevronRight className="h-5 w-5 rotate-180" />
            </button>
            <h2 className="text-lg font-bold text-white">Incident Details</h2>
          </div>
          <div className="flex-1 overflow-hidden relative">
            <IncidentDetailPanel incidentId={selectedIncidentId} />
          </div>
        </div>
      )}
    </div>
  );
};
