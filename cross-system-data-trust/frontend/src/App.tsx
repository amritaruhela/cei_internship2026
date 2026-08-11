import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';

import { ExecutiveDashboard } from './pages/ExecutiveDashboard';
import { SystemHealth } from './pages/SystemHealth';
import { Reconciliation } from './pages/Reconciliation';
import { DataQuality } from './pages/DataQuality';
import { DriftMonitor } from './pages/DriftMonitor';
import { AlertCenter } from './pages/AlertCenter';
import { TrustScorePage } from './pages/TrustScorePage';
import { PipelineRunsPage } from './pages/PipelineRunsPage';
import { SchemaMonitor } from './pages/SchemaMonitor';
import { SettingsPage } from './pages/SettingsPage';
import { fetchDashboardSummary } from './api/client';

export const App: React.FC = () => {
  const [platformScore, setPlatformScore] = useState(84.5);
  const [openAlerts, setOpenAlerts] = useState(5);

  const loadSummary = () => {
    fetchDashboardSummary().then((data) => {
      if (data) {
        setPlatformScore(data.platform_trust_score);
        setOpenAlerts(data.open_alerts);
      }
    });
  };

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
        <Navbar
          platformScore={platformScore}
          openAlertsCount={openAlerts}
          onRefresh={loadSummary}
        />

        <div className="flex flex-1 overflow-hidden">
          <Sidebar alertCount={openAlerts} />

          <main className="flex-1 overflow-y-auto bg-slate-950">
            <Routes>
              <Route path="/" element={<ExecutiveDashboard />} />
              <Route path="/system-health" element={<SystemHealth />} />
              <Route path="/reconciliation" element={<Reconciliation />} />
              <Route path="/quality" element={<DataQuality />} />
              <Route path="/drift" element={<DriftMonitor />} />
              <Route path="/alerts" element={<AlertCenter />} />
              <Route path="/trust-score" element={<TrustScorePage />} />
              <Route path="/pipelines" element={<PipelineRunsPage />} />
              <Route path="/schemas" element={<SchemaMonitor />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
