import React, { useEffect, useState } from 'react';
import { Settings, Save, Sliders, ShieldCheck, Database, CheckCircle2 } from 'lucide-react';
import { fetchRules } from '../api/client';
import { QualityRule } from '../types';

export const SettingsPage: React.FC = () => {
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [saveToast, setSaveToast] = useState(false);

  // Form states
  const [completenessWeight, setCompletenessWeight] = useState(20);
  const [consistencyWeight, setConsistencyWeight] = useState(25);
  const [accuracyWeight, setAccuracyWeight] = useState(20);
  const [freshnessWeight, setFreshnessWeight] = useState(15);
  const [uniquenessWeight, setUniquenessWeight] = useState(10);
  const [driftWeight, setDriftWeight] = useState(10);

  const [databricksMode, setDatabricksMode] = useState(false);

  useEffect(() => {
    fetchRules().then(setRules);
  }, []);

  const handleSave = () => {
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 3000);
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-6 h-6 text-sky-400" />
            <span>Platform Configuration & Monitoring Settings</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Dynamic threshold tuning, rule enabling/disabling, trust score component weighting, and deployment modes.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs shadow-lg shadow-sky-600/20 transition-all"
        >
          <Save className="w-4 h-4" />
          <span>Save Configurations</span>
        </button>
      </div>

      {saveToast && (
        <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Configurations updated successfully! Data engine will apply new rules on next run.</span>
        </div>
      )}

      {/* Trust Score Weighting Sliders */}
      <div className="p-6 rounded-2xl glass-panel space-y-6">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          <span>Trust Score Component Weights (Must sum to 100%)</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Completeness Weight</span>
              <span className="font-mono text-sky-400">{completenessWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={completenessWeight}
              onChange={(e) => setCompletenessWeight(Number(e.target.value))}
              className="w-full accent-sky-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Consistency Weight</span>
              <span className="font-mono text-indigo-400">{consistencyWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={consistencyWeight}
              onChange={(e) => setConsistencyWeight(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Accuracy / Reconciliation Weight</span>
              <span className="font-mono text-emerald-400">{accuracyWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={accuracyWeight}
              onChange={(e) => setAccuracyWeight(Number(e.target.value))}
              className="w-full accent-emerald-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Freshness Weight</span>
              <span className="font-mono text-amber-400">{freshnessWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={freshnessWeight}
              onChange={(e) => setFreshnessWeight(Number(e.target.value))}
              className="w-full accent-amber-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Uniqueness Weight</span>
              <span className="font-mono text-purple-400">{uniquenessWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={uniquenessWeight}
              onChange={(e) => setUniquenessWeight(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-300">
              <span>Drift Stability Weight</span>
              <span className="font-mono text-rose-400">{driftWeight}%</span>
            </div>
            <input
              type="range" min="0" max="50" value={driftWeight}
              onChange={(e) => setDriftWeight(Number(e.target.value))}
              className="w-full accent-rose-500"
            />
          </div>
        </div>
      </div>

      {/* Deployment Mode */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          <span>Execution & Storage Mode</span>
        </h2>

        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div>
            <div className="text-xs font-bold text-white">Databricks & Unity Catalog Integration</div>
            <div className="text-[11px] text-slate-400">
              Switch from Local Parquet mode to Databricks Spark cluster with Unity Catalog paths (<code>main.datatrust</code>).
            </div>
          </div>
          <button
            onClick={() => setDatabricksMode(!databricksMode)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors ${
              databricksMode ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'
            }`}
          >
            {databricksMode ? 'DATABRICKS MODE ACTIVE' : 'LOCAL MODE (DEFAULT)'}
          </button>
        </div>
      </div>

      {/* Quality Rules Table */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <span>Data Quality Rule Thresholds & Enablement</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Rule ID</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Rule Type</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Threshold</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Enabled</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {rules.map((r) => (
                <tr key={r.rule_id} className="hover:bg-slate-800/30">
                  <td className="py-3.5 px-4 font-bold text-white">{r.rule_id}</td>
                  <td className="py-3.5 px-4 uppercase font-sans font-semibold text-slate-300">{r.source}</td>
                  <td className="py-3.5 px-4 text-sky-300 font-sans">{r.rule_type}</td>
                  <td className="py-3.5 px-4 text-slate-300 font-sans">{r.description}</td>
                  <td className="py-3.5 px-4 font-bold text-emerald-400">
                    {r.threshold ? `${(r.threshold * 100).toFixed(0)}%` : '100%'}
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      {r.severity}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <input
                      type="checkbox"
                      checked={r.enabled}
                      onChange={() => {
                        setRules(rules.map((rule) => rule.rule_id === r.rule_id ? { ...rule, enabled: !rule.enabled } : rule));
                      }}
                      className="accent-sky-500 rounded"
                    />
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
