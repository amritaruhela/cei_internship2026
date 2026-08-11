import React, { useEffect, useState } from 'react';
import { 
  ShieldCheck, 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Workflow, 
  TrendingUp, 
  ArrowUpRight, 
  ArrowDownRight,
  Database,
  Info
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  CartesianGrid 
} from 'recharts';
import { DashboardSummary } from '../types';
import { fetchDashboardSummary } from '../api/client';

export const ExecutiveDashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardSummary().then((data) => {
      setSummary(data);
      setLoading(false);
    });
  }, []);

  if (loading || !summary) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="h-8 bg-slate-800 rounded w-1/4"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-800/60 rounded-2xl border border-slate-800"></div>
          ))}
        </div>
      </div>
    );
  }

  // Mock trend data for charts
  const trustTrend = [
    { date: 'Jun 16', score: 94.2, billing: 95, analytics: 96, crm: 94 },
    { date: 'Jun 18', score: 93.8, billing: 94, analytics: 95, crm: 94 },
    { date: 'Jun 20', score: 92.5, billing: 92, analytics: 94, crm: 93 },
    { date: 'Jun 22', score: 91.0, billing: 89, analytics: 92, crm: 93 },
    { date: 'Jun 24', score: 88.4, billing: 85, analytics: 91, crm: 93 },
    { date: 'Jun 26', score: 86.2, billing: 83, analytics: 90, crm: 92 },
    { date: 'Jun 28', score: 84.5, billing: 82, analytics: 91, crm: 93 },
  ];

  const volumeTrend = [
    { date: 'Jun 20', billing_tx: 420, analytics_rev: 7800 },
    { date: 'Jun 22', billing_tx: 415, analytics_rev: 7650 },
    { date: 'Jun 24', billing_tx: 405, analytics_rev: 7400 },
    { date: 'Jun 26', billing_tx: 380, analytics_rev: 7100 },
    { date: 'Jun 28', billing_tx: 340, analytics_rev: 6800 },
    { date: 'Jun 30', billing_tx: 320, analytics_rev: 6500 },
  ];

  const issuePie = [
    { name: 'Reconciliation', value: 4, color: '#f43f5e' },
    { name: 'Referential Integrity', value: 3, color: '#fbbf24' },
    { name: 'Completeness', value: 3, color: '#38bdf8' },
    { name: 'Volume Drift', value: 2, color: '#a855f7' },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            <span>Executive Observability Overview</span>
            <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Systems Monitored
            </span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time cross-system data consistency, drift detection, and data trust score analytics.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl">
          <Clock className="w-4 h-4 text-sky-400" />
          <span>Last Ingestion Run: <strong>{summary.last_pipeline_run ? new Date(summary.last_pipeline_run).toLocaleTimeString() : 'Just now'}</strong></span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Overall Score */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <ShieldCheck className="w-20 h-20 text-sky-400" />
          </div>
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Overall Data Trust</div>
          <div className="flex items-baseline space-x-2 mt-2">
            <span className="text-3xl font-extrabold font-mono text-white">
              {summary.platform_trust_score.toFixed(1)}
            </span>
            <span className="text-sm font-semibold text-slate-400">/ 100</span>
          </div>
          <div className="mt-3 flex items-center text-xs font-medium text-amber-400">
            <ArrowDownRight className="w-4 h-4 mr-1" />
            <span>-3.2 pts vs 7-day average (Drift Detected)</span>
          </div>
        </div>

        {/* Source Health Status */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden group">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Source Systems Status</div>
          <div className="flex items-baseline space-x-3 mt-2">
            <span className="text-3xl font-extrabold font-mono text-emerald-400">{summary.healthy_sources}</span>
            <span className="text-xs text-slate-400">Healthy</span>
            <span className="text-2xl font-bold font-mono text-amber-400 ml-2">{summary.warning_sources}</span>
            <span className="text-xs text-slate-400">Warning</span>
          </div>
          <div className="mt-3 flex items-center text-xs text-slate-400">
            <Database className="w-3.5 h-3.5 text-sky-400 mr-1.5" />
            <span>Billing, Analytics, CRM Connected</span>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden group">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Active Monitoring Alerts</div>
          <div className="flex items-baseline space-x-3 mt-2">
            <span className="text-3xl font-extrabold font-mono text-rose-400">{summary.open_alerts}</span>
            <span className="text-xs text-rose-400 font-semibold">Open</span>
            <span className="text-xs text-slate-400 font-mono font-medium">({summary.critical_alerts} Critical)</span>
          </div>
          <div className="mt-3 flex items-center text-xs text-rose-400 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
            <span>Action Required in Alert Center</span>
          </div>
        </div>

        {/* Pipeline Success Rate */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden group">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Pipeline Reliability</div>
          <div className="flex items-baseline space-x-2 mt-2">
            <span className="text-3xl font-extrabold font-mono text-sky-400">{summary.pipeline_success_rate}%</span>
            <span className="text-xs text-slate-400">Success Rate</span>
          </div>
          <div className="mt-3 flex items-center text-xs text-emerald-400 font-medium">
            <Workflow className="w-3.5 h-3.5 mr-1.5" />
            <span>Spark / Medallion Jobs Healthy</span>
          </div>
        </div>
      </div>

      {/* Main Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trust Score Trend Over Time */}
        <div className="lg:col-span-2 p-6 rounded-2xl glass-panel space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-sky-400" />
                <span>Historical Data Trust Trend (7 Days)</span>
              </h2>
              <p className="text-xs text-slate-400">Component trust scores computed per ingestion run</p>
            </div>
            <div className="flex items-center space-x-4 text-xs">
              <span className="flex items-center space-x-1.5"><span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span><span className="text-slate-300">Overall</span></span>
              <span className="flex items-center space-x-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span><span className="text-slate-300">Billing</span></span>
              <span className="flex items-center space-x-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span><span className="text-slate-300">Analytics</span></span>
            </div>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trustTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                <YAxis domain={[70, 100]} stroke="#94a3b8" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="score" stroke="#38bdf8" strokeWidth={3} fillOpacity={1} fill="url(#scoreGrad)" />
                <Area type="monotone" dataKey="billing" stroke="#fbbf24" strokeWidth={1.5} strokeDasharray="4 4" fill="none" />
                <Area type="monotone" dataKey="analytics" stroke="#34d399" strokeWidth={1.5} strokeDasharray="4 4" fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Active Issues Distribution */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Issue Categories</span>
            </h2>
            <p className="text-xs text-slate-400">Distribution of active data drift & trust anomalies</p>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={issuePie} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                  {issuePie.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {issuePie.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                <span className="text-slate-300 text-[11px] truncate">{item.name} ({item.value})</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Source Health Cards Row */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          <span>Source System Trust Breakdown</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {summary.sources.map((src) => (
            <div key={src.source_system} className="p-5 rounded-2xl glass-panel space-y-4 border border-slate-800 hover:border-slate-700 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-white uppercase text-sm tracking-wide">{src.source_system}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    src.health_status === 'HEALTHY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    src.health_status === 'WARNING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {src.health_status}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-xl font-extrabold font-mono text-white">{src.overall_score.toFixed(1)}</span>
                  <span className="text-xs text-slate-400">/100</span>
                </div>
              </div>

              {/* Components Mini Bars */}
              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Completeness</span>
                  <span className="font-mono text-slate-200">{src.components?.completeness || src.completeness}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-sky-400 rounded-full" style={{ width: `${src.components?.completeness || src.completeness}%` }}></div>
                </div>

                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Consistency</span>
                  <span className="font-mono text-slate-200">{src.components?.consistency || src.consistency}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-400 rounded-full" style={{ width: `${src.components?.consistency || src.consistency}%` }}></div>
                </div>
              </div>

              {/* Explanations */}
              {src.explanations && src.explanations.length > 0 && (
                <div className="pt-3 border-t border-slate-800/80 space-y-1.5">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Score Explanations</div>
                  {src.explanations.slice(0, 2).map((exp, idx) => (
                    <div key={idx} className="flex items-start space-x-1.5 text-[11px] text-amber-300/90 leading-tight">
                      <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
                      <span>{exp}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
