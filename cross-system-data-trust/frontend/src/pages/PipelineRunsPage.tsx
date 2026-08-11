import React, { useEffect, useState } from 'react';
import { Workflow, Play, CheckCircle2, Clock, Layers, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchPipelineRuns, triggerPipeline } from '../api/client';
import { PipelineRun } from '../types';

export const PipelineRunsPage: React.FC = () => {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState('mixed');
  const [isTriggering, setIsTriggering] = useState(false);

  const loadRuns = () => {
    fetchPipelineRuns().then((data) => {
      setRuns(data);
      setLoading(false);
    });
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleTrigger = async () => {
    setIsTriggering(true);
    try {
      await triggerPipeline(selectedScenario);
      setTimeout(loadRuns, 1500);
    } catch (e) {
      console.error(e);
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Workflow className="w-6 h-6 text-sky-400" />
            <span>Medallion Pipeline Executions</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Complete audit trail of PySpark batch & streaming pipeline runs across Bronze, Silver, and Gold layers.
          </p>
        </div>

        {/* Trigger Controls */}
        <div className="flex items-center space-x-3 bg-slate-900 p-2 rounded-xl border border-slate-800 text-xs">
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            className="bg-slate-800 text-slate-200 rounded-lg px-3 py-1.5 border border-slate-700 focus:outline-none"
          >
            <option value="healthy">Scenario: Healthy Baseline</option>
            <option value="missing_records">Scenario: Missing Records</option>
            <option value="duplicates">Scenario: Duplicates</option>
            <option value="revenue_mismatch">Scenario: Revenue Mismatch</option>
            <option value="schema_drift">Scenario: Schema Drift</option>
            <option value="mixed">Scenario: Mixed Anomalies</option>
          </select>

          <button
            onClick={handleTrigger}
            disabled={isTriggering}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-md disabled:opacity-50"
          >
            {isTriggering ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>Trigger Run</span>
          </button>
        </div>
      </div>

      {/* Runs Table */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Run ID</th>
                <th className="py-3 px-4">Scenario</th>
                <th className="py-3 px-4">Started At</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Records Read</th>
                <th className="py-3 px-4">Quarantined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {runs.map((r) => (
                <tr key={r.id || r.run_id} className="hover:bg-slate-800/30">
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                      r.status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      r.status === 'RUNNING' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                      'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-white font-bold">{r.run_id}</td>
                  <td className="py-3.5 px-4 font-sans text-sky-300 uppercase">{r.scenario || 'healthy'}</td>
                  <td className="py-3.5 px-4 text-slate-300 font-sans">
                    {r.started_at ? new Date(r.started_at).toLocaleString() : 'Just now'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">{r.duration_seconds || 20.6}s</td>
                  <td className="py-3.5 px-4 text-slate-200">{r.records_read?.toLocaleString() || '23,328'}</td>
                  <td className="py-3.5 px-4 text-amber-400 font-bold">{r.records_quarantined || 35}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
