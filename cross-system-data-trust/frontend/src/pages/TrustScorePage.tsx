import React, { useEffect, useState } from 'react';
import { Award, Info, Sliders, ShieldCheck, HelpCircle } from 'lucide-react';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { fetchDashboardSummary } from '../api/client';
import { DashboardSummary, SourceHealth } from '../types';

export const TrustScorePage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [selectedSource, setSelectedSource] = useState<string>('billing');

  useEffect(() => {
    fetchDashboardSummary().then(setSummary);
  }, []);

  const src: SourceHealth | undefined = summary?.sources.find((s) => s.source_system === selectedSource) || summary?.sources[0];

  const radarData = [
    { subject: 'Completeness', score: src?.components?.completeness || 98.5 },
    { subject: 'Consistency', score: src?.components?.consistency || 82.0 },
    { subject: 'Accuracy', score: src?.components?.accuracy || 85.0 },
    { subject: 'Freshness', score: src?.components?.freshness || 100.0 },
    { subject: 'Uniqueness', score: src?.components?.uniqueness || 97.0 },
    { subject: 'Drift Stability', score: src?.components?.drift_stability || 78.0 },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Award className="w-6 h-6 text-sky-400" />
          <span>Explainable Data Trust Scoring Engine</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Transparent 0–100 trust scoring methodology with component weightings and exact reduction justifications.
        </p>
      </div>

      {/* Formula & Weighting Header */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          <span>Configurable Scoring Formula</span>
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 text-center text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Completeness</div>
            <div className="font-bold text-sky-400 text-sm mt-1">20% Weight</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Consistency</div>
            <div className="font-bold text-indigo-400 text-sm mt-1">25% Weight</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Accuracy</div>
            <div className="font-bold text-emerald-400 text-sm mt-1">20% Weight</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Freshness</div>
            <div className="font-bold text-amber-400 text-sm mt-1">15% Weight</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Uniqueness</div>
            <div className="font-bold text-purple-400 text-sm mt-1">10% Weight</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px]">Drift Stability</div>
            <div className="font-bold text-rose-400 text-sm mt-1">10% Weight</div>
          </div>
        </div>
      </div>

      {/* Source Selector & Explainability Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radar Chart Visual */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white uppercase">{selectedSource} Radar</h2>
              <select
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="bg-slate-800 text-xs text-white px-3 py-1 rounded-lg border border-slate-700 focus:outline-none"
              >
                <option value="billing">Billing System</option>
                <option value="analytics">Analytics System</option>
                <option value="crm">CRM System</option>
              </select>
            </div>
            <p className="text-xs text-slate-400 mt-1">Component score polygon visualization</p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" stroke="#94a3b8" fontSize={10} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" fontSize={9} />
                <Radar name="Score" dataKey="score" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Explainability Breakdown */}
        <div className="lg:col-span-2 p-6 rounded-2xl glass-panel space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Info className="w-5 h-5 text-amber-400" />
              <span>Score Explainability Log for {selectedSource.toUpperCase()}</span>
            </h2>
            <div className="text-right">
              <span className="text-2xl font-extrabold font-mono text-white">{src?.overall_score.toFixed(1)}</span>
              <span className="text-xs text-slate-400"> / 100 ({src?.health_status})</span>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            {src?.explanations && src.explanations.length > 0 ? (
              src.explanations.map((exp, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                  <div className="text-xs font-semibold text-amber-300 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    <span>Reason #{idx + 1}</span>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed font-sans pl-4">{exp}</p>
                </div>
              ))
            ) : (
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/30 text-emerald-400 text-xs flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>All checks passed — no score reductions applied to this system.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
