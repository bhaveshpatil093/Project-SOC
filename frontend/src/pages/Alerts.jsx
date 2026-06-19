import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useAlerts, useTriggerScoring } from "../hooks/useAlerts";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Badge } from "../components/common/Badge";
import { formatDate } from "../utils/formatters";
import { Eye, MessageSquare, FilterX, Play, ArrowUpDown, CheckCircle, RefreshCw } from "lucide-react";

// Memoized row component to prevent re-renders
const AlertRow = React.memo(({ alert, index, page, pageSize, updateStatus, style }) => {
  const renderProgressBar = (score) => {
    const scoreNum = parseFloat(score || 0);
    const percentage = Math.min(Math.max(scoreNum * 100, 0), 100);
    
    let colorClass = "bg-green-500";
    if (percentage > 80) colorClass = "bg-red-500";
    else if (percentage > 60) colorClass = "bg-orange-500";
    else if (percentage > 30) colorClass = "bg-yellow-500";

    return (
      <div className="flex items-center gap-3">
        <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div className={`h-full ${colorClass}`} style={{ width: `${percentage}%` }} />
        </div>
        <span className="text-xs font-mono w-8 text-slate-300">{percentage.toFixed(0)}%</span>
      </div>
    );
  };

  return (
    <tr style={style} className="absolute top-0 left-0 w-full hover:bg-slate-750/70 transition-colors border-b border-slate-700/50 flex">
      <td className="w-16 flex-none px-5 py-3 text-xs text-slate-500 font-medium flex items-center">{(page * pageSize) + index + 1}</td>
      <td className="w-40 flex-none px-5 py-3 text-sm text-slate-300 flex items-center">{formatDate(alert.timestamp)}</td>
      <td className="w-32 flex-none px-5 py-3 text-sm font-medium text-slate-200 flex items-center truncate">{alert.host_id}</td>
      <td className="w-32 flex-none px-5 py-3 text-sm text-slate-300 flex items-center truncate">{alert.user_name}</td>
      <td className="w-32 flex-none px-5 py-3 text-xs text-slate-400 flex items-center truncate">{alert.log_type}</td>
      <td className="w-48 flex-none px-5 py-3 flex items-center">{renderProgressBar(alert.threat_score)}</td>
      <td className="w-32 flex-none px-5 py-3 flex items-center"><Badge variant={alert.threat_level}>{alert.threat_level}</Badge></td>
      <td className="flex-1 px-5 py-3 text-xs text-slate-300 truncate flex items-center" title={alert.mitre_tactic}>{alert.mitre_tactic || "-"}</td>
      <td className="w-36 flex-none px-5 py-3 flex items-center">
        <select 
          value={alert.alert_status || "open"} 
          onChange={(e) => updateStatus({ id: alert._id || alert.id, status: e.target.value })}
          className={`text-xs font-medium px-2 py-1.5 rounded border ${
            alert.alert_status === 'closed' ? 'border-slate-700 bg-slate-800/50 text-slate-500' : 'border-slate-600 bg-slate-800 text-slate-200'
          } focus:outline-none focus:border-blue-500 transition-colors w-full`}
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>
      </td>
      <td className="w-24 flex-none px-5 py-3 flex items-center justify-center">
        <div className="flex items-center gap-4">
          <Link to={`/alerts/${alert._id || alert.id}`} title="View Details" className="text-slate-400 hover:text-blue-400 transition-colors">
            <Eye className="h-5 w-5" />
          </Link>
          <Link to={`/investigation?alert_id=${alert._id || alert.id}`} title="Investigate in SLM" className="text-slate-400 hover:text-purple-400 transition-colors">
            <MessageSquare className="h-5 w-5" />
          </Link>
        </div>
      </td>
    </tr>
  );
});

export const Alerts = () => {
  const { 
    alerts, total, loading, error, filters, page, pageSize, sortBy, sortOrder, 
    setFilters, setPage, setSort, clearFilters, updateStatus 
  } = useAlerts();

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [toast, setToast] = useState(null);
  
  // Ref for the virtualizer container
  const parentRef = useRef(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const triggerScoringMutation = useTriggerScoring();

  const handleTriggerScoring = useCallback(() => {
    triggerScoringMutation.mutate(undefined, {
      onSuccess: () => setToast("Scoring triggered successfully!")
    });
  }, [triggerScoringMutation]);

  const handleSort = useCallback((col) => {
    if (sortBy === col) {
      setSort(col, sortOrder === "desc" ? "asc" : "desc");
    } else {
      setSort(col, "desc");
    }
  }, [sortBy, sortOrder, setSort]);

  const handleFilterChange = useCallback((e) => {
    const { name, value } = e.target;
    setFilters({ [name]: value });
  }, [setFilters]);

  // Use memo for the alerts array
  const memoizedAlerts = useMemo(() => alerts || [], [alerts]);

  // Virtualizer setup
  const rowVirtualizer = useVirtualizer({
    count: memoizedAlerts.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64, // estimated row height in px
    overscan: 10,
  });

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-center flex-none">
        <h1 className="text-2xl font-bold">Alert Investigation</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${autoRefresh ? 'bg-blue-500/20 text-blue-400 border-blue-500/50' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'}`}
          >
            <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            Auto-refresh
          </button>
          <button
            onClick={handleTriggerScoring}
            disabled={triggerScoringMutation.isPending}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {triggerScoringMutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Trigger Scoring
          </button>
        </div>
      </div>

      {toast && (
        <div className="bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-4 flex-none">
          <CheckCircle className="h-5 w-5" />
          <p>{toast}</p>
        </div>
      )}

      {/* Filters Bar */}
      <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 grid grid-cols-1 md:grid-cols-6 gap-4 items-end flex-none">
        <div>
          <label className="block text-xs text-slate-400 mb-1 font-medium">Status</label>
          <select name="status" value={filters.status} onChange={handleFilterChange} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors">
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1 font-medium">Threat Level</label>
          <select name="threat_level" value={filters.threat_level} onChange={handleFilterChange} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors">
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1 font-medium">From Date</label>
          <input type="date" name="from_time" value={filters.from_time} onChange={handleFilterChange} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors" />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1 font-medium">To Date</label>
          <input type="date" name="to_time" value={filters.to_time} onChange={handleFilterChange} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors" />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1 font-medium">Host Search</label>
          <input type="text" name="host_id" value={filters.host_id} onChange={handleFilterChange} placeholder="Enter hostname..." className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors" />
        </div>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="block text-xs text-slate-400 mb-1 font-medium">User Search</label>
            <input type="text" name="user_name" value={filters.user_name} onChange={handleFilterChange} placeholder="Enter username..." className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors" />
          </div>
          <div className="flex items-end">
            <button onClick={clearFilters} className="bg-slate-700 hover:bg-slate-600 text-slate-200 p-2 rounded-lg transition-colors h-[38px] w-[38px] flex items-center justify-center" title="Clear Filters">
              <FilterX className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg flex-1 flex flex-col min-h-0">
        <div className="overflow-x-auto flex-1 flex flex-col min-h-0">
          <div className="min-w-[1200px] flex-1 flex flex-col min-h-0">
            {/* Header */}
            <div className="bg-slate-900/80 border-b border-slate-700 flex flex-none text-left">
              <div className="w-16 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">#</div>
              <div className="w-40 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 select-none flex items-center gap-1" onClick={() => handleSort("timestamp")}>
                Timestamp <ArrowUpDown className="h-3 w-3"/>
              </div>
              <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Host</div>
              <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">User</div>
              <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Log Type</div>
              <div className="w-48 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 select-none flex items-center gap-1" onClick={() => handleSort("threat_score")}>
                Threat Score <ArrowUpDown className="h-3 w-3"/>
              </div>
              <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Threat Level</div>
              <div className="flex-1 px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">MITRE Tactic</div>
              <div className="w-36 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</div>
              <div className="w-24 flex-none px-5 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-center">Actions</div>
            </div>

            {/* Virtualized Body */}
            <div 
              ref={parentRef} 
              className="flex-1 overflow-y-auto w-full"
            >
              {loading ? (
                <div className="flex items-center justify-center p-16"><LoadingSpinner /></div>
              ) : error ? (
                <div className="p-8"><ErrorBanner message="Failed to load alerts. Please try again." /></div>
              ) : memoizedAlerts.length === 0 ? (
                <div className="p-12 text-center text-slate-400 font-medium">No alerts found matching the given filters.</div>
              ) : (
                <div 
                  style={{
                    height: `${rowVirtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                  }}
                >
                  {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                    const alert = memoizedAlerts[virtualRow.index];
                    return (
                      <AlertRow
                        key={alert._id || alert.id || virtualRow.index}
                        alert={alert}
                        index={virtualRow.index}
                        page={page}
                        pageSize={pageSize}
                        updateStatus={updateStatus}
                        style={{
                          height: `${virtualRow.size}px`,
                          transform: `translateY(${virtualRow.start}px)`,
                        }}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Pagination */}
        <div className="flex-none px-6 py-4 bg-slate-900/50 border-t border-slate-700 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="text-sm text-slate-400">
            Showing <span className="font-medium text-slate-200">{total === 0 ? 0 : (page * pageSize) + 1}</span> to <span className="font-medium text-slate-200">{Math.min((page * pageSize) + pageSize, total)}</span> of <span className="font-medium text-slate-200">{total}</span> alerts
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-4 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 transition-colors text-slate-200"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={(page + 1) * pageSize >= total}
              className="px-4 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 transition-colors text-slate-200"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
