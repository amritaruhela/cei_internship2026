import React, { useEffect, useState } from 'react';
import { TrendingDown, Activity, FileCode2, Layers, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { fetchDriftResults } from '../api/client';
import { DriftResult } from '../types';

export const DriftMonitor: React.FC = () => {
  const [results, setResults] = useState<DriftResult[]>([]);
  const [activeTab, setActiveTab] = useState<'volume' | 'distribution' | 'schema'>('volume');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDriftResults().then((data) => {
      setResults(data);
      setLoading(false);
    });
  }, []);

  const filtered = results.filter((r) => r.drift_type === activeTab);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <TrendingDown className="w-6 h-6 text-sky-400" />
          <span>Cross-System Data Drift Monitor</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Automated statistical anomaly detection across Volume Drift, Feature Distribution (PSI/KS), and Schema evolution.
        </p>
      </div>

      {/* Category Tabs */}
      <div className="flex border-b border-slate-800 space-x-8">
        <button
          onClick={() => setActiveTab('volume')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'volume' ? 'border-sky-500 text-sky-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Volume Drift (Rolling Z-Score)</span>
        </button>

        <button
          onClick={() => setActiveTab('distribution')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'distribution' ? 'border-sky-500 text-sky-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <TrendingDown className="w-4 h-4" />
          <span>Distribution Drift (PSI / KS Test)</span>
        </button>

        <button
          onClick={() => setActiveTab('schema')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'schema' ? 'border-sky-500 text-sky-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileCode2 className="w-4 h-4" />
          <span>Schema Evolution Drift</span>
        </button>
      </div>

      {/* Methodology Banner */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-1">
        <div className="font-semibold text-sky-400">
          {activeTab === 'volume' && 'Methodology: 30-Day Rolling Window Baseline with Z-Score Anomaly Flagging (|z| > 2.5)'}
          {activeTab === 'distribution' && 'Methodology: Population Stability Index (PSI > 0.20 = Critical Drift) & Kolmogorov-Smirnov 2-Sample Test'}
          {activeTab === 'schema' && 'Methodology: Automated JSON Schema Snapshot Diffing across Ingestion Runs'}
        </div>
      </div>

      {/* Drift Results Table */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Source System</th>
                <th className="py-3 px-4">Column / Feature</th>
                <th className="py-3 px-4">Baseline Baseline</th>
                <th className="py-3 px-4">Current Observed</th>
                <th className="py-3 px-4">Drift Score</th>
                <th className="py-3 px-4">Threshold</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/30">
                  <td className="py-3.5 px-4 font-sans font-bold text-white uppercase">{item.source_system}</td>
                  <td className="py-3.5 px-4 text-sky-300 font-sans font-semibold">{item.column_name || 'row_count'}</td>
                  <td className="py-3.5 px-4 text-slate-300">{item.baseline_value || 'N/A'}</td>
                  <td className="py-3.5 px-4 text-white font-bold">{item.current_value || 'N/A'}</td>
                  <td className="py-3.5 px-4 text-amber-400 font-bold">{(item.drift_score * 100).toFixed(1)}%</td>
                  <td className="py-3.5 px-4 text-slate-400">{item.threshold ? `${(item.threshold * 100).toFixed(0)}%` : '0%'}</td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.severity === 'CRITICAL' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      item.severity === 'HIGH' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                    }`}>
                      {item.is_drifted ? item.severity : 'STABLE'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
