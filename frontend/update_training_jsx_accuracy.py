import os
import re

file_path = "src/pages/Training.jsx"

with open(file_path, "r") as f:
    content = f.read()

# 1. Import Accuracy functions and Target
if "getAccuracyReport" not in content:
    content = content.replace("getInterpretabilityReport,", "getInterpretabilityReport,\n  getAccuracyReport,\n  updateThreatThreshold,")

# 2. Add Target icon
if "Target," not in content:
    content = content.replace("Eye,", "Eye,\n  Target,")

# 3. Add Queries
if "const { data: accuracyData" not in content:
    query_str = """
  const { data: accuracyData, isLoading: accuracyLoading, error: accuracyError } = useQuery({
    queryKey: ['accuracyReport'],
    queryFn: () => getAccuracyReport(),
    enabled: activeTab === 'accuracy',
  })
  const accuracy = accuracyData?.data || accuracyData

  const applyThresholdMutation = useMutation({
    mutationFn: updateThreatThreshold,
    onSuccess: () => {
      alert('Threshold applied successfully!')
    }
  })
"""
    content = content.replace("const interpretability = interpretabilityData?.data || interpretabilityData", "const interpretability = interpretabilityData?.data || interpretabilityData\n" + query_str)

# 4. Add Tab Button
if "activeTab === 'accuracy'" not in content:
    tab_btn = """
        <TabButton
          active={activeTab === 'interpretability'}
          onClick={() => setActiveTab('interpretability')}
        >
          Interpretability
        </TabButton>
        <TabButton
          active={activeTab === 'accuracy'}
          onClick={() => setActiveTab('accuracy')}
        >
          Accuracy
        </TabButton>"""
    content = content.replace("""        <TabButton
          active={activeTab === 'interpretability'}
          onClick={() => setActiveTab('interpretability')}
        >
          Interpretability
        </TabButton>""", tab_btn)

# 5. Add Tab Content
if "TAB 6: Accuracy" not in content:
    accuracy_ui = """
      {/* TAB 6: Accuracy */}
      {activeTab === 'accuracy' && (
        <div className="pt-4 animate-in fade-in slide-in-from-bottom-2 space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-[var(--text_primary)] flex items-center gap-2">
              <Target className="w-6 h-6 text-indigo-500" />
              Model Accuracy Evaluation
            </h2>
            {accuracy && !accuracyError && (
              <button
                onClick={() => applyThresholdMutation.mutate(accuracy.optimal_threshold)}
                disabled={applyThresholdMutation.isPending}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-900/20"
              >
                {applyThresholdMutation.isPending ? 'Applying...' : `Apply Optimal Threshold (${accuracy.optimal_threshold.toFixed(2)})`}
              </button>
            )}
          </div>

          {accuracyLoading ? (
            <div className="p-10 flex justify-center"><LoadingSpinner /></div>
          ) : accuracyError && accuracyError.response?.data?.error === 'insufficient data' ? (
            <div className="bg-[var(--bg_secondary)] border border-[var(--border)] rounded-xl p-8 text-center text-[var(--text_secondary)] shadow-lg">
              <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Insufficient labeled data</p>
              <p className="mt-2 text-sm">The accuracy evaluator requires a minimum of 30 analyst-labeled samples. Please label more alerts in the triage queue.</p>
            </div>
          ) : accuracyError ? (
            <ErrorBanner error={accuracyError.message} />
          ) : accuracy ? (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Precision", value: accuracy.precision, format: "pct" },
                  { label: "Recall", value: accuracy.recall, format: "pct" },
                  { label: "F1 Score", value: accuracy.f1_score, format: "pct" },
                  { label: "Accuracy", value: accuracy.accuracy, format: "pct" }
                ].map((stat, i) => (
                  <div key={i} className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-4 shadow-sm">
                    <div className="text-sm text-[var(--text_secondary)]">{stat.label}</div>
                    <div className="text-2xl font-bold text-[var(--text_primary)] mt-1">
                      {(stat.value * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Confusion Matrix */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm flex flex-col items-center">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-6 self-start">Confusion Matrix (Threshold: {accuracy.optimal_threshold.toFixed(2)})</h3>
                  <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                    <div className="bg-green-500/20 border border-green-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-green-400 mb-1">True Positive (TP)</div>
                      <div className="text-2xl font-bold text-green-500">{accuracy.true_positives}</div>
                    </div>
                    <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-red-400 mb-1">False Positive (FP)</div>
                      <div className="text-2xl font-bold text-red-500">{accuracy.false_positives}</div>
                    </div>
                    <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-yellow-400 mb-1">False Negative (FN)</div>
                      <div className="text-2xl font-bold text-yellow-500">{accuracy.false_negatives}</div>
                    </div>
                    <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-blue-400 mb-1">True Negative (TN)</div>
                      <div className="text-2xl font-bold text-blue-500">{accuracy.true_negatives}</div>
                    </div>
                  </div>
                </div>

                {/* PR Curve */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-2 flex justify-between">
                    <span>Precision-Recall Curve</span>
                    <span className="text-sm font-mono text-[var(--text_secondary)]">AUC: {accuracy.pr_auc?.toFixed(3)}</span>
                  </h3>
                  <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={accuracy.threshold_curve || []}
                        margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                        <XAxis dataKey="recall" type="number" domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <YAxis domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: 'var(--bg_secondary)', borderColor: 'var(--border)', color: 'var(--text_primary)' }}
                        />
                        <Line type="monotone" dataKey="precision" stroke="#8b5cf6" strokeWidth={2} dot={false} name="PR Curve" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Threshold Sweep */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm lg:col-span-2">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Threshold Sweep (F1 Maximization)</h3>
                  <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={accuracy.threshold_curve || []}
                        margin={{ top: 5, right: 20, left: -20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                        <XAxis dataKey="threshold" type="number" domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <YAxis domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: 'var(--bg_secondary)', borderColor: 'var(--border)', color: 'var(--text_primary)' }}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px', color: 'var(--text_secondary)' }} />
                        <Line type="monotone" dataKey="precision" stroke="#3b82f6" strokeWidth={2} dot={false} name="Precision" />
                        <Line type="monotone" dataKey="recall" stroke="#ef4444" strokeWidth={2} dot={false} name="Recall" />
                        <Line type="monotone" dataKey="f1" stroke="#10b981" strokeWidth={3} dot={false} name="F1 Score" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Per Model AUC & Calibration */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Model Contributions (AUC-ROC)</h3>
                  <div className="space-y-4">
                    {Object.entries(accuracy.per_model_auc || {}).map(([model, aucScore]) => (
                      <div key={model}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-[var(--text_secondary)] font-mono">{model}</span>
                          <span className="text-[var(--text_primary)]">{aucScore.toFixed(3)}</span>
                        </div>
                        <div className="w-full bg-[var(--bg_primary)] rounded-full h-2">
                          <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${Math.max(0, aucScore) * 100}%` }}></div>
                        </div>
                      </div>
                    ))}
                    <div className="mt-6 pt-4 border-t border-[var(--border)]">
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--text_secondary)]">Expected Calibration Error (ECE):</span>
                        <span className="text-yellow-400 font-mono">{(accuracy.calibration_error * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Per Rule Precision */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Rule Precision Breakdown</h3>
                  <div className="overflow-y-auto max-h-[200px] border border-[var(--border)] rounded-lg">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-[var(--bg_primary)] sticky top-0">
                        <tr>
                          <th className="px-4 py-2 font-semibold text-[var(--text_secondary)]">Rule ID</th>
                          <th className="px-4 py-2 font-semibold text-[var(--text_secondary)]">Precision</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {Object.entries(accuracy.per_rule_precision || {}).sort((a, b) => b[1] - a[1]).map(([rule, prec]) => (
                          <tr key={rule} className="hover:bg-[var(--bg_tertiary)]">
                            <td className="px-4 py-2 font-mono text-[var(--text_primary)]">{rule}</td>
                            <td className="px-4 py-2 text-[var(--text_primary)]">{(prec * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                        {Object.keys(accuracy.per_rule_precision || {}).length === 0 && (
                          <tr><td colSpan="2" className="px-4 py-4 text-center text-xs text-[var(--text_secondary)]">No rule triggers in feedback.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            </>
          ) : null}
        </div>
      )}
"""
    content = content.replace("    </div>\n  )\n}\n", accuracy_ui + "    </div>\n  )\n}\n")

with open(file_path, "w") as f:
    f.write(content)
