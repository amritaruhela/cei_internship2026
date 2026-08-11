import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Activity, 
  Play, 
  RefreshCw, 
  Bell, 
  User, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import { triggerPipeline } from '../api/client';

interface NavbarProps {
  platformScore?: number;
  openAlertsCount?: number;
  onRefresh?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  platformScore = 84.5,
  openAlertsCount = 5,
  onRefresh,
}) => {
  const [isTriggering, setIsTriggering] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState('healthy');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleTriggerPipeline = async () => {
    setIsTriggering(true);
    try {
      await triggerPipeline(selectedScenario);
      setToastMessage(`Pipeline triggered with scenario: '${selectedScenario}'`);
      if (onRefresh) setTimeout(onRefresh, 1500);
    } catch (e) {
      setToastMessage('Failed to trigger pipeline');
    } finally {
      setIsTriggering(false);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <ShieldCheck className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg text-white tracking-wide">DataTrust</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 font-mono border border-sky-500/20">
              v1.0 Enterprise
            </span>
          </div>
          <span className="text-xs text-slate-400">Cross-System Data Drift & Observability Platform</span>
        </div>
      </div>

      {/* Global Status & Quick Controls */}
      <div className="flex items-center space-x-4">
        {/* Score indicator */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
          <Activity className="w-4 h-4 text-sky-400" />
          <span className="text-xs text-slate-300 font-medium">Platform Trust:</span>
          <span className={`text-sm font-bold font-mono ${
            platformScore >= 85 ? 'text-emerald-400' : platformScore >= 70 ? 'text-amber-400' : 'text-rose-400'
          }`}>
            {platformScore.toFixed(1)}/100
          </span>
        </div>

        {/* Pipeline Trigger Control */}
        <div className="flex items-center space-x-2 bg-slate-800/60 p-1 rounded-xl border border-slate-700">
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            className="bg-slate-900 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-sky-500"
          >
            <option value="healthy">Scenario: Healthy Baseline</option>
            <option value="missing_records">Scenario: Missing Records (5%)</option>
            <option value="duplicates">Scenario: Duplicate Transactions</option>
            <option value="revenue_mismatch">Scenario: Revenue Mismatch (7%)</option>
            <option value="schema_drift">Scenario: Schema Drift</option>
            <option value="volume_drop">Scenario: Volume Drop (40%)</option>
            <option value="distribution_drift">Scenario: Distribution Drift (PSI)</option>
            <option value="mixed">Scenario: Mixed Anomalies</option>
          </select>

          <button
            onClick={handleTriggerPipeline}
            disabled={isTriggering}
            className="flex items-center space-x-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 active:bg-sky-700 px-3 py-1.5 rounded-lg transition-colors shadow-md shadow-sky-600/20 disabled:opacity-50"
          >
            {isTriggering ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>Run Pipeline</span>
          </button>
        </div>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          title="Refresh Data"
          className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors border border-slate-700"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <div className="relative">
          <button className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors border border-slate-700">
            <Bell className="w-4 h-4" />
            {openAlertsCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                {openAlertsCount}
              </span>
            )}
          </button>
        </div>

        {/* Profile */}
        <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-white">Lead Data Architect</div>
            <div className="text-[10px] text-slate-400 font-mono">ADMIN</div>
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center space-x-2 px-4 py-3 rounded-xl bg-slate-900 border border-sky-500/30 shadow-2xl text-slate-100 text-sm animate-bounce">
          <CheckCircle2 className="w-5 h-5 text-sky-400" />
          <span>{toastMessage}</span>
        </div>
      )}
    </header>
  );
};
