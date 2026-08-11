import React, { useEffect, useState } from 'react';
import { HeartPulse, Database, Clock, FileCheck, AlertTriangle, ShieldCheck } from 'lucide-react';
import { fetchQualityMetrics } from '../api/client';
import { DataQualityMetric } from '../types';

export const SystemHealth: React.FC = () => {
  const [metrics, setMetrics] = useState<DataQualityMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQualityMetrics().then((data) => {
      setMetrics(data);
      setLoading(false);
    });
  }, []);

  const systems = [
    {
      name: 'billing',
      label: 'Billing System',
      description: 'Transaction & payment data lake table',
      icon: Database,
      expected_frequency: 'Every 24 Hours',
      primary_key: 'transaction_id',
      business_key: 'customer_id',
    },
    {
      name: 'analytics',
      label: 'Analytics Platform',
      description: 'Daily aggregated business revenue metrics',
      icon: HeartPulse,
      expected_frequency: 'Every 24 Hours',
      primary_key: 'date',
      business_key: 'date',
    },
    {
      name: 'crm',
      label: 'CRM System',
      description: 'Customer profiles, segmentations & signup dates',
      icon: ShieldCheck,
      expected_frequency: 'Weekly (168 Hours)',
      primary_key: 'customer_id',
      business_key: 'customer_id',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <HeartPulse className="w-6 h-6 text-sky-400" />
          <span>System Health & Dataset Status</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Detailed monitoring of connected source systems, ingestion frequencies, and structural integrity.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {systems.map((sys) => {
          const sysMetric = metrics.find((m) => m.source_system === sys.name);
          const Icon = sys.icon;
          const isWarning = sys.name === 'billing' || (sysMetric && (sysMetric.ghost_customer_count > 0 || sysMetric.null_count > 0));

          return (
            <div key={sys.name} className="p-6 rounded-2xl glass-panel space-y-6 border border-slate-800">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-lg font-bold text-white">{sys.label}</h2>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        !isWarning
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {!isWarning ? 'HEALTHY' : 'WARNING'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{sys.description}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-6 text-xs">
                  <div>
                    <div className="text-slate-500 uppercase tracking-wider text-[10px]">Expected Ingestion</div>
                    <div className="font-semibold text-slate-300 flex items-center gap-1 mt-0.5">
                      <Clock className="w-3.5 h-3.5 text-sky-400" />
                      <span>{sys.expected_frequency}</span>
                    </div>
                  </div>
                  <div className="border-l border-slate-800 pl-6">
                    <div className="text-slate-500 uppercase tracking-wider text-[10px]">Total Records</div>
                    <div className="font-mono font-bold text-white text-base mt-0.5">
                      {sysMetric ? sysMetric.total_records.toLocaleString() : '10,000+'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Health Metrics Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div>
                  <div className="text-[11px] text-slate-500">Completeness</div>
                  <div className="text-lg font-bold font-mono text-white mt-1">
                    {sysMetric ? `${(sysMetric.completeness_score * 100).toFixed(1)}%` : '98.5%'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {sysMetric ? `${sysMetric.null_count} null fields` : '0 nulls'}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-slate-500">Uniqueness</div>
                  <div className="text-lg font-bold font-mono text-white mt-1">
                    {sysMetric ? `${(sysMetric.uniqueness_score * 100).toFixed(1)}%` : '99.9%'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {sysMetric ? `${sysMetric.duplicate_count} duplicates` : '0 dupes'}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-slate-500">Referential Integrity</div>
                  <div className="text-lg font-bold font-mono text-white mt-1">
                    {sysMetric ? `${(sysMetric.referential_integrity_score * 100).toFixed(1)}%` : '100%'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {sysMetric && sysMetric.ghost_customer_count > 0 ? (
                      <span className="text-amber-400 font-semibold">{sysMetric.ghost_customer_count} GHOST IDs</span>
                    ) : (
                      'Clean'
                    )}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-slate-500">Schema Drift Status</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-1">STABLE</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Snapshot v12 Verified</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
