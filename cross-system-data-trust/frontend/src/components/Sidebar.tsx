import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  HeartPulse,
  GitCompare,
  CheckCircle2,
  TrendingDown,
  AlertTriangle,
  Award,
  Workflow,
  FileCode2,
  Settings,
  Layers,
  HelpCircle,
} from 'lucide-react';

interface SidebarProps {
  alertCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ alertCount = 5 }) => {
  const navItems = [
    { to: '/', label: 'Executive Dashboard', icon: LayoutDashboard },
    { to: '/system-health', label: 'System Health', icon: HeartPulse },
    { to: '/reconciliation', label: 'Cross-System Reconciliation', icon: GitCompare },
    { to: '/quality', label: 'Data Quality & Quarantine', icon: CheckCircle2 },
    { to: '/drift', label: 'Drift Monitor', icon: TrendingDown },
    { to: '/alerts', label: 'Alert Center', icon: AlertTriangle, badge: alertCount },
    { to: '/trust-score', label: 'Trust Score Breakdown', icon: Award },
    { to: '/pipelines', label: 'Pipeline Monitoring', icon: Workflow },
    { to: '/schemas', label: 'Schema Monitor', icon: FileCode2 },
    { to: '/settings', label: 'Rule Settings & Thresholds', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-3">
            Observability Platform
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all group ${
                      isActive
                        ? 'bg-sky-600/15 text-sky-400 border border-sky-500/20 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4 transition-transform group-hover:scale-110" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 text-[10px] font-bold border border-rose-500/30">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Architecture badge footer */}
      <div className="pt-4 border-t border-slate-800/80 space-y-3">
        <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
            <Layers className="w-4 h-4 text-sky-400" />
            <span>Medallion Lakehouse</span>
          </div>
          <div className="grid grid-cols-3 gap-1 text-[10px] text-center font-mono font-medium">
            <span className="bg-amber-950/60 text-amber-400 border border-amber-800/40 rounded py-0.5">Bronze</span>
            <span className="bg-slate-800 text-slate-300 border border-slate-700 rounded py-0.5">Silver</span>
            <span className="bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 rounded py-0.5">Gold</span>
          </div>
        </div>
        <div className="text-[11px] text-slate-500 text-center font-mono">
          Delta Lake / PySpark Architecture
        </div>
      </div>
    </aside>
  );
};
