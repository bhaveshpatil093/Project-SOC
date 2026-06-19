import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { startInitialTraining, startRetraining, getTrainingStatus, getTrainingHistory } from "../api/training";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Badge } from "../components/common/Badge";
import { formatDate } from "../utils/formatters";
import { Brain, Play, RotateCw, Activity, Calendar, Server, CheckCircle, Database, ArrowRight, Loader2, Network, Clock } from "lucide-react";

// Helper hook for polling job status
const useJobStatus = (jobId) => {
  return useQuery({
    queryKey: ["trainingStatus", jobId],
    queryFn: () => getTrainingStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Keep polling every 3s if status is not final
      if (data && data.data) {
          const status = data.data.status?.toLowerCase();
          if (status === "completed" || status === "failed" || status === "error") return false;
      } else if (data) {
          const status = data.status?.toLowerCase();
          if (status === "completed" || status === "failed" || status === "error") return false;
      }
      return 3000;
    },
  });
};

const STEPS = [
  "Fetching data",
  "Feature engineering",
  "Training IF",
  "Training AE",
  "Training LSTM",
  "Complete"
];

const ProgressTracker = ({ statusData }) => {
  if (!statusData) return null;
  const status = (statusData.status || "").toLowerCase();
  const stepStr = (statusData.current_step || statusData.step || "Fetching data");
  
  let currentStepIndex = STEPS.findIndex(s => s.toLowerCase() === stepStr.toLowerCase());
  if (status === "completed") currentStepIndex = STEPS.length - 1;
  if (currentStepIndex === -1 && status !== "completed") currentStepIndex = 0; // Default

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 mt-6">
      <div className="flex justify-between items-center mb-6">
        <h4 className="text-white font-bold flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-500" />
          Training Job Progress
        </h4>
        <span className="text-xs font-mono text-slate-400">Job ID: {statusData.job_id || "N/A"}</span>
      </div>
      
      <div className="relative">
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -translate-y-1/2 z-0"></div>
        <div className="relative z-10 flex justify-between">
          {STEPS.map((step, idx) => {
            const isCompleted = idx < currentStepIndex || status === "completed";
            const isActive = idx === currentStepIndex && status !== "completed" && status !== "failed";
            const isFailed = status === "failed" && idx === currentStepIndex;

            let bgColor = "bg-slate-800";
            let borderColor = "border-slate-700";
            let textColor = "text-slate-500";
            let Icon = Server;

            if (isCompleted) {
              bgColor = "bg-green-500/20";
              borderColor = "border-green-500";
              textColor = "text-green-500";
              Icon = CheckCircle;
            } else if (isActive) {
              bgColor = "bg-blue-500/20";
              borderColor = "border-blue-500";
              textColor = "text-blue-400";
              Icon = Loader2;
            } else if (isFailed) {
              bgColor = "bg-red-500/20";
              borderColor = "border-red-500";
              textColor = "text-red-500";
            }

            return (
              <div key={idx} className="flex flex-col items-center gap-3">
                <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center ${bgColor} ${borderColor} transition-colors duration-500`}>
                  <Icon className={`h-4 w-4 ${isActive ? 'animate-spin' : ''} ${textColor}`} />
                </div>
                <span className={`text-xs font-medium max-w-[80px] text-center leading-tight ${textColor}`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {status === "completed" && statusData.metrics && (
        <div className="mt-8 bg-green-500/10 border border-green-500/50 rounded-lg p-4 animate-in fade-in slide-in-from-bottom-4">
          <h5 className="text-green-400 font-bold mb-3 flex items-center gap-2">
            <CheckCircle className="h-4 w-4" /> Training Completed Successfully
          </h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 rounded p-3">
              <div className="text-xs text-slate-400 uppercase">Samples</div>
              <div className="text-lg font-bold text-white">{statusData.metrics.n_samples || "N/A"}</div>
            </div>
            <div className="bg-slate-900 rounded p-3">
              <div className="text-xs text-slate-400 uppercase">AE Loss</div>
              <div className="text-lg font-bold text-white">{statusData.metrics.final_loss?.toFixed(4) || "N/A"}</div>
            </div>
            <div className="bg-slate-900 rounded p-3">
              <div className="text-xs text-slate-400 uppercase">IF Contamination</div>
              <div className="text-lg font-bold text-white">{statusData.metrics.contamination || "0.01"}</div>
            </div>
            <div className="bg-slate-900 rounded p-3">
              <div className="text-xs text-slate-400 uppercase">Training Time</div>
              <div className="text-lg font-bold text-white">{statusData.metrics.duration_seconds || 0}s</div>
            </div>
          </div>
        </div>
      )}
      
      {status === "failed" && (
        <div className="mt-8 bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
          <h5 className="font-bold mb-1">Training Failed</h5>
          <p className="text-sm">{statusData.error || "An unknown error occurred during training."}</p>
        </div>
      )}
    </div>
  );
};

export const Training = () => {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState(null);

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ["trainingHistory"],
    queryFn: () => getTrainingHistory(),
    refetchInterval: 30000,
  });

  const { data: statusResp } = useJobStatus(jobId);
  const statusData = statusResp?.data || statusResp;

  const initialMutation = useMutation({
    mutationFn: startInitialTraining,
    onSuccess: (res) => {
      const data = res.data || res;
      if (data.job_id) setJobId(data.job_id);
    }
  });

  const retrainMutation = useMutation({
    mutationFn: startRetraining,
    onSuccess: (res) => {
      const data = res.data || res;
      if (data.job_id) setJobId(data.job_id);
    }
  });

  const handleInitial = () => {
    setJobId(null);
    initialMutation.mutate();
  };

  const handleRetrain = () => {
    setJobId(null);
    retrainMutation.mutate();
  };

  const history = historyData?.data || historyData || [];
  
  // Extract Latest Model Metrics
  const if_runs = history.filter(h => h.model_type === "isolation_forest" || (h.params && h.params.model_type === "isolation_forest"));
  const ae_runs = history.filter(h => h.model_type === "autoencoder" || (h.params && h.params.model_type === "autoencoder"));
  const lstm_runs = history.filter(h => h.model_type === "lstm" || (h.params && h.params.model_type === "lstm"));

  const latestIF = if_runs[0] || null;
  const latestAE = ae_runs[0] || null;
  const latestLSTM = lstm_runs[0] || null;

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Model Training & Lifecycle</h1>
        <p className="text-slate-400 mt-1">Manage anomaly detection ensembles, retrain on feedback loops, and monitor MLflow artifacts.</p>
      </div>

      {/* SECTION 1: Model Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Isolation Forest Card */}
        <div className={`rounded-xl border p-6 flex flex-col justify-between ${latestIF ? 'bg-slate-800 border-slate-700' : 'bg-slate-900 border-slate-800 opacity-80'}`}>
          <div>
            <div className="flex justify-between items-start mb-4">
              <div className={`p-2 rounded-lg ${latestIF ? 'bg-blue-500/20 text-blue-500' : 'bg-slate-800 text-slate-500'}`}>
                <Network className="h-6 w-6" />
              </div>
              <Badge variant={latestIF ? "tp" : "fp"}>{latestIF ? "Loaded" : "Not Trained"}</Badge>
            </div>
            <h3 className={`text-lg font-bold ${latestIF ? 'text-white' : 'text-slate-400'}`}>Isolation Forest</h3>
            <p className="text-xs text-slate-500 mt-1">Unsupervised Outlier Detection</p>
          </div>
          <div className="mt-6 space-y-2 border-t border-slate-700/50 pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">N Samples:</span>
              <span className="text-slate-200 font-medium">{latestIF?.metrics?.n_samples || "—"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Last Trained:</span>
              <span className="text-slate-200 font-medium">{latestIF ? formatDate(latestIF.timestamp) : "—"}</span>
            </div>
          </div>
        </div>

        {/* Autoencoder Card */}
        <div className={`rounded-xl border p-6 flex flex-col justify-between ${latestAE ? 'bg-slate-800 border-slate-700' : 'bg-slate-900 border-slate-800 opacity-80'}`}>
          <div>
            <div className="flex justify-between items-start mb-4">
              <div className={`p-2 rounded-lg ${latestAE ? 'bg-purple-500/20 text-purple-500' : 'bg-slate-800 text-slate-500'}`}>
                <Brain className="h-6 w-6" />
              </div>
              <Badge variant={latestAE ? "tp" : "fp"}>{latestAE ? "Loaded" : "Not Trained"}</Badge>
            </div>
            <h3 className={`text-lg font-bold ${latestAE ? 'text-white' : 'text-slate-400'}`}>Autoencoder</h3>
            <p className="text-xs text-slate-500 mt-1">Deep Feature Reconstruction</p>
          </div>
          <div className="mt-6 space-y-2 border-t border-slate-700/50 pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Final Loss:</span>
              <span className="text-slate-200 font-medium">{latestAE?.metrics?.final_loss?.toFixed(4) || "—"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Threshold:</span>
              <span className="text-slate-200 font-medium">{latestAE?.metrics?.threshold?.toFixed(4) || "—"}</span>
            </div>
          </div>
        </div>

        {/* LSTM Card */}
        <div className={`rounded-xl border p-6 flex flex-col justify-between ${latestLSTM ? 'bg-slate-800 border-slate-700' : 'bg-slate-900 border-slate-800 opacity-80'}`}>
          <div>
            <div className="flex justify-between items-start mb-4">
              <div className={`p-2 rounded-lg ${latestLSTM ? 'bg-green-500/20 text-green-500' : 'bg-slate-800 text-slate-500'}`}>
                <Activity className="h-6 w-6" />
              </div>
              <Badge variant={latestLSTM ? "tp" : "fp"}>{latestLSTM ? "Loaded" : "Not Trained"}</Badge>
            </div>
            <h3 className={`text-lg font-bold ${latestLSTM ? 'text-white' : 'text-slate-400'}`}>LSTM Sequence</h3>
            <p className="text-xs text-slate-500 mt-1">Temporal Sequence Forecasting</p>
          </div>
          <div className="mt-6 space-y-2 border-t border-slate-700/50 pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Vocab Size:</span>
              <span className="text-slate-200 font-medium">{latestLSTM?.metrics?.vocab_size || "—"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Last Trained:</span>
              <span className="text-slate-200 font-medium">{latestLSTM ? formatDate(latestLSTM.timestamp) : "—"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: Training Actions */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 shadow-lg">
        <h2 className="text-xl font-bold text-white mb-6">Execution & Orchestration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 p-6 rounded-xl border border-slate-700 flex flex-col items-start hover:border-slate-500 transition-colors">
            <div className="p-3 bg-blue-500/10 rounded-lg text-blue-500 mb-4">
              <Database className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Initial Genesis Training</h3>
            <p className="text-sm text-slate-400 mb-6 flex-1">
              Extracts the last 7 days of raw telemetry logs, executes the massive full-feature pipeline, and trains IF, AE, and LSTM architectures from scratch.
            </p>
            <button 
              onClick={handleInitial}
              disabled={initialMutation.isPending || (jobId && statusData?.status !== 'completed' && statusData?.status !== 'failed')}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              {initialMutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
              Run Initial Training
            </button>
          </div>

          <div className="bg-slate-900 p-6 rounded-xl border border-slate-700 flex flex-col items-start hover:border-slate-500 transition-colors">
            <div className="p-3 bg-purple-500/10 rounded-lg text-purple-500 mb-4">
              <RotateCw className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Incremental Retraining</h3>
            <p className="text-sm text-slate-400 mb-6 flex-1">
              Fetches analyst-labeled TP/Benign payloads from feedback loops, augments active training datasets, and incrementally fine-tunes Autoencoder weights.
            </p>
            <button 
              onClick={handleRetrain}
              disabled={retrainMutation.isPending || (jobId && statusData?.status !== 'completed' && statusData?.status !== 'failed')}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              {retrainMutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <RotateCw className="h-5 w-5" />}
              Run Incremental Retraining
            </button>
          </div>
        </div>

        {/* Live Job Progress Tracker */}
        {jobId && <ProgressTracker statusData={statusData} />}
      </div>

      {/* SECTION 3 & 4 Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* SECTION 3: MLflow Version History */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg lg:col-span-3">
          <div className="px-6 py-5 border-b border-slate-700 bg-slate-900/50">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              MLflow Artifact History
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left whitespace-nowrap">
              <thead className="bg-slate-900/80 border-b border-slate-700">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Version</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Timestamp</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Model Type</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">N Samples</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Loss / Cont.</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {historyLoading ? (
                  <tr><td colSpan="6" className="px-6 py-8"><LoadingSpinner /></td></tr>
                ) : history.length === 0 ? (
                  <tr><td colSpan="6" className="px-6 py-8 text-center text-slate-500">No training history available.</td></tr>
                ) : (
                  history.map((run, idx) => {
                    const isLatest = idx === 0;
                    return (
                      <tr key={idx} className={`${isLatest ? 'bg-blue-900/10' : 'hover:bg-slate-750/50'} transition-colors`}>
                        <td className="px-6 py-4 text-xs font-mono text-slate-300">{(run.run_id || run.version || "N/A").substring(0, 8)}</td>
                        <td className="px-6 py-4 text-xs text-slate-400">{formatDate(run.timestamp)}</td>
                        <td className="px-6 py-4 text-sm font-medium text-slate-200 capitalize">
                          {run.model_type || (run.params && run.params.model_type) || "ensemble"}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-300">{run.metrics?.n_samples || "-"}</td>
                        <td className="px-6 py-4 text-sm font-mono text-slate-400">
                          {run.metrics?.final_loss ? run.metrics.final_loss.toFixed(4) : (run.metrics?.contamination || "-")}
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={isLatest ? "open" : "closed"}>
                            {isLatest ? "Active" : "Archived"}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION 4: Weekly Schedule */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 lg:col-span-1 h-fit shadow-lg">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-slate-900 rounded-lg text-blue-500 border border-slate-700">
              <Calendar className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-bold text-white">Scheduler</h3>
          </div>
          
          <div className="bg-slate-900 rounded-lg border border-slate-700 p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
            <h4 className="text-sm font-bold text-white mb-1">Automatic Retraining</h4>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Scheduled cron bounds automatically extract weekly true positive logs resolving ML drifts.
            </p>
            
            <div className="bg-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-300 flex items-center justify-between border border-slate-700">
              <span>Every Sunday</span>
              <span className="text-blue-400">02:00 AM</span>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-slate-700 flex items-center text-xs text-slate-500 gap-2">
            <Clock className="h-4 w-4" />
            <span>Next run: {new Date(Date.now() + (7 - new Date().getDay()) * 24 * 60 * 60 * 1000).toLocaleDateString()}</span>
          </div>
        </div>
        
      </div>
    </div>
  );
};
