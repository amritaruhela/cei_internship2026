import React, { useState } from 'react';
import { FileCode2, History, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';

export const SchemaMonitor: React.FC = () => {
  const [selectedSource, setSelectedSource] = useState('billing');

  const schemas = {
    billing: [
      { name: 'transaction_id', type: 'string', nullable: false, pk: true, description: 'Primary key (TXN0000000 format)' },
      { name: 'customer_id', type: 'string', nullable: false, pk: false, description: 'Foreign key to CRM.customer_id (GHOST IDs flag violation)' },
      { name: 'amount', type: 'double', nullable: true, pk: false, description: 'Transaction amount in INR/USD' },
      { name: 'transaction_date', type: 'date', nullable: false, pk: false, description: 'Transaction event date (YYYY-MM-DD)' },
      { name: 'status', type: 'string', nullable: false, pk: false, description: 'enum: completed, pending, failed, refunded' },
      { name: '_is_recognized_revenue', type: 'boolean', nullable: false, pk: false, description: 'Silver metadata: status == completed' },
      { name: 'discount_code', type: 'string', nullable: true, pk: false, description: 'DRIFT ADDITION: Newly detected column (Run #4e0616)' },
    ],
    analytics: [
      { name: 'date', type: 'date', nullable: false, pk: true, description: 'Primary key daily grain (YYYY-MM-DD)' },
      { name: 'total_customers', type: 'int64', nullable: true, pk: false, description: 'Daily count of transacting customers' },
      { name: 'total_revenue', type: 'double', nullable: true, pk: false, description: 'Daily aggregate revenue (Contains 17 null values)' },
      { name: 'avg_transaction', type: 'double', nullable: true, pk: false, description: 'Average transaction value per day' },
    ],
    crm: [
      { name: 'customer_id', type: 'string', nullable: false, pk: true, description: 'Primary key (CRM000000 format)' },
      { name: 'customer_name', type: 'string', nullable: false, pk: false, description: 'Customer full name' },
      { name: 'email', type: 'string', nullable: true, pk: false, description: 'Customer email address (3% null rate)' },
      { name: 'signup_date', type: 'date', nullable: false, pk: false, description: 'Account creation date' },
      { name: 'customer_status', type: 'string', nullable: false, pk: false, description: 'ACTIVE, INACTIVE, CHURNED, SUSPENDED' },
      { name: 'region', type: 'string', nullable: false, pk: false, description: 'Geographic region' },
      { name: 'segment', type: 'string', nullable: false, pk: false, description: 'Enterprise, SMB, Startup, Individual' },
    ],
  };

  const auditHistory = [
    {
      run_id: '4e0616a1',
      source: 'billing',
      change_type: 'NEW_COLUMN',
      column: 'discount_code',
      details: 'Added column discount_code (type: string)',
      timestamp: '2024-06-30T10:14:00Z',
    },
    {
      run_id: '1a90c2ef',
      source: 'analytics',
      change_type: 'TYPE_MODIFICATION',
      column: 'total_customers',
      details: 'Type changed from int32 to int64',
      timestamp: '2024-06-25T14:22:00Z',
    },
  ];

  const currentCols = schemas[selectedSource as keyof typeof schemas] || [];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <FileCode2 className="w-6 h-6 text-sky-400" />
          <span>Schema Evolution & Version Monitor</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Automated structural schema snapshotting across Delta Lake tables to detect type changes, additions, and deletions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Schema Table Inspector */}
        <div className="lg:col-span-2 p-6 rounded-2xl glass-panel space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white uppercase">{selectedSource} Table Schema (Snapshot v12)</h2>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="bg-slate-800 text-xs text-white px-3 py-1 rounded-lg border border-slate-700 focus:outline-none"
            >
              <option value="billing">billing_dataset (Delta)</option>
              <option value="analytics">analytics_dataset (Delta)</option>
              <option value="crm">crm_dataset (Delta)</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                  <th className="py-3 px-4">Column Name</th>
                  <th className="py-3 px-4">Data Type</th>
                  <th className="py-3 px-4">Nullable</th>
                  <th className="py-3 px-4">Key</th>
                  <th className="py-3 px-4">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {currentCols.map((c) => (
                  <tr key={c.name} className={`hover:bg-slate-800/30 ${c.name === 'discount_code' ? 'bg-amber-500/10' : ''}`}>
                    <td className="py-3.5 px-4 font-bold text-white font-sans flex items-center gap-2">
                      <span>{c.name}</span>
                      {c.name === 'discount_code' && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          NEW
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-sky-300">{c.type}</td>
                    <td className="py-3.5 px-4 text-slate-400">{c.nullable ? 'YES' : 'NO'}</td>
                    <td className="py-3.5 px-4 text-slate-400">{c.pk ? 'PRIMARY' : '-'}</td>
                    <td className="py-3.5 px-4 text-slate-400 font-sans">{c.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Schema Change Audit History */}
        <div className="p-6 rounded-2xl glass-panel space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <History className="w-4 h-4 text-sky-400" />
            <span>Schema Change Audit Log</span>
          </h2>

          <div className="space-y-3">
            {auditHistory.map((item, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white uppercase">{item.source}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20">
                    {item.change_type}
                  </span>
                </div>
                <p className="text-xs text-slate-300 font-sans">{item.details}</p>
                <div className="text-[10px] text-slate-500 font-mono text-right">{item.timestamp}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
