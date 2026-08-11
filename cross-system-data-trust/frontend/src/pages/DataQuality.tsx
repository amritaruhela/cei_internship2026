import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertOctagon, ShieldAlert, FileText, Database } from 'lucide-react';
import { fetchQualityMetrics } from '../api/client';
import { DataQualityMetric } from '../types';

export const DataQuality: React.FC = () => {
  const [metrics, setMetrics] = useState<DataQualityMetric[]>([]);
  const [activeTab, setActiveTab] = useState<'metrics' | 'quarantine'>('metrics');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQualityMetrics().then((m) => {
      setMetrics(m);
      setLoading(false);
    });
  }, []);

  const quarantineMock = [
    {
      run_id: 'run-8a3b1c',
      source_system: 'billing',
      record_id: 'TXN0003472',
      reason: 'Duplicate transaction_id or GHOST customer_id (referential integrity violation)',
      rule_id: 'DQ-B003',
      detected_at: '2024-06-30T10:14:02Z',
      raw_record: JSON.stringify({ transaction_id: 'TXN0003472', customer_id: 'GHOST00032', amount: 236.36, status: 'completed' }),
    },
    {
      run_id: 'run-8a3b1c',
      source_system: 'analytics',
      record_id: '2022-01-09',
      reason: 'NULL total_revenue — completeness violation',
      rule_id: 'DQ-A001',
      detected_at: '2024-06-30T10:14:03Z',
      raw_record: JSON.stringify({ date: '2022-01-09', total_customers: 3, total_revenue: null, avg_transaction: 106.39 }),
    },
    {
      run_id: 'run-8a3b1c',
      source_system: 'billing',
      record_id: 'TXN0002321',
      reason: 'GHOST customer_id (referential integrity violation)',
      rule_id: 'DQ-B003',
      detected_at: '2024-06-30T10:14:04Z',
      raw_record: JSON.stringify({ transaction_id: 'TXN0002321', customer_id: 'GHOST00262', amount: 2479.75, status: 'completed' }),
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-sky-400" />
            <span>Data Quality & Quarantine Monitor</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Standardized data validation, null checking, uniqueness validation, and non-destructive quarantine logging.
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex items-center space-x-1 p-1 rounded-xl bg-slate-900 border border-slate-800 self-start">
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'metrics' ? 'bg-sky-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            Quality Metrics
          </button>
          <button
            onClick={() => setActiveTab('quarantine')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 ${
              activeTab === 'quarantine' ? 'bg-sky-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Quarantine Log</span>
            <span className="px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px]">3</span>
          </button>
        </div>
      </div>

      {activeTab === 'metrics' ? (
        <div className="space-y-6">
          {/* Rule Category Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="p-4 rounded-xl glass-panel space-y-1 border border-slate-800">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Completeness</div>
              <div className="text-2xl font-extrabold font-mono text-white">98.2%</div>
              <div className="text-[10px] text-slate-500">17 null revenues in Analytics</div>
            </div>

            <div className="p-4 rounded-xl glass-panel space-y-1 border border-slate-800">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Uniqueness</div>
              <div className="text-2xl font-extrabold font-mono text-white">99.9%</div>
              <div className="text-[10px] text-slate-500">0 duplicate transaction_ids</div>
            </div>

            <div className="p-4 rounded-xl glass-panel space-y-1 border border-slate-800">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Validity</div>
              <div className="text-2xl font-extrabold font-mono text-white">99.5%</div>
              <div className="text-[10px] text-slate-500">Statuses & emails validated</div>
            </div>

            <div className="p-4 rounded-xl glass-panel space-y-1 border border-slate-800">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Ref Integrity</div>
              <div className="text-2xl font-extrabold font-mono text-amber-400">98.5%</div>
              <div className="text-[10px] text-amber-400/90 font-medium">18 GHOST customer IDs</div>
            </div>

            <div className="p-4 rounded-xl glass-panel space-y-1 border border-slate-800">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Freshness</div>
              <div className="text-2xl font-extrabold font-mono text-emerald-400">100%</div>
              <div className="text-[10px] text-emerald-400 font-medium">All pipelines on schedule</div>
            </div>
          </div>

          {/* Source Metrics Table */}
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-sky-400" />
              <span>Data Quality Check Matrix by Source System</span>
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                    <th className="py-3 px-4">Source System</th>
                    <th className="py-3 px-4">Total Records</th>
                    <th className="py-3 px-4">Completeness</th>
                    <th className="py-3 px-4">Uniqueness</th>
                    <th className="py-3 px-4">Validity</th>
                    <th className="py-3 px-4">Ref Integrity</th>
                    <th className="py-3 px-4">Quarantined</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {metrics.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-sans font-bold text-white uppercase">{m.source_system}</td>
                      <td className="py-3 px-4 text-slate-300">{m.total_records.toLocaleString()}</td>
                      <td className="py-3 px-4 text-slate-200">{(m.completeness_score * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-slate-200">{(m.uniqueness_score * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-slate-200">{(m.validity_score * 100).toFixed(1)}%</td>
                      <td className={`py-3 px-4 font-bold ${m.ghost_customer_count > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {(m.referential_integrity_score * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 font-sans">
                          {m.ghost_customer_count + m.null_revenue_count} records
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Quarantine Audit Log View */
        <div className="p-6 rounded-2xl glass-panel space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
                <span>silver.quarantine_records Audit Trail</span>
              </h2>
              <p className="text-xs text-slate-400">
                Invalid records isolated during Silver transformation to prevent downstream contamination.
              </p>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Non-Destructive Quarantine Engine
            </span>
          </div>

          <div className="space-y-4 pt-2">
            {quarantineMock.map((q, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="flex items-center space-x-3">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono font-bold">
                      {q.source_system.toUpperCase()}
                    </span>
                    <span className="font-mono text-white font-semibold">Record ID: {q.record_id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Rule: {q.rule_id}
                    </span>
                  </div>
                  <span className="text-slate-500 text-[11px] font-mono">{q.detected_at}</span>
                </div>

                <div className="text-xs text-amber-300/90 font-medium flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Quarantine Reason: {q.reason}</span>
                </div>

                {/* Raw Record Code View */}
                <div className="p-3 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 overflow-x-auto border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Raw Record Payload</div>
                  <code>{q.raw_record}</code>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
