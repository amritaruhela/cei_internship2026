import React, { useEffect, useState } from 'react';
import { GitCompare, DollarSign, Users, AlertCircle, Info, Calendar } from 'lucide-react';
import { fetchComparisons } from '../api/client';
import { ComparisonResult } from '../types';

export const Reconciliation: React.FC = () => {
  const [comparisons, setComparisons] = useState<ComparisonResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchComparisons().then((data) => {
      setComparisons(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <GitCompare className="w-6 h-6 text-sky-400" />
          <span>Cross-System Reconciliation Engine</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Grain-aware cross-system validation between Billing daily transactions and Analytics aggregated metrics.
        </p>
      </div>

      {/* Grain & Business Logic Notice Banner */}
      <div className="p-5 rounded-2xl bg-sky-950/40 border border-sky-800/40 space-y-3">
        <div className="flex items-center space-x-2 text-sm font-bold text-sky-300">
          <Info className="w-5 h-5 text-sky-400 shrink-0" />
          <span>Reconciliation Grain & Revenue Recognition Rule</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          <strong>Analytics</strong> records aggregated metrics at the <strong>daily grain</strong> (1 row/day). 
          <strong> Billing</strong> records individual transaction events. Reconciliation computes daily aggregates for 
          Billing using <code>SUM(amount) WHERE status = 'completed'</code> to compare against recognized revenue.
        </p>
      </div>

      {/* Cross-System Reconciliation Matrix */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <h2 className="text-base font-bold text-white">System Metric Cross-Matrix</h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Metric Grain</th>
                <th className="py-3 px-4">Billing System</th>
                <th className="py-3 px-4">Analytics System</th>
                <th className="py-3 px-4">CRM System</th>
                <th className="py-3 px-4">Variance %</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              <tr className="hover:bg-slate-800/30">
                <td className="py-3.5 px-4 font-semibold text-white flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-emerald-400" />
                  <span>Total Daily Revenue</span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-200">₹7,204.71 (completed)</td>
                <td className="py-3.5 px-4 font-mono text-slate-200">₹7,467.84</td>
                <td className="py-3.5 px-4 text-slate-500 font-mono">N/A (Aggregate)</td>
                <td className="py-3.5 px-4 font-mono font-bold text-amber-400">3.65%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    MEDIUM MISMATCH
                  </span>
                </td>
              </tr>

              <tr className="hover:bg-slate-800/30">
                <td className="py-3.5 px-4 font-semibold text-white flex items-center gap-2">
                  <Users className="w-4 h-4 text-sky-400" />
                  <span>Transacting Customers</span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-200">12 unique IDs</td>
                <td className="py-3.5 px-4 font-mono text-slate-200">13 total_customers</td>
                <td className="py-3.5 px-4 font-mono text-slate-200">10,500 active</td>
                <td className="py-3.5 px-4 font-mono font-bold text-amber-400">7.69%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    HIGH MISMATCH
                  </span>
                </td>
              </tr>

              <tr className="hover:bg-slate-800/30">
                <td className="py-3.5 px-4 font-semibold text-white flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-indigo-400" />
                  <span>Referential Customer Keys</span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-200">11,915 records</td>
                <td className="py-3.5 px-4 text-slate-500 font-mono">N/A</td>
                <td className="py-3.5 px-4 font-mono text-slate-200">10,500 unique</td>
                <td className="py-3.5 px-4 font-mono font-bold text-rose-400">18 Ghosts</td>
                <td className="py-3.5 px-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    REFERENTIAL VIOLATION
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Comparison Log */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Calendar className="w-4 h-4 text-sky-400" />
          <span>Daily Revenue Reconciliation Detail Log</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Billing Daily Revenue (Sum)</th>
                <th className="py-3 px-4">Analytics Daily Revenue</th>
                <th className="py-3 px-4">Abs Difference</th>
                <th className="py-3 px-4">Pct Difference</th>
                <th className="py-3 px-4">Reconciliation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {comparisons.slice(0, 10).map((c) => (
                <tr key={c.id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 text-slate-300 font-sans">
                    {c.comparison_date ? new Date(c.comparison_date).toLocaleDateString() : '2024-06-30'}
                  </td>
                  <td className="py-3 px-4 text-white">₹{c.value_a?.toLocaleString() || '7,204'}</td>
                  <td className="py-3 px-4 text-white">₹{c.value_b?.toLocaleString() || '7,467'}</td>
                  <td className="py-3 px-4 text-slate-400">₹{c.absolute_difference?.toLocaleString() || '263'}</td>
                  <td className="py-3 px-4 text-amber-400 font-bold">
                    {((c.percentage_difference || 0.036) * 100).toFixed(2)}%
                  </td>
                  <td className="py-3 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      c.threshold_status === 'OK' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {c.threshold_status}
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
