import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Eye, Filter, XCircle, ShieldCheck } from 'lucide-react';
import { fetchAlerts, updateAlertStatus } from '../api/client';
import { Alert } from '../types';

export const AlertCenter: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const loadAlerts = () => {
    fetchAlerts().then(setAlerts);
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleAction = async (alertId: string, newStatus: 'ACKNOWLEDGED' | 'RESOLVED' | 'IGNORED') => {
    await updateAlertStatus(alertId, newStatus);
    loadAlerts();
    if (selectedAlert?.alert_id === alertId) {
      setSelectedAlert(null);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && a.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-rose-500" />
            <span>Enterprise Alert Center</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time alert management with complete audit lifecycle (OPEN → ACKNOWLEDGED → RESOLVED / IGNORED).
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center space-x-3 bg-slate-900 p-2 rounded-xl border border-slate-800 text-xs">
          <div className="flex items-center space-x-1 text-slate-400 pl-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-800 text-slate-200 rounded-lg px-2.5 py-1 border border-slate-700 focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MEDIUM">Medium Only</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-800 text-slate-200 rounded-lg px-2.5 py-1 border border-slate-700 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open Only</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alert Table */}
      <div className="p-6 rounded-2xl glass-panel space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Alert ID</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Issue Type</th>
                <th className="py-3 px-4">Observed vs Expected</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredAlerts.map((alert) => (
                <tr key={alert.id || alert.alert_id} className="hover:bg-slate-800/30">
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      alert.severity === 'CRITICAL' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      alert.severity === 'HIGH' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                    }`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-200 font-bold">{alert.alert_id}</td>
                  <td className="py-3.5 px-4 font-sans uppercase font-bold text-slate-300">{alert.source}</td>
                  <td className="py-3.5 px-4 text-sky-300 font-sans">{alert.issue_type}</td>
                  <td className="py-3.5 px-4 text-slate-300">
                    <span className="text-white font-bold">{alert.observed_value}</span>
                    <span className="text-slate-500"> (exp: {alert.expected_value})</span>
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      alert.status === 'OPEN' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      alert.status === 'ACKNOWLEDGED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}>
                      {alert.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2 font-sans">
                    {alert.status === 'OPEN' && (
                      <button
                        onClick={() => handleAction(alert.alert_id, 'ACKNOWLEDGED')}
                        className="px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-[11px] border border-amber-500/30 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}
                    {alert.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleAction(alert.alert_id, 'RESOLVED')}
                        className="px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-[11px] border border-emerald-500/30 transition-colors"
                      >
                        Resolve
                      </button>
                    )}
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
